from __future__ import annotations

import re
import socket
import ssl
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import pstdev
from typing import Callable, List, Optional
from urllib.parse import urlsplit


DEFAULT_TARGETS = [
    "example.com",
    "cloudflare.com",
    "wikipedia.org",
    "github.com",
    "python.org",
]


@dataclass
class TargetSpec:
    original: str
    scheme: str
    host: str
    port: int
    path: str

    @property
    def host_header(self) -> str:
        default_port = 443 if self.scheme == "https" else 80
        if self.port == default_port:
            return self.host
        return f"{self.host}:{self.port}"


@dataclass
class PingResult:
    min_ms: Optional[float]
    avg_ms: Optional[float]
    max_ms: Optional[float]
    jitter_ms: Optional[float]
    packet_loss_percent: Optional[float]
    raw: str


@dataclass
class TracerouteResult:
    hop_count: int
    raw: str


@dataclass
class MeasurementResult:
    target: str
    host: str
    scheme: str
    dns_ms: Optional[float]
    tcp_ms: Optional[float]
    http_ms: Optional[float]
    ping_avg_ms: Optional[float]
    packet_loss_percent: Optional[float]
    hop_count: Optional[int]
    http_status: Optional[int]
    traceroute_raw: str
    errors: List[str]
    ping_min_ms: Optional[float] = None
    ping_max_ms: Optional[float] = None
    tls_ms: Optional[float] = None
    ping_jitter_ms: Optional[float] = None
    success_rate_percent: Optional[float] = None
    error_types: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[float] = None
    run_count: int = 1
    dns_min_ms: Optional[float] = None
    dns_max_ms: Optional[float] = None
    tcp_min_ms: Optional[float] = None
    tcp_max_ms: Optional[float] = None
    http_min_ms: Optional[float] = None
    http_max_ms: Optional[float] = None
    ping_avg_min_ms: Optional[float] = None
    ping_avg_max_ms: Optional[float] = None
    ping_stdev_ms: Optional[float] = None
    visible_latency_score_ms: Optional[float] = None
    resolved_addresses: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

        if self.run_count < 1:
            raise ValueError("run_count must be at least 1")

        if not self.error_types:
            self.error_types = classify_error_types(self.errors)

        if self.run_count == 1:
            self.dns_min_ms = self.dns_ms if self.dns_min_ms is None else self.dns_min_ms
            self.dns_max_ms = self.dns_ms if self.dns_max_ms is None else self.dns_max_ms
            self.tcp_min_ms = self.tcp_ms if self.tcp_min_ms is None else self.tcp_min_ms
            self.tcp_max_ms = self.tcp_ms if self.tcp_max_ms is None else self.tcp_max_ms
            self.http_min_ms = self.http_ms if self.http_min_ms is None else self.http_min_ms
            self.http_max_ms = self.http_ms if self.http_max_ms is None else self.http_max_ms
            self.ping_avg_min_ms = self.ping_avg_ms if self.ping_avg_min_ms is None else self.ping_avg_min_ms
            self.ping_avg_max_ms = self.ping_avg_ms if self.ping_avg_max_ms is None else self.ping_avg_max_ms

        if self.visible_latency_score_ms is None:
            self.visible_latency_score_ms = _visible_latency_score_ms(
                self.dns_ms,
                self.tcp_ms,
                self.tls_ms,
                self.http_ms,
                self.ping_avg_ms,
            )

        if self.success_rate_percent is None:
            self.success_rate_percent = _success_rate_percent(self)

    def to_dict(self) -> dict:
        return asdict(self)

    def all_core_metrics_failed(self) -> bool:
        return all(
            value is None
            for value in (
                self.dns_ms,
                self.tcp_ms,
                self.http_ms,
                self.ping_avg_ms,
                self.hop_count,
            )
        )

    @property
    def error_text(self) -> str:
        return "; ".join(self.errors)


def normalize_target(value: str) -> TargetSpec:
    raw = value.strip()
    if not raw:
        raise ValueError("target cannot be empty")

    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError(f"target has no hostname: {value}")

    default_port = 443 if parsed.scheme == "https" else 80
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    return TargetSpec(
        original=raw,
        scheme=parsed.scheme,
        host=parsed.hostname,
        port=parsed.port or default_port,
        path=path,
    )


def parse_ping_output(output: str) -> PingResult:
    loss = None
    min_ms = None
    avg = None
    max_ms = None
    jitter_ms = None

    loss_match = re.search(r"([\d.]+)%\s*packet loss", output)
    if loss_match:
        loss = float(loss_match.group(1))

    rtt_match = re.search(
        r"(?:round-trip|rtt) min/avg/max/(?:stddev|mdev) = "
        r"([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms",
        output,
    )
    if rtt_match:
        min_ms = float(rtt_match.group(1))
        avg = float(rtt_match.group(2))
        max_ms = float(rtt_match.group(3))
        jitter_ms = float(rtt_match.group(4))

    return PingResult(
        min_ms=min_ms,
        avg_ms=avg,
        max_ms=max_ms,
        jitter_ms=jitter_ms,
        packet_loss_percent=loss,
        raw=output,
    )


def parse_traceroute_output(output: str) -> TracerouteResult:
    hop_numbers = []
    for line in output.splitlines():
        match = re.match(r"^\s*(\d+)\s+", line)
        if match:
            hop_numbers.append(int(match.group(1)))
    return TracerouteResult(hop_count=max(hop_numbers, default=0), raw=output)


def measure_target(
    value: str,
    timeout: float = 5.0,
    ping_count: int = 3,
    max_hops: int = 20,
    trace_wait: float = 1.0,
    trace_timeout: Optional[float] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> MeasurementResult:
    started_at = _utc_now()
    start_clock = time.perf_counter()
    errors: List[str] = []
    target = normalize_target(value)

    def emit(stage: str, status: str, **payload: object) -> None:
        if progress_callback is not None:
            progress_callback(
                {
                    "stage": stage,
                    "status": status,
                    "target": target.original,
                    "host": target.host,
                    "timestamp": _utc_now(),
                    **payload,
                }
            )

    dns_ms = None
    tcp_ms = None
    tls_ms = None
    http_ms = None
    http_status = None
    ping_min_ms = None
    ping_avg_ms = None
    ping_max_ms = None
    ping_jitter_ms = None
    packet_loss_percent = None
    hop_count = None
    traceroute_raw = ""
    resolved_addresses: List[str] = []

    try:
        emit("dns", "started", operation=f"socket.getaddrinfo({target.host})")
        dns_ms, resolved_addresses = _measure_dns_details(target.host)
        emit(
            "dns",
            "done",
            duration_ms=_round_ms(dns_ms),
            result=f"{_round_ms(dns_ms)} ms, {len(resolved_addresses)} address(es)",
            addresses=resolved_addresses,
        )
    except Exception as exc:
        message = f"DNS failed: {exc}"
        errors.append(message)
        emit("dns", "error", error=message)

    try:
        emit("tcp", "started", operation=f"socket.create_connection({target.host}:{target.port})")
        tcp_ms = _measure_tcp_ms(target, timeout)
        emit("tcp", "done", duration_ms=_round_ms(tcp_ms), result=f"{_round_ms(tcp_ms)} ms")
    except Exception as exc:
        message = f"TCP failed: {exc}"
        errors.append(message)
        emit("tcp", "error", error=message)

    try:
        tls_ms, http_ms, http_status = _measure_http_ms(target, timeout, emit)
    except Exception as exc:
        label = "TLS/HTTP" if target.scheme == "https" else "HTTP"
        message = f"{label} failed: {exc}"
        errors.append(message)
        emit("http", "error", error=message)

    try:
        emit("ping", "started", operation=f"ping -c {ping_count} {target.host}")
        ping = _run_ping(target.host, ping_count)
        ping_min_ms = ping.min_ms
        ping_avg_ms = ping.avg_ms
        ping_max_ms = ping.max_ms
        ping_jitter_ms = ping.jitter_ms
        packet_loss_percent = ping.packet_loss_percent
        emit(
            "ping",
            "done",
            duration_ms=_round_ms(ping_avg_ms),
            result=f"avg {_round_ms(ping_avg_ms)} ms, loss {_round_ms(packet_loss_percent)}%",
        )
        if (
            ping.min_ms is None
            and ping.avg_ms is None
            and ping.max_ms is None
            and ping.packet_loss_percent is None
        ):
            message = "Ping failed: output could not be parsed"
            errors.append(message)
            emit("ping", "error", error=message)
    except Exception as exc:
        message = f"Ping failed: {exc}"
        errors.append(message)
        emit("ping", "error", error=message)

    try:
        emit(
            "trace",
            "started",
            operation=f"traceroute -m {max_hops} -w {_format_seconds(trace_wait)} {target.host}",
        )
        trace = _run_traceroute(target.host, max_hops, trace_wait, trace_timeout)
        traceroute_raw = trace.raw
        hop_count = trace.hop_count
        emit("trace", "done", result=f"{hop_count} visible hops")
        if trace.hop_count == 0:
            message = "Traceroute failed: no hops parsed"
            errors.append(message)
            emit("trace", "error", error=message)
    except Exception as exc:
        message = f"Traceroute failed: {exc}"
        errors.append(message)
        emit("trace", "error", error=message)

    finished_at = _utc_now()
    return MeasurementResult(
        target=target.original,
        host=target.host,
        scheme=target.scheme,
        dns_ms=_round_ms(dns_ms),
        tcp_ms=_round_ms(tcp_ms),
        tls_ms=_round_ms(tls_ms),
        http_ms=_round_ms(http_ms),
        ping_min_ms=_round_ms(ping_min_ms),
        ping_avg_ms=_round_ms(ping_avg_ms),
        ping_max_ms=_round_ms(ping_max_ms),
        ping_jitter_ms=_round_ms(ping_jitter_ms),
        packet_loss_percent=_round_ms(packet_loss_percent),
        hop_count=hop_count,
        http_status=http_status,
        traceroute_raw=traceroute_raw,
        errors=errors,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=_round_ms((time.perf_counter() - start_clock) * 1000),
        resolved_addresses=resolved_addresses,
    )


def aggregate_measurement_runs(runs: List[MeasurementResult]) -> MeasurementResult:
    if not runs:
        raise ValueError("cannot aggregate an empty run list")

    first = runs[0]
    for result in runs:
        if result.target != first.target:
            raise ValueError("cannot aggregate results from different targets")
        if result.host != first.host or result.scheme != first.scheme:
            raise ValueError("cannot aggregate results with different host or scheme")

    dns_values = _known_float_values([result.dns_ms for result in runs])
    tcp_values = _known_float_values([result.tcp_ms for result in runs])
    tls_values = _known_float_values([result.tls_ms for result in runs])
    http_values = _known_float_values([result.http_ms for result in runs])
    ping_min_values = _known_float_values([result.ping_min_ms for result in runs])
    ping_avg_values = _known_float_values([result.ping_avg_ms for result in runs])
    ping_max_values = _known_float_values([result.ping_max_ms for result in runs])
    ping_jitter_values = _known_float_values([result.ping_jitter_ms for result in runs])
    loss_values = _known_float_values([result.packet_loss_percent for result in runs])
    success_values = [_success_rate_percent(result) for result in runs]
    duration_values = _known_float_values([result.duration_ms for result in runs])
    hop_values = [result.hop_count for result in runs if result.hop_count is not None]

    dns_ms = _mean_ms(dns_values)
    tcp_ms = _mean_ms(tcp_values)
    tls_ms = _mean_ms(tls_values)
    http_ms = _mean_ms(http_values)
    ping_avg_ms = _mean_ms(ping_avg_values)
    errors = _combined_errors(runs)

    return MeasurementResult(
        target=first.target,
        host=first.host,
        scheme=first.scheme,
        dns_ms=dns_ms,
        tcp_ms=tcp_ms,
        tls_ms=tls_ms,
        http_ms=http_ms,
        ping_min_ms=_min_ms(ping_min_values),
        ping_avg_ms=ping_avg_ms,
        ping_max_ms=_max_ms(ping_max_values),
        ping_jitter_ms=_mean_ms(ping_jitter_values),
        packet_loss_percent=_mean_ms(loss_values),
        hop_count=_mean_hop_count(hop_values),
        http_status=_last_known([result.http_status for result in runs]),
        traceroute_raw=_combined_traceroute_raw(runs),
        errors=errors,
        error_types=classify_error_types(errors),
        success_rate_percent=_round_percent(sum(success_values) / len(success_values)),
        started_at=first.started_at,
        finished_at=_last_known_text([result.finished_at for result in runs]),
        duration_ms=_mean_ms(duration_values),
        run_count=len(runs),
        dns_min_ms=_min_ms(dns_values),
        dns_max_ms=_max_ms(dns_values),
        tcp_min_ms=_min_ms(tcp_values),
        tcp_max_ms=_max_ms(tcp_values),
        http_min_ms=_min_ms(http_values),
        http_max_ms=_max_ms(http_values),
        ping_avg_min_ms=_min_ms(ping_avg_values),
        ping_avg_max_ms=_max_ms(ping_avg_values),
        ping_stdev_ms=_stdev_ms(ping_avg_values),
        visible_latency_score_ms=_visible_latency_score_ms(
            dns_ms,
            tcp_ms,
            tls_ms,
            http_ms,
            ping_avg_ms,
        ),
        resolved_addresses=list(first.resolved_addresses),
    )


def mock_measurements(targets: List[str]) -> List[MeasurementResult]:
    results = []
    for index, target_value in enumerate(targets):
        target = normalize_target(target_value)
        dns_ms = 8.0 + index * 4.5
        tcp_ms = 18.0 + index * 8.0
        http_ms = 35.0 + index * 18.0
        ping_avg_ms = 10.0 + index * 7.0
        ping_min_ms = ping_avg_ms - 1.0
        ping_max_ms = ping_avg_ms + 1.0
        hop_count = 4 + index
        traceroute_raw = "\n".join(
            [
                f"traceroute to {target.host}, 20 hops max",
                " 1  router.local (192.168.1.1)  1.0 ms  1.1 ms  1.0 ms",
                f" 2  isp-gateway ({index + 10}.0.0.1)  8.0 ms  8.2 ms  8.1 ms",
                f" {hop_count}  {target.host}  {ping_avg_ms:.1f} ms  {ping_avg_ms + 0.2:.1f} ms",
            ]
        )
        results.append(
            MeasurementResult(
                target=target.original,
                host=target.host,
                scheme=target.scheme,
                dns_ms=dns_ms,
                tcp_ms=tcp_ms,
                tls_ms=6.0 + index * 2.0,
                http_ms=http_ms,
                ping_min_ms=ping_min_ms,
                ping_avg_ms=ping_avg_ms,
                ping_max_ms=ping_max_ms,
                ping_jitter_ms=0.5 + index * 0.1,
                packet_loss_percent=0.0,
                hop_count=hop_count,
                http_status=200,
                traceroute_raw=traceroute_raw,
                errors=[],
                started_at=_utc_now(),
                finished_at=_utc_now(),
                duration_ms=1.0,
                resolved_addresses=[f"{index + 10}.0.0.1"],
            )
        )
    return results


def _measure_dns_details(host: str) -> tuple[float, List[str]]:
    start = time.perf_counter()
    infos = socket.getaddrinfo(host, None)
    elapsed = (time.perf_counter() - start) * 1000
    addresses = sorted({item[4][0] for item in infos})
    return elapsed, addresses


def _measure_dns_ms(host: str) -> float:
    elapsed, _addresses = _measure_dns_details(host)
    return elapsed


def _measure_tcp_ms(target: TargetSpec, timeout: float) -> float:
    start = time.perf_counter()
    sock = socket.create_connection((target.host, target.port), timeout=timeout)
    sock.close()
    return (time.perf_counter() - start) * 1000


def _measure_http_ms(
    target: TargetSpec,
    timeout: float,
    progress_callback: Optional[Callable[..., None]] = None,
) -> tuple[Optional[float], float, Optional[int]]:
    raw_sock = socket.create_connection((target.host, target.port), timeout=timeout)
    sock = raw_sock
    tls_ms = None
    try:
        if target.scheme == "https":
            if progress_callback is not None:
                progress_callback("tls", "started", operation=f"ssl.wrap_socket(server_hostname={target.host})")
            context = ssl.create_default_context()
            tls_start = time.perf_counter()
            sock = context.wrap_socket(raw_sock, server_hostname=target.host)
            tls_ms = (time.perf_counter() - tls_start) * 1000
            if progress_callback is not None:
                progress_callback("tls", "done", duration_ms=_round_ms(tls_ms), result=f"{_round_ms(tls_ms)} ms")

        if progress_callback is not None:
            progress_callback("http", "started", operation=f"GET {target.path} HTTP/1.1")
        start = time.perf_counter()
        request = (
            f"GET {target.path} HTTP/1.1\r\n"
            f"Host: {target.host_header}\r\n"
            "User-Agent: PacketScope/0.1\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = sock.recv(4096)
        elapsed = (time.perf_counter() - start) * 1000
        status = _parse_http_status(response)
        if progress_callback is not None:
            progress_callback("http", "done", duration_ms=_round_ms(elapsed), result=f"HTTP {status}")
        return tls_ms, elapsed, status
    finally:
        sock.close()


def _parse_http_status(response: bytes) -> Optional[int]:
    first_line = response.splitlines()[0].decode("iso-8859-1", errors="replace")
    match = re.match(r"HTTP/\d(?:\.\d)?\s+(\d{3})", first_line)
    if not match:
        return None
    return int(match.group(1))


def _run_ping(host: str, count: int) -> PingResult:
    completed = subprocess.run(
        ["ping", "-c", str(count), host],
        text=True,
        capture_output=True,
        timeout=max(5, count * 3),
        check=False,
    )
    output = completed.stdout + completed.stderr
    return parse_ping_output(output)


def _run_traceroute(
    host: str,
    max_hops: int,
    trace_wait: float = 1.0,
    trace_timeout: Optional[float] = None,
) -> TracerouteResult:
    timeout = trace_timeout
    if timeout is None:
        timeout = max_hops * trace_wait + 5
    completed = subprocess.run(
        ["traceroute", "-m", str(max_hops), "-w", _format_seconds(trace_wait), host],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output = completed.stdout + completed.stderr
    return parse_traceroute_output(output)


def _round_ms(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 3)


def _round_percent(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 1)


def classify_error_types(errors: List[str]) -> List[str]:
    found = set()
    for error in errors:
        text = error.lower()
        if "dns failed" in text or "dns" in text:
            found.add("dns")
        if "tcp failed" in text or "tcp" in text:
            found.add("tcp")
        if "tls failed" in text or "tls/" in text or "certificate" in text:
            found.add("tls")
        if "http failed" in text or "tls/http" in text or "http" in text:
            found.add("http")
        if "ping failed" in text or "ping" in text:
            found.add("ping")
        if "traceroute failed" in text or "traceroute" in text:
            found.add("traceroute")
        if not found and error:
            found.add("unknown")
    order = ["dns", "tcp", "tls", "http", "ping", "traceroute", "unknown"]
    return [name for name in order if name in found]


def _success_rate_percent(result: MeasurementResult) -> float:
    error_types = set(classify_error_types(result.errors))
    stages = [
        ("dns", result.dns_ms is not None),
        ("tcp", result.tcp_ms is not None),
        ("http", result.http_ms is not None),
        ("ping", result.ping_avg_ms is not None or result.packet_loss_percent is not None),
        ("traceroute", result.hop_count is not None),
    ]
    if result.scheme == "https" and (result.tls_ms is not None or "tls" in error_types):
        stages.insert(2, ("tls", result.tls_ms is not None))

    successes = 0
    for stage, has_value in stages:
        if has_value and stage not in error_types:
            successes += 1
    return _round_percent((successes / len(stages)) * 100.0) or 0.0


def _known_float_values(values: List[Optional[float]]) -> List[float]:
    return [float(value) for value in values if value is not None]


def _mean_ms(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return _round_ms(sum(values) / len(values))


def _min_ms(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return _round_ms(min(values))


def _max_ms(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return _round_ms(max(values))


def _stdev_ms(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    return _round_ms(pstdev(values))


def _visible_latency_score_ms(*values: Optional[float]) -> Optional[float]:
    known = [float(value) for value in values if value is not None]
    if not known:
        return None
    return _round_ms(sum(known))


def _mean_hop_count(values: List[int]) -> Optional[int]:
    if not values:
        return None
    return int((sum(values) / len(values)) + 0.5)


def _last_known(values: List[Optional[int]]) -> Optional[int]:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def _last_known_text(values: List[Optional[str]]) -> Optional[str]:
    for value in reversed(values):
        if value:
            return value
    return None


def _combined_traceroute_raw(runs: List[MeasurementResult]) -> str:
    if len(runs) == 1:
        return runs[0].traceroute_raw
    parts = []
    for index, result in enumerate(runs, start=1):
        if result.traceroute_raw:
            parts.append(f"--- run {index} ---\n{result.traceroute_raw}")
    return "\n\n".join(parts)


def _combined_errors(runs: List[MeasurementResult]) -> List[str]:
    errors: List[str] = []
    for index, result in enumerate(runs, start=1):
        for error in result.errors:
            errors.append(f"run {index}: {error}")
    return errors


def _format_seconds(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
