# PacketScope Submission Checklist

This checklist is the handoff page for the course submission. It points to the code, reports, screenshots, verification commands, and known limits.

## Code and Tests

- Source code: `packetscope/`
- Tests: `tests/test_packetscope.py`
- Final report: `docs/final-report.md`
- Report outline: `docs/final-report-outline.md`
- One-command demo: `Makefile`
- Main CLI commands: `scan`, `experiment`, `report`, `diagnose`, `compare`
- Test command:

```bash
python3 -m unittest
```

## Demo Commands

Stable mock demo:

```bash
make demo
```

Manual equivalent:

```bash
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
```

Real network experiment:

```bash
python3 -m packetscope experiment example.com cloudflare.com wikipedia.org github.com python.org --runs 3 --trace-wait 1 --trace-timeout 25 --out reports/real-runs
```

## Generated Artifacts

- Mock experiment: `reports/mock-runs/results.json`, `results.csv`, `report.html`
- Regenerated mock report: `reports/mock-runs-regenerated/results.json`, `results.csv`, `report.html`
- Diagnosis report: `reports/mock-diagnosis/diagnosis.json`, `diagnosis.csv`, `diagnosis.html`
- Compare report: `reports/mock-compare/compare.json`, `compare.csv`, `compare.html`
- Real-run attempt: `reports/real-runs/results.json`, `results.csv`, `report.html`

## Screenshots

- Main report screenshot: `reports/screenshots/mock-report.png`
- Diagnosis screenshot: `reports/screenshots/mock-diagnosis.png`
- Compare screenshot: `reports/screenshots/mock-compare.png`
- Real experiment screenshot: `reports/screenshots/real-report.png`

## What the Report Proves

- The first screen states a main finding: fastest target, slowest target, slowest-target bottleneck, and the RTT/hop-count interpretation.
- The tool separates DNS, TCP, TLS, HTTP, ping, packet loss, jitter, and traceroute evidence.
- Results are schema-versioned and include run parameters, environment metadata, timestamps, success rate, and error types.
- `diagnose` explains the most likely bottleneck layer, stability score, evidence chain, and observation limits.
- `compare` checks whether two saved experiments improved, regressed, or stayed stable with fixed 10 ms and 10% thresholds.
- Old result JSON files still regenerate because new result fields have defaults.

## Known Limits

- PacketScope measures from one local machine, not from global probes.
- Ping and traceroute depend on ICMP/probe visibility and can be filtered or delayed.
- HTTP first-byte timing is not a full browser page-load measurement.
- Real measurement failures are exposed as failures; PacketScope does not silently fall back to mock data.
- In the restricted sandbox, the real network command can fail with DNS-related errors. When run outside the sandbox, the current real experiment completed for all five targets and recorded partial traceroute visibility failures for some targets. Those failures are kept in `reports/real-runs/` instead of being replaced by mock data.
