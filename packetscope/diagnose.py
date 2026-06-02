from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .measure import MeasurementResult


DIAGNOSIS_SCHEMA_VERSION = 2

DIAGNOSIS_CSV_FIELDS = [
    "target",
    "bottleneck_layer",
    "bottleneck_value_ms",
    "stability_score",
    "success_rate_percent",
    "error_types",
    "evidence",
    "limitations",
]


def diagnose_results(results: List[MeasurementResult]) -> dict:
    targets = [diagnose_target(result) for result in results]
    return {
        "schema_version": DIAGNOSIS_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _summary(targets),
        "targets": targets,
    }


def diagnose_target(result: MeasurementResult) -> dict:
    bottleneck_layer, bottleneck_label, bottleneck_value = _dominant_layer(result)
    stability_score = _stability_score(result, bottleneck_layer)
    evidence = _evidence(result, bottleneck_label, bottleneck_value)
    limitations = _limitations(result)

    return {
        "target": result.target,
        "bottleneck_layer": bottleneck_layer,
        "bottleneck_value_ms": bottleneck_value,
        "stability_score": stability_score,
        "success_rate_percent": result.success_rate_percent,
        "error_types": list(result.error_types),
        "evidence": evidence,
        "limitations": limitations,
    }


def write_diagnosis_report(results: List[MeasurementResult], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = diagnose_results(results)

    json_path = out_dir / "diagnosis.json"
    csv_path = out_dir / "diagnosis.csv"
    html_path = out_dir / "diagnosis.html"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DIAGNOSIS_CSV_FIELDS)
        writer.writeheader()
        for item in payload["targets"]:
            writer.writerow(
                {
                    "target": item["target"],
                    "bottleneck_layer": item["bottleneck_layer"],
                    "bottleneck_value_ms": _empty_if_none(item["bottleneck_value_ms"]),
                    "stability_score": _empty_if_none(item["stability_score"]),
                    "success_rate_percent": _empty_if_none(item["success_rate_percent"]),
                    "error_types": ", ".join(item["error_types"]),
                    "evidence": " | ".join(item["evidence"]),
                    "limitations": " | ".join(item["limitations"]),
                }
            )

    html_path.write_text(_build_diagnosis_html(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "html": html_path}


def _dominant_layer(result: MeasurementResult) -> tuple[str, str, Optional[float]]:
    metrics = [
        ("dns", "DNS lookup", result.dns_ms),
        ("tcp", "TCP connection", result.tcp_ms),
        ("tls", "TLS handshake", result.tls_ms),
        ("http", "HTTP response", result.http_ms),
        ("ping", "Ping RTT", result.ping_avg_ms),
    ]
    known = [(layer, label, float(value)) for layer, label, value in metrics if value is not None]
    if not known:
        return "unknown", "Unknown", None
    return max(known, key=lambda item: item[2])


def _stability_score(result: MeasurementResult, bottleneck_layer: str) -> Optional[float]:
    if bottleneck_layer == "unknown":
        return None

    score = 100.0
    if result.success_rate_percent is not None:
        score -= 100.0 - float(result.success_rate_percent)
    if result.packet_loss_percent is not None:
        score -= float(result.packet_loss_percent) * 2.0
    if result.ping_jitter_ms is not None:
        score -= float(result.ping_jitter_ms) * 2.0
    return round(max(0.0, min(100.0, score)), 1)


def _evidence(
    result: MeasurementResult,
    bottleneck_label: str,
    bottleneck_value: Optional[float],
) -> List[str]:
    if bottleneck_value is None:
        return ["No successful timing metrics were available, so PacketScope leaves the bottleneck as unknown."]

    evidence = [
        f"Most likely bottleneck: {bottleneck_label} at {bottleneck_value:.1f} ms.",
        f"Visible latency score: {_format_ms(result.visible_latency_score_ms)}.",
        f"Success rate: {_format_percent(result.success_rate_percent)}.",
    ]
    if result.ping_jitter_ms is not None:
        evidence.append(f"Ping jitter: {result.ping_jitter_ms:.1f} ms.")
    if result.packet_loss_percent is not None:
        evidence.append(f"Packet loss: {result.packet_loss_percent:.1f}%.")
    if result.error_types:
        evidence.append("Error types: " + ", ".join(result.error_types) + ".")
    return evidence


def _limitations(result: MeasurementResult) -> List[str]:
    limitations = [
        "This is one local vantage point, not a global Internet measurement.",
        "ICMP-based ping and traceroute can be filtered, delayed, or deprioritized by networks.",
    ]
    if result.hop_count is None:
        limitations.append("Traceroute did not return a visible hop count for this target.")
    if result.tls_ms is None and result.scheme == "https":
        limitations.append("TLS timing is unavailable for this target or this older result file.")
    if result.errors:
        limitations.append("Recorded failures may reduce confidence in the diagnosis.")
    return limitations


def _summary(targets: List[dict]) -> dict:
    diagnosed = [target for target in targets if target["bottleneck_layer"] != "unknown"]
    unknown = len(targets) - len(diagnosed)
    return {
        "target_count": len(targets),
        "diagnosed_count": len(diagnosed),
        "unknown_count": unknown,
    }


def _build_diagnosis_html(payload: dict) -> str:
    rows = "\n".join(_diagnosis_row(item) for item in payload["targets"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>PacketScope Diagnosis</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f8fb; color: #172033; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 48px; }}
    section {{ margin-top: 24px; padding: 22px; background: #fff; border: 1px solid #d9e0ea; border-radius: 8px; }}
    table {{ width: 100%; min-width: 900px; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid #d9e0ea; text-align: left; vertical-align: top; }}
    th {{ color: #5d687a; }}
    .table-wrap {{ overflow-x: auto; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>PacketScope Diagnosis</h1>
      <p>Deterministic bottleneck, stability, evidence, and limitation summary.</p>
    </header>
    <section>
      <h2>Targets</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Target</th>
              <th>Bottleneck</th>
              <th>Stability</th>
              <th>Success</th>
              <th>Error Types</th>
              <th>Evidence</th>
              <th>Limitations</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""


def _diagnosis_row(item: dict) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(item['target'])}</td>"
        f"<td>{html.escape(item['bottleneck_layer'])} ({_format_ms(item['bottleneck_value_ms'])})</td>"
        f"<td>{_empty_if_none(item['stability_score'])}</td>"
        f"<td>{_format_percent(item['success_rate_percent'])}</td>"
        f"<td>{html.escape(', '.join(item['error_types']) or '-')}</td>"
        f"<td>{html.escape(' | '.join(item['evidence']))}</td>"
        f"<td>{html.escape(' | '.join(item['limitations']))}</td>"
        "</tr>"
    )


def _format_ms(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f} ms"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}%"


def _empty_if_none(value):
    return "" if value is None else value
