const strings = {
  en: {
    appTitle: "PacketScope",
    appSubtitle: "Website Network Diagnostics",
    serverReady: "Live server",
    productLine: "Live website diagnostics",
    heroTitle: "Find out why a website feels slow.",
    heroCopy: "Measure the real network path behind a website visit, then see which layer added the most visible delay.",
    stepOneTitle: "Choose a website",
    stepOneCopy: "Enter any public URL that you want to inspect.",
    stepTwoTitle: "Measure the visit",
    stepTwoCopy: "PacketScope checks DNS, TCP, TLS, HTTP, ping, and traceroute from this server.",
    stepThreeTitle: "Read the bottleneck",
    stepThreeCopy: "Start with the verdict, then inspect the evidence behind it.",
    checkupTitle: "Check a website",
    checkupCopy: "Run a live network measurement. Use Single for one URL, or Compare to measure two URLs side by side.",
    singleMode: "One site",
    compareMode: "Compare two",
    targetLabel: "Website URL",
    targetBLabel: "Second website URL",
    runButton: "Run network check",
    runningButton: "Checking...",
    examplesLabel: "Examples",
    vantageTitle: "Measurement location",
    journeyKicker: "Network journey",
    journeyTitle: "How PacketScope breaks down a website visit",
    journeyCopy: "Each measurement separates address lookup, connection setup, encryption, server response, round-trip delay, and route visibility.",
    conceptDns: "Finds the website address.",
    conceptTcp: "Opens the connection.",
    conceptTls: "Secures HTTPS traffic.",
    conceptHttp: "Waits for the server.",
    conceptRtt: "Measures round-trip delay.",
    conceptRoute: "Reveals visible hops.",
    originNote: "Results reflect the PacketScope server's network location, so they may differ from measurements made on your own device.",
    runningKicker: "Live measurement in progress",
    pipelineTitle: "PacketScope is measuring the network path.",
    progressCaption: "Ping and traceroute can take longer because they wait for network replies.",
    executionTitle: "Live execution log",
    executionCopy: "These events come from the PacketScope server while it runs each network check.",
    streamIdle: "Waiting",
    streamRunning: "Running",
    streamComplete: "Complete",
    streamError: "Error",
    elapsedLabel: "Elapsed",
    errorTitle: "Measurement error",
    answerKicker: "Result in plain language",
    mainFinding: "Analysis verdict",
    resultsTitle: "Measurement Results",
    resultsCopy: "Review the verdict, compare the timing layers, and inspect the raw evidence.",
    downloadJson: "Download JSON",
    downloadHtml: "Download HTML Report",
    compareKicker: "Side-by-side insight",
    compareStoryTitle: "Compare two public websites.",
    compareStoryCopy: "When Compare is on, PacketScope measures both URLs with the same settings and highlights the lower visible-latency score.",
    storyKicker: "Connection story",
    stageTitle: "Where the time went",
    chartKicker: "Evidence",
    latencyTitle: "Layer timing comparison",
    diagnosisKicker: "Interpretation",
    diagnosisTitle: "Why PacketScope thinks this is the bottleneck",
    conceptTitle: "Course concepts connected to this run",
    routeVizTitle: "Traceroute path visualization",
    technicalSummary: "Technical evidence table",
    traceTitle: "Raw traceroute evidence",
    targetCol: "Target",
    resolvedCol: "Resolved IPs",
    pingCol: "Ping",
    lossCol: "Loss",
    hopsCol: "Hops",
    statusCol: "Status",
    successCol: "Success",
    waiting: "waiting",
    running: "running",
    done: "done",
    dns: "DNS lookup",
    tcp: "TCP connect",
    tls: "TLS handshake",
    http: "HTTP response",
    ping: "Ping RTT",
    trace: "Traceroute",
    diagnosis: "Diagnosis",
    address: "Address",
    connect: "Connect",
    secure: "Secure",
    wait: "Response",
    rtt: "RTT",
    route: "Route",
    fastest: "Fastest target",
    bottleneck: "Main bottleneck",
    successRate: "Success rate",
    visibleScore: "Visible score",
    totalDuration: "Run duration",
    packetLoss: "Packet loss",
    noTrace: "No traceroute output was returned.",
    winner: "Lower visible latency",
    noWinner: "Comparison unavailable",
    emptyHeadline: "Enter a website URL to get a network verdict.",
    emptyFinding: "PacketScope will identify the slowest visible layer, then show the measurements behind the conclusion.",
    emptyVerdict: "Waiting for a measurement",
    emptyCompare: "Switch to Compare to measure two sites side by side.",
    singleHeadline: layer => `The biggest visible delay is ${layer}.`,
    compareHeadline: winner => winner ? `${winner} is faster in this run.` : "The comparison needs more timing data.",
    singleFinding: target => `${target} was measured from the PacketScope server. The visit was separated into address lookup, connection setup, HTTPS security, server response, round-trip delay, and route visibility.`,
    compareFinding: (winner, delta) => winner ? `${winner} had the lower visible latency score by ${formatMs(delta)}. Use the timing bars to show which layer created the gap.` : "The two targets could not be compared with the available timing data.",
    diagnosisCopy: item => `PacketScope labels ${item.bottleneck_layer} as the bottleneck because it is the largest successful timing signal for this target. Stability score: ${formatValue(item.stability_score)}.`,
    reportUnavailable: "Run a measurement before downloading an HTML report.",
    reportError: "Could not generate the HTML report.",
  },
  zh: {
    appTitle: "PacketScope",
    appSubtitle: "网站网络诊断台",
    serverReady: "实时服务器",
    productLine: "实时网站网络诊断",
    heroTitle: "看清一个网站为什么会慢。",
    heroCopy: "输入一个公开网站，PacketScope 会真实测量一次访问背后的网络路径，并指出哪一层带来了最明显的延迟。",
    stepOneTitle: "选择网站",
    stepOneCopy: "输入你想检查的任意公开 URL。",
    stepTwoTitle: "测量访问过程",
    stepTwoCopy: "PacketScope 会从这台服务器检查 DNS、TCP、TLS、HTTP、Ping 和 Traceroute。",
    stepThreeTitle: "读懂瓶颈",
    stepThreeCopy: "先看诊断结论，再检查支撑结论的测量证据。",
    checkupTitle: "检查网站连接",
    checkupCopy: "从当前 PacketScope 服务器发起真实测量。选择「单网站」只需要一个 URL，选择「对比」才需要第二个 URL。",
    singleMode: "单网站",
    compareMode: "对比",
    targetLabel: "网站 URL",
    targetBLabel: "第二个网站 URL",
    runButton: "运行网络检查",
    runningButton: "检查中...",
    examplesLabel: "示例",
    vantageTitle: "测量位置",
    journeyKicker: "网络旅程",
    journeyTitle: "PacketScope 如何拆解一次网站访问",
    journeyCopy: "每次测量都会拆分寻址、连接、加密、服务器响应、往返延迟和路由可见性。",
    conceptDns: "找到网站地址。",
    conceptTcp: "打开连接。",
    conceptTls: "建立 HTTPS 加密。",
    conceptHttp: "等待服务器响应。",
    conceptRtt: "测量往返延迟。",
    conceptRoute: "展示可见路由跳数。",
    originNote: "结果反映的是 PacketScope 服务器所在网络位置的访问情况，可能与你当前设备上的测量不同。",
    runningKicker: "实时测量中",
    pipelineTitle: "PacketScope 正在测量网络路径。",
    progressCaption: "Ping 和 Traceroute 需要等待网络回复，所以可能会多花一点时间。",
    executionTitle: "实时执行日志",
    executionCopy: "这些事件由 PacketScope 服务器在执行每一项网络检查时实时返回。",
    streamIdle: "等待中",
    streamRunning: "运行中",
    streamComplete: "完成",
    streamError: "错误",
    elapsedLabel: "已用时间",
    errorTitle: "测量错误",
    answerKicker: "人话结果",
    mainFinding: "分析结论",
    resultsTitle: "测量结果",
    resultsCopy: "查看诊断结论、分层耗时和原始证据。",
    downloadJson: "下载 JSON",
    downloadHtml: "下载 HTML 报告",
    compareKicker: "并排对比",
    compareStoryTitle: "对比两个公开网站。",
    compareStoryCopy: "开启对比后，PacketScope 会用相同设置测量两个 URL，并标出可见延迟分数更低的一方。",
    storyKicker: "连接故事",
    stageTitle: "时间花在哪里",
    chartKicker: "证据",
    latencyTitle: "分层耗时对比",
    diagnosisKicker: "解释",
    diagnosisTitle: "为什么 PacketScope 认为这里是瓶颈",
    conceptTitle: "本次测量对应的课程知识点",
    routeVizTitle: "Traceroute 路径可视化",
    technicalSummary: "技术证据表",
    traceTitle: "原始 Traceroute 证据",
    targetCol: "目标",
    resolvedCol: "解析 IP",
    pingCol: "Ping",
    lossCol: "丢包",
    hopsCol: "跳数",
    statusCol: "状态码",
    successCol: "成功率",
    waiting: "等待",
    running: "运行中",
    done: "完成",
    dns: "DNS 解析",
    tcp: "TCP 连接",
    tls: "TLS 握手",
    http: "HTTP 响应",
    ping: "Ping 往返延迟",
    trace: "Traceroute 路由",
    diagnosis: "诊断",
    address: "寻址",
    connect: "连接",
    secure: "加密",
    wait: "响应",
    rtt: "往返",
    route: "路由",
    fastest: "最快目标",
    bottleneck: "主要瓶颈",
    successRate: "成功率",
    visibleScore: "可见延迟分数",
    totalDuration: "运行总耗时",
    packetLoss: "丢包率",
    noTrace: "没有返回 traceroute 输出。",
    winner: "较低可见延迟",
    noWinner: "无法对比",
    emptyHeadline: "输入一个网站 URL，获得网络诊断结论。",
    emptyFinding: "PacketScope 会找出最慢的可见网络层，并展示支撑结论的测量数据。",
    emptyVerdict: "等待测量",
    emptyCompare: "切换到「对比」后，可以并排测量两个网站。",
    singleHeadline: layer => `最大可见延迟出现在 ${layer}。`,
    compareHeadline: winner => winner ? `${winner} 在本次测量中更快。` : "当前数据不足以完成对比。",
    singleFinding: target => `${target} 已从 PacketScope 服务器完成真实测量。本次访问被拆分为寻址、连接、加密、服务器响应、往返延迟和路由可见性。`,
    compareFinding: (winner, delta) => winner ? `${winner} 的可见延迟分数更低，差值为 ${formatMs(delta)}。可以用下方耗时条解释差距来自哪一层。` : "当前可用计时数据不足，无法可靠对比两个目标。",
    diagnosisCopy: item => `PacketScope 将 ${item.bottleneck_layer} 标记为瓶颈，因为它是该目标中最大的成功计时信号。稳定性评分：${formatValue(item.stability_score)}。`,
    reportUnavailable: "请先完成一次测量，再下载 HTML 报告。",
    reportError: "无法生成 HTML 报告。",
  },
};

const stages = ["dns", "tcp", "tls", "http", "ping", "trace", "diagnosis"];
const metricKeys = [
  ["DNS", "dns_ms"],
  ["TCP", "tcp_ms"],
  ["TLS", "tls_ms"],
  ["HTTP", "http_ms"],
  ["Ping", "ping_avg_ms"],
];

let lang = "en";
let mode = "single";
let progressTimer = null;
let elapsedTimer = null;
let startedAt = 0;
let lastPayload = null;
let liveStageStates = {};
let liveStageValues = {};
let executionEvents = [];

const els = {
  form: document.querySelector("#measureForm"),
  targetA: document.querySelector("#targetA"),
  targetB: document.querySelector("#targetB"),
  compareOnly: document.querySelector(".compare-only"),
  runButton: document.querySelector(".run-button"),
  progressSurface: document.querySelector("#progressSurface"),
  pipeline: document.querySelector("#pipeline"),
  elapsedTimer: document.querySelector("#elapsedTimer"),
  overallProgressBar: document.querySelector("#overallProgressBar"),
  executionLog: document.querySelector("#executionLog"),
  streamStatus: document.querySelector("#streamStatus"),
  errorSurface: document.querySelector("#errorSurface"),
  errorText: document.querySelector("#errorText"),
  resultsSurface: document.querySelector("#resultsSurface"),
  answerHeadline: document.querySelector("#answerHeadline"),
  findingText: document.querySelector("#findingText"),
  winnerPill: document.querySelector("#winnerPill"),
  downloadJson: document.querySelector("#downloadJson"),
  downloadHtml: document.querySelector("#downloadHtml"),
  journeyTrack: document.querySelector("#journeyTrack"),
  compareSection: document.querySelector(".compare-section"),
  compareInsight: document.querySelector("#compareInsight"),
  summaryGrid: document.querySelector("#summaryGrid"),
  stageGrid: document.querySelector("#stageGrid"),
  conceptGrid: document.querySelector("#conceptGrid"),
  latencyCharts: document.querySelector("#latencyCharts"),
  diagnosisList: document.querySelector("#diagnosisList"),
  detailsRows: document.querySelector("#detailsRows"),
  traceList: document.querySelector("#traceList"),
  routeViz: document.querySelector("#routeViz"),
};

const requiredElements = Object.entries(els)
  .filter(([, element]) => !element)
  .map(([name]) => name);

if (requiredElements.length) {
  throw new Error(`PacketScope UI is missing required elements: ${requiredElements.join(", ")}`);
}

document.querySelectorAll("[data-lang]").forEach(button => {
  button.addEventListener("click", () => {
    lang = button.dataset.lang;
    document.querySelectorAll("[data-lang]").forEach(item => item.classList.toggle("active", item === button));
    applyLanguage();
    if (lastPayload) {
      renderResults(lastPayload);
    }
  });
});

document.querySelectorAll("[data-mode]").forEach(button => {
  button.addEventListener("click", () => {
    mode = button.dataset.mode;
    syncModeControls();
  });
});

document.querySelectorAll("[data-example]").forEach(button => {
  button.addEventListener("click", () => {
    if (mode === "compare" && document.activeElement === els.targetB) {
      els.targetB.value = button.dataset.example;
    } else {
      els.targetA.value = button.dataset.example;
    }
  });
});

els.form.addEventListener("submit", async event => {
  event.preventDefault();
  await submitMeasurement();
});

els.runButton.addEventListener("click", async () => {
  await submitMeasurement();
});

els.downloadJson.addEventListener("click", () => {
  if (!lastPayload) return;
  const blob = new Blob([JSON.stringify(lastPayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "packetscope-live-result.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

els.downloadHtml.addEventListener("click", async () => {
  if (!lastPayload) {
    showError(t("reportUnavailable"));
    return;
  }
  try {
    const response = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        measurement: lastPayload,
        execution_events: executionEvents.map(event => ({
          time: event.time instanceof Date ? event.time.toISOString() : event.time,
          status: event.status,
          stage: event.stage,
          message: event.message,
        })),
      }),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "packetscope-report.html";
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showError(`${t("reportError")} ${error.message}`);
  }
});

applyLanguage();
syncModeControls();
renderPipeline(0);
renderJourneyTrack();
renderEmptyState();

function syncModeControls() {
  const isCompare = mode === "compare";
  document.querySelectorAll("[data-mode]").forEach(item => {
    item.classList.toggle("active", item.dataset.mode === mode);
    item.setAttribute("aria-selected", String(item.dataset.mode === mode));
  });
  els.compareOnly.hidden = !isCompare;
  els.form.classList.toggle("compare", isCompare);
  els.compareSection.hidden = !isCompare && !lastPayload?.comparison;
  renderCompareInsight(lastPayload?.comparison || null, lastPayload?.results || []);
}

async function submitMeasurement() {
  const targets = mode === "compare" ? [els.targetA.value, els.targetB.value] : [els.targetA.value];
  await runMeasurement(targets);
}

async function runMeasurement(targets) {
  setBusy(true);
  hideError();
  renderCheckingState(targets);
  els.progressSurface.hidden = false;
  startProgress();

  try {
    const payload = await streamMeasurement(targets);
    lastPayload = payload;
    stopProgress(true);
    renderResults(payload);
  } catch (error) {
    stopProgress(false);
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function streamMeasurement(targets) {
  const response = await fetch("/api/measure/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ targets, runs: 1 }),
  });
  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completePayload = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      const payload = handleStreamEvent(event);
      if (payload) {
        completePayload = payload;
      }
    }
  }

  if (buffer.trim()) {
    const payload = handleStreamEvent(JSON.parse(buffer));
    if (payload) completePayload = payload;
  }
  if (!completePayload) {
    throw new Error("The measurement stream ended before returning a result.");
  }
  return completePayload;
}

function handleStreamEvent(event) {
  if (event.type === "accepted") {
    els.streamStatus.textContent = t("streamRunning");
    addExecutionEvent("started", "server", `Accepted ${event.targets.length} target(s) from ${event.origin}.`);
    return null;
  }
  if (event.type === "target_started") {
    addExecutionEvent("started", "target", `Starting measurement for ${event.target}.`);
    return null;
  }
  if (event.type === "stage") {
    liveStageStates[event.stage] = event.status;
    if (event.duration_ms != null || event.result) {
      liveStageValues[event.stage] = event.duration_ms != null ? formatSmartTime(event.duration_ms) : event.result;
    }
    renderPipelineFromLive();
    addExecutionEvent(event.status, t(event.stage) || event.stage, event.operation || event.result || event.error || event.status);
    return null;
  }
  if (event.type === "target_done") {
    addExecutionEvent("done", "target", `Finished ${event.target}.`);
    return null;
  }
  if (event.type === "complete") {
    els.streamStatus.textContent = t("streamComplete");
    addExecutionEvent("done", "server", "Final diagnosis payload returned to the browser.");
    return event.payload;
  }
  if (event.type === "error") {
    els.streamStatus.textContent = t("streamError");
    addExecutionEvent("error", "server", event.error);
    throw new Error(event.error);
  }
  return null;
}

function startProgress() {
  startedAt = Date.now();
  liveStageStates = {};
  liveStageValues = {};
  executionEvents = [];
  els.streamStatus.textContent = t("streamRunning");
  renderExecutionLog();
  updateElapsed();
  renderPipelineFromLive();
  clearInterval(progressTimer);
  clearInterval(elapsedTimer);
  progressTimer = null;
  elapsedTimer = setInterval(updateElapsed, 100);
}

function stopProgress(done) {
  clearInterval(progressTimer);
  clearInterval(elapsedTimer);
  progressTimer = null;
  elapsedTimer = null;
  updateElapsed();
  els.streamStatus.textContent = done ? t("streamComplete") : t("streamError");
  renderPipeline(done ? stages.length : 0, lastPayload?.results || []);
}

function renderPipelineFromLive() {
  const completed = stages.filter(stage => liveStageStates[stage] === "done").length;
  const runningIndex = stages.findIndex(stage => liveStageStates[stage] === "started");
  const progressPercent = Math.min(100, Math.max(0, (completed / stages.length) * 100));
  els.overallProgressBar.style.width = `${progressPercent}%`;
  els.pipeline.innerHTML = stages.map((stage, index) => {
    const status = liveStageStates[stage];
    const state = status === "done" ? "done" : status === "error" ? "error" : status === "started" ? "running" : "";
    const label = status === "done" ? t("done") : status === "error" ? t("streamError") : status === "started" || index === runningIndex ? t("running") : t("waiting");
    const value = liveStageValues[stage] || "-";
    return `<div class="pipeline-step ${state}">
      <strong>${escapeHtml(t(stage))}</strong>
      <span>${escapeHtml(label)}</span>
      <em>${escapeHtml(value)}</em>
    </div>`;
  }).join("");
}

function renderPipeline(activeIndex, results = []) {
  const primary = results[0];
  const stageValues = primary ? stageMetrics(primary) : {};
  const progressPercent = Math.min(100, Math.max(0, (activeIndex / stages.length) * 100));
  els.overallProgressBar.style.width = `${progressPercent}%`;
  els.pipeline.innerHTML = stages.map((stage, index) => {
    const state = index < activeIndex ? "done" : index === activeIndex ? "running" : "";
    const label = index < activeIndex ? t("done") : index === activeIndex ? t("running") : t("waiting");
    const value = stageValues[stage];
    return `<div class="pipeline-step ${state}">
      <strong>${escapeHtml(t(stage))}</strong>
      <span>${escapeHtml(label)}</span>
      <em>${escapeHtml(value == null ? "-" : formatSmartTime(value))}</em>
    </div>`;
  }).join("");
}

function addExecutionEvent(status, stage, message) {
  executionEvents.push({
    time: new Date(),
    status,
    stage,
    message,
  });
  if (executionEvents.length > 80) {
    executionEvents = executionEvents.slice(-80);
  }
  renderExecutionLog();
}

function renderExecutionLog() {
  if (!executionEvents.length) {
    els.executionLog.innerHTML = `<div class="log-row started">
      <time>--:--:--</time>
      <strong>${escapeHtml(t("streamIdle"))}</strong>
      <span>${escapeHtml(t("executionCopy"))}</span>
      <em>-</em>
    </div>`;
    return;
  }
  els.executionLog.innerHTML = executionEvents.map(event => `<div class="log-row ${escapeHtml(event.status)}">
    <time>${escapeHtml(event.time.toLocaleTimeString())}</time>
    <strong>${escapeHtml(event.stage)}</strong>
    <span>${escapeHtml(event.message)}</span>
    <em>${escapeHtml(event.status)}</em>
  </div>`).join("");
  els.executionLog.scrollTop = els.executionLog.scrollHeight;
}

function renderResults(payload) {
  const results = payload.results || [];
  const diagnoses = payload.diagnosis?.targets || [];
  const comparison = payload.comparison;
  const fastest = findFastest(results);
  const first = results[0];
  const primaryDiagnosis = diagnoses[0];
  renderPipeline(stages.length, results);
  renderJourneyTrack(results);

  els.resultsSurface.hidden = false;
  els.answerHeadline.textContent = comparison
    ? t("compareHeadline")(comparison.winner)
    : t("singleHeadline")(friendlyLayer(primaryDiagnosis?.bottleneck_layer));
  els.findingText.textContent = comparison
    ? t("compareFinding")(comparison.winner, comparison.delta_ms)
    : t("singleFinding")(first?.target || "");

  els.winnerPill.textContent = comparison
    ? `${t("winner")}: ${comparison.winner || t("noWinner")}`
    : `${t("visibleScore")}: ${formatMs(first?.visible_latency_score_ms)}`;

  const bottleneck = diagnoses[0]?.bottleneck_layer || "-";
  const avgSuccess = average(results.map(item => item.success_rate_percent));
  els.summaryGrid.innerHTML = [
    summaryCard(t("fastest"), fastest?.target || "-"),
    summaryCard(t("bottleneck"), bottleneck),
    summaryCard(t("successRate"), formatPercent(avgSuccess)),
    summaryCard(t("totalDuration"), formatSeconds(maxValue(results.map(item => item.duration_ms)))),
  ].join("");

  renderStageGrid(results);
  renderConceptGrid(results);
  renderLatencyCharts(results);
  renderDiagnosis(diagnoses);
  renderDetails(results);
  renderTraces(results);
  renderRouteViz(results);
  renderCompareInsight(comparison, results);
  els.compareSection.hidden = !comparison && mode !== "compare";
}

function renderEmptyState() {
  els.resultsSurface.hidden = false;
  els.answerHeadline.textContent = t("emptyHeadline");
  els.findingText.textContent = t("emptyFinding");
  els.winnerPill.textContent = t("emptyVerdict");
  els.summaryGrid.innerHTML = [
    summaryCard(t("bottleneck"), "-"),
    summaryCard(t("visibleScore"), "-"),
    summaryCard(t("totalDuration"), "-"),
    summaryCard(t("successRate"), "-"),
  ].join("");
  els.stageGrid.innerHTML = journeySteps().map(step => `<article class="stage-card empty">
    <span>${escapeHtml(step.short)}</span>
    <strong>-</strong>
    <small>${escapeHtml(step.copy)}</small>
  </article>`).join("");
  els.latencyCharts.innerHTML = `<article class="target-chart empty-chart">
    <h3>${escapeHtml(t("emptyVerdict"))}</h3>
    ${metricKeys.map(([label]) => `<div class="bar-row muted-row">
      <span>${label}</span>
      <div class="bar-track"><div class="bar-fill" style="width: 0"></div></div>
      <span>-</span>
    </div>`).join("")}
  </article>`;
  els.diagnosisList.innerHTML = `<article class="diagnosis-card">
    <h3>${escapeHtml(t("mainFinding"))}</h3>
    <p>${escapeHtml(t("emptyFinding"))}</p>
  </article>`;
  renderConceptGrid([]);
  els.detailsRows.innerHTML = `<tr><td colspan="11">${escapeHtml(t("emptyVerdict"))}</td></tr>`;
  els.traceList.innerHTML = `<p class="muted-copy">${escapeHtml(t("noTrace"))}</p>`;
  els.routeViz.innerHTML = `<p class="muted-copy">${escapeHtml(t("noTrace"))}</p>`;
  els.compareInsight.textContent = t("emptyCompare");
  els.compareSection.hidden = mode !== "compare";
}

function renderCheckingState(targets) {
  els.resultsSurface.hidden = false;
  els.answerHeadline.textContent = t("runningButton");
  els.findingText.textContent = targets.join(" vs ");
  els.winnerPill.textContent = 