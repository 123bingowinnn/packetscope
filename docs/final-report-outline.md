# PacketScope Final Report Outline

## Title

PacketScope: A Local Network Measurement Toolkit for Website Latency, Routing, and Stability Analysis

## Abstract

Briefly explain that PacketScope measures DNS lookup time, TCP connection time, TLS handshake time, HTTP/HTTPS first-byte response time, ping RTT, jitter, packet loss, and traceroute paths from one local client. State the main contribution: a reproducible command line experiment that generates JSON, CSV, HTML, diagnosis, and comparison reports with charts and networking explanations.

## 1. Introduction

Motivate the problem: website speed is not one number. A slow visit can come from DNS delay, connection setup, TLS setup, server response time, round-trip delay, packet loss, or routing path behavior.

State the project goal: build a small, local-first network measurement tool that helps students connect course concepts to real measurements.

## 2. Background and Related Work

Explain these concepts in simple terms:

- DNS translates a name into network addresses.
- TCP connection time shows transport-layer setup cost.
- TLS handshake time shows HTTPS security setup cost.
- HTTP response time shows how quickly the server begins returning data after the request is sent.
- Ping estimates round-trip time, jitter, and packet loss.
- Traceroute uses packet lifetime behavior to reveal visible hops along a path.

Mention related systems:

- RIPE Atlas performs measurements such as ping, traceroute, DNS, TLS, and HTTP from many probes.
- Globalping is a community-driven platform for ping, traceroute, and DNS measurements from distributed probes.
- PacketScope keeps the same measurement idea but limits scope to one local client for a readable course implementation.

## 3. Methodology

Describe the measurement pipeline:

1. Normalize a target domain or URL.
2. Measure DNS lookup time with local name resolution.
3. Measure TCP connection time to the target host and port.
4. For HTTPS, measure TLS handshake time.
5. Measure HTTP or HTTPS first-byte response time after TLS setup.
6. Run ping and parse min, average, max RTT, jitter, and packet loss.
7. Run traceroute and preserve the raw route output.
8. Repeat each target when `--runs N` is used.
9. Aggregate averages, min/max ranges, RTT standard deviation, success rate, error types, and visible latency score.

Define the visible latency score as the sum of available DNS, TCP, TLS, HTTP, and average RTT values. Explain that it is not a full page-load time; it is a compact comparison of visible network-layer and request-start latency.

Explain that schema version 2 records run parameters, environment metadata, measurement timestamps, duration, success rate, and error types. Old result files remain readable.

## 4. Implementation

Describe the main components:

- `packetscope/cli.py`: command line interface for `scan`, `experiment`, `report`, `diagnose`, and `compare`.
- `packetscope/measure.py`: target normalization, measurement collection, parsing, and repeated-run aggregation.
- `packetscope/report.py`: JSON, CSV, and HTML report generation.
- `packetscope/diagnose.py`: deterministic bottleneck, stability, evidence, and limitation generation.
- `packetscope/compare.py`: baseline/current comparison using fixed 10 ms and 10% thresholds.
- `tests/test_packetscope.py`: regression tests for parsers, reports, diagnosis, comparison, CLI behavior, old JSON compatibility, and repeated-run aggregation.

Emphasize the design choices:

- Python standard library only.
- Explicit `--mock` mode for deterministic demos.
- No silent fallback from failed real measurements to mock data.
- Old `results.json` files remain readable.
- Failures are exposed through `errors` and `error_types`.

## 5. Experiment

Use this demo command:

```bash
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
```

Then regenerate, diagnose, and compare:

```bash
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

For a real network experiment, use:

```bash
python3 -m packetscope experiment example.com cloudflare.com wikipedia.org github.com python.org --runs 3 --trace-wait 1 --trace-timeout 25 --out reports/real-runs
```

Report these outputs:

- `results.json` for raw structured data.
- `results.csv` for spreadsheet analysis.
- `report.html` for charts and explanation.
- `diagnosis.html` for bottleneck, stability, evidence, and limits.
- `compare.html` for baseline/current changes.

## 6. Results and Analysis

Discuss:

- Fastest and slowest target by visible latency score.
- Dominant bottleneck layer for the slowest target.
- Whether TLS setup is visible and meaningful for HTTPS targets.
- Whether RTT and hop count move together.
- Whether repeated runs are stable by RTT standard deviation and jitter.
- Which targets had missing traceroute data or failed measurements.
- Whether the regenerated baseline/current comparison is stable.

Use screenshots from `report.html` for the final submission.

## 7. Limitations

State these clearly:

- One local machine is one vantage point, not a global measurement network.
- Ping and traceroute depend on ICMP or probe responses, which can be filtered or deprioritized.
- Traceroute can hide intermediate hops.
- TLS timing is measured for HTTPS but still does not represent full browser page-load behavior.
- HTTP first-byte response time is not the same as full browser page load time.
- Diagnosis is rule-based and evidence-first; when measurements are missing, it reports `unknown` rather than guessing.

## 8. Conclusion

Summarize what PacketScope demonstrates: layered network measurement, reproducible experiments, route visibility, stability analysis, and honest measurement limits.

## References

- RIPE Atlas documentation: Internet measurement probes and built-in measurements.
- Globalping paper: community-driven ping, traceroute, and DNS measurement platform.
- APNIC Blog: practical interpretation of traceroute and MTR output.
