(function () {
  "use strict";

  const JSON_URL_BASE = "json";
  const TOP_N = 25;
  const HIST_WINDOW = 12;
  const EXTERNAL_LINK_ATTRS = ' target="_blank" rel="noopener noreferrer"';
  const IT_MONTHS = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
  ];
  const DAYS_SHORT = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"];
  const DAYS_FULL = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"];
  const TREND_COLORS = { strong: "#202122", up: "#54595d", down: "#a2a9b1" };

  // ---------------------------------------------------------------------------
  // Utility (riprese dalla versione precedente di week.html)

  function getWeekFromQuery() {
    const params = new URLSearchParams(window.location.search);
    return params.get("week");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeWeekId(year, week) {
    return `${year}-${String(week).padStart(2, "0")}`;
  }

  function parseWeekId(weekId) {
    const [yearRaw, weekRaw] = String(weekId || "").split("-");
    return { year: Number(yearRaw), week: Number(weekRaw) };
  }

  function parseIsoDate(value) {
    if (typeof value !== "string") return null;
    const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;
    if (month < 1 || month > 12 || day < 1 || day > 31) return null;
    return new Date(Date.UTC(year, month - 1, day));
  }

  function getIsoWeekMonday(year, week, deltaWeeks = 0) {
    const jan4 = new Date(Date.UTC(year, 0, 4));
    const day = jan4.getUTCDay() || 7;
    const monday = new Date(jan4);
    monday.setUTCDate(jan4.getUTCDate() - day + 1 + ((week - 1 + deltaWeeks) * 7));
    return monday;
  }

  function shiftIsoWeek(year, week, deltaWeeks) {
    const monday = getIsoWeekMonday(year, week, deltaWeeks);
    // L'anno ISO è quello del giovedì: il lunedì 29/12/2025 appartiene alla sett. 1/2026.
    const thursday = new Date(monday);
    thursday.setUTCDate(monday.getUTCDate() + 3);
    const shiftedYear = thursday.getUTCFullYear();
    const jan4Shifted = new Date(Date.UTC(shiftedYear, 0, 4));
    const dayShifted = jan4Shifted.getUTCDay() || 7;
    const firstMonday = new Date(jan4Shifted);
    firstMonday.setUTCDate(jan4Shifted.getUTCDate() - dayShifted + 1);
    const diffDays = Math.round((monday - firstMonday) / 86400000);
    const shiftedWeek = Math.floor(diffDays / 7) + 1;
    return { year: shiftedYear, week: shiftedWeek };
  }

  // "14 – 20 settembre 2026", "31 agosto – 6 settembre 2026",
  // "29 dicembre 2025 – 4 gennaio 2026"
  function formatWeekTitle(startDate, endDate) {
    const startDay = startDate.getUTCDate();
    const endDay = endDate.getUTCDate();
    const startMonthIndex = startDate.getUTCMonth();
    const endMonthIndex = endDate.getUTCMonth();
    const startYear = startDate.getUTCFullYear();
    const endYear = endDate.getUTCFullYear();
    const end = `${endDay} ${IT_MONTHS[endMonthIndex]} ${endYear}`;

    if (startYear === endYear && startMonthIndex === endMonthIndex) {
      return `${startDay} – ${end}`;
    }
    if (startYear === endYear) {
      return `${startDay} ${IT_MONTHS[startMonthIndex]} – ${end}`;
    }
    return `${startDay} ${IT_MONTHS[startMonthIndex]} ${startYear} – ${end}`;
  }

  function weekRange(weekId, data) {
    let start = parseIsoDate(data?.start_date);
    let end = parseIsoDate(data?.end_date);
    if (!start || !end) {
      const { year, week } = parseWeekId(weekId);
      if (!Number.isFinite(year) || !Number.isFinite(week)) return { start: null, end: null };
      start = getIsoWeekMonday(year, week);
      end = new Date(start);
      end.setUTCDate(start.getUTCDate() + 6);
    }
    return { start, end };
  }

  function weekRangeLabel(weekId, data) {
    const { start, end } = weekRange(weekId, data);
    return start ? formatWeekTitle(start, end) : weekId;
  }

  // "Settimana 38 · 14 – 20 settembre" (intervallo ISO, senza anno)
  function weekOptionLabel(weekId) {
    const { year, week } = parseWeekId(weekId);
    const start = getIsoWeekMonday(year, week);
    const end = new Date(start);
    end.setUTCDate(start.getUTCDate() + 6);
    const startMonth = start.getUTCMonth();
    const endMonth = end.getUTCMonth();
    const range =
      startMonth === endMonth
        ? `${start.getUTCDate()} – ${end.getUTCDate()} ${IT_MONTHS[endMonth]}`
        : `${start.getUTCDate()} ${IT_MONTHS[startMonth]} – ${end.getUTCDate()} ${IT_MONTHS[endMonth]}`;
    return `Settimana ${week} · ${range}`;
  }

  function weekLabel(weekId) {
    const { year, week } = parseWeekId(weekId);
    return `sett. ${week} · ${year}`;
  }

  function formatViews(value) {
    return Math.round(Number(value) || 0).toLocaleString("it-IT", { useGrouping: "always" });
  }

  function decodeSafe(value) {
    try {
      return decodeURIComponent(value);
    } catch (error) {
      return value;
    }
  }

  function articleTitle(article) {
    return decodeSafe(String(article || "").replaceAll("_", " "));
  }

  function sameArticle(a, b) {
    return decodeSafe(String(a || "")).replaceAll(" ", "_") === decodeSafe(String(b || "")).replaceAll(" ", "_");
  }

  // ---------------------------------------------------------------------------
  // Dati

  const cache = new Map();
  const ready = new Map();

  function fetchWeek(weekId) {
    if (!cache.has(weekId)) {
      const promise = fetch(`${JSON_URL_BASE}/${weekId}.json`)
        .then((response) => {
          if (!response.ok) throw new Error("JSON not found");
          return response.json();
        })
        .then((data) => {
          ready.set(weekId, data);
          return data;
        })
        .catch(() => {
          cache.delete(weekId);
          return null;
        });
      cache.set(weekId, promise);
    }
    return cache.get(weekId);
  }

  function articlesOf(data, n) {
    const rows = Array.isArray(data?.articles) ? data.articles : [];
    return rows.slice(0, n);
  }

  function rankOf(article, index) {
    const rank = Number(article.rank);
    return Number.isFinite(rank) && rank > 0 ? rank : index + 1;
  }

  function isAdjacent(data, prevData) {
    const start = parseIsoDate(data?.start_date);
    const prevStart = parseIsoDate(prevData?.start_date);
    if (!start || !prevStart) return false;
    return Math.round((start - prevStart) / 86400000) === 7;
  }

  function dailyValues(article) {
    const points = Array.isArray(article.daily_views) ? article.daily_views : [];
    return points.map((point) => Math.max(Number(point.views) || 0, 0));
  }

  function shapeSentence(share, zeros) {
    if (share >= 55) return "Picco concentrato in un solo giorno.";
    if (zeros >= 3) return "Pagina praticamente non vista prima del picco.";
    if (share >= 35) return "Salita netta in pochi giorni.";
    return "Interesse distribuito sui sette giorni.";
  }

  function buildEntry(article, index, prevTop, adjacent) {
    const views = Number(article.views) || 0;
    const daily = dailyValues(article);
    const max = daily.length ? Math.max(...daily) : 0;
    const share = views ? Math.round((max / views) * 100) : 0;
    const zeros = daily.filter((value) => value === 0).length;
    const rank = rankOf(article, index);

    let prevIndex = -1;
    if (adjacent && prevTop) prevIndex = prevTop.findIndex((p) => p.article === article.article);
    const prev = prevIndex >= 0 ? prevTop[prevIndex] : null;
    const prevRank = prev ? rankOf(prev, prevIndex) : null;

    let pct = null;
    let trend = "";
    let trendColor = TREND_COLORS.up;
    let rankMove = "";
    if (adjacent && !prev) {
      trend = "nuova entrata";
      trendColor = TREND_COLORS.strong;
    } else if (adjacent && prev) {
      const prevViews = Number(prev.views) || 0;
      pct = prevViews ? (views / prevViews - 1) * 100 : 0;
      const rounded = Math.round(pct);
      trend = `${rounded >= 0 ? "+" : "−"}${Math.abs(rounded)}%`;
      trendColor = pct >= 50 ? TREND_COLORS.strong : pct < 0 ? TREND_COLORS.down : TREND_COLORS.up;
      if (prevRank <= TOP_N) {
        const delta = prevRank - rank;
        rankMove = delta === 0 ? "=" : delta > 0 ? `▲ ${delta}` : `▼ ${-delta}`;
      } else {
        rankMove = `dalla ${prevRank}ª`;
      }
    }

    return {
      raw: article,
      key: article.article,
      rank,
      title: articleTitle(article.article),
      description: article.description || "",
      views,
      daily,
      max,
      share,
      shape: shapeSentence(share, zeros),
      isNew: adjacent && !prev,
      pct,
      trend,
      trendColor,
      rankMove,
      image: article.image_url || "",
    };
  }

  function buildModel(weekId, data, prevData) {
    const adjacent = !!prevData && isAdjacent(data, prevData);
    const prevTop = adjacent ? articlesOf(prevData, 30) : null;
    const entries = articlesOf(data, TOP_N).map((article, index) => buildEntry(article, index, prevTop, adjacent));
    return {
      weekId,
      data,
      adjacent,
      entries,
      total: entries.reduce((sum, entry) => sum + entry.views, 0),
      range: weekRangeLabel(weekId, data),
    };
  }

  function filterEntries(model, filter) {
    const entries = model.entries;
    if (filter === "novita") return entries.filter((e) => e.isNew);
    if (filter === "crescita") return entries.filter((e) => !e.isNew && e.pct !== null && e.pct >= 50);
    if (filter === "picco") return entries.filter((e) => e.share >= 55);
    return entries;
  }

  // ---------------------------------------------------------------------------
  // Stato e URL

  const state = {
    weeks: [],
    weekSet: new Set(),
    weekId: null,
    vsId: null,
    view: "list",
    filter: "tutte",
    openArticle: null,
  };

  let model = null;
  let vsData = null;
  let loadToken = 0;
  let sheetPushed = false;
  let sheetReturnFocus = null;

  const els = {
    main: document.getElementById("main"),
    sheetRoot: document.getElementById("sheet-root"),
    select: document.getElementById("week-select"),
    year: document.getElementById("year-select"),
    prev: document.getElementById("prev-week"),
    next: document.getElementById("next-week"),
    tabs: Array.from(document.querySelectorAll(".tab")),
  };

  function previousAdjacentId(weekId) {
    return adjacentWeekId(weekId, -1);
  }

  function sameWeekLastYear(weekId) {
    const { year, week } = parseWeekId(weekId);
    return normalizeWeekId(year - 1, week);
  }

  function defaultVs(weekId) {
    const adjacent = previousAdjacentId(weekId);
    if (state.weekSet.has(adjacent)) return adjacent;
    const index = state.weeks.indexOf(weekId);
    if (index > 0) return state.weeks[index - 1];
    if (index >= 0 && index + 1 < state.weeks.length) return state.weeks[index + 1];
    return adjacent;
  }

  function readUrl() {
    const params = new URLSearchParams(window.location.search);
    const hash = window.location.hash ? window.location.hash.slice(1) : "";
    return {
      week: getWeekFromQuery(),
      vs: params.get("vs"),
      view: params.get("view") === "cmp" ? "cmp" : "list",
      article: hash ? decodeSafe(hash) : null,
    };
  }

  function buildUrl() {
    const params = new URLSearchParams();
    params.set("week", state.weekId);
    if (state.view === "cmp") {
      params.set("view", "cmp");
      params.set("vs", state.vsId);
    }
    const hash = state.openArticle ? `#${encodeURIComponent(state.openArticle).replace(/%2F/g, "/")}` : "";
    return `${window.location.pathname}?${params.toString()}${hash}`;
  }

  function pushUrl() {
    window.history.pushState(null, "", buildUrl());
  }

  function replaceUrl() {
    window.history.replaceState(null, "", buildUrl());
  }

  // ---------------------------------------------------------------------------
  // Render: header

  function weekOption(id) {
    return `<option value="${escapeHtml(id)}">${escapeHtml(weekOptionLabel(id))}</option>`;
  }

  function weeksOfYear(year) {
    return state.weeks.filter((id) => parseWeekId(id).year === year);
  }

  function adjacentWeekId(weekId, delta) {
    const { year, week } = parseWeekId(weekId);
    const shifted = shiftIsoWeek(year, week, delta);
    return normalizeWeekId(shifted.year, shifted.week);
  }

  // Stesso numero di settimana nell'anno scelto, altrimenti la disponibile più vicina.
  function closestWeekInYear(year, week) {
    const candidates = weeksOfYear(year);
    let best = null;
    candidates.forEach((id) => {
      const distance = Math.abs(parseWeekId(id).week - week);
      if (!best || distance < best.distance) best = { id, distance };
    });
    return best ? best.id : null;
  }

  function renderGroupedWeekOptions(excludeId) {
    const byYear = new Map();
    state.weeks
      .slice()
      .reverse()
      .forEach((id) => {
        const { year } = parseWeekId(id);
        if (!byYear.has(year)) byYear.set(year, []);
        byYear.get(year).push(id);
      });
    return Array.from(byYear.entries())
      .map(([year, ids]) => {
        const options = ids.filter((id) => id !== excludeId).map(weekOption).join("");
        return `<optgroup label="${year}">${options}</optgroup>`;
      })
      .join("");
  }

  function renderHeader() {
    const { year } = parseWeekId(state.weekId);
    const years = Array.from(new Set(state.weeks.map((id) => parseWeekId(id).year))).sort((a, b) => b - a);
    const yearKey = years.join(",");
    if (els.year.dataset.key !== yearKey) {
      els.year.innerHTML = years.map((y) => `<option value="${y}">${y}</option>`).join("");
      els.year.dataset.key = yearKey;
    }
    els.year.value = String(year);
    const yearWeeks = weeksOfYear(year).reverse();
    const weekKey = yearWeeks.join(",");
    if (els.select.dataset.key !== weekKey) {
      els.select.innerHTML = yearWeeks.map(weekOption).join("");
      els.select.dataset.key = weekKey;
    }
    els.select.value = state.weekId;
    els.prev.disabled = !state.weekSet.has(adjacentWeekId(state.weekId, -1));
    els.next.disabled = !state.weekSet.has(adjacentWeekId(state.weekId, 1));
    els.tabs.forEach((tab) => {
      tab.setAttribute("aria-selected", String(tab.dataset.view === state.view));
    });
  }

  // ---------------------------------------------------------------------------
  // Render: stati

  function renderSkeleton() {
    els.main.innerHTML = `
      <div class="skeleton" aria-busy="true" aria-label="Caricamento">
        <div class="ph sk-bar"></div>
        <div class="ph sk-img"></div>
        <div class="ph sk-t1"></div>
        <div class="ph sk-t2"></div>
        <div class="ph sk-row"></div>
        <div class="ph sk-row"></div>
        <div class="ph sk-row"></div>
      </div>`;
  }

  function renderError(weekId) {
    els.main.innerHTML = `<div class="error">Impossibile caricare la settimana ${escapeHtml(weekId)}.</div>`;
  }

  // ---------------------------------------------------------------------------
  // Render: classifica

  function sparkline(entry, size) {
    const bars = entry.daily
      .map((value) => {
        if (!value || !entry.max) return `<span style="height:0"></span>`;
        const height = (value / entry.max) * 100;
        const peak = value === entry.max ? ' class="peak"' : "";
        return `<span${peak} style="height:${height.toFixed(1)}%"></span>`;
      })
      .join("");
    return `<span class="spark spark-${size}" aria-hidden="true">${bars}</span>`;
  }

  function rowAriaLabel(entry) {
    const parts = [`N° ${entry.rank}`, entry.title, `${formatViews(entry.views)} visite`];
    if (entry.trend) parts.push(entry.trend);
    return parts.join(", ");
  }

  function renderHero(entry) {
    const image = entry.image
      ? `<span class="hero-img" style="display:block"><img src="${escapeHtml(entry.image)}" alt="" /></span>`
      : `<span class="hero-img ph"><span class="ph-label">nessuna immagine su commons</span></span>`;
    const description = entry.description ? `<span class="hero-desc">${escapeHtml(entry.description)}</span>` : "";
    return `
      <button type="button" class="hero rowbtn" data-article="${escapeHtml(entry.key)}" aria-label="${escapeHtml(rowAriaLabel(entry))}">
        ${image}
        <span class="hero-body">
          <span class="hero-meta">
            <span class="badge num">N° 1</span>
            ${entry.trend ? `<span class="hero-trend" style="color:${entry.trendColor}">${escapeHtml(entry.trend)}</span>` : ""}
            ${entry.rankMove ? `<span class="hero-move num">${escapeHtml(entry.rankMove)}</span>` : ""}
          </span>
          <span class="hero-title">${escapeHtml(entry.title)}</span>
          ${description}
          <span class="hero-numbers">
            <span>
              <span class="hero-views num">${formatViews(entry.views)}</span>
              <span class="hero-shape">${escapeHtml(entry.shape)}</span>
            </span>
            ${sparkline(entry, "lg")}
          </span>
        </span>
      </button>`;
  }

  function renderRow(entry) {
    const thumb = entry.image
      ? `<span class="thumb"><img src="${escapeHtml(entry.image)}" alt="" loading="lazy" /></span>`
      : `<span class="thumb ph"></span>`;
    const description = entry.description ? `<span class="row-desc cl2">${escapeHtml(entry.description)}</span>` : "";
    return `
      <button type="button" class="row rowbtn" data-article="${escapeHtml(entry.key)}" aria-label="${escapeHtml(rowAriaLabel(entry))}">
        <span class="row-rank num">${entry.rank}</span>
        ${thumb}
        <span class="row-text">
          <span class="row-title">${escapeHtml(entry.title)}</span>
          ${description}
          <span class="row-bottom">
            <span class="row-stats">
              <span class="row-views num">${formatViews(entry.views)}</span>
              ${entry.trend ? `<span class="row-trend" style="color:${entry.trendColor}">${escapeHtml(entry.trend)}</span>` : ""}
              ${entry.rankMove ? `<span class="row-move num">${escapeHtml(entry.rankMove)}</span>` : ""}
            </span>
            ${sparkline(entry, "sm")}
          </span>
        </span>
      </button>`;
  }

  function renderChips() {
    const all = model.entries;
    const defs = [["tutte", "Tutte le 25"]];
    if (model.adjacent) {
      defs.push(["novita", `Nuove entrate · ${all.filter((e) => e.isNew).length}`]);
      defs.push(["crescita", `In crescita · ${filterEntries(model, "crescita").length}`]);
    }
    defs.push(["picco", `Picco in un giorno · ${filterEntries(model, "picco").length}`]);
    const chips = defs
      .map(
        ([id, label]) =>
          `<button type="button" class="chip" data-filter="${id}" aria-pressed="${state.filter === id}">${escapeHtml(label)}</button>`
      )
      .join("");
    return `<div class="chips hidebar" role="group" aria-label="Filtra la classifica">${chips}</div>`;
  }

  function renderList() {
    if (!model.adjacent && (state.filter === "novita" || state.filter === "crescita")) state.filter = "tutte";
    const shown = filterEntries(model, state.filter);
    const showHero = state.filter === "tutte" && shown.length > 0;
    const rows = (showHero ? shown.slice(1) : shown).map(renderRow).join("");
    const missing = Array.isArray(model.data.missing_days) ? model.data.missing_days.length : 0;
    const incomplete =
      model.data.complete === false
        ? `<div class="datebar-note">Settimana incompleta: ${missing === 1 ? "manca 1 giorno" : `mancano ${missing} giorni`}</div>`
        : "";

    els.main.innerHTML = `
      <div class="datebar">
        <div>
          <div class="datebar-range">${escapeHtml(model.range)}</div>
          ${incomplete}
        </div>
        <div class="datebar-total num">${formatViews(model.total)} visite</div>
      </div>
      ${renderChips()}
      ${showHero ? renderHero(shown[0]) : ""}
      ${rows}
      ${shown.length === 0 ? `<div class="empty">Nessuna voce corrisponde a questo filtro.</div>` : ""}
      <div class="footer">
        Fonte: <a href="https://wikitech.wikimedia.org/wiki/Analytics/AQS/Pageviews"${EXTERNAL_LINK_ATTRS}>Wikimedia Pageviews API</a>,
        progetto it.wikipedia, tutti gli accessi.
      </div>`;
  }

  // ---------------------------------------------------------------------------
  // Render: confronta

  function moveLabel(delta) {
    if (delta === 0) return "=";
    return delta > 0 ? `▲ ${delta}` : `▼ ${-delta}`;
  }

  function renderCompare() {
    const vsId = state.vsId;
    const vsTop = vsData ? articlesOf(vsData, TOP_N) : [];
    const vsTotal = vsTop.reduce((sum, a) => sum + (Number(a.views) || 0), 0);
    const max = Math.max(model.total, vsTotal) || 1;
    const vsRanks = new Map(vsTop.map((a, i) => [a.article, rankOf(a, i)]));
    const currentKeys = new Set(model.entries.map((e) => e.key));

    const options = renderGroupedWeekOptions(state.weekId);

    const prevId = previousAdjacentId(state.weekId);
    const yearAgoId = sameWeekLastYear(state.weekId);
    const shortcut = (id, label) =>
      `<button type="button" class="chip" data-vs="${escapeHtml(id)}" aria-pressed="${vsId === id}"${
        state.weekSet.has(id) ? "" : " disabled"
      }>${label}</button>`;

    const moves = model.entries
      .filter((e) => vsRanks.has(e.key))
      .map((e) => {
        const delta = vsRanks.get(e.key) - e.rank;
        return `
          <div class="cmp-row">
            <span class="cmp-rank num">${e.rank}</span>
            <span class="cmp-title">${escapeHtml(e.title)}</span>
            <span class="cmp-move num${delta > 0 ? " up" : ""}">${moveLabel(delta)}</span>
          </div>`;
      })
      .join("");

    const mutedRow = (rank, title, views) => `
      <div class="cmp-row muted">
        <span class="cmp-rank num">${rank}</span>
        <span class="cmp-title">${escapeHtml(title)}</span>
        <span class="cmp-views num">${formatViews(views)}</span>
      </div>`;

    const onlyVs = vsTop
      .map((a, i) => (currentKeys.has(a.article) ? "" : mutedRow(rankOf(a, i), articleTitle(a.article), a.views)))
      .join("");
    const onlyCurrent = model.entries
      .filter((e) => !vsRanks.has(e.key))
      .map((e) => mutedRow(e.rank, e.title, e.views))
      .join("");

    const vsBody = vsData
      ? `
        <h2 class="cmp-section">Presenti in entrambe le settimane</h2>
        ${moves || `<div class="cmp-empty">Nessuna pagina in comune: le due settimane non condividono nemmeno un titolo nella top 25.</div>`}
        <h2 class="cmp-section cmp-gap">Solo in ${escapeHtml(weekLabel(vsId))}</h2>
        ${onlyVs}
        <h2 class="cmp-section cmp-gap">Solo in questa settimana</h2>
        ${onlyCurrent}`
      : `<div class="error">Impossibile caricare la settimana ${escapeHtml(vsId)}.</div>`;

    els.main.innerHTML = `
      <div class="cmp-head">
        <label class="cmp-label" for="vs-select">Confronta con</label>
        <div class="select-wrap">
          <select id="vs-select">${options}</select>
        </div>
        <div class="chips chips-inline">
          ${shortcut(prevId, "Settimana prima")}
          ${shortcut(yearAgoId, "Un anno fa")}
        </div>
        <div class="cmp-totals">
          <div class="cmp-total">
            <div class="caps">${escapeHtml(model.range)}</div>
            <div class="cmp-sum num">${formatViews(model.total)}</div>
            <div class="cmp-bar" style="width:${Math.round((model.total / max) * 100)}%"></div>
          </div>
          <div class="cmp-total">
            <div class="caps">${escapeHtml(weekRangeLabel(vsId, vsData))}</div>
            <div class="cmp-sum other num">${vsData ? formatViews(vsTotal) : "n.d."}</div>
            <div class="cmp-bar other" style="width:${Math.round((vsTotal / max) * 100)}%"></div>
          </div>
        </div>
        <div class="cmp-note">Somma delle visite delle prime 25 pagine.</div>
      </div>
      ${vsBody}
      <div class="cmp-end"></div>`;

    const vsSelect = document.getElementById("vs-select");
    vsSelect.value = vsId;
  }

  function renderMain() {
    if (!model) return;
    if (state.view === "cmp") renderCompare();
    else renderList();
  }

  // ---------------------------------------------------------------------------
  // Scheda di dettaglio

  function renderHistory(entry, histWeeks) {
    const cols = histWeeks.map(({ id, data }) => {
      const top = articlesOf(data, 30);
      const index = top.findIndex((a) => a.article === entry.key);
      const rank = index >= 0 ? rankOf(top[index], index) : 0;
      const current = id === state.weekId;
      const height = rank ? ((31 - rank) / 30) * 100 : 0;
      return {
        present: rank > 0,
        html: `
          <div class="hist-col${current ? " current" : ""}">
            <div class="hist-rank num">${rank || "—"}</div>
            ${rank ? `<div class="hist-bar" style="height:${height.toFixed(1)}%"></div>` : ""}
            <div class="hist-week num">${parseWeekId(id).week}</div>
          </div>`,
      };
    });
    if (cols.filter((c) => c.present).length <= 1) return "";
    return `
      <div class="sheet-label hist-label">Posizione nelle settimane disponibili</div>
      <div class="hist" aria-label="Posizione in classifica nelle ultime ${cols.length} settimane disponibili">
        ${cols.map((c) => c.html).join("")}
      </div>`;
  }

  async function loadHistory(entry) {
    const index = state.weeks.indexOf(state.weekId);
    const ids = index >= 0 ? state.weeks.slice(Math.max(0, index - HIST_WINDOW + 1), index + 1) : [state.weekId];
    const weekId = state.weekId;
    const datas = await Promise.all(ids.map((id) => fetchWeek(id)));
    if (state.weekId !== weekId || state.openArticle !== entry.key) return;
    const slot = document.getElementById("sheet-hist");
    if (!slot) return;
    slot.innerHTML = renderHistory(
      entry,
      ids.map((id, i) => ({ id, data: datas[i] })).filter((item) => item.data)
    );
  }

  function renderSheet(entry) {
    const raw = entry.raw;
    const peakIndex = entry.daily.indexOf(entry.max);
    const daily = entry.daily
      .map((value) => {
        const peak = value > 0 && value === entry.max;
        const height = entry.max ? (value / entry.max) * 100 : 0;
        return `
          <div class="daily-col${peak ? " peak" : ""}">
            <div class="daily-val num">${value ? formatViews(value) : ""}</div>
            ${value ? `<div class="daily-bar" style="height:${height.toFixed(1)}%"></div>` : ""}
          </div>`;
      })
      .join("");
    const days = entry.daily.map((_, i) => `<div>${DAYS_SHORT[i] || ""}</div>`).join("");
    const trend = model.adjacent ? entry.trend : "n.d.";
    const trendColor = model.adjacent ? entry.trendColor : "#a2a9b1";
    const license = raw.image_license || "vedi licenza";
    const creditUrl = raw.image_commons_url || raw.image_url;

    els.sheetRoot.innerHTML = `
      <div class="overlay" data-close></div>
      <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" tabindex="-1">
        <div class="sheet-top">
          <span class="badge num">N° ${entry.rank}</span>
          <button type="button" class="sheet-close" data-close aria-label="Chiudi">✕</button>
        </div>
        ${entry.image ? `<div class="sheet-img"><img src="${escapeHtml(entry.image)}" alt="" /></div>` : ""}
        <div class="sheet-body">
          <h2 class="sheet-title" id="sheet-title">${escapeHtml(entry.title)}</h2>
          ${entry.description ? `<div class="sheet-desc">${escapeHtml(entry.description)}</div>` : ""}
          <div class="metrics">
            <div class="metric">
              <div class="metric-label">visite</div>
              <div class="metric-value num">${formatViews(entry.views)}</div>
            </div>
            <div class="metric">
              <div class="metric-label">vs settimana prec.</div>
              <div class="metric-value num" style="color:${trendColor}">${escapeHtml(trend)}</div>
            </div>
          </div>
          <div class="sheet-label">Andamento giornaliero</div>
          <div class="daily" aria-hidden="true">${daily}</div>
          <div class="days" aria-hidden="true">${days}</div>
          <div class="peak-note">
            Picco <strong>${DAYS_FULL[peakIndex] || ""}</strong>, il <strong class="num">${entry.share}%</strong>
            delle visite della settimana. ${escapeHtml(entry.shape)}
          </div>
          <div id="sheet-hist"></div>
          <div class="actions">
            ${raw.article_url ? `<a class="cta cta-primary" href="${escapeHtml(raw.article_url)}"${EXTERNAL_LINK_ATTRS}>Leggi su Wikipedia</a>` : ""}
            ${raw.google_news_url ? `<a class="cta cta-secondary" href="${escapeHtml(raw.google_news_url)}"${EXTERNAL_LINK_ATTRS}>Perché? Notizie di quella settimana</a>` : ""}
            ${raw.pageviews_url ? `<a class="cta-link" href="${escapeHtml(raw.pageviews_url)}"${EXTERNAL_LINK_ATTRS}>Serie completa su Pageviews ↗</a>` : ""}
          </div>
          ${
            entry.image
              ? `<div class="credit">Immagine: ${
                  creditUrl ? `<a href="${escapeHtml(creditUrl)}"${EXTERNAL_LINK_ATTRS}>${escapeHtml(license)}</a>` : escapeHtml(license)
                } · Wikimedia Commons</div>`
              : ""
          }
        </div>
      </div>`;
    document.body.classList.add("sheet-open");
    els.sheetRoot.querySelector(".sheet").focus();
    loadHistory(entry);
  }

  function findEntry(article) {
    if (!model || !article) return null;
    return model.entries.find((e) => sameArticle(e.key, article)) || null;
  }

  function showSheet(article) {
    const entry = findEntry(article);
    if (!entry) {
      state.openArticle = null;
      return false;
    }
    state.openArticle = entry.key;
    renderSheet(entry);
    return true;
  }

  function hideSheet() {
    const hadSheet = !!els.sheetRoot.firstChild;
    const article = state.openArticle;
    els.sheetRoot.innerHTML = "";
    document.body.classList.remove("sheet-open");
    state.openArticle = null;
    if (hadSheet && article) {
      const target = sheetReturnFocus && document.contains(sheetReturnFocus)
        ? sheetReturnFocus
        : Array.from(els.main.querySelectorAll("[data-article]")).find((el) => el.dataset.article === article);
      if (target) target.focus({ preventScroll: true });
    }
    sheetReturnFocus = null;
  }

  function openSheetFromUser(article, trigger) {
    sheetReturnFocus = trigger || null;
    if (!showSheet(article)) return;
    pushUrl();
    sheetPushed = true;
  }

  function closeSheetFromUser() {
    if (!state.openArticle) return;
    if (sheetPushed) {
      sheetPushed = false;
      window.history.back();
      return;
    }
    hideSheet();
    replaceUrl();
  }

  function trapFocus(event) {
    const sheet = els.sheetRoot.querySelector(".sheet");
    if (!sheet) return;
    const focusable = Array.from(sheet.querySelectorAll("a[href], button:not([disabled])"));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === sheet)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  // ---------------------------------------------------------------------------
  // Caricamento

  async function load() {
    const token = ++loadToken;
    const weekId = state.weekId;
    renderHeader();
    if (!ready.has(weekId)) renderSkeleton();

    const prevId = previousAdjacentId(weekId);
    const [data, prevData, vs] = await Promise.all([
      fetchWeek(weekId),
      state.weekSet.has(prevId) ? fetchWeek(prevId) : null,
      state.view === "cmp" && state.vsId ? fetchWeek(state.vsId) : null,
    ]);
    if (token !== loadToken) return;

    if (!data) {
      model = null;
      renderError(weekId);
      return;
    }
    if (!state.weekSet.has(weekId)) {
      state.weeks.push(weekId);
      state.weeks.sort();
      state.weekSet.add(weekId);
      renderHeader();
    }
    model = buildModel(weekId, data, prevData);
    vsData = vs;
    document.title = `Le 25 più lette · ${model.range}`;
    renderMain();
  }

  async function loadVs() {
    const token = loadToken;
    const vsId = state.vsId;
    if (!ready.has(vsId)) renderSkeleton();
    const data = await fetchWeek(vsId);
    if (token !== loadToken || vsId !== state.vsId || state.view !== "cmp") return;
    vsData = data;
    renderMain();
  }

  function goToWeek(weekId) {
    if (!weekId || weekId === state.weekId) return;
    hideSheet();
    sheetPushed = false;
    state.weekId = weekId;
    state.vsId = defaultVs(weekId);
    pushUrl();
    window.scrollTo(0, 0);
    load();
  }

  function setView(view) {
    if (view === state.view) return;
    state.view = view;
    pushUrl();
    renderHeader();
    if (view === "cmp") loadVs();
    else renderMain();
  }

  function setVs(vsId) {
    if (!vsId || vsId === state.vsId) return;
    state.vsId = vsId;
    replaceUrl();
    loadVs();
  }

  // ---------------------------------------------------------------------------
  // Eventi

  els.prev.addEventListener("click", () => {
    const target = adjacentWeekId(state.weekId, -1);
    if (state.weekSet.has(target)) goToWeek(target);
  });

  els.next.addEventListener("click", () => {
    const target = adjacentWeekId(state.weekId, 1);
    if (state.weekSet.has(target)) goToWeek(target);
  });

  els.select.addEventListener("change", (event) => goToWeek(event.target.value));

  els.year.addEventListener("change", (event) => {
    const target = closestWeekInYear(Number(event.target.value), parseWeekId(state.weekId).week);
    if (target) goToWeek(target);
  });

  els.tabs.forEach((tab) => tab.addEventListener("click", () => setView(tab.dataset.view)));

  els.main.addEventListener("click", (event) => {
    const row = event.target.closest("[data-article]");
    if (row) {
      openSheetFromUser(row.dataset.article, row);
      return;
    }
    const chip = event.target.closest("[data-filter]");
    if (chip) {
      state.filter = chip.dataset.filter;
      renderList();
      const active = els.main.querySelector(`[data-filter="${state.filter}"]`);
      if (active) active.focus();
      return;
    }
    const vsChip = event.target.closest("[data-vs]");
    if (vsChip && !vsChip.disabled) setVs(vsChip.dataset.vs);
  });

  els.main.addEventListener("change", (event) => {
    if (event.target.id === "vs-select") setVs(event.target.value);
  });

  els.sheetRoot.addEventListener("click", (event) => {
    if (event.target.closest("[data-close]")) closeSheetFromUser();
  });

  document.addEventListener("keydown", (event) => {
    if (!state.openArticle) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeSheetFromUser();
    } else if (event.key === "Tab") {
      trapFocus(event);
    }
  });

  window.addEventListener("popstate", () => {
    const url = readUrl();
    sheetPushed = false;
    const weekChanged = url.week && url.week !== state.weekId;
    state.view = url.view;
    if (weekChanged) {
      hideSheet();
      state.weekId = url.week;
      state.vsId = url.vs || defaultVs(url.week);
      load().then(() => {
        if (url.article) showSheet(url.article);
      });
      return;
    }
    const vsChanged = (url.vs || defaultVs(state.weekId)) !== state.vsId;
    state.vsId = url.vs || defaultVs(state.weekId);
    renderHeader();
    if (state.view === "cmp" && vsChanged) loadVs();
    else renderMain();
    if (url.article) {
      if (!state.openArticle || !sameArticle(url.article, state.openArticle)) showSheet(url.article);
    } else {
      hideSheet();
    }
  });

  // ---------------------------------------------------------------------------
  // Avvio

  async function init() {
    try {
      const response = await fetch("weeks.json");
      const weeks = await response.json();
      if (Array.isArray(weeks)) state.weeks = weeks.slice().sort();
    } catch (error) {
      state.weeks = [];
    }
    state.weekSet = new Set(state.weeks);

    const url = readUrl();
    const weekId = url.week || state.weeks[state.weeks.length - 1];
    if (!weekId) {
      els.main.innerHTML = `<div class="error">Nessuna settimana disponibile.</div>`;
      return;
    }
    state.weekId = weekId;
    state.view = url.view;
    state.vsId = url.vs || defaultVs(weekId);
    replaceUrl();
    await load();
    if (url.article && showSheet(url.article)) {
      sheetPushed = false;
      replaceUrl();
    }
  }

  init();
})();
