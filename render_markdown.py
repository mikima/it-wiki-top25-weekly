#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

from render_utils import (
    bar_chart_svg,
    escape_html_attr,
    escape_markdown,
    format_views,
    load_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Markdown report from a weekly JSON export."
    )
    parser.add_argument("input", help="Path to JSON file")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path, use '-' for stdout",
    )
    return parser.parse_args()


def build_rows(articles: List[Dict[str, object]]) -> List[str]:
    rows = []
    for item in articles:
        title = str(item.get("article", ""))
        title_display = title.replace("_", " ")
        name = escape_markdown(title_display)
        alt_text = escape_html_attr(title_display)
        views = format_views(item.get("views", 0))
        daily_views = item.get("daily_views", [])
        svg = bar_chart_svg(daily_views)
        pageviews_url = str(item.get("pageviews_url", ""))
        if svg:
            chart_src = "data:image/svg+xml;utf8," + quote(svg, safe="")
            chart_img = (
                f'<img src="{chart_src}" alt="{alt_text}" '
                'style="max-width:200px; max-height:200px;" />'
            )
            trend_cell = (
                f'<a href="{pageviews_url}">{chart_img}</a>'
                if pageviews_url
                else chart_img
            )
        else:
            trend_cell = ""
        image_url = str(item.get("image_url", ""))
        image_cell = (
            f'<img src="{image_url}" alt="{alt_text}" '
            'style="max-width:200px; max-height:200px;" />'
            if image_url
            else ""
        )
        article_url = str(item.get("article_url", ""))
        name_cell = f"[{name}]({article_url})" if article_url else name
        news_url = str(item.get("google_news_url", ""))
        news_cell = f"[Google News]({news_url})" if news_url else ""
        description = escape_markdown(item.get("description", ""))
        rows.append(
            f"| {item.get('rank', '')} | {name_cell} | {views} | {trend_cell} | "
            f"{image_cell} | {news_cell} | {description} |"
        )
    return rows


def render_markdown(data: Dict[str, object]) -> str:
    lines = [
        "| Rank | Name | Views | Trend | Image | Google News | Description |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(build_rows(data.get("articles", [])))
    lines.append("")
    return "\n".join(lines)


def resolve_output_path(output: Optional[str], year: int, week: int) -> Optional[Path]:
    if output == "-":
        return None
    if output:
        return Path(output)
    output_dir = Path("markdown")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{year}-{week:02d}.md"


def main() -> int:
    args = parse_args()
    data = load_json(Path(args.input))
    year = int(data.get("year", 0))
    week = int(data.get("week", 0))
    output_path = resolve_output_path(args.output, year, week)
    content = render_markdown(data)

    if output_path is None:
        sys.stdout.write(content)
        return 0

    output_path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
