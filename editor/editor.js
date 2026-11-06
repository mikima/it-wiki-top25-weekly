(() => {
  "use strict";

  const DEFAULT_FOCUS = { x: 50, y: 22 }; // same as "object-position: center 22%" in docs/week.css
  const DAYS = ["L", "M", "M", "G", "V", "S", "D"];
  const $ = (sel) => document.querySelector(sel);

  const state = { weeks: [], weekId: null, data: null, mtime: null, edits: new Map(), context: {}, lookups: {} };

  // Same framing rules as frameStyle in docs/week.js: keep them in sync.
  // crop: 0 = whole height visible ... 100 = whole width visible (needs the image aspect ratio);
  // fit: legacy modes "width" / "height"; nothing set = cover centred on the focus point.
  // Frames need `container-type: size` for the cqw/cqh units.
  function frameStyle(focus, fit, crop, aspect) {
    const x = focus ? focus.x : DEFAULT_FOCUS.x;
    const y = focus ? focus.y : DEFAULT_FOCUS.y;
    if (crop !== null && crop !== undefined && aspect) {
      const t = crop / 100;
      const w = `calc(${((1 - t) * aspect).toFixed(4)} * 100cqh + ${t.toFixed(4)} * 100cqw)`;
      return `position:absolute;max-width:none;height:auto;width:${w};left:${x}%;top:${y}%;transform:translate(-${x}%,-${y}%)`;
    }
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
  const findArticle = (name) => state.data.articles.find((a) => a.article === name);

  function current(article) {
    const edit = state.edits.get(article.article) || {};
    const image = "image" in edit ? edit.image : null;
    const fit = "image_fit" in edit ? edit.image_fit : image ? "cover" : article.image_fit || "cover";
    let crop = "image_crop" in edit ? edit.image_crop : image ? null : article.image_crop ?? null;
    const aspect = edit.image_aspect || (image ? null : article.image_aspect) || null;
    return {
      description: "description" in edit ? edit.description : article.description || "",
      focus: "image_focus" in edit ? edit.image_focus : image ? null : article.image_focus || null,
      fit,
      crop,
      aspect,
      // slider position shown for the legacy modes
      sliderValue: crop ?? (fit === "width" ? 100 : fit === "height" ? 0 : null),
      image: image || {
        image_url: article.image_url || "",
        image_filename: article.image_filename || "",
        image_commons_url: article.image_commons_url || "",
        image_license: article.image_license || "",
        image_artist: article.image_artist || "",
        image_source: article.image_source || "",
      },
      imageChanged: !!image,
    };
  }

  function originalOf(article, key) {
    if (key === "description") return article.description || "";
    if (key === "image_fit") return article.image_fit || "cover";
    if (key === "image_focus") return article.image_focus || null;
    if (key === "image_crop") return article.image_crop ?? null;
    return undefined; // "image": always a change
  }

  function setEdit(articleName, key, value, extra = {}) {
    const article = findArticle(articleName);
    const edit = state.edits.get(articleName) || {};
    if (key !== "image" && JSON.stringify(value) === JSON.stringify(originalOf(article, key))) delete edit[key];
    else edit[key] = value;
    Object.assign(edit, extra);
    if (!("image_crop" in edit)) delete edit.image_aspect;
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

  function previews(c) {
    const img = (large) => `<img src="${esc(c.image.image_url)}" alt="" style="${frameStyle(c.focus, large ? c.fit : "cover", large ? c.crop : null, c.aspect)}" />`;
    return `
      <div><div class="pv-label">primo piano</div><div class="frame hero">${img(true)}</div></div>
      <div><div class="pv-label">scheda mobile</div><div class="frame sheet">${img(true)}</div></div>
      <div class="pv-wide"><div class="pv-label">scheda desktop (larga)</div><div class="frame wide">${img(true)}</div></div>
      <div><div class="pv-label">miniatura</div><div class="frame thumb">${img(false)}</div></div>`;
  }

  function cropControls(c) {
    const v = c.sliderValue;
    return `
      <div class="crop">
        <button type="button" class="auto" aria-pressed="${v === null}" title="Riempie la cornice (comportamento predefinito)">auto</button>
        <span class="crop-end">altezza<br>intera</span>
        <input type="range" min="0" max="100" step="1" value="${v ?? 100}" class="${v === null ? "off" : ""}" aria-label="Ritaglio" />
        <span class="crop-end">larghezza<br>intera</span>
        <span class="crop-val">${v === null ? "auto" : v + "%"}</span>
        <button type="button" class="reset" title="Torna all'inquadratura predefinita">reimposta</button>
      </div>`;
  }

  function licenseLine(image) {
    if (!image.image_url) return "";
    const parts = [];
    if (image.image_license) parts.push(esc(image.image_license));
    if (image.image_artist) parts.push(esc(image.image_artist));
    const label = parts.join(" · ") || "licenza non indicata";
    const link = image.image_commons_url ? `<a href="${esc(image.image_commons_url)}" target="_blank" rel="noopener">Commons</a>` : "";
    return `<div class="lic">${label}${image.image_source === "manual" ? ' <span class="badge manual">scelta a mano</span>' : ""} ${link}</div>`;
  }

  function lookupBox(name) {
    const look = state.lookups[name];
    if (!look) return "";
    if (look.loading) return `<div class="look">Cerco su Commons…</div>`;
    if (look.error) return `<div class="look err">${esc(look.error)}</div>`;
    const info = look.info;
    const verdict = info.free
      ? `<span class="ok">Licenza libera: ${esc(info.image_license)}</span>`
      : `<span class="warn">Da controllare${info.image_license ? ": " + esc(info.image_license) : ""}</span>`;
    return `<div class="look">
        <img src="${esc(info.image_url)}" alt="" />
        <div>
          <div>${verdict}</div>
          ${info.image_artist ? `<div>Autore: ${esc(info.image_artist)}</div>` : ""}
          ${info.attribution_required ? `<div>Attribuzione obbligatoria (il sito mostra autore e licenza)</div>` : ""}
          ${info.warnings.map((w) => `<div class="warn">⚠ ${esc(w)}</div>`).join("")}
          <div>${fmt(info.width)}×${fmt(info.height)} px · <a href="${esc(info.image_commons_url)}" target="_blank" rel="noopener">pagina del file</a></div>
          <div class="look-actions">
            <button type="button" class="use">Usa questa immagine</button>
            <button type="button" class="cancel">Annulla</button>
          </div>
        </div>
      </div>`;
  }

  function cardInner(article) {
    const c = current(article);
    const hasImg = !!c.image.image_url;
    const focus = c.focus || DEFAULT_FOCUS;
    const src = article.description_source || "";
    const imageCol = hasImg ? `
        <div class="src" title="Clicca per scegliere il punto centrale">
          <img src="${esc(c.image.image_url)}" alt="" />
          <span class="dot" style="left:${focus.x}%;top:${focus.y}%"></span>
        </div>
        ${licenseLine(c.image)}
        ${cropControls(c)}
        <div class="previews">${previews(c)}</div>` : `<div class="noimg-box">Nessuna immagine</div>`;
    return `
        <div class="imgcol">
          ${imageCol}
          <form class="commons">
            <input type="text" placeholder="${hasImg ? "Sostituisci" : "Aggiungi"}: link o nome file su Commons" aria-label="Immagine da Commons" />
            <button type="submit">Cerca</button>
          </form>
          ${lookupBox(article.article)}
        </div>
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
          ${contextPanel(article)}
        </div>`;
  }

  function renderCard(article) {
    return `<section class="card${state.edits.has(article.article) ? " dirty" : ""}" data-article="${esc(article.article)}">${cardInner(article)}</section>`;
  }

  function rerenderCard(card) {
    const open = card.querySelector(".ctx")?.open;
    card.innerHTML = cardInner(findArticle(card.dataset.article));
    if (open) card.querySelector(".ctx").open = true;
  }

  function contextPanel(article) {
    const ctx = state.context[article.article];
    if (!ctx) return `<div class="ctx-none">Notizie usate: non salvate (descrizione precedente al salvataggio del contesto).</div>`;
    const news = ctx.news || [];
    const items = news.map((n) => `<li><span class="ctx-date">${esc((n.pubDate || "").slice(5, 16))}</span> ${esc(n.title)}${n.source ? ` <span class="ctx-src">${esc(n.source)}</span>` : ""}</li>`).join("");
    return `<details class="ctx"><summary>Notizie usate (${news.length}) · ${esc((ctx.fetched_at || "").slice(0, 10))} · ${esc(ctx.model || "")}</summary>
      ${items ? `<ol>${items}</ol>` : `<p>Nessuna notizia trovata.</p>`}
      ${ctx.wikipedia_summary ? `<p class="ctx-sum"><b>Riassunto Wikipedia:</b> ${esc(ctx.wikipedia_summary)}</p>` : ""}
    </details>`;
  }

  function render() {
    const list = $("#list");
    if (!state.data) { list.innerHTML = `<div class="empty">Caricamento…</div>`; return; }
    const onlyImg = $("#only-img").checked;
    const articles = state.data.articles.filter((a) => !onlyImg || current(a).image.image_url);
    list.innerHTML = articles.map(renderCard).join("") || `<div class="empty">Nessuna voce.</div>`;
  }

  // Updates only the framing parts of a card (keeps focus in the textarea).
  function refreshFraming(card) {
    const c = current(findArticle(card.dataset.article));
    const pv = card.querySelector(".previews");
    if (pv) pv.innerHTML = previews(c);
    const crop = card.querySelector(".crop");
    if (crop) crop.outerHTML = cropControls(c);
    placeDot(card);
  }

  function imageAspect(card) {
    const img = card.querySelector(".src img");
    return img && img.naturalWidth ? img.naturalWidth / img.naturalHeight : null;
  }

  function placeDot(card) {
    const img = card.querySelector(".src img");
    const dot = card.querySelector(".dot");
    if (!img || !dot || !img.naturalWidth) return;
    const focus = current(findArticle(card.dataset.article)).focus || DEFAULT_FOCUS;
    const box = img.getBoundingClientRect(), wrap = card.querySelector(".src").getBoundingClientRect();
    const ratio = img.naturalWidth / img.naturalHeight;
    let w = box.width, h = box.width / ratio;
    if (h > box.height) { h = box.height; w = h * ratio; }
    const offX = box.left - wrap.left + (box.width - w) / 2, offY = box.top - wrap.top + (box.height - h) / 2;
    dot.style.left = `${offX + (focus.x / 100) * w}px`;
    dot.style.top = `${offY + (focus.y / 100) * h}px`;
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
      const ratio = img.naturalWidth / img.naturalHeight;
      let w = r.width, h = r.width / ratio;
      if (h > r.height) { h = r.height; w = h * ratio; }
      const left = r.left + (r.width - w) / 2, top = r.top + (r.height - h) / 2;
      const x = Math.round(Math.max(0, Math.min(100, ((event.clientX - left) / w) * 100)));
      const y = Math.round(Math.max(0, Math.min(100, ((event.clientY - top) / h) * 100)));
      setEdit(name, "image_focus", { x, y });
      refreshFraming(card);
      return;
    }
    if (event.target.closest(".crop .auto")) {
      setEdit(name, "image_crop", null);
      setEdit(name, "image_fit", "cover");
      refreshFraming(card);
      return;
    }
    if (event.target.closest(".crop .reset")) {
      setEdit(name, "image_focus", null);
      setEdit(name, "image_crop", null);
      setEdit(name, "image_fit", "cover");
      refreshFraming(card);
      return;
    }
    if (event.target.closest(".look .use")) {
      const info = state.lookups[name].info;
      const image = {};
      for (const key of ["image_filename", "image_url", "image_commons_url", "image_license", "image_license_url", "image_copyrighted", "image_artist", "image_source"]) image[key] = info[key];
      const edit = state.edits.get(name) || {};
      for (const key of ["image_focus", "image_fit", "image_crop", "image_aspect"]) delete edit[key];
      state.edits.set(name, edit);
      setEdit(name, "image", image);
      delete state.lookups[name];
      rerenderCard(card);
      return;
    }
    if (event.target.closest(".look .cancel")) {
      delete state.lookups[name];
      rerenderCard(card);
    }
  });

  $("#list").addEventListener("input", (event) => {
    const card = event.target.closest(".card");
    if (!card) return;
    if (event.target.tagName === "TEXTAREA") {
      setEdit(card.dataset.article, "description", event.target.value.replace(/\s+/g, " ").trim());
      card.querySelector(".count").textContent = `${event.target.value.length} caratteri`;
      return;
    }
    if (event.target.matches(".crop input[type=range]")) {
      const value = Number(event.target.value);
      setEdit(card.dataset.article, "image_crop", value, { image_aspect: imageAspect(card) });
      const c = current(findArticle(card.dataset.article));
      card.querySelector(".previews").innerHTML = previews(c);
      card.querySelector(".crop-val").textContent = value + "%";
      card.querySelector(".crop .auto").setAttribute("aria-pressed", "false");
      event.target.classList.remove("off");
    }
  });

  $("#list").addEventListener("submit", async (event) => {
    if (!event.target.matches(".commons")) return;
    event.preventDefault();
    const card = event.target.closest(".card");
    const name = card.dataset.article;
    const value = event.target.querySelector("input").value.trim();
    if (!value) return;
    state.lookups[name] = { loading: true };
    rerenderCard(card);
    try {
      const res = await fetch(`/api/commons?file=${encodeURIComponent(value)}`);
      const out = await res.json();
      state.lookups[name] = res.ok ? { info: out } : { error: out.error || "Errore" };
    } catch (err) {
      state.lookups[name] = { error: String(err) };
    }
    rerenderCard(card);
  });

  // position the dot correctly once images know their size (object-fit: contain)
  $("#list").addEventListener("load", (event) => {
    if (event.target.matches(".src img")) placeDot(event.target.closest(".card"));
  }, true);

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
    state.lookups = {};
    state.data = null;
    updateDirty();
    setStatus("");
    fillSelectors();
    render();
    location.hash = weekId;
    const [res, ctxRes] = await Promise.all([fetch(`/api/week/${weekId}`), fetch(`/api/context/${weekId}`)]);
    const out = await res.json();
    state.context = ctxRes.ok ? (await ctxRes.json()).articles || {} : {};
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
