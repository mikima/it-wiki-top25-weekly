#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

WEEK_FILE_PATTERN = re.compile(r"^(\d{4})-(\d{2})\.json$")
THUMB_SIZE_PX = 80
BASE_CHART_MAX_VIEWS = 500_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dynamic HTML pages in docs/ from weekly JSON files."
    )
    parser.add_argument(
        "--json-dir",
        default="docs/json",
        help="Directory containing weekly JSON files (YYYY-WW.json)",
    )
    parser.add_argument("--docs-dir", default="docs", help="Directory for HTML output files")
    parser.add_argument(
        "--json-url-base",
        default="json",
        help="Base URL path used by week.html to fetch week JSON files",
    )
    parser.add_argument(
        "--previous-years",
        type=int,
        default=5,
        help="How many previous-year links to show in header navigation",
    )
    return parser.parse_args()


def discover_week_files(json_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in sorted(json_dir.glob("*.json")):
        if WEEK_FILE_PATTERN.match(path.name):
            files.append(path)
    return files


def write_weeks_file(week_ids: List[str], docs_dir: Path) -> None:
    weeks_path = docs_dir / "weeks.json"
    weeks_path.write_text(json.dumps(week_ids, indent=2) + "\n", encoding="utf-8")


def write_index_html(docs_dir: Path) -> None:
    content = """<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>it-wiki top weekly</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; }
  </style>
</head>
<body>
  <h1>it-wiki top weekly</h1>
  <p id="status">Caricamento ultima settimana...</p>
  <script>
    fetch("weeks.json")
      .then((response) => response.json())
      .then((weeks) => {
        if (Array.isArray(weeks) && weeks.length > 0) {
          const latest = weeks[weeks.length - 1];
          window.location.href = `week.html?week=${latest}`;
          return;
        }
        document.getElementById("status").textContent = "Nessuna settimana disponibile.";
      })
      .catch(() => {
        document.getElementById("status").textContent = "Errore nel caricamento di weeks.json";
      });
  </script>
</body>
</html>
"""
    (docs_dir / "index.html").write_text(content, encoding="utf-8")


def write_week_html(
    docs_dir: Path,
    previous_years: int,
    json_url_base: str,
    thumb_size_px: int,
) -> None:
    content = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Top pagine it.wiki</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      margin: 16px;
      line-height: 1.4;
    }}
    .week-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      padding: 12px;
      border: 1px solid #ddd;
      background: #fafafa;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .week-nav .current {{ font-weight: 700; }}
    .previous-years {{ width: 100%; font-size: 0.9rem; }}
    .previous-years a {{ margin-right: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; text-align: left; }}
    th {{ background: #f0f0f0; position: sticky; top: 64px; z-index: 5; }}
    .trend-cell svg {{ display: block; width: 120px; height: {thumb_size_px}px; }}
    .thumb-wrap {{ display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }}
    .thumb {{
      width: {thumb_size_px}px;
      height: {thumb_size_px}px;
      object-fit: cover;
      object-position: center;
      display: block;
      border-radius: 4px;
    }}
    .thumb-empty {{
      width: {thumb_size_px}px;
      height: {thumb_size_px}px;
      border: 1px dashed #bbb;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.7rem;
      color: #777;
    }}
    .copyright {{ font-size: 10px; color: #555; max-width: 220px; }}
    .error {{ color: #b3261e; font-weight: 600; margin: 12px 0; }}
    a {{ color: #1a5fb4; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 900px) {{
      th, td {{ font-size: 0.9rem; padding: 6px; }}
      .trend-cell svg {{ width: 100px; height: {thumb_size_px}px; }}
    }}
  </style>
</head>
<body>
  <header class="week-nav" id="nav-top"></header>
  <div id="error" class="error"></div>
  <table>
    <thead>
      <tr>
        <th>Rank</th>
        <th>Name</th>
        <th>Views</th>
        <th>Trend</th>
        <th>Image</th>
        <th>Google News</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
  <header class="week-nav" id="nav-bottom"></header>
  <script>
    const PREVIOUS_YEARS = {previous_years};
    const JSON_URL_BASE = {json.dumps(json_url_base)};
    const EXTERNAL_LINK_ATTRS = ' target="_blank" rel="noopener noreferrer"';
    const BASE_CHART_MAX_VIEWS = {BASE_CHART_MAX_VIEWS};
    const THUMB_SIZE = {thumb_size_px};
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

    function getWeekFromQuery() {{
      const params = new URLSearchParams(window.location.search);
      return params.get("week");
    }}

    function escapeHtml(value) {{
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }}

    function formatViews(value) {{
      const num = Number(value || 0);
      return num.toLocaleString("it-IT");
    }}

    function normalizeWeekId(year, week) {{
      return `${{year}}-${{String(week).padStart(2, "0")}}`;
    }}

    function parseIsoDate(value) {{
      if (typeof value !== "string") return null;
      const match = value.match(/^(\\d{{4}})-(\\d{{2}})-(\\d{{2}})$/);
      if (!match) return null;
      const year = Number(match[1]);
      const month = Number(match[2]);
      const day = Number(match[3]);
      if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;
      if (month < 1 || month > 12 || day < 1 || day > 31) return null;
      return new Date(Date.UTC(year, month - 1, day));
    }}

    function getIsoWeekMonday(year, week, deltaWeeks = 0) {{
      const jan4 = new Date(Date.UTC(year, 0, 4));
      const day = jan4.getUTCDay() || 7;
      const monday = new Date(jan4);
      monday.setUTCDate(jan4.getUTCDate() - day + 1 + ((week - 1 + deltaWeeks) * 7));
      return monday;
    }}

    function getWeekRange(year, week) {{
      const start = getIsoWeekMonday(year, week);
      const end = new Date(start);
      end.setUTCDate(start.getUTCDate() + 6);
      return {{ start, end }};
    }}

    function formatWeekTitle(startDate, endDate) {{
      const startDay = startDate.getUTCDate();
      const endDay = endDate.getUTCDate();
      const startMonthIndex = startDate.getUTCMonth();
      const endMonthIndex = endDate.getUTCMonth();
      const startMonth = IT_MONTHS[startMonthIndex];
      const endMonth = IT_MONTHS[endMonthIndex];
      const startYear = startDate.getUTCFullYear();
      const endYear = endDate.getUTCFullYear();

      if (startYear === endYear && startMonthIndex === endMonthIndex) {{
        return `Settimana dal ${{startDay}} al ${{endDay}} ${{endMonth}} ${{startYear}}`;
      }}
      if (startYear === endYear) {{
        return `Settimana dal ${{startDay}} ${{startMonth}} al ${{endDay}} ${{endMonth}} ${{startYear}}`;
      }}
      return `Settimana dal ${{startDay}} ${{startMonth}} ${{startYear}} al ${{endDay}} ${{endMonth}} ${{endYear}}`;
    }}

    function resolveWeekTitle(weekId, data = null) {{
      const [yearRaw, weekRaw] = weekId.split("-");
      const year = Number(yearRaw);
      const week = Number(weekRaw);
      let startDate = parseIsoDate(data?.start_date);
      let endDate = parseIsoDate(data?.end_date);

      if (!startDate || !endDate) {{
        if (!Number.isFinite(year) || !Number.isFinite(week)) return weekId;
        const range = getWeekRange(year, week);
        startDate = range.start;
        endDate = range.end;
      }}

      return formatWeekTitle(startDate, endDate);
    }}

    function shiftIsoWeek(year, week, deltaWeeks) {{
      const monday = getIsoWeekMonday(year, week, deltaWeeks);
      const shiftedYear = monday.getUTCFullYear();
      const jan4Shifted = new Date(Date.UTC(shiftedYear, 0, 4));
      const dayShifted = jan4Shifted.getUTCDay() || 7;
      const firstMonday = new Date(jan4Shifted);
      firstMonday.setUTCDate(jan4Shifted.getUTCDate() - dayShifted + 1);
      const diffDays = Math.round((monday - firstMonday) / 86400000);
      const shiftedWeek = Math.floor(diffDays / 7) + 1;
      return {{ year: shiftedYear, week: shiftedWeek }};
    }}

    function getWeekChartMax(rows) {{
      if (!Array.isArray(rows) || rows.length === 0) return BASE_CHART_MAX_VIEWS;
      let weekMax = 0;
      rows.forEach((item) => {{
        const points = Array.isArray(item.daily_views) ? item.daily_views : [];
        points.forEach((point) => {{
          const value = Number(point.views || 0);
          if (Number.isFinite(value) && value > weekMax) {{
            weekMax = value;
          }}
        }});
      }});
      return Math.max(BASE_CHART_MAX_VIEWS, weekMax);
    }}

    function buildBarChart(dailyViews, maxScale) {{
      if (!Array.isArray(dailyViews) || dailyViews.length === 0) return "";
      const width = 120;
      const height = THUMB_SIZE;
      const pad = 0;
      const values = dailyViews.map((d) => Number(d.views || 0));
      const innerWidth = Math.max(width - (pad * 2), 1);
      const innerHeight = Math.max(height - (pad * 2), 1);
      const step = innerWidth / values.length;
      const barWidth = Math.max(step * 0.8, 1);
      const scaleMax = Math.max(Number(maxScale) || 0, 1);

      const bars = dailyViews.map((item, index) => {{
        const value = Number(item.views || 0);
        const normalized = Math.max(value, 0) / scaleMax;
        const scaled = Math.min(normalized, 1);
        const barHeight = value <= 0 ? 0 : Math.max(Math.floor(scaled * innerHeight), 1);
        const x = pad + (index * step) + ((step - barWidth) / 2);
        const y = pad + (innerHeight - barHeight);
        const tip = escapeHtml(`${{item.date}}: ${{value}}`);
        return `<rect x="${{x.toFixed(2)}}" y="${{y.toFixed(2)}}" width="${{barWidth.toFixed(2)}}" height="${{barHeight.toFixed(2)}}" fill="#3a3a3a"><title>${{tip}}</title></rect>`;
      }}).join("");

      return `<svg xmlns="http://www.w3.org/2000/svg" width="${{width}}" height="${{height}}" viewBox="0 0 ${{width}} ${{height}}">${{bars}}</svg>`;
    }}

    function renderNav(weekId, data = null) {{
      const [yearRaw, weekRaw] = weekId.split("-");
      const year = Number(yearRaw);
      const week = Number(weekRaw);
      const prev = shiftIsoWeek(year, week, -1);
      const next = shiftIsoWeek(year, week, 1);
      const prevId = normalizeWeekId(prev.year, prev.week);
      const nextId = normalizeWeekId(next.year, next.week);
      const weekTitle = resolveWeekTitle(weekId, data);
      const prevYears = [];
      for (let i = 1; i <= PREVIOUS_YEARS; i += 1) {{
        const y = year - i;
        prevYears.push(`<a href="week.html?week=${{normalizeWeekId(y, week)}}">${{normalizeWeekId(y, week)}}</a>`);
      }}

      const html = `
        <a href="week.html?week=${{prevId}}">&larr; Settimana precedente</a>
        <span class="current">${{weekTitle}}</span>
        <a href="week.html?week=${{nextId}}">Settimana successiva &rarr;</a>
        <div class="previous-years">
          <strong>Stessa settimana negli anni precedenti:</strong> ${{prevYears.join(" ")}}
        </div>
      `;
      document.getElementById("nav-top").innerHTML = html;
      document.getElementById("nav-bottom").innerHTML = html;
      document.title = weekTitle;
    }}

    function renderRows(data) {{
      const rows = Array.isArray(data.articles) ? data.articles : [];
      const weekChartMax = getWeekChartMax(rows);
      const html = rows.map((item) => {{
        const title = String(item.article || "").replaceAll("_", " ");
        const titleEsc = escapeHtml(title);
        const titleCell = item.article_url
          ? `<a href="${{escapeHtml(item.article_url)}}"${{EXTERNAL_LINK_ATTRS}}>${{titleEsc}}</a>`
          : titleEsc;
        const trendSvg = buildBarChart(item.daily_views || [], weekChartMax);
        const trendCell = item.pageviews_url && trendSvg
          ? `<a href="${{escapeHtml(item.pageviews_url)}}" class="trend-link"${{EXTERNAL_LINK_ATTRS}}>${{trendSvg}}</a>`
          : trendSvg;
        const commonsUrl = String(item.image_commons_url || "");
        const licenseText = escapeHtml(item.image_license || "");
        const imageHtml = commonsUrl
          ? `<a href="${{escapeHtml(commonsUrl)}}"${{EXTERNAL_LINK_ATTRS}}><img src="${{escapeHtml(item.image_url)}}" alt="${{titleEsc}}" class="thumb" loading="lazy" /></a>`
          : `<img src="${{escapeHtml(item.image_url)}}" alt="${{titleEsc}}" class="thumb" loading="lazy" />`;
        const copyrightHtml = commonsUrl
          ? `<a href="${{escapeHtml(commonsUrl)}}" class="copyright"${{EXTERNAL_LINK_ATTRS}}>${{licenseText}}</a>`
          : `<div class="copyright">${{licenseText}}</div>`;
        const imageCell = item.image_url
          ? `<div class="thumb-wrap">${{imageHtml}}${{copyrightHtml}}</div>`
          : `<div class="thumb-wrap"><div class="thumb-empty">No image</div>${{copyrightHtml}}</div>`;
        const newsCell = item.google_news_url
          ? `<a href="${{escapeHtml(item.google_news_url)}}"${{EXTERNAL_LINK_ATTRS}}>Google News</a>`
          : "";
        return `<tr>
          <td>${{escapeHtml(item.rank ?? "")}}</td>
          <td>${{titleCell}}</td>
          <td>${{formatViews(item.views)}}</td>
          <td class="trend-cell">${{trendCell}}</td>
          <td>${{imageCell}}</td>
          <td>${{newsCell}}</td>
          <td>${{escapeHtml(item.description || "")}}</td>
        </tr>`;
      }}).join("");
      document.getElementById("rows").innerHTML = html;
    }}

    async function loadWeek(weekId) {{
      const errorNode = document.getElementById("error");
      errorNode.textContent = "";
      try {{
        const response = await fetch(`${{JSON_URL_BASE}}/${{weekId}}.json`);
        if (!response.ok) throw new Error("JSON not found");
        const data = await response.json();
        renderNav(weekId, data);
        renderRows(data);
      }} catch (error) {{
        renderNav(weekId);
        document.getElementById("rows").innerHTML = "";
        errorNode.textContent = `Impossibile caricare ${{JSON_URL_BASE}}/${{weekId}}.json`;
      }}
    }}

    async function init() {{
      let weekId = getWeekFromQuery();
      if (!weekId) {{
        const response = await fetch("weeks.json");
        const weeks = await response.json();
        if (Array.isArray(weeks) && weeks.length > 0) {{
          weekId = weeks[weeks.length - 1];
          window.history.replaceState(null, "", `?week=${{weekId}}`);
        }}
      }}
      if (!weekId) {{
        document.getElementById("error").textContent = "Nessuna settimana disponibile.";
        return;
      }}
      await loadWeek(weekId);
    }}

    init();
  </script>
</body>
</html>
"""
    (docs_dir / "week.html").write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    json_dir = Path(args.json_dir)
    docs_dir = Path(args.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    if not json_dir.exists():
        raise SystemExit(f"JSON directory not found: {json_dir}")

    week_files = discover_week_files(json_dir)
    week_ids = [path.stem for path in week_files]
    write_weeks_file(week_ids, docs_dir)
    write_index_html(docs_dir)
    write_week_html(
        docs_dir,
        args.previous_years,
        args.json_url_base,
        THUMB_SIZE_PX,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
