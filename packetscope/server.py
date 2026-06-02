from __future__ import annotations

import argparse
import html
import ipaddress
import json
import mimetypes
import re
import socket
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from .diagnose import diagnose_results
from .measure import MeasurementResult, aggregate_measurement_runs, measure_target, normalize_target


MAX_TARGETS = 2
MAX_RUNS = 3
DEFAULT_TIMEOUT = 4.0
DEFAULT_PING_COUNT = 2
DEFAULT_MAX_HOPS = 12
DEFAULT_TRACE_WAIT = 1.0
DEFAULT_TRACE_TIMEOUT = 14.0

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"


class PublicTargetError(ValueError):
    pass


class PacketScopeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def run_server(host: str = "127.0.0.1", port: int = 8000, web_root: Optional[Path] = None) -> None:
    root = web_root or WEB_ROOT
    handler = _handler_factory(root)
    server = PacketScopeHTTPServer((host, port), handler)
    print(f"PacketScope Live Lab running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


def measure_for_web(
    targets: List[str],
    runs: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
    ping_count: int = DEFAULT_PING_COUNT,
    max_hops: int = DEFAULT_MAX_HOPS,
    trace_wait: float = DEFAULT_TRACE_WAIT,
    trace_timeout: float = DEFAULT_TRACE_TIMEOUT,
) -> dict:
    cleaned_targets = _validate_targets(targets)
    bounded_runs = max(1, min(int(runs), MAX_RUNS))
    results = [_measure_runs(target, bounded_runs, timeout, ping_count, max_hops, trace_wait, trace_timeout) for target in cleaned_targets]
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "measurement_origin": "PacketScope server network",
        "targets": cleaned_targets,
        "runs": bounded_runs,
        "results": [result.to_dict() for result in results],
        "diagnosis": diagnose_results(results),
        "comparison": _comparison_summary(results),
    }


def measure_for_web_stream(
    targets: List[str],
    emit: Callable[[dict], None],
    runs: int = 1,
    timeout: float = DEFAULT_TIMEOUT,
    ping_count: int = DEFAULT_PING_COUNT,
    max_hops: int = DEFAULT_MAX_HOPS,
    trace_wait: float = DEFAULT_TRACE_WAIT,
    trace_timeout: float = DEFAULT_TRACE_TIMEOUT,
) -> dict:
    cleaned_targets = _validate_targets(targets)
    bounded_runs = max(1, min(int(runs), MAX_RUNS))
    emit(
        {
            "type": "accepted",
            "targets": cleaned_targets,
            "runs": bounded_runs,
            "origin": "PacketScope server network",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    results = []
    for target in cleaned_targets:
        emit({"type": "target_started", "target": target})
        result = _measure_runs(
            target,
            bounded_runs,
            timeout,
            ping_count,
            max_hops,
            trace_wait,
            trace_timeout,
            progress_callback=lambda event, current_target=target: emit(
                {"type": "stage", "target": current_target, **event}
            ),
        )
        results.append(result)
        emit({"type": "target_done", "target": target, "result": result.to_dict()})

    payload = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "measurement_origin": "PacketScope server network",
        "targets": cleaned_targets,
        "runs": bounded_runs,
        "results": [result.to_dict() for result in results],
        "diagnosis": diagnose_results(results),
        "comparison": _comparison_summary(results),
    }
    emit({"type": "complete", "payload": payload})
    return payload


def _handler_factory(web_root: Path):
    class PacketScopeHandler(SimpleHTTPRequestHandler):
        server_version = "PacketScopeLive/0.1"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(web_root), **kwargs)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._write_json({"ok": True, "service": "packetscope-live"})
                return
            if self.path in {"/", ""}:
                self.path = "/index.html"
            return super().do_GET()

        def do_POST(self) -> None:
            if self.path == "/api/measure/stream":
                self._stream_measurement()
                return
            if self.path == "/api/report":
                self._download_report()
                return

            if self.path != "/api/measure":
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
                return

            try:
                payload = self._read_json()
                result = measure_for_web(
                    targets=payload.get("targets") or [payload.get("target", "")],
                    runs=int(payload.get("runs", 1)),
                    timeout=float(payload.get("timeout", DEFAULT_TIMEOUT)),
                    ping_count=int(payload.get("ping_count", DEFAULT_PING_COUNT)),
                    max_hops=int(payload.get("max_hops", DEFAULT_MAX_HOPS)),
                    trace_wait=float(payload.get("trace_wait", DEFAULT_TRACE_WAIT)),
                    trace_timeout=float(payload.get("trace_timeout", DEFAULT_TRACE_TIMEOUT)),
                )
            except PublicTargetError as exc:
                self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except Exception as exc:
                self._write_json({"ok": False, "error": f"Measurement failed: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            self._write_json(result)

        def _stream_measurement(self) -> None:
            try:
                payload = self._read_json(max_length=256_000)
            except PublicTargetError as exc:
                self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            def emit(event: dict) -> None:
                body = json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n"
                self.wfile.write(body)
                self.wfile.flush()

            try:
                measure_for_web_stream(
                    targets=payload.get("targets") or [payload.get("target", "")],
                    emit=emit,
                    runs=int(payload.get("runs", 1)),
                    timeout=float(payload.get("timeout", DEFAULT_TIMEOUT)),
                    ping_count=int(payload.get("ping_count", DEFAULT_PING_COUNT)),
                    max_hops=int(payload.get("max_hops", DEFAULT_MAX_HOPS)),
                    trace_wait=float(payload.get("trace_wait", DEFAULT_TRACE_WAIT)),
                    trace_timeout=float(payload.get("trace_timeout", DEFAULT_TRACE_TIMEOUT)),
                )
            except PublicTargetError as exc:
                emit({"type": "error", "error": str(exc)})
            except Exception as exc:
                emit({"type": "error", "error": f"Measurement failed: {exc}"})

        def _download_report(self) -> None:
            try:
                payload = self._read_json()
                report_html = _build_web_report_html(payload)
            except Exception as exc:
                self._write_json({"ok": False, "error": f"Report failed: {exc}"}, status=HTTPStatus.BAD_REQUEST)
                return

            body = report_html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", 'attachment; filename="packetscope-report.html"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def guess_type(self, path: str) -> str:
            if path.endswith(".js"):
                return "text/javascript"
            return mimetypes.guess_type(path)[0] or "application/octet-stream"

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _read_json(self, max_length: int = 4096) -> dict:
            length = int(self.headers.get("content-length", "0"))
            if length <= 0 or length > max_length:
                raise PublicTargetError("Request body must be a JSON object within the size limit.")
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise PublicTargetError("Request body is not valid JSON.") from exc
            if not isinstance(payload, dict):
                raise PublicTargetError("Request body must be a JSON object.")
            return payload

        def _write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return PacketScopeHandler


def _measure_runs(
    target: str,
    runs: int,
    timeout: float,
    ping_count: int,
    max_hops: int,
    trace_wait: float,
    trace_timeout: float,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> MeasurementResult:
    measurements = [
        measure_target(
            target,
            timeout=timeout,
            ping_count=ping_count,
            max_hops=max_hops,
            trace_wait=trace_wait,
            trace_timeout=trace_timeout,
            progress_callback=progress_callback,
        )
        for _ in range(runs)
    ]
    if len(measurements) == 1:
        return measurements[0]
    return aggregate_measurement_runs(measurements)


def _validate_targets(values: Iterable[str]) -> List[str]:
    targets = [str(value).strip() for value in values if str(value).strip()]
    if not targets:
        raise PublicTargetError("Enter at least one public website.")
    if len(targets) > MAX_TARGETS:
        raise PublicTargetError(f"Measure at most {MAX_TARGETS} targets at a time.")

    cleaned = []
    for value in targets:
        target = normalize_target(value)
        _reject_private_host(target.host)
        cleaned.append(target.original)
    return cleaned


def _reject_private_host(host: str) -> None:
    lowered = host.lower().strip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        raise PublicTargetError("Localhost targets are not allowed in the online demo.")

    try:
        direct_ip = ipaddress.ip_address(lowered)
    except ValueError:
        direct_ip = None

    if direct_ip is not None:
        _reject_private_ip(direct_ip, host)
        return

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise PublicTargetError(f"Could not resolve {host}: {exc}") from exc

    addresses = {item[4][0] for item in infos}
    if not addresses:
        raise PublicTargetError(f"Could not resolve {host}.")

    for address in addresses:
        _reject_private_ip(ipaddress.ip_address(address), host)


def _reject_private_ip(address: ipaddress._BaseAddress, host: str) -> None:
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise PublicTargetError(f"{host} resolves to a non-public address, so PacketScope will not measure it online.")


def _comparison_summary(results: List[MeasurementResult]) -> Optional[dict]:
    if len(results) != 2:
        return None
    first, second = results
    first_score = first.visible_latency_score_ms
    second_score = second.visible_latency_score_ms
    if first_score is None or second_score is None:
        return {
            "winner": None,
            "message": "Not enough successful timing data to compare both targets.",
        }
    if first_score == second_score:
        winner = None
    else:
        winner = first.target if first_score < second_score else second.target
    return {
        "winner": winner,
        "first_score_ms": first_score,
        "second_score_ms": second_score,
        "delta_ms": round(abs(first_score - second_score), 3),
    }


def _build_web_report_html(payload: dict) -> str:
    measurement = payload.get("measurement") or payload
    results = measurement.get("results") or []
    if not results:
        raise ValueError("Report payload does not contain measurement results.")
    events = payload.get("execution_events") or []
    diagnosis = measurement.get("diagnosis", {}).get("targets", [])
    generated_at = measurement.get("generated_at") or datetime.now(timezone.utc).isoformat()
    targets = ", ".join(_escape(result.get("target", "-")) for result in results)
    summary_cards = "\n".join(_report_summary_card(result) for result in results)
    timeline = "\n".join(_report_timeline_item(item) for item in _course_timeline())
    concept_rows = "\n".join(_report_concept_row(item) for item in _course_concepts())
    metric_rows = "\n".join(_report_metric_row(result) for result in results)
    route_sections = "\n".join(_report_route_section(result) for result in results)
    execution_rows = "\n".join(_report_execution_row(event) for event in events[-120:]) or "<tr><td colspan='4'>No execution events were captured.</td></tr>"
    diagnosis_rows = "\n".join(_report_diagnosis_row(item) for item in diagnosis) or "<p>No diagnosis was returned.</p>"
    raw_json = _escape(json.dumps(measurement, indent=2, ensure_ascii=False))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PacketScope Network Report</title>
  <style>
    body {{ margin: 0; background: #eef3f8; color: #111c2e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.5; }}
    main {{ width: min(1120px, calc(100% - 36px)); margin: 0 auto; padding: 28px 0 56px; }}
    header {{ background: #101a2b; color: #fff; padding: 24px; border-radius: 10px; }}
    h1, h2, h3, p {{ margin: 0; }} h1 {{ font-size: 30px; }} h2 {{ font-size: 21px; margin-bottom: 12px; }}
    section {{ margin-top: 16px; background: #fff; border: 1px solid #d8e1eb; border-radius: 10px; padding: 18px; }}
    .muted {{ color: #667386; }} .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid #d8e1eb; border-radius: 8px; padding: 14px; background: #f7f9fc; }}
    .card strong {{ display: block; font-size: 20px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }} th, td {{ border-bottom: 1px solid #d8e1eb; padding: 9px; text-align: left; vertical-align: top; }}
    th {{ background: #f7f9fc; }} code, pre {{ font-family: SFMono-Regular, Consolas, monospace; }}
    pre {{ white-space: pre-wrap; overflow: auto; background: #0f1a2b; color: #dce8f8; border-radius: 8px; padding: 12px; }}
    .timeline {{ display: grid; gap: 10px; }} .step {{ border-left: 4px solid #176bff; padding: 8px 12px; background: #f7f9fc; border-radius: 6px; }}
    .route {{ display: flex; flex-wrap: wrap; gap: 8px; }} .hop {{ border: 1px solid #d8e1eb; border-radius: 8px; padding: 9px; background: #f7f9fc; min-width: 130px; }}
    .hop span {{ display: block; color: #667386; font-size: 12px; }} .badge {{ display: inline-block; border-radius: 999px; background: #e8f1ff; color: #176bff; padding: 2px 8px; font-size: 12px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="badge">PacketScope Report</p>
      <h1>Network Request Analysis</h1>
      <p class="muted">Targets: {targets}</p>
      <p class="muted">Generated: {_escape(generated_at)}</p>
    </header>
    <section>
      <h2>Executive Summary</h2>
      <div class="grid">{summary_cards}</div>
    </section>
    <section>
      <h2>Complete Website Visit Timeline</h2>
      <div class="timeline">{timeline}</div>
    </section>
    <section>
      <h2>Course Concepts Mapping</h2>
      <table><thead><tr><th>Concept</th><th>Layer</th><th>Evidence in PacketScope</th></tr></thead><tbody>{concept_rows}</tbody></table>
    </section>
    <section>
      <h2>Measured Metrics</h2>
      <table><thead><tr><th>Target</th><th>Resolved IPs</th><th>DNS</th><th>TCP</th><th>TLS</th><th>HTTP</th><th>Ping</th><th>Loss</th><th>Hops</th><th>Status</th></tr></thead><tbody>{metric_rows}</tbody></table>
    </section>
    <section>
      <h2>Diagnosis</h2>
      {diagnosis_rows}
    </section>
    <section>
      <h2>Traceroute Path Visualization</h2>
      {route_sections}
    </section>
    <section>
      <h2>Live Execution Evidence</h2>
      <table><thead><tr><th>Time</th><th>Status</th><th>Stage</th><th>Message</th></tr></thead><tbody>{execution_rows}</tbody></table>
    </section>
    <section>
      <h2>Raw Measurement JSON</h2>
      <pre>{raw_json}</pre>
    </section>
  </main>
</body>
</html>"""


def _report_summary_card(result: dict) -> str:
    return (
        "<div class='card'>"
        f"<span>{_escape(result.get('target', '-'))}</span>"
        f"<strong>{_format_ms(result.get('visible_latency_score_ms'))}</strong>"
        f"<p class='muted'>Visible latency score, {result.get('success_rate_percent', 'N/A')}% success</p>"
        "</div>"
    )


def _report_timeline_item(item: dict) -> str:
    return f"<div class='step'><strong>{_escape(item['title'])}</strong><p class='muted'>{_escape(item['copy'])}</p></div>"


def _report_concept_row(item: dict) -> str:
    return f"<tr><td>{_escape(item['concept'])}</td><td>{_escape(item['layer'])}</td><td>{_escape(item['evidence'])}</td></tr>"


def _report_metric_row(result: dict) -> str:
    addresses = ", ".join(result.get("resolved_addresses") or []) or "N/A"
    return (
        "<tr>"
        f"<td>{_escape(result.get('target', '-'))}</td>"
        f"<td>{_escape(addresses)}</td>"
        f"<td>{_format_ms(result.get('dns_ms'))}</td>"
        f"<td>{_format_ms(result.get('tcp_ms'))}</td>"
        f"<td>{_format_ms(result.get('tls_ms'))}</td>"
        f"<td>{_format_ms(result.get('http_ms'))}</td>"
        f"<td>{_format_ms(result.get('ping_avg_ms'))}</td>"
        f"<td>{_escape(_format_percent(result.get('packet_loss_percent')))}</td>"
        f"<td>{_escape(result.get('hop_count', 'N/A'))}</td>"
        f"<td>{_escape(result.get('http_status', 'N/A'))}</td>"
        "</tr>"
    )


def _report_diagnosis_row(item: dict) -> str:
    evidence = "".join(f"<li>{_escape(line)}</li>" for line in item.get("evidence", []))
    return f"<div class='card'><strong>{_escape(item.get('target', '-'))}</strong><p class='muted'>Bottleneck: {_escape(item.get('bottleneck_layer', 'unknown'))}</p><ul>{evidence}</ul></div>"


def _report_route_section(result: dict) -> str:
    hops = _parse_trace_hops(result.get("traceroute_raw") or "")
    if not hops:
        return f"<div class='card'><strong>{_escape(result.get('target', '-'))}</strong><p class='muted'>No traceroute hops were parsed.</p></div>"
    hop_html = "".join(
        f"<div class='hop'><strong>Hop {_escape(hop['number'])}</strong><span>{_escape(hop['label'])}</span><span>{_escape(hop['latency'])}</span></div>"
        for hop in hops
    )
    return f"<h3>{_escape(result.get('target', '-'))}</h3><div class='route'>{hop_html}</div>"


def _report_execution_row(event: dict) -> str:
    return f"<tr><td>{_escape(event.get('time', '-'))}</td><td>{_escape(event.get('status', '-'))}</td><td>{_escape(event.get('stage', '-'))}</td><td>{_escape(event.get('message', '-'))}</td></tr>"


def _parse_trace_hops(raw: str) -> List[dict]:
    hops = []
    for line in raw.splitlines():
        match = re.match(r"^\s*(\d+)\s+(.+)$", line)
        if not match:
            continue
        body = match.group(2).strip()
        latencies = re.findall(r"(\d+(?:\.\d+)?)\s*ms", body)
        label = re.sub(r"\s+\d+(?:\.\d+)?\s*ms", "", body).strip()
        hops.append({"number": match.group(1), "label": label or "*", "latency": ", ".join(f"{item} ms" for item in latencies) or "no reply"})
    return hops


def _course_timeline() -> List[dict]:
    return [
        {"title": "1. DNS resolution", "copy": "The client converts a domain name into one or more IP addresses."},
        {"title": "2. TCP connection", "copy": "The transport layer opens a reliable connection to the server port."},
        {"title": "3. TLS handshake", "copy": "HTTPS sites negotiate encryption before application data is sent."},
        {"title": "4. HTTP request and response", "copy": "The application layer sends a request and waits for the first response bytes."},
        {"title": "5. Ping RTT and packet loss", "copy": "ICMP probes estimate round-trip time and whether packets are lost."},
        {"title": "6. Traceroute route path", "copy": "Hop-limited probes reveal visible routers between the measuring server and target."},
    ]


def _course_concepts() -> List[dict]:
    return [
        {"concept": "DNS", "layer": "Application layer support service", "evidence": "DNS lookup time and resolved IP addresses."},
        {"concept": "HTTP/HTTPS", "layer": "Application layer", "evidence": "HTTP status code, response wait, and TLS timing for HTTPS."},
        {"concept": "TCP", "layer": "Transport layer", "evidence": "Connection setup time to port 80 or 443."},
        {"concept": "IP routing", "layer": "Network layer", "evidence": "Traceroute hop count and visible route nodes."},
        {"concept": "RTT and packet loss", "layer": "Network performance", "evidence": "Ping average/min/max RTT and packet loss percentage."},
        {"concept": "Client-server model", "layer": "End-to-end architecture", "evidence": "PacketScope server acts as the measuring client for each target website."},
    ]


def _format_ms(value: object) -> str:
    try:
        if value is None:
            return "N/A"
        return f"{float(value):.1f} ms"
    except (TypeError, ValueError):
        return "N/A"


def _format_percent(value: object) -> str:
    try:
        if value is None:
            return "N/A"
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _escape(value: object) -> str:
    return html.escape(str(value))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the PacketScope Live Lab web server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
