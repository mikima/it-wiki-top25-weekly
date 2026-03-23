#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import requests


API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top"
DEFAULT_PROJECT = "it.wikipedia"
DEFAULT_ACCESS = "all-access"
DEFAULT_USER_AGENT = (
    "it-wiki-top25-weekly/2.0 "
    "(https://github.com/michelemauri/it-wiki-top25-weekly)"
)
WEEK_FILE_PATTERN = re.compile(r"^(\d{4})-(\d{2})\.json$")


@dataclass(frozen=True, order=True)
class WeekId:
    year: int
    week: int

    def monday(self) -> date:
        return date.fromisocalendar(self.year, self.week, 1)

    def label(self) -> str:
        return f"{self.year}-{self.week:02d}"


@dataclass(frozen=True)
class WeekRange:
    start: WeekId
    end: WeekId

    def label(self) -> str:
        if self.start == self.end:
            return self.start.label()
        return f"{self.start.label()} -> {self.end.label()}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit missing weekly JSON files and optionally probe the Wikimedia "
            "pageviews API to classify why a week is missing."
        )
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        default="docs/json",
        help="Directory containing weekly JSON files (default: docs/json)",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=None,
        help=(
            "Start the audit from ISO week 1 of this year; if omitted, start from "
            "the first existing JSON file"
        ),
    )
    parser.add_argument(
        "--probe-week",
        action="append",
        default=[],
        metavar="YYYY-WW",
        help="Probe a specific missing week against Wikimedia; repeatable",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds when probing (default: 30)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=DEFAULT_PROJECT,
        help=f"Wikimedia project to probe (default: {DEFAULT_PROJECT})",
    )
    parser.add_argument(
        "--access",
        type=str,
        default=DEFAULT_ACCESS,
        help=f"Access class to probe (default: {DEFAULT_ACCESS})",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default=DEFAULT_USER_AGENT,
        help="User-Agent for Wikimedia requests",
    )
    return parser.parse_args()


def load_existing_weeks(json_dir: Path) -> List[WeekId]:
    weeks: List[WeekId] = []
    for path in sorted(json_dir.glob("*.json")):
        match = WEEK_FILE_PATTERN.match(path.name)
        if not match:
            continue
        weeks.append(WeekId(int(match.group(1)), int(match.group(2))))
    return weeks


def iter_weeks(start: WeekId, end: WeekId) -> Iterable[WeekId]:
    current = start.monday()
    end_date = end.monday()
    while current <= end_date:
        iso_year, iso_week, _ = current.isocalendar()
        yield WeekId(iso_year, iso_week)
        current += timedelta(days=7)


def find_missing_weeks(existing: Sequence[WeekId], start: WeekId, end: WeekId) -> List[WeekId]:
    existing_set = set(existing)
    return [week for week in iter_weeks(start, end) if week not in existing_set]


def compress_ranges(weeks: Sequence[WeekId]) -> List[WeekRange]:
    if not weeks:
        return []

    ranges: List[WeekRange] = []
    start = weeks[0]
    prev = weeks[0]
    for current in weeks[1:]:
        if (current.monday() - prev.monday()).days == 7:
            prev = current
            continue
        ranges.append(WeekRange(start, prev))
        start = current
        prev = current
    ranges.append(WeekRange(start, prev))
    return ranges


def parse_week_id(value: str) -> WeekId:
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if not match:
        raise ValueError(f"Invalid week id '{value}'; expected YYYY-WW")
    year = int(match.group(1))
    week = int(match.group(2))
    return WeekId(year, week)


def week_dates(week_id: WeekId) -> List[date]:
    start = week_id.monday()
    return [start + timedelta(days=offset) for offset in range(7)]


def probe_week(
    session: requests.Session,
    week_id: WeekId,
    project: str,
    access: str,
    timeout: float,
) -> List[Tuple[date, int, str]]:
    failures: List[Tuple[date, int, str]] = []
    for day in week_dates(week_id):
        url = f"{API_BASE}/{project}/{access}/{day:%Y/%m/%d}"
        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException as exc:
            failures.append((day, 0, str(exc)))
            continue

        if response.status_code >= 400:
            snippet = response.text.strip().replace("\n", " ")
            failures.append((day, response.status_code, snippet[:180]))
    return failures


def main() -> int:
    args = parse_args()
    json_dir = Path(args.json_dir)
    existing = load_existing_weeks(json_dir)
    if not existing:
        print(f"No weekly JSON files found in {json_dir}", file=sys.stderr)
        return 2

    first_existing = existing[0]
    last_existing = existing[-1]
    range_start = WeekId(args.min_year, 1) if args.min_year is not None else first_existing
    range_end = last_existing

    missing = find_missing_weeks(existing, range_start, range_end)
    missing_ranges = compress_ranges(missing)

    print(f"Existing range: {first_existing.label()} -> {last_existing.label()}")
    print(f"Audited range: {range_start.label()} -> {range_end.label()}")
    print(f"Missing weeks: {len(missing)}")
    for item in missing_ranges:
        print(f"- {item.label()}")

    if not args.probe_week:
        return 0

    requested = [parse_week_id(value) for value in args.probe_week]
    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    for week_id in requested:
        print(f"\nProbe {week_id.label()}")
        failures = probe_week(
            session,
            week_id,
            project=args.project,
            access=args.access,
            timeout=args.timeout,
        )
        if not failures:
            print("- all 7 daily endpoints returned 2xx")
            continue
        for day, status, detail in failures:
            status_label = "request-error" if status == 0 else str(status)
            print(f"- {day.isoformat()} -> {status_label}: {detail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
