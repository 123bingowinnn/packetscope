# PacketScope Online Teacher Demo Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real online bilingual PacketScope demo where a teacher can enter any website, run live measurements from the deployed server, and see visual DNS/TCP/TLS/HTTP/ping/traceroute diagnosis.

**Architecture:** Keep the existing PacketScope measurement engine as the core, then wrap it with a small web application: a browser frontend for input/visualization and a Python backend API that runs real measurements server-side. The deployed app should be honest that the measurements come from the server's network location, not from the teacher's laptop.

**Tech Stack:** Existing Python PacketScope code, Python HTTP backend, React/Vite frontend or a lightweight server-rendered page, bilingual UI strings, deployable Python web service on a platform that allows outbound network calls and subprocess-based diagnostics.

---

## Updated Demo Direction

The earlier idea was a static generated showcase page. That is stable, but it still feels like "showing an HTML report." The stronger direction is a real online measurement lab:

1. The teacher opens a deployed URL.
2. The page supports English / Chinese switching.
3. The teacher enters a website, for example:
   - `kean.edu`
   - the school portal
   - `github.com`
   - `python.org`
   - `wikipedia.org`
4. The server runs real PacketScope measurements.
5. The page animates the measurement pipeline:
   - DNS
   - TCP
   - TLS
   - HTTP first byte
   - Ping RTT
   - Traceroute hops
6. The page shows a visual diagnosis:
   - fastest / slowest stage
   - bottleneck layer
   - success rate
   - traceroute visibility
   - plain-language explanation
7. The page can export or link to the original JSON/CSV/HTML report artifacts.

This makes the project feel like a real tool instead of a submitted report.

## Product Concept

Working name:

```text
PacketScope Live Lab
```

Chinese name option:

```text
PacketScope 实时网络观测台
```

One-sentence positioning:

```text
Enter a website. PacketScope breaks the connection into DNS, TCP, TLS, HTTP, ping, and traceroute evidence, then explains where the delay appears.
```

Chinese:

```text
输入一个网站，PacketScope 会把访问过程拆成 DNS、TCP、TLS、HTTP、Ping 和 Traceroute，并解释延迟主要出现在哪一层。
```

## Teacher-Facing User Flow

### First Screen

The first screen should not look like a marketing page. It should look like a usable tool.

Recommended layout:

```text
Top bar:
PacketScope Live Lab                    EN / 中文

Main input area:
[ https://www.kean.edu                    ] [Run Measurement]

Quick examples:
Kean University | GitHub | Python | Wikipedia | Cloudflare

Live status:
Waiting for target...
```

After the user clicks "Run Measurement", the page changes into a live measurement workspace.

### During Measurement

Show a step-by-step progress rail:

```text
DNS lookup -> TCP connect -> TLS handshake -> HTTP response -> Ping -> Traceroute -> Diagnosis
```

Each step can have states:

```text
waiting / running / done / failed
```

This is important for presentation. Even if the measurement takes 15-30 seconds, the teacher sees that the system is doing real work.

### Result Screen

Show the answer first:

```text
Main finding:
The largest visible delay for www.kean.edu is HTTP response time.
```

Then show:

- Layer timing bars.
- Ping RTT range.
- Packet loss.
- Hop count.
- HTTP status.
- Error types, if any.
- Raw traceroute in a collapsible panel.
- "What this means" bilingual explanation.

### Comparison Mode

For more interest, add a "Compare two websites" mode:

```text
Target A: kean.edu
Target B: github.com
[Compare]
```

This is likely more engaging than one target because the teacher immediately sees contrast:

- Which site has faster DNS?
- Which site has slower TLS?
- Which one has lower RTT?
- Does hop count match speed?

This can reuse the existing `experiment` logic.

## What Makes It Interesting

### 1. Let The Teacher Pick The Target

The best live moment is:

> "Professor, give us a website. We can measure it now."

This makes the demo feel real.

Good prepared examples:

- School homepage.
- Course LMS page, if publicly reachable.
- `github.com`
- `python.org`
- `cloudflare.com`
- `wikipedia.org`

Avoid private login pages during the demo. Use public pages so HTTP/TLS timing is meaningful and there are no privacy issues.

### 2. Explain "This Is From Our Server's Viewpoint"

If deployed online, the measurement is not from the teacher's laptop. It is from the deployment server.

The UI should include a small note:

```text
Measurements are taken from the PacketScope server's network location.
```

Chinese:

```text
测量结果来自 PacketScope 服务器所在的网络位置，而不是当前浏览器所在的电脑。
```

This is not a weakness. It is a chance to talk about "vantage point", which is a real networking concept.

### 3. Make Failures Part Of The Demo

Some real network measurements will fail:

- ICMP ping may be blocked.
- Traceroute may show missing hops.
- TLS can fail on unusual servers.
- Some platforms may restrict subprocess tools.

The UI should frame this as observability:

```text
Traceroute visibility is partial. This usually means some routers did not answer probes; it does not mean the website is unreachable.
```

That is more impressive than hiding failures.

### 4. Add A "Networking Concepts" Explanation Panel

For each layer, add a short bilingual explanation:

| Layer | English | 中文 |
|---|---|---|
| DNS | Converts a domain name into an IP address. | 把域名解析成 IP 地址。 |
| TCP | Establishes a connection to the server. | 和服务器建立连接。 |
| TLS | Sets up encrypted HTTPS communication. | 建立 HTTPS 加密通信。 |
| HTTP | Time until the server sends the first response bytes. | 服务器开始返回响应前的等待时间。 |
| Ping | Measures round-trip delay using ICMP. | 使用 ICMP 测量往返延迟。 |
| Traceroute | Shows visible routing hops. | 显示可见的路由跳数。 |

This helps the teacher see the course knowledge behind the tool.

## Deployment Reality Check

### Static hosting is not enough

A purely static site cannot run real DNS/TCP/TLS/ping/traceroute measurements from the browser. Browser JavaScript cannot open raw TCP sockets, run `ping`, or run `traceroute`.

### Cloudflare Workers is probably not the best fit

Cloudflare Workers supports HTTP-style workloads and has outbound TCP socket support, but it is not a normal Linux host where we can run the existing Python measurement code, `ping`, and `traceroute`. Cloudflare's own docs describe Workers protocol/runtime limits and outbound TCP support, but this project needs a server-like runtime for subprocess diagnostics. Sources checked: Cloudflare Workers protocol support and limits docs. [Cloudflare Workers protocols](https://developers.cloudflare.com/workers/reference/protocols/), [Cloudflare Workers limits](https://developers.cloudflare.com/workers/platform/limits/)

### Better deployment fit

Use a Python web service host where the existing project can run as a server process.

Good candidates to verify in implementation:

- Render Web Service: official docs support Python web services such as Django/FastAPI-style apps. [Render Web Services](https://render.com/docs/web-services/), [Render Deploys](https://render.com/docs/deploys/)
- Railway: official docs support deploying apps from the CLI and build/deploy workflows. [Railway Deploying with CLI](https://docs.railway.com/cli/deploying)
- A small VPS: most realistic for `ping` and `traceroute`, but more setup work.

Recommended first try:

```text
Render or Railway for the web app; if ping/traceroute are restricted, keep DNS/TCP/TLS/HTTP live and show ping/traceroute as "server environment restricted" instead of faking it.
```

Most robust technical option:

```text
Deploy on a small VPS where we control the OS packages and can install traceroute.
```

## Architecture Options

### Option A: Fastest Real Online MVP

Backend:

- Python standard-library HTTP server or Flask/FastAPI if we allow dependencies.
- Endpoint:

```text
POST /api/measure
{ "targets": ["https://www.kean.edu"], "runs": 1 }
```

Response:

```text
{
  "results": [...],
  "diagnosis": {...}
}
```

Frontend:

- React + Vite dashboard.
- Bilingual string dictionary.
- Form input.
- Loading states.
- Charts built with CSS/SVG, no heavy chart dependency.

Pros:

- Feels like a real product.
- Strong visual presentation.
- Easy to deploy if using a Python service host.

Cons:

- Requires adding a web stack.
- Deployment environment may limit ping/traceroute.

### Option B: Server-Rendered Minimal Web App

Backend:

- Python `http.server` style custom handler.
- Generate HTML directly.
- Form submits target to server.

Pros:

- Keeps "standard library only" story.
- Minimal dependencies.

Cons:

- Harder to make polished bilingual interactive UI.
- Less modern-looking.

### Option C: Local App During Presentation

Run locally:

```bash
python3 -m packetscope web
```

Then open:

```text
http://127.0.0.1:8000
```

Pros:

- Measurements come from your laptop/classroom network.
- Existing ping/traceroute likely work better.
- No deployment risk.

Cons:

- Not truly online.
- Need to run server before presentation.

## Recommendation

Build Option A, but keep Option C as backup.

Final demo plan:

1. Deploy the online app.
2. Teacher enters a real website.
3. App runs real measurements from the server.
4. If cloud environment blocks ping/traceroute, the app still shows DNS/TCP/TLS/HTTP live and marks ICMP/traceroute as restricted.
5. Keep local mode ready for a stronger "from this laptop/network" demo.

This gives you both:

- online shareable product feel
- reliable fallback for the actual classroom

## Revised Presentation Flow

### 1. Opening, 20 seconds

English:

> PacketScope is a live network measurement lab. Instead of showing only whether a website is reachable, it breaks the connection into DNS, TCP, TLS, HTTP, ping, and traceroute evidence.

中文：

> PacketScope 是一个实时网络观测工具。它不只是告诉我们网站能不能打开，而是把访问过程拆成 DNS、TCP、TLS、HTTP、Ping 和 Traceroute 几个层次。

### 2. Teacher Input, 30 seconds

Ask:

> Could you give us a public website to measure?

中文：

> 老师可以给我们一个公开的网站，我们现场测一下。

### 3. Live Pipeline, 60-90 seconds

Show the pipeline while it runs.

Explain:

> Each stage is measured separately, so we can see whether the delay comes from name lookup, connection setup, encryption, server response, round-trip time, or route visibility.

### 4. Diagnosis, 60 seconds

Show the main finding and bottleneck.

Explain:

> PacketScope does not guess. It uses the largest visible metric, success rate, jitter, packet loss, and recorded errors to produce an evidence-based diagnosis.

### 5. Compare, 60 seconds

Run school website vs `github.com` or `cloudflare.com`.

Explain:

> This comparison shows that hop count and speed are related but not identical. Network performance depends on many layers.

### 6. Closing, 20 seconds

Explain:

> The important part is reproducibility. The same tool can run live, export JSON/CSV/HTML, and keep failures visible instead of hiding them.

## Revised File Structure

### Create: `web/`

A new web app folder.

Possible structure:

```text
web/
  package.json
  index.html
  src/
    App.jsx
    api.js
    i18n.js
    styles.css
```

Responsible for:

- Bilingual UI.
- Target input.
- Measurement progress.
- Charts and diagnosis display.

### Create: `packetscope/server.py`

Responsible for:

- Serving API requests.
- Calling existing `measure_target`, `aggregate_measurement_runs`, and `diagnose_results`.
- Returning JSON.
- Applying safety limits.

### Modify: `packetscope/cli.py`

Add:

```bash
python3 -m packetscope web --host 127.0.0.1 --port 8000
```

Optional if we use a framework:

```bash
python3 -m packetscope api
```

### Modify: `Makefile`

Add:

```bash
make web
make build-web
```

### Create: deployment files

Depending on chosen host:

```text
requirements.txt
Procfile or render.yaml or railway.json
```

## Safety Constraints

Because this becomes a public measurement tool, the API must be limited.

Required:

- Only allow `http://` and `https://` URLs or plain domains.
- Reject private/local IP ranges:
  - `127.0.0.0/8`
  - `10.0.0.0/8`
  - `172.16.0.0/12`
  - `192.168.0.0/16`
  - `localhost`
  - link-local addresses
- Limit target count:

```text
1 target for single mode, 2 targets for compare mode.
```

- Limit runs:

```text
1 live run by default, maybe 3 only for local/demo mode.
```

- Limit traceroute timeout.
- Add request timeout.
- Do not store user input permanently.

This matters because an online measurement tool can otherwise be abused as a scanner.

## Open Decisions

1. Use React/Vite frontend or standard-library server-rendered HTML?
2. Deploy first to Render, Railway, or VPS?
3. Keep dependencies minimal, or allow Flask/FastAPI for a cleaner backend?
4. Should compare mode be part of v1, or added after single-target mode works?
5. Should the public deployment disable traceroute if the platform is unreliable?

## Strong Recommendation

Build v1 as:

```text
React/Vite frontend + Python API backend + real live measurement + bilingual UI + local fallback.
```

Feature priority:

1. Single target live measurement.
2. Bilingual English/Chinese switch.
3. Visual layer chart.
4. Diagnosis explanation.
5. Compare two targets.
6. Export JSON/CSV/HTML links.

Do not start with authentication, databases, user accounts, historical storage, or complex dashboards. The goal is not to build a full SaaS product. The goal is to make the course project feel alive and technically convincing.

---

## Previous Static Showcase Notes

The original static showcase idea below is kept for reference, but it is no longer the recommended main direction.

## Demo Direction

### 1. Opening, 20-30 seconds

Say:

> PacketScope is a local network measurement and diagnosis toolkit. Instead of saying "this website feels slow", it breaks the visit into DNS, TCP, TLS, HTTP response, ping RTT, packet loss, and traceroute evidence.

Show:

- Demo showcase first screen.
- A clear "fastest vs slowest" summary.
- One visible latency score comparison.

### 2. Measurement Pipeline, 45-60 seconds

Show a horizontal pipeline:

```text
Input target -> DNS -> TCP -> TLS -> HTTP -> Ping -> Traceroute -> Report
```

Say:

> Each step is measured separately, so the tool can explain where the delay appears instead of only giving one total time.

### 3. Visualization, 60-90 seconds

Show:

- Stacked or grouped latency bars for DNS/TCP/TLS/HTTP/Ping.
- Ping RTT range.
- Hop count / traceroute visibility.
- Success rate and error types.

Say:

> The visualization lets us compare targets quickly. For example, a site might have normal DNS but slower TCP or HTTP response. Hop count helps, but it does not perfectly predict RTT.

### 4. Diagnosis, 45-60 seconds

Show:

- Bottleneck layer per target.
- Evidence chain.
- Stability score.
- Observation limits.

Say:

> The diagnosis is rule-based and evidence-first. If there is not enough data, it reports unknown instead of guessing.

### 5. Comparison, 30-45 seconds

Show:

- Baseline vs current score.
- Improved / regressed / stable labels.
- New or missing targets.

Say:

> This turns PacketScope from a one-time report into a repeatable experiment tool.

### 6. Closing, 20-30 seconds

Say:

> The important design choice is honesty: mock mode is deterministic for classroom demos, real mode records real failures, and PacketScope never silently replaces failed real measurements with fake data.

## Proposed Demo Artifact

Create a new generated static page:

```text
reports/showcase/index.html
```

It should include:

- Header: "PacketScope Demo Showcase"
- Summary cards:
  - Fastest target
  - Slowest target
  - Main bottleneck
  - Average success rate
- Layer pipeline visualization
- Latency comparison chart
- Target detail table
- Diagnosis cards
- Comparison summary
- Links to:
  - `reports/mock-runs/report.html`
  - `reports/mock-diagnosis/diagnosis.html`
  - `reports/mock-compare/compare.html`
  - `reports/mock-runs/results.json`
  - `reports/mock-runs/results.csv`

The page should read from generated mock artifacts or be generated after `make demo`.

## File Structure

### Create: `packetscope/showcase.py`

Responsible for:

- Loading `results.json`, `diagnosis.json`, and `compare.json`.
- Computing the showcase summary.
- Generating a static `index.html`.
- Keeping all output self-contained so it can be opened directly in a browser.

### Modify: `packetscope/cli.py`

Add a new command:

```bash
python3 -m packetscope showcase \
  --results reports/mock-runs/results.json \
  --diagnosis reports/mock-diagnosis/diagnosis.json \
  --compare reports/mock-compare/compare.json \
  --out reports/showcase
```

### Modify: `Makefile`

Add a target:

```bash
make showcase
```

This should run the deterministic demo pipeline and generate the showcase page.

### Modify: `README.md`

Add a short "Teacher Demo Showcase" section with:

- One command to generate it.
- Which file to open.
- Suggested presentation order.

### Modify: `tests/test_packetscope.py`

Add focused tests for:

- Showcase HTML file creation.
- Summary includes fastest/slowest target.
- Showcase links to report, diagnosis, compare, JSON, and CSV.
- CLI `showcase` command works with temporary sample files.

## Visual Style

The showcase should feel like a clean technical dashboard:

- Light background.
- Compact summary cards.
- Clear charts.
- Minimal text.
- No marketing landing page.
- No decorative effects that distract from the data.

Suggested sections:

```text
PacketScope Demo Showcase
Main finding
Measurement pipeline
Latency by layer
Diagnosis
Baseline comparison
Open the full artifacts
```

## Chunk 1: Confirm Demo Scope

### Task 1: Choose The Demo Mode

**Files:**
- Modify later: `README.md`
- Create later: `packetscope/showcase.py`

- [ ] **Step 1: Confirm whether the showcase should use mock data, real data, or both**

Recommended choice:

```text
Use mock data for the live classroom demo, and keep real results as a secondary artifact.
```

Reason:

Mock data avoids Wi-Fi, DNS, ICMP, and traceroute failures during presentation. Real data can still be shown as proof that the system supports actual measurements.

- [ ] **Step 2: Confirm whether the page should be English or bilingual**

Recommended choice:

```text
English UI, Chinese speaker notes.
```

Reason:

The submitted report and existing generated pages are English. Chinese notes help the team present naturally.

- [ ] **Step 3: Confirm presentation length**

Recommended choice:

```text
3-5 minutes.
```

Reason:

This is enough to show the pipeline, charts, diagnosis, and comparison without getting trapped in implementation details.

## Chunk 2: Generate Showcase Page

### Task 2: Add Showcase Generator

**Files:**
- Create: `packetscope/showcase.py`
- Test: `tests/test_packetscope.py`

- [ ] **Step 1: Write a failing test for showcase output**

Expected behavior:

```text
write_showcase(...) creates reports/showcase/index.html.
The HTML includes PacketScope Demo Showcase, fastest target, slowest target, and links to existing artifacts.
```

- [ ] **Step 2: Implement `write_showcase`**

Implementation notes:

- Use `json.loads(path.read_text(encoding="utf-8"))`.
- Use `html.escape`.
- Use existing result fields from schema v2.
- Avoid external dependencies.

- [ ] **Step 3: Run tests**

Run:

```bash
python3 -m unittest
```

Expected:

```text
OK
```

## Chunk 3: CLI And Makefile

### Task 3: Add `showcase` Command

**Files:**
- Modify: `packetscope/cli.py`
- Modify: `Makefile`
- Test: `tests/test_packetscope.py`

- [ ] **Step 1: Add CLI parser**

Command shape:

```bash
python3 -m packetscope showcase \
  --results reports/mock-runs/results.json \
  --diagnosis reports/mock-diagnosis/diagnosis.json \
  --compare reports/mock-compare/compare.json \
  --out reports/showcase
```

- [ ] **Step 2: Add `make showcase`**

Expected behavior:

```text
make showcase
```

Runs:

```bash
python3 -m unittest
python3 -m packetscope experiment --mock --runs 3 --out reports/mock-runs
python3 -m packetscope diagnose reports/mock-runs/results.json --out reports/mock-diagnosis
python3 -m packetscope report reports/mock-runs/results.json --out reports/mock-runs-regenerated
python3 -m packetscope compare reports/mock-runs/results.json reports/mock-runs-regenerated/results.json --out reports/mock-compare
python3 -m packetscope showcase --results reports/mock-runs/results.json --diagnosis reports/mock-diagnosis/diagnosis.json --compare reports/mock-compare/compare.json --out reports/showcase
```

- [ ] **Step 3: Test the full pipeline**

Run:

```bash
make showcase
```

Expected:

```text
reports/showcase/index.html exists and opens locally.
```

## Chunk 4: Presentation Script

### Task 4: Add Demo Script

**Files:**
- Modify: `docs/demo-script.md`
- Modify: `README.md`

- [ ] **Step 1: Add a 3-5 minute speaking script**

Include:

- Opening line.
- Pipeline explanation.
- Visualization explanation.
- Diagnosis explanation.
- Compare explanation.
- Limitations.
- Closing line.

- [ ] **Step 2: Add exact commands**

Include:

```bash
make showcase
open reports/showcase/index.html
```

On non-macOS systems:

```bash
python3 -m http.server 8000
```

- [ ] **Step 3: Verify documentation matches actual commands**

Run:

```bash
python3 -m unittest
make showcase
```

Expected:

```text
All tests pass and showcase artifacts exist.
```

## Open Questions For The Team

1. Should the demo UI be English-only, or English UI with Chinese speaker notes?
2. Do you want a simple generated static page, or a more interactive page with tabs and collapsible sections?
3. Will the teacher watch this on your laptop, or do you need a shareable folder/zip that opens anywhere?
4. Do you want to show only deterministic mock data live, or also run a real network scan during the presentation?
5. How long is the expected demo slot: 3 minutes, 5 minutes, or longer?

## Recommendation

Use a deterministic mock-based showcase as the main live demo. Keep real network results in the project as supporting evidence, but do not depend on live network behavior during the presentation.

This gives the teacher a clean visual experience and still demonstrates the real technical work:

- CLI design
- Network layer measurement
- TLS/HTTP timing separation
- Ping/traceroute parsing
- Repeated-run aggregation
- Schema-versioned artifacts
- Diagnosis rules
- Baseline comparison
- Static visualization generation
