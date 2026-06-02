from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .diagnose import diagnose_target
from .measure import MeasurementResult


COMPARE_SCHEMA_VERSION = 2
ABSOLUTE_THRESHOLD_MS = 10.0
PERCENT_THRESHOLD = 10.0

COMPARE_CSV_FIELDS = [
    "target",
    "baseline_latency_score_ms",
    "current_latency_score_ms",
    "delta_ms",
    "percent_change",
    "status",
    "baseline_bottleneck_layer",
    "current_bottleneck_layer",
    "failure_change",
]


def compare_results(
    baseline: List[MeasurementResult],
    current: List[MeasurementResult],
) -> dict:
    baseline_by_target = {result.target: result for result in baseline}
    current_by_target = {result.target: result for result in current}
    baseline_targets = set(baseline_by_target)
    current_targets = set(current_by_target)

    common_targets = []
    for target in sorted(baseline_targets & current_targets):
        common_targets.append(_compare_one(baseline_by_target[target], current_by_target[target]))

    return {
        "schema_version": COMPARE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "absolute_ms": ABSOLUTE_THRESHOLD_MS,
            "percent": PERCENT_THRESHOLD,
        },
        "common_targets": common_targets,
        "new_targets": sorted(current_targets - baseline_targets),
        "missing_targets": sorted(baseline_targets - current_targets),
    }


def write_compare_report(
    baseline: List[MeasurementResult],
    current: List[MeasurementResult],
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = compare_results(baseline, current)

    json_path = out_dir / "compare.json"
    csv_path = out_dir / "compare.csv"
    html_path = out_dir / "compare.html"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMPARE_CSV_FIELDS)
        writer.writeheader()
        for item in payload["common_targets"]:
            writer.writerow({field: _empty_if_none(item.get(field)) for field in COMPARE_CSV_FIELDS})

    html_path.write_text(_build_compare_html(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "html": html_path}


def _compare_one(baseline: MeasurementResult, current: MeasurementResult) -> dict:
    baseline_score = baseline.visible_latency_score_ms
    current_score = current.visible_latency_score_ms
    delta_ms = _delta(baseline_score, current_score)
    percent_change = _percent_change(baseline_score, delta_ms)
    baseline_diagnosis = diagnose_target(baseline)
    current_diagnosis = diagnose_target(current)

    return {
        "target": baseline.target,
        "baseline_latency_score_ms": baseline_score,
        "current_latency_score_ms": current_score,
        "delta_ms": delta_ms,
        "percent_change": percent_change,
        "status": _status(delta_ms, percent_change),
        "baseline_bottleneck_layer": baseline_diagnosis["bottleneck_layer"],
        "current_bottleneck_layer": current_diagnosis["bottleneck_layer"],
        "failure_change": _failure_change(baseline, current),
        "baseline_error_types": list(baseline.error_types),
        "current_error_types": list(current.error_types),
    }


def _status(delta_ms: Optional[float], percent_change: Optional[float]) -> str:
    if delta_ms is None or percent_change is None:
        return "unknown"
    if delta_ms < -ABSOLUTE_THRESHOLD_MS and percent_change < -PERCENT_THRESHOLD:
        return "improved"
    if delta_ms > ABSOLUTE_THRESHOLD_MS and percent_change > PERCENT_THRESHOLD:
        return "regressed"
    return "stable"


def _failure_change(baseline: MeasurementResult, current: MeasurementResult) -> str:
    baseline_failures = len(baseline.error_types)
    current_failures = len(current.error_types)
    if current_failures > baseline_failures:
        return "worse"
    if current_failures < baseline_failures:
        return "better"
    return "unchanged"


def _delta(baseline: Optional[float], current: Optional[float]) -> Optional[float]:
    if baseline is None or current is None:
        return None
    return round(float(current) - float(baseline), 3)


def _percent_change(baseline: Optional[float], delta_ms: Optional[float]) -> Optional[float]:
    if baseline is None or delta_ms is None or float(baseline) == 0.0:
        return None
    return round((float(delta_ms) / float(baseline)) * 100.0, 1)


def _build_compare_html(payload: dict) -> str:
    rows = "\n".join(_compare_row(item) for item in payload["common_targets"])
    new_targets = ", ".join(payload["new_targets"]) or "None"
    missing_targets = ", ".join(payload["missing_targets"]) or "None"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>PacketScope Compare</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f8fb; color: #172033; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 48px; }}
    section {{ margin-top: 24px; padding: 22px; background: #fff; border: 1px solid #d9e0ea; border-radius: 8px; }}
    table {{ width: 100%; min-width: 960px; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid #d9e0ea; text-align: left; vertical-align: top; }}
    th {{ color: #5d687a; }}
    .table-wrap {{ overflow-x: auto; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>PacketScope Compare</h1>
      <p>Baseline vs current experiment comparison using fixed 10 ms and 10% thresholds.</p>
    </header>
    <section>
      <h2>Target Changes</h2>
      <p>New targets: {html.escape(new_targets)}</p>
      <p>Missing targets: {html.escape(missing_targets)}</p>
    </section>
    <section>
      <h2>Common Targets</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Target</th>
              <th>Baseline</th>
              <th>Current</th>
              <th>Delta</th>
              <th>Percent</th>
              <th>Status</th>
              <th>Bottleneck Change</th>
              <th>Failure Change</th>
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


def _compare_row(item: dict) -> str:
    bottleneck = f"{item['baseline_bottleneck_layer']} -> {item['current_bottleneck_layer']}"
    return (
        "<tr>"
        f"<td>{html.escape(item['target'])}</td>"
        f"<td>{_format_ms(item['baseline_latency_score_ms'])}</td>"
        f"<td>{_format_ms(item['current_latency_score_ms'])}</td>"
        f"<td>{_format_ms(item['delta_ms'])}</td>"
        f"<td>{_format_percent(item['percent_change'])}</td>"
        f"<td>{html.escape(item['status'])}</td>"
        f"<td>{html.escape(bottleneck)}</td>"
        f"<td>{html.escape(item['failure_change'])}</td>"
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
