# PacketScope Demo Script

## Goal

Show that PacketScope is more than a ping wrapper. It separates website latency into DNS, TCP, TLS, HTTP, RTT, jitter, packet loss, and routing visibility, then repeats measurements to discuss stability and comparison.

## 1. Open With the Problem

Say:

"When a website feels slow, the cause is not always the website itself. Delay can come from DNS lookup, TCP setup, TLS setup, server response time, network round-trip time, packet loss, or the route between client and server. PacketScope measures these pieces separately."

## 2. Prove the Code Is Testable

Run:

```bash
python3 -m unittest
```

Say:

"The tests cover target parsing, ping and traceroute parsing, TLS timing, jitter parsing, report generation, diagnosis, comparison, old report compatibility, and repeated-run aggregation."

## 3. Run a Stable Classroom Demo

Run:

```bash
make demo
```

If `make` is not available, run the pipeline manually:

```bash
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

Say:

"Mock mode is explicit demo data. It is not a fallback for failed real measurements. This keeps the presentation stable while showing the same report pipeline."

## 4. Regenerate the Report From JSON

If running manually, run:

```bash
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
```

Say:

"The JSON file is reusable. PacketScope can regenerate CSV and HTML reports from saved experiment data."

## 5. Generate Diagnosis and Comparison

If running manually, run:

```bash
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

Say:

"Diagnosis turns saved measurements into bottleneck, stability, evidence, and limitation statements. Compare checks whether two saved experiments improved, regressed, or stayed stable using fixed 10 ms and 10% thresholds."

## 6. Walk Through the HTML Report

Open:

```text
reports/mock-runs/report.html
reports/mock-diagnosis/diagnosis.html
reports/mock-compare/compare.html
```

Explain these sections:

- Main Finding: the one-paragraph answer naming the fastest target, slowest target, slowest-target bottleneck, and RTT/hop-count context.
- Summary cards: fastest, slowest, average RTT, average hop count.
- Experiment Metadata: targets, run count, mock flag, and environment.
- Measurement Method: what each layer means.
- Experiment Insights: automatic explanation of speed and bottlenecks.
- Stability Summary: run count, min/max ranges, jitter, success rate, RTT standard deviation, visible latency score.
- Latency Comparison: DNS, TCP, TLS, and HTTP bars.
- Ping RTT Range: min, average, and max RTT.
- Diagnostic Summary: most likely bottleneck layer, stability score, and evidence chain.
- Observation Limits: what one local machine can and cannot prove.
- Hop Count: visible routing depth.
- Traceroute Paths: raw route evidence.
- Conclusion: course concepts tied to results.

## 7. Optional Real Network Run

Run this only if the network is stable and there is enough time:

```bash
python3 -m packetscope experiment example.com cloudflare.com wikipedia.org github.com python.org --runs 3 --trace-wait 1 --trace-timeout 25 --out reports/real-runs
```

Say:

"Real traceroute can be slow or partially hidden. That is a real networking lesson, not just a tool bug."

## 8. Closing Line

Say:

"PacketScope demonstrates layered network measurement, reproducible experiments, and honest interpretation. It does not claim one local run represents the whole Internet; it shows what this client can observe and explains the limits of those observations."
