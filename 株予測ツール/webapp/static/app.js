// 株予測ツール Web版 フロントエンド
// 「分析」を押すたびに /api/analyze を叩き、常にサーバー側でyfinanceから
// 取得した最新（ライブ）データを描画する。クライアント側キャッシュはしない。

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const els = {
  input: document.getElementById("search-input"),
  analyzeBtn: document.getElementById("analyze-btn"),
  suggestions: document.getElementById("suggestions"),
  stateEmpty: document.getElementById("state-empty"),
  stateLoading: document.getElementById("state-loading"),
  stateError: document.getElementById("state-error"),
  errorMessage: document.getElementById("error-message"),
  result: document.getElementById("result"),
  refreshBtn: document.getElementById("refresh-btn"),
};

let currentSymbol = null;
let searchDebounceTimer = null;
let activeSuggestionIndex = -1;
let lastCandidates = [];

let priceChart, rsiChart, macdChart;
let priceSeries = {};
let rsiSeries = {};
let macdSeriesRefs = {};

// ---------------------------------------------------------------------
// 状態表示切り替え
// ---------------------------------------------------------------------

function showState(state) {
  els.stateEmpty.classList.toggle("hidden", state !== "empty");
  els.stateLoading.classList.toggle("hidden", state !== "loading");
  els.stateError.classList.toggle("hidden", state !== "error");
  els.result.classList.toggle("hidden", state !== "result");
}

// ---------------------------------------------------------------------
// 会社名サジェスト
// ---------------------------------------------------------------------

async function fetchSuggestions(q) {
  if (q.trim().length < 2) {
    closeSuggestions();
    return;
  }
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    lastCandidates = data.candidates || [];
    renderSuggestions(lastCandidates);
  } catch (e) {
    closeSuggestions();
  }
}

function renderSuggestions(candidates) {
  activeSuggestionIndex = -1;
  if (!candidates.length) {
    closeSuggestions();
    return;
  }
  els.suggestions.innerHTML = candidates.map((c, i) => `
    <div class="suggestion-item" data-index="${i}" data-symbol="${escapeHtml(c.symbol)}">
      <span class="suggestion-symbol">${escapeHtml(c.symbol)}</span>
      <span class="suggestion-name">${escapeHtml(c.name || "")}</span>
      <span class="suggestion-exchange">${escapeHtml(c.exchange || "")}</span>
    </div>
  `).join("");
  els.suggestions.classList.add("open");

  els.suggestions.querySelectorAll(".suggestion-item").forEach((item) => {
    item.addEventListener("click", () => {
      const symbol = item.getAttribute("data-symbol");
      els.input.value = symbol;
      closeSuggestions();
      runAnalysis(symbol);
    });
  });
}

function closeSuggestions() {
  clearTimeout(searchDebounceTimer);
  els.suggestions.classList.remove("open");
  els.suggestions.innerHTML = "";
  activeSuggestionIndex = -1;
}

function moveSuggestionSelection(delta) {
  const items = els.suggestions.querySelectorAll(".suggestion-item");
  if (!items.length) return;
  activeSuggestionIndex = (activeSuggestionIndex + delta + items.length) % items.length;
  items.forEach((it, i) => it.classList.toggle("active", i === activeSuggestionIndex));
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

els.input.addEventListener("input", () => {
  clearTimeout(searchDebounceTimer);
  const q = els.input.value;
  searchDebounceTimer = setTimeout(() => fetchSuggestions(q), 250);
});

els.input.addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    moveSuggestionSelection(1);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    moveSuggestionSelection(-1);
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (activeSuggestionIndex >= 0 && lastCandidates[activeSuggestionIndex]) {
      const symbol = lastCandidates[activeSuggestionIndex].symbol;
      els.input.value = symbol;
      closeSuggestions();
      runAnalysis(symbol);
    } else {
      closeSuggestions();
      runAnalysis(els.input.value);
    }
  } else if (e.key === "Escape") {
    closeSuggestions();
  }
});

document.addEventListener("click", (e) => {
  if (!els.suggestions.contains(e.target) && e.target !== els.input) {
    closeSuggestions();
  }
});

els.analyzeBtn.addEventListener("click", () => {
  closeSuggestions();
  runAnalysis(els.input.value);
});

els.refreshBtn.addEventListener("click", () => {
  if (currentSymbol) runAnalysis(currentSymbol);
});

// ---------------------------------------------------------------------
// 分析実行
// ---------------------------------------------------------------------

async function runAnalysis(query) {
  const q = (query || "").trim();
  if (!q) return;

  showState("loading");
  els.analyzeBtn.disabled = true;
  els.refreshBtn.disabled = true;

  try {
    const res = await fetch(`/api/analyze?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "分析に失敗しました。");
    }
    currentSymbol = data.symbol;
    renderResult(data);
    showState("result");
  } catch (e) {
    els.errorMessage.textContent = e.message || String(e);
    showState("error");
  } finally {
    els.analyzeBtn.disabled = false;
    els.refreshBtn.disabled = false;
  }
}

// ---------------------------------------------------------------------
// 結果描画
// ---------------------------------------------------------------------

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "N/A";
  return Number(v).toLocaleString("ja-JP", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtPct(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "N/A";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

function signalClass(score) {
  if (score >= 50) return "buy2";
  if (score >= 20) return "buy1";
  if (score > -20) return "neutral";
  if (score > -50) return "sell1";
  return "sell2";
}

function reasonIcon(reasonText) {
  const m = reasonText.match(/([+\-])(\d+)\）$/) || reasonText.match(/[（(]([+\-])(\d+)[)）]/);
  if (!m) return { cls: "neu", glyph: "・" };
  return m[1] === "+" ? { cls: "pos", glyph: "▲" } : { cls: "neg", glyph: "▼" };
}

function renderReasons(container, reasons) {
  if (!reasons || !reasons.length) {
    container.innerHTML = `<li class="reason-empty">該当する材料なし</li>`;
    return;
  }
  container.innerHTML = reasons.map((r) => {
    const { cls, glyph } = reasonIcon(r);
    return `<li><span class="reason-icon ${cls}">${glyph}</span><span>${escapeHtml(r)}</span></li>`;
  }).join("");
}

function renderResult(data) {
  document.getElementById("r-name").textContent = data.name;
  document.getElementById("r-symbol").textContent = data.symbol;

  const priceEl = document.getElementById("r-price");
  const changeEl = document.getElementById("r-change");
  const dir = data.change > 0 ? "up" : data.change < 0 ? "down" : "flat";
  priceEl.textContent = `${data.currency_symbol}${fmtNum(data.live_price, 0)}`;
  priceEl.className = `live-price tabular ${dir}`;
  const arrow = dir === "up" ? "▲" : dir === "down" ? "▼" : "―";
  changeEl.textContent = `${arrow} ${data.change >= 0 ? "+" : ""}${fmtNum(data.change, 0)}（${fmtPct(data.change_pct)}）`;
  changeEl.className = `change-badge tabular ${dir}`;

  const badge = document.getElementById("r-signal-badge");
  badge.textContent = data.combined.label;
  badge.className = `signal-badge ${signalClass(data.combined.score)}`;
  document.getElementById("r-signal-score").textContent = `総合スコア ${data.combined.score >= 0 ? "+" : ""}${data.combined.score} / -100〜+100`;

  const pos = (data.combined.score + 100) / 200 * 100;
  document.getElementById("r-score-marker").style.left = `${pos}%`;

  document.getElementById("r-weight-note").textContent =
    `テクニカル ${Math.round(data.combined.tech_weight * 100)}% ＋ ファンダメンタルズ ${Math.round(data.combined.fund_weight * 100)}% の加重平均`;

  const now = new Date();
  document.getElementById("r-updated").textContent =
    `取得時刻: ${now.toLocaleTimeString("ja-JP")}（確定データ基準日: ${data.updated_at}）`;

  document.getElementById("r-tech-score").textContent = `${data.tech.score >= 0 ? "+" : ""}${data.tech.score}`;
  document.getElementById("r-fund-score").textContent = `${data.fund.score >= 0 ? "+" : ""}${data.fund.score}`;
  renderReasons(document.getElementById("r-tech-reasons"), data.tech.reasons);
  renderReasons(document.getElementById("r-fund-reasons"), data.fund.reasons);

  renderMetrics(data);
  renderForecastNote(data);
  renderCharts(data);
}

function renderMetrics(data) {
  const m = data.metrics;
  const tiles = [
    ["PER", m.per != null ? `${fmtNum(m.per, 1)}倍` : "N/A"],
    ["PBR", m.pbr != null ? `${fmtNum(m.pbr, 2)}倍` : "N/A"],
    ["配当利回り", m.dividend_yield_pct != null ? fmtPct(m.dividend_yield_pct).replace("+", "") : "N/A"],
    ["ROE", m.roe_pct != null ? fmtPct(m.roe_pct).replace("+", "") : "N/A"],
    ["時価総額", m.market_cap_fmt || "N/A"],
    ["52週高値/安値", `${fmtNum(m.week52_high, 0)} / ${fmtNum(m.week52_low, 0)}`],
    ["RSI(14)", m.rsi != null ? fmtNum(m.rsi, 1) : "N/A"],
    ["出来高", m.volume != null ? Number(m.volume).toLocaleString("ja-JP") : "N/A"],
  ];
  document.getElementById("r-metrics").innerHTML = tiles.map(([label, value]) => `
    <div class="stat-tile">
      <div class="stat-label">${label}</div>
      <div class="stat-value tabular">${value}</div>
    </div>
  `).join("");
}

function renderForecastNote(data) {
  const f = data.forecast;
  document.getElementById("r-forecast-note").innerHTML =
    `<strong>簡易トレンド予測：</strong>今後${f.forecast_days}営業日で ${fmtPct(f.change_pct)}（${f.trend}）※過去${f.lookback_days}営業日の線形トレンドを機械的に延長した参考値です。` +
    `決算発表・ニュース・市場全体の動向は考慮していません。将来の株価を保証するものではありません。`;
}

// ---------------------------------------------------------------------
// チャート（lightweight-charts）
// ---------------------------------------------------------------------

function baseChartOptions(heightPx) {
  return {
    height: heightPx,
    layout: {
      background: { type: "solid", color: "transparent" },
      textColor: cssVar("--text-secondary"),
      fontFamily: cssVar("--font-sans"),
    },
    grid: {
      vertLines: { color: cssVar("--gridline") },
      horzLines: { color: cssVar("--gridline") },
    },
    rightPriceScale: { borderColor: cssVar("--border-strong") },
    timeScale: { borderColor: cssVar("--border-strong") },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  };
}

function ensureCharts() {
  if (!priceChart) {
    priceChart = LightweightCharts.createChart(document.getElementById("chart-price"), {
      ...baseChartOptions(360),
    });
    priceSeries.candle = priceChart.addCandlestickSeries({
      upColor: cssVar("--status-good"),
      downColor: cssVar("--status-critical"),
      borderUpColor: cssVar("--status-good"),
      borderDownColor: cssVar("--status-critical"),
      wickUpColor: cssVar("--status-good"),
      wickDownColor: cssVar("--status-critical"),
    });
    priceSeries.volume = priceChart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    priceChart.priceScale("").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    const overlayLineOpts = { lineWidth: 2, lastValueVisible: false, priceLineVisible: false };
    priceSeries.sma5 = priceChart.addLineSeries({ ...overlayLineOpts, color: cssVar("--series-sma5") });
    priceSeries.sma25 = priceChart.addLineSeries({ ...overlayLineOpts, color: cssVar("--series-sma25") });
    priceSeries.sma75 = priceChart.addLineSeries({ ...overlayLineOpts, color: cssVar("--series-sma75") });
    priceSeries.forecast = priceChart.addLineSeries({
      ...overlayLineOpts,
      color: cssVar("--series-forecast"),
      lineStyle: LightweightCharts.LineStyle.Dashed,
      lastValueVisible: true,
    });

    rsiChart = LightweightCharts.createChart(document.getElementById("chart-rsi"), baseChartOptions(200));
    rsiSeries.rsi = rsiChart.addLineSeries({ color: cssVar("--series-rsi"), lineWidth: 2 });
    rsiSeries.rsi.createPriceLine({ price: 70, color: cssVar("--status-critical"), lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: "買われすぎ" });
    rsiSeries.rsi.createPriceLine({ price: 30, color: cssVar("--status-good"), lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: "売られすぎ" });

    macdChart = LightweightCharts.createChart(document.getElementById("chart-macd"), baseChartOptions(200));
    macdSeriesRefs.hist = macdChart.addHistogramSeries({
      priceFormat: { type: "price", precision: 2 },
      lastValueVisible: false,
      priceLineVisible: false,
    });
    macdSeriesRefs.macd = macdChart.addLineSeries({ color: cssVar("--series-macd"), lineWidth: 2, priceLineVisible: false });
    macdSeriesRefs.signal = macdChart.addLineSeries({ color: cssVar("--series-macd-signal"), lineWidth: 2, priceLineVisible: false });

    syncTimeScales([priceChart, rsiChart, macdChart]);
    window.addEventListener("resize", resizeCharts);
  }
}

function syncTimeScales(charts) {
  charts.forEach((chart) => {
    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range) return;
      charts.forEach((other) => {
        if (other !== chart) other.timeScale().setVisibleLogicalRange(range);
      });
    });
  });
}

function resizeCharts() {
  [["chart-price", priceChart], ["chart-rsi", rsiChart], ["chart-macd", macdChart]].forEach(([id, chart]) => {
    if (!chart) return;
    const el = document.getElementById(id);
    chart.applyOptions({ width: el.clientWidth });
  });
}

function renderCharts(data) {
  ensureCharts();
  const c = data.chart;

  priceSeries.candle.setData(c.candles);
  priceSeries.volume.setData(c.volume);
  priceSeries.sma5.setData(c.sma5);
  priceSeries.sma25.setData(c.sma25);
  priceSeries.sma75.setData(c.sma75);
  priceSeries.forecast.setData(data.forecast.line);

  rsiSeries.rsi.setData(c.rsi);

  macdSeriesRefs.hist.setData(c.macd_hist);
  macdSeriesRefs.macd.setData(c.macd);
  macdSeriesRefs.signal.setData(c.macd_signal);

  resizeCharts();
  priceChart.timeScale().fitContent();
  rsiChart.timeScale().fitContent();
  macdChart.timeScale().fitContent();
}
