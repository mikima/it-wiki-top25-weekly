(() => {
  "use strict";

  const DEFAULT_FOCUS = { x: 50, y: 22 }; // same as "object-position: center 22%" in docs/week.css
  const DAYS = ["L", "M", "M", "G", "V", "S", "D"];
  const $ = (sel) => document.querySelector(sel);

  const state = { weeks: [], weekId: null, data: null, mtime: null, edits: new Map() };

  // Same framing rules as docs/week.js (frameStyle): keep them in sync.
  function frameStyle(focus, fit) {
    const x = focus ? focus.x : DEFAULT_FOCUS.x;
    const y = focus ? focus.y : DEFAULT_FOCUS.y;
    if (fit === "width") {
      return `position:absolute;left:0;width:100%;height:auto;top:${y}%;transform:translateY(-${y}%)`;
    }
    if (fit === "height") {
      return `position:absolute;top:0;height:100%;width:auto;max-width:none;left:${x}%;transform:translateX(-${x}%)`;
    }
    return `display:block;width:100%;height:100%;object-fit:cover;object-position:${x}% ${y}%`;
  }

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n) => Number(n || 0).toLocaleString("it-IT");

  function current(article) {
    const edit = state.edits.get(article.article) || {};
    return {
      description: "description" in edit ? edit.description : article.description || "",
      focus: "image_focus" in edit ? edit.image_focus : article.image_focus || null,
      fit: "image_fit" in edit ? edit.image_fit : article.image_fit || "cover",
    };
  }

  function setEdit(articleName, key, value) {
    const article = state.data.articles.find((a) => a.article === articleName);
    const edit = state.edits.get(articleName) || {};
    const original = key === "description" ? article.description || ""
      : key === "image_fit" ? article.image_fit || "cover"
      : article.image_focus || null;
    if (JSON.stringify(value) === JSON.stringify(original)) delete edit[key];
    else edit[key] = value;
    if (Object.keys(edit).length) state.edits.set(articleName, edit);
    else state.edits.delete(articleName);
    updateDirty();
  }

  function updateDirty() {
    const n = state.edits.size;
    $("#save").disabled = n === 0;
    $("#save").textContent = n ? `Salva (${n})` : "Salva";
    document.querySelectorAll(".card").forEach((card) => card.classList.toggle("dirty", state.edits.has(card.dataset.article)));
    if (n) setStatus(`${n} voce/i modificate, non salvate`);
  }

  function setStatus(text, cls = "") {
    const el = $("#status");
    el.textContent = text;
    el.className = "status " + cls;
  }

  function sparkline(article) {
    const views = (article.daily_views || []).map((d) => d.views || 0);
    const max = Math.max(1, ...views);
    const peak = views.indexOf(Math.max(...views));
    return `<div class="spark">${views.map((v, i) => `<span class="${i === peak ? "peak" : ""}" style="height:${Math.max(2, (v / max) * 100)}%" title="${fmt(v)}"></span>`).join("")}</div>
      <div class="days">${views.map((_, i) => `<span>${DAYS[i]}</span>`).join("")}</div>`;
  }

  function peakLabel(article) {
    const daily = article.daily_views || [];
    if (!daily.length) return "";
    const top = daily.reduce((a, b) => (b.views > a.views ? b : a));
    const [, m, d] = top.date.split("-");
    return `picco ${d}/${m}`;
  }

  function previews(article, c) {
    const img = (fit) => `<img src="${esc(article.image_url)}" alt="" style="${frameStyle(c.focus, fit)}" />`;
    return `
      <div><div class="pv-label">primo piano</div><div class="frame hero">${img(c.fit)}</div></div>
      <div><div class="pv-label">scheda mobile</div><div class="frame sheet">${img(c.fit)}</div></div>
      <div class="pv-wide"><div class="pv-label">scheda desktop (larga)</div><div class="frame wide">${img(c.fit)}</div></div>
      <div><div class="pv-label">miniatura</div><div class="frame thumb">${img("cover")}</div></div>`;
  }

  function renderCard(article) {
    const c = current(article);
    const hasImg = !!article.image_url;
    const focus = c.focus || DEFAULT_FOCUS;
    const src = article.description_source || "";
    const fitBtn = (value, label) => `<button type="button" data-fit="${value}" aria-pressed="${c.fit === value}">${label}</button>`;
    const imageCol = hasImg ? `
      <div class="imgcol">
        <div class="src" title="Clicca per scegliere il punto centrale">
          <img src="${esc(article.image_url)}" alt="" />
          <span class="dot" style="left:${focus.x}%;top:${focus.y}%"></span>
        </div>
        <div class="fit">
          ${fitBtn("cover", "riempi")}${fitBtn("width", "larghezza intera")}${fitBtn("height", "altezza intera")}
          <button type="button" class="reset" title="Torna all'inquadratura predefinita">reimposta</button>
        </div>
        <div class="previews">${previews(article, c)}</div>
      </div>` : "";
    return `
      <section class="card${hasImg ? "" : " noimg"}${state.edits.has(article.article) ? " dirty" : ""}" data-article="${esc(article.article)}">
        ${imageCol}
        <div class="textcol">
          <div class="meta">
            <span class="rank">${article.rank}</span>
            <a class="title" href="${esc(article.article_url)}" target="_blank" rel="noopener">${esc(article.article.replace(/_/g, " "))}</a>
            <span class="badge ${esc(src)}">${esc(src || "vuota")}${article.description_model ? " · " + esc(article.description_model) : ""}</span>
            <span class="links">
              ${article.google_news_url ? `<a href="${esc(article.google_news_url)}" target="_blank" rel="noopener">notizie</a>` : ""}
              ${article.pageviews_url ? `<a href="${esc(article.pageviews_url)}" target="_blank" rel="noopener">pageviews</a>` : ""}
            </span>
          </div>
          <div class="facts">${fmt(article.views)} visite · ${peakLabel(article)}</div>
          <textarea spellcheck="true" lang="it">${esc(c.description)}</textarea>
          <div class="count">${c.description.length} caratteri</div>
          ${sparkline(article)}
        </div>
      </section>`;
  }

  function render() {
    const list = $("#list");
    if (!state.data) { list.innerHTML = `<div class="empty">Caricamento…</div>`; return; }
    const onlyImg = $("#only-img").checked;
    const articles = state.data.articles.filter((a) => !onlyImg || a.image_url);
    list.innerHTML = articles.map(renderCard).join("") || `<div class="empty">Nessuna voce.</div>`;
  }

  function refreshCard(card) {
    const article = state.data.articles.find((a) => a.article === card.dataset.article);
    const c = current(article);
    const focus = c.focus || DEFAULT_FOCUS;
    const dot = card.querySelector(".dot");
    if (dot) { dot.style.left = focus.x + "%"; dot.style.top = focus.y + "%"; }
    card.querySelectorAll(".fit [data-fit]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.fit === c.fit)));
    const pv = card.querySelector(".previews");
    if (pv) pv.innerHTML = previews(article, c);
    placeDot(card);
  }

  // --- events -------------------------------------------------------------
  $("#list").addEventListener("click", (event) => {
    const card = event.target.closest(".card");
    if (!card) return;
    const name = card.dataset.article;
    const src = event.target.closest(".src");
    if (src) {
      const img = src.querySelector("img");
      const r = img.getBoundingClientRect();
      // object-fit: contain -> compute the drawn image box inside the element
      const ratio = img.naturalWidth / img.naturalHeight;
      let w = r.width, h = r.width / ratio;
      if (h > r.height) { h = r.height; w = h * ratio; }
      const left = r.left + (r.width - w) / 2, top = r.top + (r.height - h) / 2;
      const x = Math.round(Math.max(0, Math.min(100, ((event.clientX - left) / w) * 100)));
      const y = Math.round(Math.max(0, Math.min(100, ((event.clientY - top) / h) * 100)));
      setEdit(name, "image_focus", { x, y });
      refreshCard(card);
      return;
    }
    const fitBtn = event.target.closest("[data-fit]");
    if (fitBtn) { setEdit(name, "image_fit", fitBtn.dataset.fit); refreshCard(card); return; }
    if (event.target.closest(".reset")) {
      setEdit(name, "image_focus", null);
      setEdit(name, "image_fit", "cover");
      refreshCard(card);
    }
  });

  $("#list").addEventListener("input", (event) => {
    if (event.target.tagName !== "TEXTAREA") return;
    const card = event.target.closest(".card");
    setEdit(card.dataset.article, "description", event.target.value.replace(/\s+/g, " ").trim());
    card.querySelector(".count").textContent = `${event.target.value.length} caratteri`;
  });

  // position the dot correctly once images know their size (object-fit: contain)
  $("#list").addEventListener("load", (event) => {
    if (event.target.matches(".src img")) placeDot(event.target.closest(".card"));
  }, true);

  function placeDot(card) {
    const img = card.querySelector(".src img");
    const dot = card.querySelector(".dot");
    if (!img || !dot || !img.naturalWidth) return;
    const article = state.data.articles.find((a) => a.article === card.dataset.article);
    const focus = current(article).focus || DEFAULT_FOCUS;
    const box = img.getBoundingClientRect(), wrap = card.querySelector(".src").getBoundingClientRect();
    const ratio = img.naturalWidth / img.naturalHeight;
    let w = box.width, h = box.width / ratio;
    if (h > box.height) { h = box.height; w = h * ratio; }
    const offX = box.left - wrap.left + (box.width - w) / 2, offY = box.top - wrap.top + (box.height - h) / 2;
    dot.style.left = `${offX + (focus.x / 100) * w}px`;
    dot.style.top = `${offY + (focus.y / 100) * h}px`;
  }

  $("#only-img").addEventListener("change", render);
  $("#save").addEventListener("click", () => save(false));
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); if (state.edits.size) save(false); }
  });
  window.addEventListener("beforeunload", (e) => { if (state.edits.size) { e.preventDefault(); e.returnValue = ""; } });
  window.addEventListener("resize", () => document.querySelectorAll(".card").forEach(placeDot));

  async function save(force) {
    const changes = [...state.edits].map(([article, edit]) => ({ article, ...edit }));
    setStatus("Salvataggio…");
    const res = await fetch(`/api/week/${state.weekId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mtime: state.mtime, changes, force }),
    });
    const out = await res.json();
    if (res.status === 409) {
      setStatus("File modificato da un altro programma", "err");
      if (confirm(out.error + "\n\nOK = salva comunque (sovrascrive), Annulla = non salvare")) return save(true);
      return;
    }
    if (!res.ok) { setStatus(out.error || "Errore nel salvataggio", "err"); return; }
    state.data = out.data;
    state.mtime = out.mtime;
    state.edits.clear();
    render();
    updateDirty();
    setStatus(`Salvato ${new Date().toLocaleTimeString("it-IT")}`, "ok");
  }

  // --- navigation ---------------------------------------------------------
  function fillSelectors() {
    const years = [...new Set(state.weeks.map((w) => w.slice(0, 4)))];
    const [y] = state.weekId.split("-");
    $("#year").innerHTML = years.map((v) => `<option${v === y ? " selected" : ""}>${v}</option>`).join("");
    const weeks = state.weeks.filter((w) => w.startsWith(y));
    $("#week").innerHTML = weeks.map((w) => `<option value="${w}"${w === state.weekId ? " selected" : ""}>settimana ${w.slice(5)}</option>`).join("");
    const i = state.weeks.indexOf(state.weekId);
    $("#prev").disabled = i <= 0;
    $("#next").disabled = i >= state.weeks.length - 1;
  }

  async function loadWeek(weekId) {
    if (state.edits.size && !confirm("Ci sono modifiche non salvate. Cambiare settimana e perderle?")) { fillSelectors(); return; }
    state.weekId = weekId;
    state.edits.clear();
    state.data = null;
    updateDirty();
    setStatus("");
    fillSelectors();
    render();
    location.hash = weekId;
    const res = await fetch(`/api/week/${weekId}`);
    const out = await res.json();
    if (!res.ok) { setStatus(out.error || "Errore", "err"); return; }
    state.data = out.data;
    state.mtime = out.mtime;
    render();
  }

  $("#year").addEventListener("change", (e) => {
    const first = state.weeks.filter((w) => w.startsWith(e.target.value));
    loadWeek(first[first.length - 1]);
  });
  $("#week").addEventListener("change", (e) => loadWeek(e.target.value));
  $("#prev").addEventListener("click", () => loadWeek(state.weeks[state.weeks.indexOf(state.weekId) - 1]));
  $("#next").addEventListener("click", () => loadWeek(state.weeks[state.weeks.indexOf(state.weekId) + 1]));

  (async () => {
    const out = await (await fetch("/api/weeks")).json();
    state.weeks = out.weeks;
    const fromHash = location.hash.slice(1);
    loadWeek(state.weeks.includes(fromHash) ? fromHash : state.weeks[state.weeks.length - 1]);
  })();
})();
