from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from .compare import write_compare_report
from .diagnose import write_diagnosis_report
from .measure import (
    DEFAULT_TARGETS,
    MeasurementResult,
    aggregate_measurement_runs,
    measure_target,
    mock_measurements,
)
from .report import write_reports


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "report":
        payload = _load_result_payload(Path(args.results_json))
        results = payload["results"]
        out_dir = Path(args.out) if args.out else Path(args.results_json).parent
        written = write_reports(
            results,
            out_dir,
            run_metadata=payload["metadata"].get("run", {}),
            environment=payload["metadata"].get("environment"),
        )
        print("Regenerated:")
        print(f"- JSON: {written['json']}")
        print(f"- CSV:  {written['csv']}")
        print(f"- HTML: {written['html']}")
        return 0

    if args.command == "diagnose":
        results = _load_results(Path(args.results_json))
        out_dir = Path(args.out) if args.out else Path(args.results_json).parent
        written = write_diagnosis_report(results, out_dir)
        print("Diagnosed:")
        print(f"- JSON: {written['json']}")
        print(f"- CSV:  {written['csv']}")
        print(f"- HTML: {written['html']}")
        return 0

    if args.command == "compare":
        baseline = _load_results(Path(args.baseline_json))
        current = _load_results(Path(args.current_json))
        out_dir = Path(args.out) if args.out else Path("reports") / "compare"
        written = write_compare_report(baseline, current, out_dir)
        print("Compared:")
        print(f"- JSON: {written['json']}")
        print(f"- CSV:  {written['csv']}")
        print(f"- HTML: {written['html']}")
        return 0

    if args.command == "web":
        from .server import run_server

        run_server(args.host, args.port)
        return 0

    if args.command == "scan":
        targets = [args.target]
        default_out = Path("reports") / _safe_name(args.target)
    else:
        targets = args.targets or DEFAULT_TARGETS
        default_out = Path("reports") / "experiment"

    out_dir = Path(args.out) if args.out else default_out

    results = _run_measurements(targets, args)

    written = write_reports(results, out_dir, run_metadata=_run_metadata(args, targets))
    _print_terminal_results(results, written)

    failed_targets = [result.target for result in results if result.all_core_metrics_failed()]
    if failed_targets:
        print("\nFailed target(s): " + ", ".join(failed_targets))
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="packetscope",
        description="Analyze DNS, TCP, HTTP, ping, and traceroute timing for websites.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Analyze one target website.")
    scan.add_argument("target", help="Domain or URL, for example example.com")
    _add_common_options(scan)

    experiment = subparsers.add_parser("experiment", help="Compare five default websites or custom targets.")
    experiment.add_argument("targets", nargs="*", help="Optional custom domains or URLs.")
    _add_common_options(experiment)

    report = subparsers.add_parser("report", help="Regenerate CSV and HTML from an existing results.json.")
    report.add_argument("results_json", help="Path to a PacketScope results.json file.")
    report.add_argument("--out", help="Output directory for regenerated results.json, results.csv, and report.html.")

    diagnose = subparsers.add_parser("diagnose", help="Generate diagnosis from an existing results.json.")
    diagnose.add_argument("results_json", help="Path to a PacketScope results.json file.")
    diagnose.add_argument("--out", help="Output directory for diagnosis.json, diagnosis.csv, and diagnosis.html.")

    compare = subparsers.add_parser("compare", help="Compare two PacketScope results.json files.")
    compare.add_argument("baseline_json", help="Baseline PacketScope results.json file.")
    compare.add_argument("current_json", help="Current PacketScope results.json file.")
    compare.add_argument("--out", help="Output directory for compare.json, compare.csv, and compare.html.")

    web = subparsers.add_parser("web", help="Run the PacketScope Live Lab web application.")
    web.add_argument("--host", default="127.0.0.1", help="Host address for the web server.")
    web.add_argument("--port", type=int, default=8000, help="Port for the web server.")

    return parser


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", help="Output directory for results.json, results.csv, and report.html.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic demo data instead of network calls.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout in seconds.")
    parser.add_argument("--ping-count", type=int, default=3, help="Number of ping packets.")
    parser.add_argument("--max-hops", type=int, default=20, help="Maximum traceroute hops.")
    parser.add_argument("--trace-wait", type=float, default=1.0, help="Seconds to wait for each traceroute hop.")
    parser.add_argument("--trace-timeout", type=float, help="Overall traceroute timeout in seconds.")
    parser.add_argument("--runs", type=_positive_int, default=1, help="Number of measurement runs per target.")


def _run_measurements(targets: List[str], args: argparse.Namespace) -> List[MeasurementResult]:
    if args.runs == 1:
        if args.mock:
            return mock_measurements(targets)
        return [
            _measure_one_target(target, args)
            for target in targets
        ]

    runs_by_target: List[List[MeasurementResult]] = [[] for _ in targets]
    for _ in range(args.runs):
        if args.mock:
            run_results = mock_measurements(targets)
        else:
            run_results = [_measure_one_target(target, args) for target in targets]
        for index, result in enumerate(run_results):
            runs_by_target[index].append(result)

    return [aggregate_measurement_runs(target_runs) for target_runs in runs_by_target]


def _measure_one_target(target: str, args: argparse.Namespace) -> MeasurementResult:
    return measure_target(
        target,
        timeout=args.timeout,
        ping_count=args.ping_count,
        max_hops=args.max_hops,
        trace_wait=args.trace_wait,
        trace_timeout=args.trace_timeout,
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _load_result_payload(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("results")
    if not isinstance(items, list):
        raise ValueError(f"{path} is not a PacketScope results.json file")
    return {
        "metadata": payload,
        "results": [MeasurementResult(**item) for item in items],
    }


def _load_results(path: Path) -> List[MeasurementResult]:
    return _load_result_payload(path)["results"]


def _run_metadata(args: argparse.Namespace, targets: List[str]) -> dict:
    return {
        "command": args.command,
        "targets": list(targets),
        "runs": args.runs,
        "mock": bool(args.mock),
        "timeout": args.timeout,
        "ping_count": args.ping_count,
        "max_hops": args.max_hops,
        "trace_wait": args.trace_wait,
        "trace_timeout": args.trace_timeout,
    }


def _print_terminal_results(results: List[MeasurementResult], written: dict) -> None:
    columns = [
        ("Target", 22),
        ("DNS", 9),
        ("TCP", 9),
        ("TLS", 9),
        ("HTTP", 9),
        ("Ping", 9),
        ("Loss", 8),
        ("Hops", 6),
        ("Status", 8),
        ("Errors", 28),
    ]
    header = " ".join(label.ljust(width) for label, width in columns)
    print(header)
    print("-" * len(header))
    for result in results:
        row = [
            _trim(result.target, 22),
            _fmt_ms(result.dns_ms).ljust(9),
            _fmt_ms(result.tcp_ms).ljust(9),
            _fmt_ms(result.tls_ms).ljust(9),
            _fmt_ms(result.http_ms).ljust(9),
            _fmt_ms(result.ping_avg_ms).ljust(9),
            _fmt_loss(result.packet_loss_percent).ljust(8),
            _fmt_value(result.hop_count).ljust(6),
            _fmt_value(result.http_status).ljust(8),
            _trim(result.error_text or "-", 28),
        ]
        print(" ".join(row))

    print("\nWrote:")
    print(f"- JSON: {written['json']}")
    print(f"- CSV:  {written['csv']}")
    print(f"- HTML: {written['html']}")


def _fmt_ms(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}"


def _fmt_loss(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def _fmt_value(value) -> str:
    return "-" if value is None else str(value)


def _trim(value: str, width: int) -> str:
    if len(value) <= width:
        return value.ljust(width)
    return value[: width - 3] + "..."


def _safe_name(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in ".-" else "-" for char in value)
    return cleaned.strip("-") or "scan"
