# PacketScope

PacketScope is a local-first Network Measurement & Diagnostic Toolkit for a computer networking course project. It measures what happens when a client visits a website, then turns the results into reproducible experiment artifacts and an explanation of the visible network bottlenecks.

## Project Introduction

PacketScope was developed as a Wenzhou-Kean University CPS 4222 course project under the guidance of Dr. Ken Ehimwenma, Ph.D. The project explores practical Internet measurement by combining DNS, TCP, TLS, HTTP, ping, and traceroute checks into a reproducible toolkit for classroom demonstrations and network-performance analysis.

It measures:

- DNS lookup time
- TCP connection time
- TLS handshake time for HTTPS targets
- HTTP/HTTPS first-byte response time
- Ping RTT, jitter, and packet loss
- Traceroute hop count and route output
- Repeated-run stability, including min/max ranges and RTT variation

It writes:

- Terminal summary
- `results.json`
- `results.csv`
- `report.html`
- `diagnosis.json`, `diagnosis.csv`, and `diagnosis.html`
- `compare.json`, `compare.csv`, and `compare.html`

The project is intentionally small and reproducible: it uses only the Python standard library, keeps all measurements local to the machine running the command, and includes an explicit `--mock` path for stable classroom demos.

## Usage

Analyze one website:

```bash
python3 -m packetscope scan example.com --out reports/example
```

Run the default 5-site experiment:

```bash
python3 -m packetscope experiment --out reports/experiment
```

Run the default experiment three times per target and aggregate the results:

```bash
python3 -m packetscope experiment --runs 3 --out reports/experiment-runs
```

Run the experiment with faster traceroute limits:

```bash
python3 -m packetscope experiment --out reports/demo --trace-wait 1 --trace-timeout 25
```

Use custom experiment targets:

```bash
python3 -m packetscope experiment example.com github.com python.org --out reports/custom
```

Run without real network calls:

```bash
python3 -m packetscope experiment --mock --out reports/mock-demo
```

Run a reproducible multi-run classroom demo without real network calls:

```bash
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
```

Regenerate reports from an existing JSON result:

```bash
python3 -m packetscope report reports/demo/results.json --out reports/demo-v2
```

Generate a diagnosis from saved results:

```bash
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
```

Compare two saved experiments:

```bash
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

Run tests:

```bash
python3 -m unittest
```

Run the live bilingual web app:

```bash
python3 -m packetscope web --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

Run the full classroom demo pipeline with one command:

```bash
make demo
```

Preview the generated HTML report locally:

```bash
make preview
```

## Course Project Framing

PacketScope can be presented as a small version of an Internet measurement platform. Tools such as RIPE Atlas and Globalping use measurements like ping, traceroute, DNS, TLS, and HTTP to understand network reachability and performance from different vantage points. PacketScope keeps the same educational idea but uses one local machine so the implementation stays readable for a course project.

A good experiment should answer:

- Which target is fastest from this client?
- Is the visible delay mostly DNS, TCP, TLS, HTTP response time, or RTT?
- Are repeated measurements stable, or does RTT jitter across runs?
- Does a higher traceroute hop count always mean higher RTT?
- Which measurements failed, and what does that say about ICMP or traceroute visibility?
- Did the current experiment improve, regress, or stay stable compared with a baseline?

## Live Web Demo

PacketScope now includes a real bilingual web interface for teacher-facing demos:

- English / Chinese UI switch.
- Single website measurement.
- Two-website comparison.
- Real server-side DNS, TCP, TLS, HTTP, ping, and traceroute measurement.
- Layered latency visualization.
- Rule-based diagnosis using the same PacketScope engine as the CLI.
- Public-target safety checks so the online app does not measure localhost or private network addresses.

Start it locally:

```bash
make web
```

Open `http://127.0.0.1:8000`, enter a public URL such as `https://www.kean.edu`, and click **Run measurement**.

Important demo note: when deployed online, measurements are taken from the PacketScope server's network location, not from the browser user's laptop. This is a real networking concept called the measurement vantage point.

For deployment on a Python web-service host such as Render or Railway, use:

```bash
python3 -m packetscope web --host 0.0.0.0 --port $PORT
```

Some cloud platforms restrict ICMP or do not include `traceroute`. PacketScope keeps those failures visible in the result instead of replacing them with mock data.

## Result Schema

`results.json` uses schema version 2. The top level includes:

- `schema_version`: current result schema number.
- `generated_at`: report generation time.
- `run`: target list, run count, mock flag, timeout, ping, and traceroute parameters.
- `environment`: Python version, platform, and PacketScope version.
- `results`: one record per target.

Each target result keeps the original DNS/TCP/HTTP/Ping/Traceroute fields and also records TLS timing, ping jitter, success rate, error types, timing metadata, and duration. Old JSON files without schema v2 fields still regenerate.

## Report Interpretation

`report.html` includes:

- **Main Finding**: a first-screen answer naming the fastest and slowest target, the largest slow-target component, and the RTT/hop-count interpretation.
- **Measurement Method**: explains what each metric means.
- **Experiment Metadata**: records targets, run parameters, and environment.
- **Experiment Insights**: summarizes fastest and slowest targets.
- **Stability Summary**: shows run count, latency score, success rate, min/max ranges, jitter, and RTT standard deviation.
- **Latency Comparison**: compares DNS, TCP, TLS, and HTTP timing.
- **Ping RTT Range**: compares min, average, and max ping RTT.
- **Hop Count**: compares visible traceroute depth.
- **Traceroute Paths**: preserves raw route output for inspection.
- **Diagnostic Summary**: gives the most likely bottleneck layer, stability score, and evidence chain.
- **Observation Limits**: states what the local experiment can and cannot prove.
- **Conclusion**: connects the numbers to networking concepts and measurement limits.

## Demo Checklist

Use this short sequence for a stable classroom presentation:

```bash
make demo
```

Or run the commands manually:

```bash
python3 -m unittest
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

Then open `reports/mock-runs/report.html`, `reports/mock-diagnosis/diagnosis.html`, and `reports/mock-compare/compare.html`.

For final handoff, use `docs/submission-checklist.md` and `docs/final-report.md`. They list the code, tests, demo commands, generated reports, screenshots, results, and known limits.

## Notes

- This first version targets macOS and Linux.
- It uses only the Python standard library.
- `--mock` is explicit demo data. It is not used as a fallback for failed real measurements.
- Real traceroute can be slow because it waits for route hops to answer. Use `--trace-wait` and `--trace-timeout` to keep experiments bounded.
- For HTTPS targets, TLS is measured separately, and HTTP response time starts after TLS setup.
- Ping and traceroute are diagnostic signals, not perfect ground truth. ICMP traffic can be filtered or deprioritized, and some routers do not answer traceroute probes.
- A single local machine cannot represent global Internet performance. For this project, that limitation is part of the analysis: the tool measures one client vantage point clearly and reproducibly.
