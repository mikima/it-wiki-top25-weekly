#!/usr/bin/env python3
"""
Use the OpenAI API to enrich weekly JSON files with contextual descriptions.

The script updates only articles[*].description and preserves every other field.
It reads the writing rules from agent-instructions.md by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple
from urllib.parse import quote


DEFAULT_MODEL = "gpt-4.1"
DEFAULT_JSON_DIR = Path("docs/json")
DEFAULT_INSTRUCTIONS = Path("agent-instructions.md")
DEFAULT_ENV_FILE = Path(".env")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
WIKIPEDIA_SUMMARY_URL = "https://it.wikipedia.org/api/rest_v1/page/summary/{title}"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
USER_AGENT = (
    "it-wiki-top25-weekly-openai/1.0 "
    "(https://github.com/michelemauri/it-wiki-top25-weekly)"
)
WEEK_RE = re.compile(r"^(?P<year>\d{4})-(?P<week>\d{2})$")


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Italian weekly article descriptions with the OpenAI API."
        )
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Week ids (YYYY-WW) or JSON paths. Example: 2026-21 "
            "docs/json/2026-21.json"
        ),
    )
    parser.add_argument(
        "--year",
        type=int,
        help="ISO year to process, used with --week.",
    )
    parser.add_argument(
        "--week",
        type=int,
        help="ISO week to process, used with --year.",
    )
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=DEFAULT_JSON_DIR,
        help="Directory containing docs/json/YYYY-WW.json files.",
    )
    parser.add_argument(
        "--instructions",
        type=Path,
        default=DEFAULT_INSTRUCTIONS,
        help="Markdown file with description rules.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model. Can also be set with OPENAI_MODEL.",
    )
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the OpenAI API key.",
    )
    parser.add_argument(
        "--mode",
        choices=("missing", "stubs", "all"),
        default="all",
        help=(
            "Which entries to update: missing only blank descriptions; stubs "
            "also updates short MediaWiki-style descriptions; all rewrites all "
            "(default)."
        ),
    )
    parser.add_argument(
        "--articles",
        nargs="+",
        help=(
            "Optional article titles to update in each selected file. Accepts "
            "underscores or spaces."
        ),
    )
    parser.add_argument(
        "--same-week-previous-years",
        action="store_true",
        help=(
            "Also process the same ISO week in previous years, when the JSON "
            "file exists and has matching entries for --mode."
        ),
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2015,
        help="Lower bound for --same-week-previous-years.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of articles per OpenAI request.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to wait between OpenAI requests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show selected files and articles without calling OpenAI or writing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Alias for --mode all.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds for OpenAI calls.",
    )
    parser.add_argument(
        "--context-timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds for Wikipedia/Google News context.",
    )
    parser.add_argument(
        "--max-news-items",
        type=int,
        default=5,
        help="Maximum Google News RSS items to pass to OpenAI per article.",
    )
    parser.add_argument(
        "--no-fetch-context",
        action="store_true",
        help="Do not fetch Wikipedia summaries or Google News RSS context.",
    )
    return parser.parse_args()


def load_env_file(path: Path = DEFAULT_ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize_article_title(value: str) -> str:
    return value.strip().replace(" ", "_")


def week_id_from_path(path: Path) -> str:
    return path.stem


def week_id(year: int, week: int) -> str:
    return f"{year:04d}-{week:02d}"


def path_for_week(json_dir: Path, value: str) -> Path:
    match = WEEK_RE.match(value)
    if not match:
        return Path(value)
    return json_dir / f"{value}.json"


def resolve_targets(args: argparse.Namespace) -> List[Path]:
    values = list(args.targets)
    if args.year is not None or args.week is not None:
        if args.year is None or args.week is None:
            raise SystemExit("--year and --week must be used together.")
        values.append(week_id(args.year, args.week))
    if not values:
        raise SystemExit("Provide at least one target week/path or --year --week.")

    paths: List[Path] = []
    seen: set[Path] = set()
    for value in values:
        path = path_for_week(args.json_dir, value)
        for expanded in expand_previous_years(path, args):
            normalized = expanded.resolve()
            if normalized not in seen:
                paths.append(expanded)
                seen.add(normalized)
    return paths


def expand_previous_years(path: Path, args: argparse.Namespace) -> List[Path]:
    paths = [path]
    if not args.same_week_previous_years:
        return paths

    current_id = week_id_from_path(path)
    match = WEEK_RE.match(current_id)
    if not match:
        raise SystemExit(
            "--same-week-previous-years requires targets named YYYY-WW.json or YYYY-WW."
        )

    start_year = int(match.group("year"))
    week = int(match.group("week"))
    for year in range(start_year - 1, args.min_year - 1, -1):
        candidate = args.json_dir / f"{year:04d}-{week:02d}.json"
        if candidate.exists():
            paths.append(candidate)
    return paths


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("articles"), list):
        raise ValueError(f"{path} is not a weekly JSON file.")
    return data


def write_json(path: Path, data: Dict[str, Any]) -> None:
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    json.loads(encoded)
    path.write_text(encoded + "\n", encoding="utf-8")


def is_stub_description(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if len(text) <= 70 and text[:1].islower():
        return True
    if len(text) <= 90 and re.search(r"\(\d{4}(?:-\d{4})?\)$", text):
        return True
    return False


def selected_articles(
    data: Dict[str, Any],
    mode: str,
    article_filter: set[str] | None,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for item in data["articles"]:
        if not isinstance(item, dict):
            continue
        article = str(item.get("article", ""))
        if article_filter is not None and normalize_article_title(article) not in article_filter:
            continue
        description = item.get("description", "")
        if mode == "all":
            selected.append(item)
        elif mode == "missing" and not str(description or "").strip():
            selected.append(item)
        elif mode == "stubs" and is_stub_description(description):
            selected.append(item)
    return selected


def chunks(values: Sequence[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    if size <= 0:
        raise SystemExit("--batch-size must be greater than zero.")
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def read_instructions(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Instruction file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def strip_markup(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def fetch_article_context(
    item: Dict[str, Any],
    week_data: Dict[str, Any],
    *,
    timeout: float,
    max_news_items: int,
) -> Dict[str, Any]:
    import requests

    article = str(item.get("article", ""))
    title_for_query = article.replace("_", " ")
    context: Dict[str, Any] = {"wikipedia_summary": "", "news": []}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        summary_url = WIKIPEDIA_SUMMARY_URL.format(title=quote(article, safe=""))
        response = session.get(summary_url, timeout=timeout)
        if response.ok:
            summary = response.json().get("extract", "")
            if isinstance(summary, str):
                context["wikipedia_summary"] = summary.strip()
    except requests.RequestException:
        pass
    except ValueError:
        pass

    start = parse_iso_date(week_data.get("start_date"))
    end = parse_iso_date(week_data.get("end_date"))
    if start is None or end is None:
        return context

    before = end + timedelta(days=1)
    query = f'{title_for_query} after:{start.isoformat()} before:{before.isoformat()}'
    params = {"q": query, "hl": "it", "gl": "IT", "ceid": "IT:it"}
    try:
        response = session.get(GOOGLE_NEWS_RSS_URL, params=params, timeout=timeout)
        if response.ok:
            root = ET.fromstring(response.text)
            items = []
            for node in root.findall("./channel/item")[:max_news_items]:
                title = node.findtext("title", default="")
                pub_date = node.findtext("pubDate", default="")
                source = node.findtext("source", default="")
                description = node.findtext("description", default="")
                items.append(
                    {
                        "title": strip_markup(title),
                        "source": strip_markup(source),
                        "pubDate": strip_markup(pub_date),
                        "description": strip_markup(description),
                    }
                )
            context["news"] = items
    except requests.RequestException:
        pass
    except ET.ParseError:
        pass

    return context


def collect_context(
    article_batch: Sequence[Dict[str, Any]],
    week_data: Dict[str, Any],
    *,
    args: argparse.Namespace,
) -> Dict[str, Dict[str, Any]]:
    if args.no_fetch_context:
        return {}
    contexts: Dict[str, Dict[str, Any]] = {}
    for item in article_batch:
        article = normalize_article_title(str(item.get("article", "")))
        if not article:
            continue
        contexts[article] = fetch_article_context(
            item,
            week_data,
            timeout=args.context_timeout,
            max_news_items=args.max_news_items,
        )
    return contexts


def compact_article_payload(
    item: Dict[str, Any],
    context_by_article: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    article = normalize_article_title(str(item.get("article", "")))
    return {
        "rank": item.get("rank"),
        "article": item.get("article"),
        "views": item.get("views"),
        "daily_views": item.get("daily_views", []),
        "google_news_url": item.get("google_news_url", ""),
        "pageviews_url": item.get("pageviews_url", ""),
        "article_url": item.get("article_url", ""),
        "current_description": item.get("description", ""),
        "context": context_by_article.get(article, {}),
    }


def build_prompt(
    instructions: str,
    week_data: Dict[str, Any],
    article_batch: Sequence[Dict[str, Any]],
    context_by_article: Dict[str, Dict[str, Any]],
) -> str:
    payload = {
        "week": {
            "year": week_data.get("year"),
            "week": week_data.get("week"),
            "start_date": week_data.get("start_date"),
            "end_date": week_data.get("end_date"),
        },
        "articles": [
            compact_article_payload(item, context_by_article) for item in article_batch
        ],
    }
    return (
        "Segui queste istruzioni per scrivere descrizioni in italiano:\n\n"
        f"{instructions}\n\n"
        "Restituisci solo JSON valido conforme allo schema richiesto. "
        "Non includere markdown.\n\n"
        "Dati da analizzare:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def extract_output_text(payload: Dict[str, Any]) -> str:
    texts: List[str] = []
    for output in payload.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if texts:
        return "\n".join(texts)
    text = payload.get("output_text")
    if isinstance(text, str):
        return text
    raise ValueError("OpenAI response did not contain output text.")


def call_openai(
    *,
    api_key: str,
    model: str,
    prompt: str,
    timeout: float,
) -> List[Dict[str, str]]:
    import requests

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "descriptions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "article": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["article", "description"],
                },
            }
        },
        "required": ["descriptions"],
    }
    body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "Sei un redattore di dati per una classifica settimanale "
                    "di pagine Wikipedia in italiano. Scrivi frasi compatte, "
                    "fattuali e verificabili."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "weekly_descriptions",
                "strict": True,
                "schema": schema,
            }
        },
    }
    response = requests.post(
        OPENAI_RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=timeout,
    )
    if response.status_code >= 400:
        detail = response.text.strip().replace("\n", " ")
        raise RuntimeError(f"OpenAI API error {response.status_code}: {detail[:1000]}")
    payload = response.json()
    text = extract_output_text(payload)
    parsed = json.loads(text)
    descriptions = parsed.get("descriptions")
    if not isinstance(descriptions, list):
        raise ValueError("OpenAI JSON response has no descriptions list.")
    return descriptions


def apply_descriptions(
    data: Dict[str, Any],
    descriptions: Sequence[Dict[str, str]],
) -> int:
    by_article = {
        normalize_article_title(str(item.get("article", ""))): item
        for item in data["articles"]
        if isinstance(item, dict)
    }
    updated = 0
    for result in descriptions:
        article = normalize_article_title(str(result.get("article", "")))
        description = str(result.get("description", "")).strip()
        if not article or not description:
            log("WARNING skipping OpenAI result with missing article or description")
            continue
        target = by_article.get(article)
        if target is None:
            log(f"WARNING OpenAI returned an unknown article, not applied: {article}")
            continue
        target["description"] = description
        updated += 1
    return updated


def process_file(
    path: Path,
    *,
    args: argparse.Namespace,
    api_key: str | None,
    instructions: str,
    article_filter: set[str] | None,
) -> Tuple[int, int]:
    if not path.exists():
        log(f"SKIP missing file: {path}")
        return (0, 0)
    log(f"Reading {path}")
    data = load_json(path)
    mode = "all" if args.force else args.mode
    articles = selected_articles(data, mode, article_filter)
    log(f"{path}: {len(articles)} article(s) selected")
    for item in articles:
        log(f"  - {item.get('rank')}: {item.get('article')}")
    if args.dry_run or not articles:
        return (len(articles), 0)
    if not api_key:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set.")

    total_updated = 0
    batches = list(chunks(articles, args.batch_size))
    for batch_index, batch in enumerate(batches, start=1):
        batch_label = f"batch {batch_index}/{len(batches)}"
        article_names = ", ".join(str(item.get("article", "")) for item in batch)
        log(f"Collecting context for {batch_label}: {article_names}")
        context_by_article = collect_context(batch, data, args=args)
        prompt = build_prompt(instructions, data, batch, context_by_article)
        log(f"Sending {batch_label} to OpenAI ({len(batch)} article(s), model {args.model})")
        descriptions = call_openai(
            api_key=api_key,
            model=args.model,
            prompt=prompt,
            timeout=args.timeout,
        )
        log(f"Received OpenAI response for {batch_label}: {len(descriptions)} description(s)")
        updated = apply_descriptions(data, descriptions)
        total_updated += updated
        log(f"Applied {updated} description(s) from {batch_label}")
        if args.sleep:
            log(f"Sleeping {args.sleep:g}s before next request")
            time.sleep(args.sleep)

    log(f"Writing updated JSON: {path}")
    write_json(path, data)
    load_json(path)
    log(f"Validated JSON: {path}")
    return (len(articles), total_updated)


def main() -> int:
    load_env_file()
    args = parse_args()
    log(f"Using model: {args.model}")
    instructions = read_instructions(args.instructions)
    paths = resolve_targets(args)
    log(f"Resolved {len(paths)} file(s) to process")
    article_filter = None
    if args.articles:
        article_filter = {normalize_article_title(value) for value in args.articles}
    api_key = None if args.dry_run else os.environ.get(args.api_key_env)

    selected_total = 0
    updated_total = 0
    for path in paths:
        selected, updated = process_file(
            path,
            args=args,
            api_key=api_key,
            instructions=instructions,
            article_filter=article_filter,
        )
        selected_total += selected
        updated_total += updated

    print(
        f"Done. Selected {selected_total} article(s), updated {updated_total} description(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
