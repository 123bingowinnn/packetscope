from __future__ import annotations

import csv
import html
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from . import __version__
from .diagnose import diagnose_results
from .measure import MeasurementResult


SCHEMA_VERSION = 2

CSV_FIELDS = [
    "target",
    "dns_ms",
    "tcp_ms",
    "tls_ms",
    "http_ms",
    "ping_min_ms",
    "ping_avg_ms",
    "ping_max_ms",
    "ping_jitter_ms",
    "run_count",
    "dns_min_ms",
    "dns_max_ms",
    "tcp_min_ms",
    "tcp_max_ms",
    "http_min_ms",
    "http_max_ms",
    "ping_avg_min_ms",
    "ping_avg_max_ms",
    "ping_stdev_ms",
    "visible_latency_score_ms",
    "success_rate_percent",
    "packet_loss_percent",
    "hop_count",
    "http_status",
    "error_types",
    "error",
]


def write_reports(
    results: List[MeasurementResult],
    out_dir: Path,
    run_metadata: Optional[dict] = None,
    environment: Optional[dict] = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "results.json"
    csv_path = out_dir / "results.csv"
    html_path = out_dir / "report.html"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": run_metadata or {},
        "environment": environment or _environment_metadata(),
        "results": [result.to_dict() for result in results],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(_csv_row(result))

    html_path.write_text(
        build_html_report(results, payload["run"], payload["environment"]),
        encoding="utf-8",
    )

    return {"json": json_path, "csv": csv_path, "html": html_path}


def build_conclusion(results: List[MeasurementResult]) -> str:
    ranked = sorted(
        (result for result in results if _latency_score(result) is not None),
        key=lambda result: _latency_score(result) or 0,
    )
    if not ranked:
        return (
            "No complete latency comparison is available. All targets failed the "
            "core measurements, so PacketScope cannot explain relative speed."
        )

    fastest = ranked[0]
    slowest = ranked[-1]
    fastest_score = _latency_score(fastest)
    slowest_score = _latency_score(slowest)

    if fastest is slowest:
        opening = f"{fastest.target} has the best measured response in this run."
    else:
        opening = (
            f"{fastest.target} is faster than {slowest.target} in this run "
            f"because its combined DNS, TCP, TLS, HTTP, and RTT time is lower "
            f"({fastest_score:.1f} ms vs {slowest_score:.1f} ms)."
        )

    bottleneck = _dominant_metric(slowest)
    hop_note = _hop_relationship_note(results)
    stability_note = _stability_note(results)

    return (
        f"{opening} The largest visible delay for {slowest.target} is "
        f"{bottleneck}. RTT is the base round-trip delay between the client and "
        "the server. More routing hops can increase RTT because packets pass "
        f"through more routers, but this run shows the relationship is not exact: "
        f"{hop_note} DNS cache state, TLS setup, server distance, congestion, "
        "and server processing also affect HTTP response time. A website is "
        "usually faster when RTT is low, DNS answers quickly, and the server "
        f"begins sending the HTTP response quickly. {stability_note} Ping and "
        "traceroute also have measurement limits: ICMP traffic can be filtered "
        "or deprioritized, and missing traceroute hops do not always mean that "
        "end-to-end connectivity failed."
    )


def build_main_finding(results: List[MeasurementResult]) -> str:
    ranked = sorted(
        (result for result in results if _latency_score(result) is not None),
        key=lambda result: _latency_score(result) or 0,
    )
    if not ranked:
        return (
            "No target has enough successful measurements for a main finding. "
            "Check the error fields before comparing website speed."
        )

    fastest = ranked[0]
    slowest = ranked[-1]
    fastest_score = _latency_score(fastest) or 0.0
    slowest_score = _latency_score(slowest) or 0.0
    if fastest is slowest:
        opening = (
            f"{fastest.target} has the lowest visible latency score in this "
            f"single-target report ({fastest_score:.1f} ms)."
        )
    else:
        opening = (
            f"{fastest.target} is the fastest target in this experiment "
            f"({fastest_score:.1f} ms visible latency score), while "
            f"{slowest.target} is the slowest ({slowest_score:.1f} ms)."
        )

    missing_trace = [result.target for result in results if result.hop_count is None]
    trace_note = ""
    if missing_trace:
        trace_note = (
            " Traceroute was incomplete for "
            + ", ".join(missing_trace)
            + ", so hop-count comparisons should be treated as partial evidence."
        )

    return (
        f"{opening} The slowest target's largest measured component is "
        f"{_dominant_metric(slowest)}. RTT and routing hops should be read "
        f"together: {_hop_relationship_note(results)}{trace_note}"
    )


def build_html_report(
    results: List[MeasurementResult],
    run_metadata: Optional[dict] = None,
    environment: Optional[dict] = None,
) -> str:
    summary = _summary(results)
    main_finding = html.escape(build_main_finding(results))
    latency_chart = _bar_chart(
        "Latency Comparison",
        results,
        [
            ("DNS", "dns_ms", "#2f80ed"),
            ("TCP", "tcp_ms", "#27ae60"),
            ("TLS", "tls_ms", "#9b51e0"),
            ("HTTP", "http_ms", "#f2994a"),
        ],
        "ms",
    )
    ping_chart = _bar_chart(
        "Ping RTT Range",
        results,
        [
            ("Min RTT", "ping_min_ms", "#56cc9d"),
            ("Avg RTT", "ping_avg_ms", "#9b51e0"),
            ("Max RTT", "ping_max_ms", "#eb5757"),
        ],
        "ms",
    )
    hop_chart = _bar_chart(
        "Hop Count",
        results,
        [("Hops", "hop_count", "#eb5757")],
        "hops",
    )
    rows = "\n".join(_html_table_row(result) for result in results)
    traces = "\n".join(_html_trace(result) for result in results)
    stability_rows = "\n".join(_html_stability_row(result) for result in results)
    insights = _html_insights(results)
    metadata = _html_metadata(run_metadata or {}, environment or {})
    diagnosis_summary = _html_diagnosis_summary(results)
    observation_limits = _html_observation_limits()
    conclusion = html.escape(build_conclusion(results))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>PacketScope Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --text: #172033;
      --muted: #5d687a;
      --panel: #ffffff;
      --line: #d9e0ea;
      --accent: #2f80ed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    header {{
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
      line-height: 1.1;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--muted);
    }}
    section {{
      margin-top: 24px;
      padding: 22px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}
    .metric {{
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
    }}
    .metric strong {{
      display: block;
      margin-top: 6px;
      font-size: 20px;
      color: var(--text);
      overflow-wrap: anywhere;
    }}
    .main-finding {{
      margin-top: 0;
      border-left: 5px solid var(--accent);
    }}
    .main-finding p {{
      color: var(--text);
      font-size: 16px;
    }}
    .method-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .method-item {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
    }}
    .method-item strong {{
      display: block;
      margin-bottom: 4px;
    }}
    .insights {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
    }}
    .insights li {{
      margin: 8px 0;
    }}
    .section-note {{
      margin-bottom: 12px;
    }}
    .chart-wrap {{
      overflow-x: auto;
    }}
    svg {{
      display: block;
      height: auto;
    }}
    .chart-wrap svg {{
      max-width: none;
    }}
    table {{
      width: 100%;
      min-width: 980px;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .stability-table {{
      min-width: 1120px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th:not(:last-child), td:not(:last-child) {{
      white-space: nowrap;
    }}
    td:last-child {{
      min-width: 320px;
      overflow-wrap: anywhere;
    }}
    th {{
      color: var(--muted);
      font-weight: 650;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    details {{
      border-top: 1px solid var(--line);
      padding: 12px 0;
    }}
    details:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    summary {{
      cursor: pointer;
      font-weight: 650;
    }}
    pre {{
      white-space: pre-wrap;
      overflow-x: auto;
      padding: 12px;
      border-radius: 8px;
      background: #101828;
      color: #eef4ff;
      font-size: 13px;
    }}
    .error {{
      color: #b42318;
    }}
    @media (max-width: 760px) {{
      main {{
        width: min(100% - 20px, 1120px);
        padding-top: 20px;
      }}
      h1 {{ font-size: 28px; }}
      section {{ padding: 16px; }}
      .summary {{ grid-template-columns: 1fr 1fr; }}
      .method-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 480px) {{
      .summary {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>PacketScope Report</h1>
      <p>DNS lookup, TCP connection, TLS handshake, HTTP response, Ping RTT, packet loss, and traceroute comparison.</p>
    </header>

    <section class="main-finding">
      <h2>Main Finding</h2>
      <p>{main_finding}</p>
    </section>

    <section class="summary" aria-label="Summary">
      {_summary_card("Fastest", summary["fastest"])}
      {_summary_card("Slowest", summary["slowest"])}
      {_summary_card("Average RTT", summary["avg_rtt"])}
      {_summary_card("Average Hop Count", summary["avg_hops"])}
    </section>

    <section>
      <h2>Experiment Metadata</h2>
      {metadata}
    </section>

    <section>
      <h2>Measurement Method</h2>
      <div class="method-grid">
        <div class="method-item"><strong>DNS lookup</strong><span>Measures how long local name resolution takes with socket.getaddrinfo().</span></div>
        <div class="method-item"><strong>TCP connection</strong><span>Measures the time to establish a socket connection to the target host and port.</span></div>
        <div class="method-item"><strong>TLS handshake</strong><span>For HTTPS, measures the encrypted session setup before the HTTP request starts.</span></div>
        <div class="method-item"><strong>HTTP response</strong><span>Measures from sending the HTTP request to receiving the first response bytes. For HTTPS, this starts after TLS completes.</span></div>
        <div class="method-item"><strong>Ping and traceroute</strong><span>Ping reports RTT and packet loss. Traceroute reports visible routing hops; some hosts may hide or delay hop replies.</span></div>
      </div>
    </section>

    <section>
      <h2>Experiment Insights</h2>
      {insights}
    </section>

    <section>
      <h2>Stability Summary</h2>
      <p class="section-note">Repeated runs make the experiment more reproducible. Average fields show the mean; range and standard deviation fields show variation.</p>
      <div class="table-wrap">
        <table class="stability-table">
          <thead>
            <tr>
              <th>Target</th>
              <th>Runs</th>
              <th>Visible latency score</th>
              <th>Success rate</th>
              <th>DNS range</th>
              <th>TCP range</th>
              <th>HTTP range</th>
              <th>Avg RTT range</th>
              <th>RTT stdev</th>
              <th>Ping jitter</th>
            </tr>
          </thead>
          <tbody>{stability_rows}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Latency Comparison</h2>
      <div class="chart-wrap">{latency_chart}</div>
    </section>

    <section>
      <h2>Ping RTT Range</h2>
      <div class="chart-wrap">{ping_chart}</div>
    </section>

    <section>
      <h2>Hop Count</h2>
      <div class="chart-wrap">{hop_chart}</div>
    </section>

    <section>
      <h2>Detailed Results</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Target</th>
              <th>DNS ms</th>
              <th>TCP ms</th>
              <th>TLS ms</th>
              <th>HTTP ms</th>
              <th>Ping min ms</th>
              <th>Ping avg ms</th>
              <th>Ping max ms</th>
              <th>Ping jitter ms</th>
              <th>Success rate</th>
              <th>Packet loss</th>
              <th>Hops</th>
              <th>Status</th>
              <th>Error types</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Traceroute Paths</h2>
      {traces}
    </section>

    <section>
      <h2>Diagnostic Summary</h2>
      {diagnosis_summary}
    </section>

    <section>
      <h2>Observation Limits</h2>
      {observation_limits}
    </section>

    <section>
      <h2>Conclusion</h2>
      <p>{conclusion}</p>
    </section>
  </main>
</body>
</html>
"""


def _csv_row(result: MeasurementResult) -> dict:
    return {
        "target": result.target,
        "dns_ms": _empty_if_none(result.dns_ms),
        "tcp_ms": _empty_if_none(result.tcp_ms),
        "tls_ms": _empty_if_none(result.tls_ms),
        "http_ms": _empty_if_none(result.http_ms),
        "ping_min_ms": _empty_if_none(result.ping_min_ms),
        "ping_avg_ms": _empty_if_none(result.ping_avg_ms),
        "ping_max_ms": _empty_if_none(result.ping_max_ms),
        "ping_jitter_ms": _empty_if_none(result.ping_jitter_ms),
        "run_count": result.run_count,
        "dns_min_ms": _empty_if_none(result.dns_min_ms),
        "dns_max_ms": _empty_if_none(result.dns_max_ms),
        "tcp_min_ms": _empty_if_none(result.tcp_min_ms),
        "tcp_max_ms": _empty_if_none(result.tcp_max_ms),
        "http_min_ms": _empty_if_none(result.http_min_ms),
        "http_max_ms": _empty_if_none(result.http_max_ms),
        "ping_avg_min_ms": _empty_if_none(result.ping_avg_min_ms),
        "ping_avg_max_ms": _empty_if_none(result.ping_avg_max_ms),
        "ping_stdev_ms": _empty_if_none(result.ping_stdev_ms),
        "visible_latency_score_ms": _empty_if_none(result.visible_latency_score_ms),
        "success_rate_percent": _empty_if_none(result.success_rate_percent),
        "packet_loss_percent": _empty_if_none(result.packet_loss_percent),
        "hop_count": _empty_if_none(result.hop_count),
        "http_status": _empty_if_none(result.http_status),
        "error_types": ", ".join(result.error_types),
        "error": result.error_text,
    }


def _environment_metadata() -> dict:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packetscope_version": __version__,
    }


def _html_metadata(run_metadata: dict, environment: dict) -> str:
    run_items = [
        ("Command", run_metadata.get("command")),
        ("Targets", ", ".join(run_metadata.get("targets", [])) if run_metadata.get("targets") else None),
        ("Runs", run_metadata.get("runs")),
        ("Mock", run_metadata.get("mock")),
        ("Timeout", run_metadata.get("timeout")),
        ("Ping count", run_metadata.get("ping_count")),
        ("Max hops", run_metadata.get("max_hops")),
        ("Trace wait", run_metadata.get("trace_wait")),
        ("Trace timeout", run_metadata.get("trace_timeout")),
    ]
    env_items = [
        ("Python", environment.get("python_version")),
        ("Platform", environment.get("platform")),
        ("PacketScope", environment.get("packetscope_version")),
    ]
    items = run_items + env_items
    rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(str(value))}</td></tr>"
        for label, value in items
        if value is not None
    )
    if not rows:
        rows = '<tr><td colspan="2">No run metadata is available for this older result.</td></tr>'
    return f'<div class="table-wrap"><table><tbody>{rows}</tbody></table></div>'


def _html_diagnosis_summary(results: List[MeasurementResult]) -> str:
    diagnosis = diagnose_results(results)
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(item['target'])}</td>"
        f"<td>{html.escape(item['bottleneck_layer'])}</td>"
        f"<td>{_format_cell(item['bottleneck_value_ms'], suffix=' ms', none_text='N/A')}</td>"
        f"<td>{_format_cell(item['stability_score'], none_text='N/A')}</td>"
        f"<td>{html.escape(' | '.join(item['evidence']))}</td>"
        "</tr>"
        for item in diagnosis["targets"]
    )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>Target</th><th>Bottleneck</th><th>Value</th>"
        "<th>Stability score</th><th>Evidence chain</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _html_observation_limits() -> str:
    limits = [
        "A single local machine is one vantage point, not a global Internet view.",
        "Ping and traceroute depend on ICMP or probe replies, which can be filtered or deprioritized.",
        "Traceroute can hide intermediate hops, so missing hops do not always mean broken connectivity.",
        "HTTP first-byte timing is not the same as full browser page-load time.",
        "Real measurement failures are reported directly and are not replaced by mock data.",
    ]
    return "<ul class=\"insights\">" + "".join(
        f"<li>{html.escape(item)}</li>" for item in limits
    ) + "</ul>"


def _html_table_row(result: MeasurementResult) -> str:
    error_class = ' class="error"' if result.errors else ""
    return (
        "<tr>"
        f"<td>{html.escape(result.target)}</td>"
        f"<td>{_format_cell(result.dns_ms)}</td>"
        f"<td>{_format_cell(result.tcp_ms)}</td>"
        f"<td>{_format_cell(result.tls_ms)}</td>"
        f"<td>{_format_cell(result.http_ms)}</td>"
        f"<td>{_format_cell(result.ping_min_ms)}</td>"
        f"<td>{_format_cell(result.ping_avg_ms)}</td>"
        f"<td>{_format_cell(result.ping_max_ms)}</td>"
        f"<td>{_format_cell(result.ping_jitter_ms)}</td>"
        f"<td>{_format_cell(result.success_rate_percent, suffix='%')}</td>"
        f"<td>{_format_cell(result.packet_loss_percent, suffix='%')}</td>"
        f"<td>{_format_cell(result.hop_count)}</td>"
        f"<td>{_format_cell(result.http_status)}</td>"
        f"<td>{html.escape(', '.join(result.error_types) or '-')}</td>"
        f"<td{error_class}>{html.escape(result.error_text) or '-'}</td>"
        "</tr>"
    )


def _html_stability_row(result: MeasurementResult) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(result.target)}</td>"
        f"<td>{result.run_count}</td>"
        f"<td>{_format_cell(result.visible_latency_score_ms, suffix=' ms')}</td>"
        f"<td>{_format_cell(result.success_rate_percent, suffix='%')}</td>"
        f"<td>{_format_range(result.dns_min_ms, result.dns_max_ms, 'ms')}</td>"
        f"<td>{_format_range(result.tcp_min_ms, result.tcp_max_ms, 'ms')}</td>"
        f"<td>{_format_range(result.http_min_ms, result.http_max_ms, 'ms')}</td>"
        f"<td>{_format_range(result.ping_avg_min_ms, result.ping_avg_max_ms, 'ms')}</td>"
        f"<td>{_format_cell(result.ping_stdev_ms, suffix=' ms', none_text='N/A')}</td>"
        f"<td>{_format_cell(result.ping_jitter_ms, suffix=' ms', none_text='N/A')}</td>"
        "</tr>"
    )


def _html_trace(result: MeasurementResult) -> str:
    trace = result.traceroute_raw or "No traceroute output."
    return (
        "<details>"
        f"<summary>{html.escape(result.target)}"
        f" ({_format_cell(result.hop_count, none_text='N/A')} hops)</summary>"
        f"<pre>{html.escape(trace)}</pre>"
        "</details>"
    )


def _bar_chart(
    title: str,
    results: List[MeasurementResult],
    series: List[tuple[str, str, str]],
    unit: str,
) -> str:
    width = max(760, 160 + len(results) * max(120, len(series) * 44))
    height = 340
    left = 72
    bottom = 64
    top = 28
    chart_width = width - left - 32
    chart_height = height - top - bottom
    values = [
        float(getattr(result, attr))
        for result in results
        for _, attr, _ in series
        if getattr(result, attr) is not None
    ]
    max_value = max(values, default=1.0)
    if max_value <= 0:
        max_value = 1.0

    group_width = chart_width / max(1, len(results))
    bar_width = min(28, group_width / (len(series) + 1))
    parts = [
        f'<svg role="img" aria-label="{html.escape(title)}" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#b7c2d0"/>',
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - 24}" y2="{height - bottom}" stroke="#b7c2d0"/>',
        f'<text x="{left}" y="18" font-size="12" fill="#5d687a">{html.escape(unit)}</text>',
    ]

    for index, result in enumerate(results):
        group_x = left + index * group_width + group_width * 0.16
        label_y = height - 24
        parts.append(
            f'<text x="{group_x}" y="{label_y}" font-size="12" '
            f'fill="#384152">{html.escape(_short_label(result.target))}</text>'
        )
        missing_series = [
            label for label, attr, _ in series if getattr(result, attr) is None
        ]
        if missing_series:
            parts.append(
                f'<text x="{group_x}" y="{height - bottom - 10}" font-size="11" '
                f'fill="#9aa4b2">N/A</text>'
            )
        for series_index, (label, attr, color) in enumerate(series):
            value = getattr(result, attr)
            if value is None:
                continue
            bar_height = (float(value) / max_value) * (chart_height - 12)
            x = group_x + series_index * (bar_width + 8)
            y = height - bottom - bar_height
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="{bar_height:.1f}" rx="4" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{y - 6:.1f}" font-size="11" fill="#384152">'
                f'{float(value):.1f}</text>'
            )

    legend_x = left
    legend_y = height - 6
    for label, _, color in series:
        parts.append(f'<rect x="{legend_x}" y="{legend_y - 10}" width="10" height="10" fill="{color}"/>')
        parts.append(f'<text x="{legend_x + 16}" y="{legend_y}" font-size="12" fill="#384152">{html.escape(label)}</text>')
        legend_x += 92

    parts.append("</svg>")
    return "".join(parts)


def _summary(results: List[MeasurementResult]) -> dict:
    ranked = sorted(
        (result for result in results if _latency_score(result) is not None),
        key=lambda result: _latency_score(result) or 0,
    )
    rtts = [result.ping_avg_ms for result in results if result.ping_avg_ms is not None]
    hops = [result.hop_count for result in results if result.hop_count is not None]
    return {
        "fastest": ranked[0].target if ranked else "N/A",
        "slowest": ranked[-1].target if ranked else "N/A",
        "avg_rtt": f"{_avg(rtts):.1f} ms" if rtts else "N/A",
        "avg_hops": f"{_avg(hops):.1f}" if hops else "N/A",
    }


def _summary_card(label: str, value: str) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        "</div>"
    )


def _html_insights(results: List[MeasurementResult]) -> str:
    items = _insight_items(results)
    return "<ul class=\"insights\">" + "".join(
        f"<li>{html.escape(item)}</li>" for item in items
    ) + "</ul>"


def _insight_items(results: List[MeasurementResult]) -> List[str]:
    ranked = sorted(
        (result for result in results if _latency_score(result) is not None),
        key=lambda result: _latency_score(result) or 0,
    )
    if not ranked:
        return ["No target has enough successful measurements for comparison."]

    fastest = ranked[0]
    slowest = ranked[-1]
    items = [
        f"Fastest target: {fastest.target} with a combined visible latency of {_latency_score(fastest):.1f} ms.",
        f"Slowest target: {slowest.target}; its largest visible delay is {_dominant_metric(slowest)}.",
    ]
    missing_trace = [result.target for result in results if result.hop_count is None]
    if missing_trace:
        items.append(
            "Targets with missing traceroute data: "
            + ", ".join(missing_trace)
            + ". This usually means route hops did not answer before the timeout."
        )
    else:
        items.append("All targets returned visible traceroute hop counts.")
    items.append(_hop_relationship_note(results))
    items.append(_stability_note(results))
    return items


def _dominant_metric(result: MeasurementResult) -> str:
    metrics = [
        ("DNS lookup", result.dns_ms),
        ("TCP connection", result.tcp_ms),
        ("TLS handshake", result.tls_ms),
        ("HTTP response", result.http_ms),
        ("Ping RTT", result.ping_avg_ms),
    ]
    known = [(name, value) for name, value in metrics if value is not None]
    if not known:
        return "not available"
    name, value = max(known, key=lambda item: item[1])
    return f"{name} ({value:.1f} ms)"


def _hop_relationship_note(results: List[MeasurementResult]) -> str:
    paired = [
        result for result in results
        if result.hop_count is not None and result.ping_avg_ms is not None
    ]
    if len(paired) < 2:
        return "Not enough targets have both RTT and hop count to compare routing depth directly."
    highest_hops = max(paired, key=lambda result: result.hop_count)
    lowest_rtt = min(paired, key=lambda result: result.ping_avg_ms)
    if highest_hops.target == lowest_rtt.target:
        return (
            f"{highest_hops.target} has the most visible hops and also the lowest RTT, "
            "so fewer hops did not automatically mean faster RTT here."
        )
    return (
        f"{highest_hops.target} has the most visible hops, while {lowest_rtt.target} "
        "has the lowest RTT, so routing depth and RTT should be compared together."
    )


def _stability_note(results: List[MeasurementResult]) -> str:
    repeated = [result for result in results if result.run_count > 1]
    if not repeated:
        return (
            "This report uses one run per target; using --runs can reveal whether "
            "a target is consistently fast or only fast in one sample."
        )

    stable = [
        result for result in repeated
        if result.ping_stdev_ms is not None
    ]
    if not stable:
        return (
            "Repeated runs were recorded, but there are not enough successful "
            "ping RTT samples to compare stability."
        )

    best = min(stable, key=lambda result: result.ping_stdev_ms or 0)
    return (
        f"Across repeated runs, {best.target} has the lowest RTT variation "
        f"({best.ping_stdev_ms:.1f} ms), so it is the most stable target by "
        "this experiment's ping samples."
    )


def _latency_score(result: MeasurementResult) -> Optional[float]:
    values = [
        result.dns_ms,
        result.tcp_ms,
        result.tls_ms,
        result.http_ms,
        result.ping_avg_ms,
    ]
    known = [value for value in values if value is not None]
    if not known:
        return None
    return float(sum(known))


def _avg(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items)


def _empty_if_none(value):
    return "" if value is None else value


def _format_cell(value, suffix: str = "", none_text: str = "-") -> str:
    if value is None:
        return none_text
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _format_range(low, high, unit: str) -> str:
    if low is None and high is None:
        return "N/A"
    if low is None:
        return f"N/A - {_format_cell(high, suffix=' ' + unit)}"
    if high is None:
        return f"{_format_cell(low, suffix=' ' + unit)} - N/A"
    return f"{_format_cell(low, suffix=' ' + unit)} - {_format_cell(high, suffix=' ' + unit)}"


def _short_label(value: str) -> str:
    if len(value) <= 18:
        return value
    return value[:15] + "..."
