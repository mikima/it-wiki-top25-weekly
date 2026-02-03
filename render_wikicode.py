#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from render_utils import escape_wikicode, format_views, load_json

MONTHS_IT = [
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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render wikicode from a weekly JSON export."
    )
    parser.add_argument("input", help="Path to JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path, use '-' for stdout",
    )
    return parser.parse_args()


def week_navigation(year: int, week: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    start = date.fromisocalendar(year, week, 1)
    prev_week = start - timedelta(days=7)
    next_week = start + timedelta(days=7)
    prev_year, prev_week_num, _ = prev_week.isocalendar()
    next_year, next_week_num, _ = next_week.isocalendar()
    return (prev_year, prev_week_num), (next_year, next_week_num)


def format_week_range(start_date: date, end_date: date) -> str:
    if start_date.year != end_date.year:
        return (
            "Settimana dal "
            f"{start_date.day} {MONTHS_IT[start_date.month - 1]} {start_date.year} "
            f"al {end_date.day} {MONTHS_IT[end_date.month - 1]} {end_date.year}"
        )
    if start_date.month == end_date.month:
        return (
            "Settimana dal "
            f"{start_date.day} al {end_date.day} "
            f"{MONTHS_IT[end_date.month - 1]} {end_date.year}"
        )
    return (
        "Settimana dal "
        f"{start_date.day} {MONTHS_IT[start_date.month - 1]} "
        f"al {end_date.day} {MONTHS_IT[end_date.month - 1]} {end_date.year}"
    )


def build_table_rows(articles: List[Dict[str, object]]) -> List[str]:
    rows = []
    for item in articles:
        title = str(item.get("article", ""))
        title_display = title.replace("_", " ")
        article_url = str(item.get("article_url", ""))
        if article_url:
            article_cell = f"[{article_url} {escape_wikicode(title_display)}]"
        else:
            article_cell = f"[[{escape_wikicode(title_display)}]]"
        rows.extend(
            [
                "|-",
                f"!{item.get('rank', '')}",
                f"|{article_cell}",
                f"|{escape_wikicode(title_display)}",
                f"|{format_views(item.get('views', 0))}",
                f"|{escape_wikicode(item.get('description', ''))}",
            ]
        )
    return rows


def render_wikicode(data: Dict[str, object]) -> str:
    year = int(data.get("year", 0))
    week = int(data.get("week", 0))
    start_date = date.fromisoformat(str(data.get("start_date")))
    end_date = date.fromisoformat(str(data.get("end_date")))
    (prev_year, prev_week), (next_year, next_week) = week_navigation(year, week)

    lines = [
        f"{{{{Utente:Mikima/Top25/Template:Anni|settimana={week}}}}}",
        "",
        (
            f"&larr; [[Utente:Mikima/Top25/{prev_year}-{prev_week}"
            "|Settimana precedente]] "
            f"&ndash; [[Utente:Mikima/Top25/{next_year}-{next_week}"
            "|Settimana successiva]] &rarr;"
        ),
        "",
        format_week_range(start_date, end_date),
        "",
        '{| class="wikitable sortable"',
        "!Posizione",
        "!Articolo",
        "!Nome",
        "!Visite",
        "!Descrizione",
    ]
    lines.extend(build_table_rows(data.get("articles", [])))
    lines.append("|}")
    lines.append("")
    return "\n".join(lines)


def resolve_output_path(output: Optional[str], year: int, week: int) -> Optional[Path]:
    if output == "-":
        return None
    if output:
        return Path(output)
    output_dir = Path("wikicode")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{year}-{week:02d}.wiki"


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.input))
    year = int(data.get("year", 0))
    week = int(data.get("week", 0))
    output_path = resolve_output_path(args.output, year, week)
    content = render_wikicode(data)

    if output_path is None:
        sys.stdout.write(content)
        return 0

    output_path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
