#!/usr/bin/env python3
"""Import the hand-written weekly descriptions from it.wikipedia user pages.

Source pages: https://it.wikipedia.org/wiki/Utente:Mikima/Top25/YYYY-W

Steps:
1. download the raw wikitext of every weekly subpage (cached in
   archive/wiki_manual/raw/, use --refresh to download again)
2. parse each table row (rank, article, views, image, description)
3. reconcile each page with the right ISO week, comparing article titles
   and view counts with docs/rawjson (page names were written by hand and
   may be off by one; header dates are used as a further hint)
4. write an archive spreadsheet (archive/wiki_manual/descrizioni_manuali.xlsx)
5. unless --dry-run, copy manual descriptions (plain text, no links) into
   docs/json/YYYY-WW.json, marking them with "description_source": "manual".
   Automatic snippets ("(descrizione automatica)") are archived but never
   imported.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "archive" / "wiki_manual" / "raw"
XLSX_PATH = ROOT / "archive" / "wiki_manual" / "descrizioni_manuali.xlsx"
JSON_DIR = ROOT / "docs" / "json"
RAWJSON_DIR = ROOT / "docs" / "rawjson"
API = "https://it.wikipedia.org/w/api.php"
INDEX = "https://it.wikipedia.org/w/index.php"
PREFIX = "Mikima/Top25/"
USER_AGENT = "it-wiki-top25-weekly archiver (User:Mikima)"

MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
    "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10,
    "novembre": 11, "dicembre": 12,
}
AUTO_MARK = "descrizione automatica"


# --------------------------------------------------------------------------
# download
# --------------------------------------------------------------------------

def download_pages(refresh: bool) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    params = dict(action="query", list="allpages", apprefix=PREFIX,
                  apnamespace=2, aplimit="max", format="json")
    data = session.get(API, params=params, timeout=30).json()
    names = [p["title"].split(PREFIX, 1)[1] for p in data["query"]["allpages"]]
    names = [n for n in names if re.fullmatch(r"\d{4}-\d{1,2}", n)]
    for name in names:
        path = RAW_DIR / f"{name}.wiki"
        if path.exists() and not refresh:
            continue
        resp = session.get(INDEX, params=dict(title=f"Utente:{PREFIX}{name}", action="raw"), timeout=30)
        resp.raise_for_status()
        path.write_text(resp.text, encoding="utf-8")
        time.sleep(0.3)
    print(f"Pagine settimanali sul wiki: {len(names)}")


# --------------------------------------------------------------------------
# wikitext helpers
# --------------------------------------------------------------------------

def norm_title(title: str) -> str:
    title = title.strip().replace(" ", "_")
    title = re.sub(r"_+", "_", title)
    return title[:1].upper() + title[1:]


def wiki_to_plain(text: str) -> str:
    t = text
    # <nowiki>''</nowiki> was used as an apostrophe ("l<nowiki>''</nowiki>8 dicembre")
    t = re.sub(r"<nowiki>(.*?)</nowiki>", lambda m: m.group(1).replace("''", "'"), t, flags=re.S)
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:File|Immagine|Image):[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\]", "", t)
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("'''", "").replace("''", "")
    t = t.replace("&nbsp;", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.;:)])", r"\1", t)
    t = re.sub(r"\(\s+", "(", t)
    return t


def parse_header_dates(wikitext: str, page_year: int) -> Tuple[Optional[dt.date], Optional[dt.date], str]:
    line = next((l for l in wikitext.splitlines() if l.strip().lower().startswith("settimana")), "")
    clean = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", line)
    clean = clean.replace("º", "").replace("°", "")
    m = re.search(
        r"dal(?:l')?\s*(\d{1,2})\s*([a-z]+)?\s*(\d{4})?\s*al(?:l')?\s*(\d{1,2})\s*([a-z]+)\s*(\d{4})?",
        clean.lower(),
    )
    if not m:
        return None, None, line.strip()
    d1, m1, y1, d2, m2, y2 = m.groups()
    try:
        month2 = MONTHS[m2]
        month1 = MONTHS[m1] if m1 in MONTHS else month2
        year2 = int(y2) if y2 else (int(y1) if y1 else page_year)
        year1 = int(y1) if y1 else (year2 - 1 if month1 > month2 else year2)
        return dt.date(year1, month1, int(d1)), dt.date(year2, month2, int(d2)), line.strip()
    except (KeyError, ValueError):
        return None, None, line.strip()


def parse_views(cell: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", wiki_to_plain(cell))
    return int(digits) if digits else None


def parse_image(cell: str) -> str:
    m = re.search(r"Image\s*=\s*([^|}]+)", cell) or re.search(r"\[\[(?:File|Immagine):([^|\]]+)", cell, re.I)
    return m.group(1).strip() if m else ""


def split_cells(block: str) -> List[str]:
    cells: List[str] = []
    for line in block.split("\n"):
        if line.startswith(("|", "!")):
            body = line[1:]
            # inline cells separated by || or !!
            parts = re.split(r"\|\||!!", body)
            cells.extend(parts)
        elif cells:
            cells[-1] += "\n" + line
    return [c.strip() for c in cells]


def parse_table(wikitext: str) -> List[Dict[str, Any]]:
    start = wikitext.find("{|")
    end = wikitext.find("\n|}", start)
    if start < 0:
        return []
    table = wikitext[start: end if end > 0 else None]
    blocks = re.split(r"\n\|-[^\n]*", table)
    header_block = blocks[0].split("\n", 1)[1] if "\n" in blocks[0] else ""
    headers = [h.strip().lower() for h in split_cells(header_block)]
    rows = []
    for block in blocks[1:]:
        cells = split_cells(block.strip("\n"))
        if not cells:
            continue
        row = dict(zip(headers, cells))
        art = row.get("articolo", "")
        m = re.search(r"\[\[([^\]|#]+)", art)
        if not m:
            continue
        desc = row.get("descrizione", "")
        rank_m = re.search(r"\d+", row.get("posizione", ""))
        rows.append({
            "rank": int(rank_m.group()) if rank_m else None,
            "article": m.group(1).strip(),
            "views": parse_views(row.get("visite", "")),
            "image": parse_image(row.get("immagine", "")),
            "description_wiki": desc,
            "description_plain": wiki_to_plain(re.sub(r"\(\s*" + AUTO_MARK + r"\s*\)", "", desc, flags=re.I)),
            "automatic": AUTO_MARK in desc.lower(),
        })
    return rows


# --------------------------------------------------------------------------
# week reconciliation
# --------------------------------------------------------------------------

_rank_cache: Dict[str, Dict[str, int]] = {}


def week_ranking(week_id: str) -> Dict[str, int]:
    if week_id not in _rank_cache:
        path = RAWJSON_DIR / f"{week_id}.json"
        if not path.exists():
            path = JSON_DIR / f"{week_id}.json"
        ranking: Dict[str, int] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for a in data.get("articles", [])[:300]:
                ranking[norm_title(a["article"])] = int(a.get("views") or 0)
        _rank_cache[week_id] = ranking
    return _rank_cache[week_id]


def week_id_of(day: dt.date) -> str:
    y, w, _ = day.isocalendar()
    return f"{y}-{w:02d}"


def shift_week(week_id: str, delta: int) -> str:
    y, w = map(int, week_id.split("-"))
    monday = dt.date.fromisocalendar(y, w, 1) + dt.timedelta(weeks=delta)
    return week_id_of(monday)


def score_week(rows: List[Dict[str, Any]], week_id: str) -> Tuple[float, int, int]:
    """Return (score, title matches, view matches within 2%)."""
    ranking = week_ranking(week_id)
    if not ranking:
        return 0.0, 0, 0
    titles = views_ok = 0
    for r in rows:
        v = ranking.get(norm_title(r["article"]))
        if v is None:
            continue
        titles += 1
        if r["views"] and v and abs(v - r["views"]) / max(v, r["views"]) <= 0.02:
            views_ok += 1
    return titles + 2 * views_ok, titles, views_ok


def reconcile(page: str, rows: List[Dict[str, Any]], header_start: Optional[dt.date]) -> Dict[str, Any]:
    y, w = map(int, page.split("-"))
    name_week = week_id_of(dt.date.fromisocalendar(y, w, 1))
    header_week = week_id_of(header_start) if header_start else None
    candidates = {shift_week(name_week, d) for d in (-2, -1, 0, 1, 2)}
    if header_week:
        candidates |= {shift_week(header_week, d) for d in (-1, 0, 1)}
    scored = sorted(((score_week(rows, c), c) for c in candidates), key=lambda x: (-x[0][0], x[1] != name_week))
    (best_score, titles, views_ok), best = scored[0]
    second = scored[1][0][0] if len(scored) > 1 else 0
    if best_score == 0:
        best, confidence = header_week or name_week, "nessun dato"
    elif views_ok >= max(3, len(rows) // 2) and best_score > second:
        confidence = "alta"
    elif best_score > second:
        confidence = "media"
    else:
        confidence = "bassa"
    return {
        "name_week": name_week,
        "header_week": header_week,
        "week": best,
        "title_matches": titles,
        "view_matches": views_ok,
        "confidence": confidence,
    }


def _tokens(title: str) -> set:
    return {t for t in re.split(r"[\W_]+", title.lower()) if len(t) >= 4}


def match_renamed(row: Dict[str, Any], articles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find an article renamed since the wiki page was written: views within 1%
    and at least one shared word in the title."""
    views = row.get("views")
    if not views:
        return None
    words = _tokens(row["article"])
    best = None
    for a in articles:
        v = int(a.get("views") or 0)
        if not v or abs(v - views) / max(v, views) > 0.01 or not (words & _tokens(a["article"])):
            continue
        if best is None or abs(v - views) < abs(int(best["views"]) - views):
            best = a
    return best


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def page_sort_key(name: str) -> Tuple[int, int]:
    y, w = name.split("-")
    return int(y), int(w)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="Download the wiki pages again.")
    ap.add_argument("--no-download", action="store_true", help="Use only cached raw pages.")
    ap.add_argument("--dry-run", action="store_true", help="Write the spreadsheet but do not touch docs/json.")
    args = ap.parse_args()

    if not args.no_download:
        download_pages(args.refresh)

    pages = sorted((p.stem for p in RAW_DIR.glob("*.wiki")), key=page_sort_key)
    all_rows: List[Dict[str, Any]] = []
    weeks: List[Dict[str, Any]] = []
    for page in pages:
        text = (RAW_DIR / f"{page}.wiki").read_text(encoding="utf-8")
        start, end, header = parse_header_dates(text, int(page.split("-")[0]))
        rows = parse_table(text)
        rec = reconcile(page, rows, start)
        weeks.append({"page": page, "header": header, "start": start, "end": end, "rows": len(rows),
                      "manual": sum(1 for r in rows if not r["automatic"] and r["description_plain"]), **rec})
        for r in rows:
            r.update(page=page, week=rec["week"])
            all_rows.append(r)

    # pages that resolved to the same week: keep the one with more view matches
    by_week: Dict[str, List[Dict[str, Any]]] = {}
    for w in weeks:
        by_week.setdefault(w["week"], []).append(w)
    for wk, lst in by_week.items():
        if len(lst) > 1:
            lst.sort(key=lambda x: (-x["view_matches"], -x["title_matches"]))
            for loser in lst[1:]:
                loser["confidence"] = f"duplicato di {lst[0]['page']}"

    skipped_pages = {w["page"] for w in weeks if w["confidence"].startswith(("duplicato", "nessun"))}

    # apply to JSON
    stats = {"imported": 0, "auto_skipped": 0, "empty": 0, "not_in_json": 0, "page_skipped": 0}
    json_cache: Dict[str, Tuple[Path, Dict[str, Any]]] = {}
    for r in all_rows:
        r["json_status"] = ""
        if r["automatic"]:
            r["json_status"] = "automatica, non importata"
            stats["auto_skipped"] += 1
            continue
        if not r["description_plain"]:
            r["json_status"] = "vuota"
            stats["empty"] += 1
            continue
        if r["page"] in skipped_pages:
            r["json_status"] = "pagina non abbinata"
            stats["page_skipped"] += 1
            continue
        if r["week"] not in json_cache:
            path = JSON_DIR / f"{r['week']}.json"
            json_cache[r["week"]] = (path, json.loads(path.read_text(encoding="utf-8")) if path.exists() else {})
        path, data = json_cache[r["week"]]
        target = next((a for a in data.get("articles", []) if norm_title(a["article"]) == norm_title(r["article"])), None)
        if target is None:
            target = match_renamed(r, data.get("articles", []))
            if target is not None:
                r["json_article"] = target["article"]
        if target is None:
            r["json_status"] = "articolo non presente nel JSON"
            stats["not_in_json"] += 1
            continue
        target["description"] = r["description_plain"]
        target["description_source"] = "manual"
        r["json_status"] = "importata" if not r.get("json_article") else f"importata come {r['json_article']}"
        stats["imported"] += 1

    if not args.dry_run:
        for path, data in json_cache.values():
            if data:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write_xlsx(weeks, all_rows)

    print(f"Pagine: {len(pages)}  righe: {len(all_rows)}")
    print("Esito:", stats)
    print(f"Archivio: {XLSX_PATH.relative_to(ROOT)}")
    print("\nPagine con settimana diversa dal nome o da verificare:")
    for w in weeks:
        if w["week"] != w["name_week"] or w["confidence"] not in ("alta",):
            print(f"  {w['page']:>8} -> {w['week']}  (intestazione: {w['header_week']}, "
                  f"titoli {w['title_matches']}/{w['rows']}, visite {w['view_matches']}, {w['confidence']})")
    if args.dry_run:
        print("\n--dry-run: docs/json non modificati.")


def write_xlsx(weeks: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = "descrizioni"
    cols = [
        ("pagina_wiki", 12), ("settimana_iso", 12), ("posizione", 9), ("articolo", 40), ("visite", 11),
        ("immagine", 30), ("descrizione_wikitext", 80), ("descrizione_testo", 80), ("automatica", 10),
        ("stato_json", 28), ("url_pagina", 50),
    ]
    ws.append([c for c, _ in cols])
    for r in rows:
        ws.append([
            r["page"], r["week"], r["rank"], r["article"], r["views"], r["image"],
            r["description_wiki"], r["description_plain"], "sì" if r["automatic"] else "no",
            r["json_status"], f"https://it.wikipedia.org/wiki/Utente:{PREFIX}{r['page']}",
        ])
    style_sheet(ws, cols, wrap_cols={7, 8})

    ws2 = wb.create_sheet("settimane")
    cols2 = [
        ("pagina_wiki", 12), ("intestazione", 50), ("data_inizio", 12), ("data_fine", 12),
        ("settimana_da_nome", 14), ("settimana_da_date", 14), ("settimana_scelta", 14),
        ("righe", 7), ("descrizioni_manuali", 12), ("titoli_trovati", 10), ("visite_coincidenti", 10),
        ("affidabilità", 22),
    ]
    ws2.append([c for c, _ in cols2])
    for w in weeks:
        ws2.append([w["page"], w["header"], w["start"], w["end"], w["name_week"], w["header_week"],
                    w["week"], w["rows"], w["manual"], w["title_matches"], w["view_matches"], w["confidence"]])
    style_sheet(ws2, cols2, wrap_cols=set())

    XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX_PATH)


def style_sheet(ws, cols, wrap_cols) -> None:
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    for i, (_, width) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
        ws.cell(row=1, column=i).font = Font(bold=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column in wrap_cols)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


if __name__ == "__main__":
    main()
