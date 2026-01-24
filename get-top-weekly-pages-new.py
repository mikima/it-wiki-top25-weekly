#!/usr/bin/env python3
"""
Aggregate weekly top pageviews using the Wikimedia REST API.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import requests

API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top"
DEFAULT_PROJECT = "it.wikipedia"
DEFAULT_ACCESS = "all-access"
DEFAULT_USER_AGENT = (
    "it-wiki-top25-weekly/2.0 "
    "(https://github.com/michelemauri/it-wiki-top25-weekly)"
)
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
MAX_TITLES_PER_REQUEST = 50
STOPWORD_PREFIXES = (
    "Progetto:",
    "Wikipedia:",
    "Aiuto:",
    "Speciale:",
    "Special:",
    "File:",
    "Categoria:",
)
STOPWORD_TITLES = (
    "Pagina_principale",
    "load.php",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate daily top pageviews into a weekly ranking using the "
            "Wikimedia REST API."
        )
    )
    parser.add_argument("--year", type=int, required=True, help="ISO year")
    parser.add_argument("--week", type=int, required=True, help="ISO week number (1-53)")
    parser.add_argument(
        "--project",
        type=str,
        default=DEFAULT_PROJECT,
        help="Wikimedia project, e.g. it.wikipedia",
    )
    parser.add_argument(
        "--access",
        type=str,
        default=DEFAULT_ACCESS,
        help="Access type (all-access, desktop, mobile-app, mobile-web)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Limit the number of ranked articles in the output",
    )
    parser.add_argument(
        "--exclude-special-pages",
        action="store_true",
        dest="exclude_stopwords",
        help="Exclude stopwords like Pagina_principale or Speciale:",
    )
    parser.add_argument(
        "--exclude-stopwords",
        action="store_true",
        dest="exclude_stopwords",
        help=(
            "Exclude stopwords: Pagina_principale, load.php, and titles starting "
            "with Progetto:, Wikipedia:, Aiuto:, Speciale:, Special:, File:, "
            "Categoria:"
        ),
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=("json", "csv"),
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--thumbsize",
        type=int,
        default=1000,
        help="Thumbnail size in pixels for pageimages",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path, use '-' for stdout",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default=DEFAULT_USER_AGENT,
        help="User-Agent header for API requests",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds",
    )
    return parser.parse_args()


def week_dates(year: int, week: int) -> Tuple[date, date, List[date]]:
    start = date.fromisocalendar(year, week, 1)
    days = [start + timedelta(days=offset) for offset in range(7)]
    end = days[-1]
    return start, end, days


def fetch_daily_top(
    session: requests.Session,
    project: str,
    access: str,
    day: date,
    timeout: float,
) -> List[Dict[str, object]]:
    url = f"{API_BASE}/{project}/{access}/{day:%Y/%m/%d}"
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed for {day.isoformat()}: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON for {day.isoformat()}") from exc

    items = payload.get("items")
    if not items or "articles" not in items[0]:
        raise RuntimeError(f"Unexpected response for {day.isoformat()}")

    return items[0]["articles"]


def aggregate_weekly(daily_lists: Iterable[List[Dict[str, object]]]) -> Dict[str, int]:
    totals: Dict[str, int] = defaultdict(int)
    for daily in daily_lists:
        for entry in daily:
            article = entry.get("article")
            if not article:
                continue
            try:
                views = int(entry.get("views", 0))
            except (TypeError, ValueError):
                continue
            totals[str(article)] += views
    return totals


def rank_articles(totals: Dict[str, int], limit: int) -> List[Dict[str, object]]:
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if limit:
        ranked = ranked[:limit]
    return [
        {"rank": index + 1, "article": article, "views": views}
        for index, (article, views) in enumerate(ranked)
    ]


def is_excluded_title(title: str) -> bool:
    normalized = title.replace(" ", "_")
    if normalized in STOPWORD_TITLES:
        return True
    return normalized.startswith(STOPWORD_PREFIXES)


def filter_totals(totals: Dict[str, int]) -> Dict[str, int]:
    return {
        title: views
        for title, views in totals.items()
        if not is_excluded_title(title)
    }


def chunked(values: List[str], size: int) -> Iterable[List[str]]:
    for offset in range(0, len(values), size):
        yield values[offset : offset + size]


def project_api_url(project: str) -> str:
    if project.endswith(".org"):
        return f"https://{project}/w/api.php"
    return f"https://{project}.org/w/api.php"


def fetch_descriptions(
    session: requests.Session,
    project: str,
    titles: List[str],
    timeout: float,
) -> Dict[str, str]:
    if not titles:
        return {}

    api_url = project_api_url(project)

    descriptions: Dict[str, str] = {}
    for batch in chunked(titles, MAX_TITLES_PER_REQUEST):
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "pageterms",
            "titles": "|".join(batch),
        }
        try:
            response = session.get(api_url, params=params, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Description request failed: {exc}") from exc

        payload = response.json()
        pages = payload.get("query", {}).get("pages", [])
        for page in pages:
            title = page.get("title")
            if not title:
                continue
            description = ""
            terms = page.get("terms", {})
            if "description" in terms and terms["description"]:
                description = str(terms["description"][0])
            descriptions[title] = description
            descriptions[title.replace(" ", "_")] = description

    return descriptions


def fetch_pageimages(
    session: requests.Session,
    project: str,
    titles: List[str],
    thumbsize: int,
    timeout: float,
) -> Dict[str, Dict[str, str]]:
    if not titles:
        return {}

    api_url = project_api_url(project)
    images: Dict[str, Dict[str, str]] = {}
    for batch in chunked(titles, MAX_TITLES_PER_REQUEST):
        params = {
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "piprop": "thumbnail|name",
            "pithumbsize": str(thumbsize),
            "titles": "|".join(batch),
        }
        try:
            response = session.get(api_url, params=params, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Pageimage request failed: {exc}") from exc

        payload = response.json()
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title")
            if not title:
                continue
            pageimage = page.get("pageimage", "")
            thumbnail = page.get("thumbnail", {})
            source = thumbnail.get("source", "")
            record = {
                "image_filename": str(pageimage) if pageimage else "",
                "image_url": str(source) if source else "",
            }
            images[title] = record
            images[title.replace(" ", "_")] = record

    return images


def fetch_image_licenses(
    session: requests.Session,
    filenames: List[str],
    timeout: float,
) -> Dict[str, Dict[str, str]]:
    if not filenames:
        return {}

    licenses: Dict[str, Dict[str, str]] = {}
    for batch in chunked(filenames, MAX_TITLES_PER_REQUEST):
        titles = [f"File:{name}" for name in batch if name]
        if not titles:
            continue
        params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "iiprop": "extmetadata",
            "titles": "|".join(titles),
        }
        try:
            response = session.get(COMMONS_API_URL, params=params, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"License request failed: {exc}") from exc

        payload = response.json()
        pages = payload.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "")
            if not title.startswith("File:"):
                continue
            filename = title.replace("File:", "", 1)
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue
            metadata = imageinfo[0].get("extmetadata", {})
            license_short = metadata.get("LicenseShortName", {}).get("value", "")
            copyrighted = metadata.get("Copyrighted", {}).get("value", "")
            licenses[filename] = {
                "image_license": str(license_short),
                "image_copyrighted": str(copyrighted),
            }

    return licenses


def resolve_output_path(fmt: str, output: Optional[str]) -> Optional[str]:
    if output == "-":
        return None
    if output:
        return output
    return f"weekly_data.{fmt}"


def write_json(data: Dict[str, object], output_path: Optional[str]) -> None:
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        return

    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


def write_csv(rows: List[Dict[str, object]], output_path: Optional[str]) -> None:
    if output_path:
        handle = open(output_path, "w", encoding="utf-8", newline="")
        close_handle = True
    else:
        handle = sys.stdout
        close_handle = False

    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "rank",
            "article",
            "views",
            "description",
            "image_filename",
            "image_url",
            "image_license",
            "image_copyrighted",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

    if close_handle:
        handle.close()


def main() -> int:
    args = parse_args()

    try:
        start_date, end_date, days = week_dates(args.year, args.week)
    except ValueError as exc:
        print(f"Invalid year/week: {exc}", file=sys.stderr)
        return 2

    output_path = resolve_output_path(args.format, args.output)

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    daily_lists: List[List[Dict[str, object]]] = []
    for day in days:
        daily_lists.append(
            fetch_daily_top(session, args.project, args.access, day, args.timeout)
        )

    totals = aggregate_weekly(daily_lists)
    if args.exclude_stopwords:
        totals = filter_totals(totals)
    ranked = rank_articles(totals, args.limit)
    descriptions = fetch_descriptions(
        session, args.project, [item["article"] for item in ranked], args.timeout
    )
    for item in ranked:
        article = str(item["article"])
        description = descriptions.get(article)
        if description is None:
            description = descriptions.get(article.replace("_", " "), "")
        item["description"] = description
        item["image_filename"] = ""
        item["image_url"] = ""
        item["image_license"] = ""
        item["image_copyrighted"] = ""

    pageimages = fetch_pageimages(
        session,
        args.project,
        [item["article"] for item in ranked],
        args.thumbsize,
        args.timeout,
    )
    image_filenames = []
    for item in ranked:
        article = str(item["article"])
        image = pageimages.get(article)
        if image is None:
            image = pageimages.get(article.replace("_", " "), {})
        if image:
            item["image_filename"] = image.get("image_filename", "")
            item["image_url"] = image.get("image_url", "")
            if item["image_filename"]:
                image_filenames.append(item["image_filename"])

    licenses = fetch_image_licenses(session, image_filenames, args.timeout)
    for item in ranked:
        filename = item.get("image_filename", "")
        if not filename:
            continue
        license_info = licenses.get(filename, {})
        item["image_license"] = license_info.get("image_license", "")
        item["image_copyrighted"] = license_info.get("image_copyrighted", "")

    output_data = {
        "project": args.project,
        "access": args.access,
        "year": args.year,
        "week": args.week,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": [day.isoformat() for day in days],
        "total_articles": len(totals),
        "articles": ranked,
    }

    if args.format == "json":
        write_json(output_data, output_path)
    else:
        write_csv(ranked, output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
