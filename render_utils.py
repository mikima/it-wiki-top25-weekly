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
