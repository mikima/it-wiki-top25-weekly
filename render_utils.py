#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

SPARKLINE_BLOCKS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    return text.strip()


def escape_wikicode(value: object) -> str:
    text = normalize_text(value)
    text = text.replace("|", "&#124;")
    text = text.replace("_", "&#95;")
    return text


def escape_markdown(value: object) -> str:
    text = normalize_text(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("_", "\\_")
    return text


def escape_html_attr(value: object) -> str:
    text = normalize_text(value)
    text = text.replace("&", "&amp;")
    text = text.replace('"', "&quot;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def format_views(value: object) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "0"
    return f"{number:,}".replace(",", ".")


def sparkline(values: Iterable[object]) -> str:
    clean: List[int] = []
    for value in values:
        try:
            clean.append(int(value))
        except (TypeError, ValueError):
            clean.append(0)
    if not clean:
        return ""
    min_value = min(clean)
    max_value = max(clean)
    if max_value == min_value:
        return SPARKLINE_BLOCKS[4] * len(clean)
    scale = max_value - min_value
    last_index = len(SPARKLINE_BLOCKS) - 1
    return "".join(
        SPARKLINE_BLOCKS[int((value - min_value) / scale * last_index)]
        for value in clean
    )


def bar_chart_svg(
    daily_views: Iterable[dict],
    width: int = 100,
    height: int = 24,
    pad: int = 2,
    bar_color: str = "#3a3a3a",
) -> str:
    items = []
    for item in daily_views:
        if not isinstance(item, dict):
            continue
        date_value = normalize_text(item.get("date", ""))
        try:
            views_value = int(item.get("views", 0))
        except (TypeError, ValueError):
            views_value = 0
        items.append((date_value, views_value))
    if not items:
        return ""

    values = [views for _, views in items]
    min_value = min(values)
    max_value = max(values)
    bar_count = len(values)
    if bar_count == 0:
        return ""
    inner_width = max(width - pad * 2, 1)
    inner_height = max(height - pad * 2, 1)
    step = inner_width / bar_count
    bar_width = max(step * 0.8, 1)
    if max_value == min_value:
        max_value = min_value + 1

    rects = []
    for index, (date_value, views_value) in enumerate(items):
        bar_height = int((views_value - min_value) / (max_value - min_value) * inner_height)
        bar_height = max(bar_height, 1)
        x = pad + index * step + (step - bar_width) / 2
        y = pad + (inner_height - bar_height)
        title = escape_html_attr(f"{date_value}: {views_value}")
        rects.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" '
            f'height="{bar_height:.2f}" fill="{bar_color}">'
            f"<title>{title}</title></rect>"
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        + "".join(rects)
        + "</svg>"
    )
    return svg
