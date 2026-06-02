# PacketScope Observability Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade PacketScope into a local-first network observability and diagnostic workbench while keeping the existing `scan`, `experiment`, and `report` flow stable.

**Architecture:** Keep the current standard-library Python package as the base. Add schema v2 metadata, richer per-target measurement fields, deterministic diagnosis and comparison helpers, and report rendering around the existing JSON/CSV/HTML pipeline.

**Tech Stack:** Python standard library, `unittest`, handcrafted HTML/SVG reports, no new third-party dependencies.

---

## Summary

- Keep `scan`, `experiment`, and `report` working.
- Add `diagnose RESULTS_JSON --out DIR`.
- Add `compare BASELINE_JSON CURRENT_JSON --out DIR`.
- Write `schema_version`, run metadata, and environment metadata into `results.json`.
- Add `tls_ms`, `ping_jitter_ms`, `success_rate_percent`, `error_types`, `started_at`, `finished_at`, and `duration_ms` to each result.
- Preserve old JSON regeneration by giving every new result field a default.

## Implementation Tasks

- [ ] Add tests for schema v2 payload metadata and old JSON compatibility.
- [ ] Add tests for TLS timing, ping jitter parsing, error classification, and aggregate success rate.
- [ ] Add diagnosis tests for bottleneck layer, stability score, evidence chain, limitations, and unknown cases.
- [ ] Add comparison tests for common, new, missing, improved, regressed, and stable targets.
- [ ] Add CLI tests for `diagnose` and `compare`.
- [ ] Implement measurement model changes in `packetscope/measure.py`.
- [ ] Implement diagnosis in `packetscope/diagnose.py`.
- [ ] Implement comparison in `packetscope/compare.py`.
- [ ] Extend report JSON/CSV/HTML output in `packetscope/report.py`.
- [ ] Wire new CLI commands and metadata handling in `packetscope/cli.py`.
- [ ] Update README, demo script, and final report outline.
- [ ] Run final verification commands from the user plan.

## Acceptance Commands

```bash
python3 -m unittest
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
python3 -m packetscope experiment example.com cloudflare.com wikipedia.org github.com python.org --runs 3 --trace-wait 1 --trace-timeout 25 --out reports/real-runs
```

## Assumptions

- No new branch, worktree, Git history operation, or dependency.
- User-visible CLI and report text remain English.
- Real measurement failures are recorded and exposed; they never auto-switch to mock data.
- The local repository root is not isolated from the user home Git root, so do not stage or commit automatically.
