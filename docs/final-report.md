# PacketScope: Local Network Measurement and Diagnosis Workbench

## Abstract

PacketScope is a local-first network measurement toolkit for a computer networking course project. It measures the visible stages of visiting websites from one client machine, then generates reproducible JSON, CSV, HTML, diagnosis, and comparison artifacts. The tool focuses on evidence: DNS, TCP, TLS, HTTP first-byte response, ping RTT, jitter, packet loss, traceroute visibility, success rate, and explicit error types.

## 1. Problem

Website speed is not one number. A slow visit can come from name resolution, connection setup, TLS setup, server response time, network round-trip delay, packet loss, or routing path behavior. PacketScope separates those layers so the report can answer:

- Where is the visible delay?
- What evidence supports that answer?
- Is the result stable across repeated runs?
- What can this local machine not observe?

## 2. Related Work

PacketScope follows the same measurement idea as Internet measurement platforms, but keeps the scope local and readable for a course project.

- RIPE Atlas supports measurements such as ping, traceroute, DNS, TLS, and HTTP from distributed probes.
- Globalping shows that ping, traceroute, DNS, and HTTP can form a useful shared diagnostic platform.
- perfSONAR separates measurement, scheduling, archiving, configuration, and visualization.
- M-Lab NDT emphasizes measured performance, published data, and clear methodology.
- OpenTelemetry's observability framing inspires PacketScope's user-facing indicators such as latency, packet loss, stability, and success rate.

## 3. Method

For each target, PacketScope:

1. Normalizes a domain or URL.
2. Measures DNS lookup time.
3. Measures TCP connection time.
4. Measures TLS handshake time for HTTPS targets.
5. Measures HTTP first-byte response time after TLS setup.
6. Runs ping and parses min, average, max RTT, jitter, and packet loss.
7. Runs traceroute and preserves raw path output.
8. Repeats measurements when `--runs N` is used.
9. Writes schema-versioned JSON, CSV, HTML, diagnosis, and comparison reports.

The visible latency score is the sum of available DNS, TCP, TLS, HTTP, and average RTT values. It is not a full browser page-load time. It is a compact comparison of what this local client can observe. The HTML report now opens with a main finding that directly names the fastest target, slowest target, likely slowest-target bottleneck, and RTT/hop-count interpretation before the detailed tables.

## 4. Implementation

Main components:

- `packetscope/cli.py`: CLI for `scan`, `experiment`, `report`, `diagnose`, and `compare`.
- `packetscope/measure.py`: target parsing, measurements, ping/traceroute parsers, repeated-run aggregation, error classification.
- `packetscope/report.py`: schema v2 JSON, CSV, and HTML report generation.
- `packetscope/diagnose.py`: bottleneck layer, stability score, evidence chain, and observation limits.
- `packetscope/compare.py`: baseline/current comparison using fixed 10 ms and 10% thresholds.
- `tests/test_packetscope.py`: regression tests for parsers, schema compatibility, reports, diagnosis, comparison, and CLI behavior.
- `Makefile`: one-command classroom demo targets for tests, mock reports, diagnosis, comparison, preview, and real experiments.

Design choices:

- Python standard library only.
- Explicit `--mock` mode for deterministic classroom demos.
- No silent fallback from real failures to mock data.
- Old `results.json` files remain readable because new schema fields have defaults.
- High-load throughput testing is not part of the default tool.

## 5. Demo and Verification

Stable classroom demo:

```bash
make demo
```

Manual equivalent:

```bash
python3 -m unittest
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

Real network experiment:

```bash
python3 -m packetscope experiment example.com cloudflare.com wikipedia.org github.com python.org --runs 3 --trace-wait 1 --trace-timeout 25 --out reports/real-runs
```

Screenshots:

- `reports/screenshots/mock-report.png`
- `reports/screenshots/mock-diagnosis.png`
- `reports/screenshots/mock-compare.png`
- `reports/screenshots/real-report.png`

## 6. Results

The mock experiment confirms that the full artifact pipeline is stable and deterministic. All five mock targets have 100% success rate and produce JSON, CSV, HTML, diagnosis, comparison, and screenshots.

Current real experiment summary:

| Target | DNS ms | TCP ms | TLS ms | HTTP ms | Ping avg ms | Hops | Success | Error types |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| example.com | 80.0 | 893.0 | 469.8 | 527.5 | 245.7 | 12 | 100.0% | none |
| cloudflare.com | 69.4 | 192.0 | 393.7 | 206.4 | 201.6 | 14 | 100.0% | none |
| wikipedia.org | 135.7 | 212.9 | 427.9 | 216.3 | 212.6 | N/A | 83.3% | traceroute |
| github.com | 211.4 | 256.5 | 440.3 | 218.3 | 227.7 | N/A | 83.3% | traceroute |
| python.org | 75.6 | 210.1 | 431.6 | 218.9 | 224.8 | N/A | 83.3% | traceroute |

In this run, `example.com` had the highest visible latency score because TCP and HTTP timing were much higher than the other targets. `cloudflare.com` had lower TCP and HTTP timing than `example.com`, while still showing a visible traceroute path. For `wikipedia.org`, `github.com`, and `python.org`, PacketScope recorded successful DNS/TCP/TLS/HTTP/Ping measurements but also exposed traceroute visibility failures.

The key interpretation is that response time is layered. A site can have acceptable DNS time but still be slower because connection setup, TLS setup, RTT, or server first-byte response is larger. Hop count helps explain routing depth, but it does not by itself determine speed: a route with more visible hops can still have lower RTT than another route, and missing traceroute hops often mean routers did not answer probes rather than that the website was unreachable.

## 7. Diagnosis

The diagnosis report converts measurements into:

- Most likely bottleneck layer.
- Bottleneck value in milliseconds.
- Stability score.
- Success rate.
- Error types.
- Evidence chain.
- Observation limits.

This is rule-based and evidence-first. If no timing metrics are available, PacketScope reports `unknown` instead of guessing.

## 8. Limitations

- PacketScope measures from one local machine only.
- Results do not represent global Internet performance.
- Ping and traceroute can be filtered, delayed, or deprioritized.
- Missing traceroute hops do not always mean end-to-end connectivity failed.
- HTTP first-byte timing is not a full browser page-load measurement.
- Real measurements can fail because of network permissions, DNS, ICMP filtering, or local environment limits. PacketScope records those failures instead of replacing them with mock data.

## 9. Conclusion

PacketScope now acts like a small local network observability workbench. It keeps the original course-friendly `scan / experiment / report` workflow, adds reproducible schema v2 artifacts, and supports diagnosis and historical comparison. The project demonstrates layered measurement, repeated experiments, clear reports, honest failure handling, and explicit limits without adding heavy dependencies or unsafe high-load testing.
