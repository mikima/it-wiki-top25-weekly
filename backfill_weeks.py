#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, timedelta
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run wiki-get-top-weekly-pages.py for each ISO week, "
            "from a start week backwards to a minimum year."
        )
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Start ISO year (default: current week year)",
    )
    parser.add_argument(
        "--start-week",
        type=int,
        default=None,
        help="Start ISO week number (default: current week number)",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2010,
        help="Last year to include while going backwards (default: 2010)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Top articles to request for each week (default: 25)",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="Python executable used to run the weekly script",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately if one week fails",
    )
    return parser.parse_args()


def resolve_start_date(start_year: Optional[int], start_week: Optional[int]) -> date:
    if start_year is None and start_week is None:
        today = date.today()
        iso_year, iso_week, _ = today.isocalendar()
        return date.fromisocalendar(iso_year, iso_week, 1)
    if start_year is None or start_week is None:
        raise ValueError("You must provide both --start-year and --start-week together.")
    return date.fromisocalendar(start_year, start_week, 1)


def build_command(python_bin: str, year: int, week: int, top: int) -> list[str]:
    return [
        python_bin,
        "wiki-get-top-weekly-pages.py",
        "--exclude-stopwords",
        "--format",
        "json",
        "--top",
        str(top),
        "--year",
        str(year),
        "--week",
        str(week),
    ]


def main() -> int:
    args = parse_args()
    try:
        current = resolve_start_date(args.start_year, args.start_week)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    failures = 0
    total = 0

    while current.isocalendar().year >= args.min_year:
        year, week, _ = current.isocalendar()
        cmd = build_command(args.python, year, week, args.top)
        total += 1
        print(f"[{total}] {year}-W{week:02d}: {' '.join(cmd)}")

        if not args.dry_run:
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                failures += 1
                print(
                    f"Failed week {year}-W{week:02d} (exit {result.returncode})",
                    file=sys.stderr,
                )
                if args.stop_on_error:
                    return result.returncode

        current = current - timedelta(days=7)

    if failures:
        print(f"Completed with {failures} failures.", file=sys.stderr)
        return 1

    print("Completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
