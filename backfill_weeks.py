#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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
        default=2015,
        help="Last year to include while going backwards (default: 2015)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Top articles to request for each week (default: 30)",
    )
    parser.add_argument(
        "--max-weeks",
        type=int,
        default=None,
        help="Maximum number of ISO weeks to process in this run",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=sys.executable,
        help="Python executable used to run the weekly script",
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        default="docs/json",
        help="Directory checked for existing weekly JSON output files",
    )
    parser.add_argument(
        "--raw-json-dir",
        type=str,
        default="docs/rawjson",
        help="Directory checked for existing raw weekly JSON output files",
    )
    parser.add_argument(
        "--report-file",
        type=str,
        default="backfill-report.json",
        help="JSON report written at the end of the run",
    )
    parser.add_argument(
        "--force-rewrite",
        action="store_true",
        help="Run all weeks even if output JSON already exists",
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


def build_command(
    python_bin: str,
    year: int,
    week: int,
    top: int,
    json_dir: str,
    raw_json_dir: str,
) -> list[str]:
    return [
        python_bin,
        "wiki-get-top-weekly-pages.py",
        "--exclude-stopwords",
        "--allow-missing-days",
        "--format",
        "json",
        "--top",
        str(top),
        "--json-dir",
        json_dir,
        "--raw-json-dir",
        raw_json_dir,
        "--year",
        str(year),
        "--week",
        str(week),
    ]


def load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def extract_missing_days(data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    missing_days = data.get("missing_days", [])
    if not isinstance(missing_days, list):
        return []
    return [item for item in missing_days if isinstance(item, dict)]


def existing_output_state(json_path: Path, raw_json_path: Path) -> List[str]:
    if not json_path.exists() and not raw_json_path.exists():
        return []

    reasons: List[str] = []

    if not json_path.exists():
        reasons.append("missing enriched JSON")
    if not raw_json_path.exists():
        reasons.append("missing raw JSON")

    if json_path.exists():
        payload = load_json_file(json_path)
        if payload is None:
            reasons.append("unreadable enriched JSON")
        else:
            missing_days = extract_missing_days(payload)
            if missing_days:
                reasons.append(f"{len(missing_days)} missing day(s) recorded")

    return reasons


def write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        current = resolve_start_date(args.start_year, args.start_week)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    failures = 0
    total = 0
    skipped = 0
    retried = 0
    visited = 0
    failed_weeks: List[Dict[str, Any]] = []
    incomplete_weeks: List[Dict[str, Any]] = []
    retried_weeks: List[Dict[str, Any]] = []

    while current.isocalendar().year >= args.min_year:
        if args.max_weeks is not None and visited >= args.max_weeks:
            break
        visited += 1
        year, week, _ = current.isocalendar()
        week_id = f"{year}-W{week:02d}"
        output_path = Path(args.json_dir) / f"{year}-{week:02d}.json"
        raw_output_path = Path(args.raw_json_dir) / f"{year}-{week:02d}.json"
        retry_reasons = existing_output_state(output_path, raw_output_path)

        if output_path.exists() and not args.force_rewrite and not retry_reasons:
            skipped += 1
            print(f"[skip] {week_id}: found {output_path}")
            current = current - timedelta(days=7)
            continue

        if retry_reasons and not args.force_rewrite:
            retried += 1
            retried_weeks.append({"week": f"{year}-{week:02d}", "reasons": retry_reasons})
            print(f"[retry] {week_id}: " + ", ".join(retry_reasons))

        cmd = build_command(
            args.python,
            year,
            week,
            args.top,
            args.json_dir,
            args.raw_json_dir,
        )
        total += 1
        print(f"[{total}] {week_id}: {' '.join(cmd)}")

        if not args.dry_run:
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                failures += 1
                failed_weeks.append(
                    {
                        "week": f"{year}-{week:02d}",
                        "returncode": result.returncode,
                    }
                )
                print(
                    f"Failed week {week_id} (exit {result.returncode})",
                    file=sys.stderr,
                )
                if args.stop_on_error:
                    report = {
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "executed": total,
                        "skipped": skipped,
                        "retried": retried,
                        "failed_weeks": failed_weeks,
                        "incomplete_weeks": incomplete_weeks,
                        "retried_weeks": retried_weeks,
                    }
                    write_report(Path(args.report_file), report)
                    return result.returncode
            else:
                if not output_path.exists() or not raw_output_path.exists():
                    failures += 1
                    failed_weeks.append(
                        {
                            "week": f"{year}-{week:02d}",
                            "returncode": result.returncode,
                            "error": "collector exited successfully but did not write both JSON files",
                        }
                    )
                    print(
                        f"Failed week {week_id}: missing output artifact after successful run.",
                        file=sys.stderr,
                    )
                    if args.stop_on_error:
                        report = {
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "executed": total,
                            "skipped": skipped,
                            "retried": retried,
                            "failed_weeks": failed_weeks,
                            "incomplete_weeks": incomplete_weeks,
                            "retried_weeks": retried_weeks,
                        }
                        write_report(Path(args.report_file), report)
                        return 1
                    current = current - timedelta(days=7)
                    continue
                payload = load_json_file(output_path)
                if payload is None:
                    failures += 1
                    failed_weeks.append(
                        {
                            "week": f"{year}-{week:02d}",
                            "returncode": result.returncode,
                            "error": "collector wrote unreadable enriched JSON",
                        }
                    )
                    print(
                        f"Failed week {week_id}: unreadable enriched JSON after run.",
                        file=sys.stderr,
                    )
                    if args.stop_on_error:
                        report = {
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "executed": total,
                            "skipped": skipped,
                            "retried": retried,
                            "failed_weeks": failed_weeks,
                            "incomplete_weeks": incomplete_weeks,
                            "retried_weeks": retried_weeks,
                        }
                        write_report(Path(args.report_file), report)
                        return 1
                    current = current - timedelta(days=7)
                    continue
                missing_days = extract_missing_days(payload)
                if missing_days:
                    incomplete_weeks.append(
                        {
                            "week": f"{year}-{week:02d}",
                            "missing_days": missing_days,
                        }
                    )

        current = current - timedelta(days=7)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executed": total,
        "skipped": skipped,
        "retried": retried,
        "failed_weeks": failed_weeks,
        "incomplete_weeks": incomplete_weeks,
        "retried_weeks": retried_weeks,
    }
    if not args.dry_run:
        write_report(Path(args.report_file), report)

    if failures:
        print(
            f"Completed with {failures} failures and {len(incomplete_weeks)} incomplete week(s).",
            file=sys.stderr,
        )
        return 1

    print(
        "Completed successfully. "
        f"Executed: {total}, skipped: {skipped}, retried: {retried}, "
        f"incomplete weeks: {len(incomplete_weeks)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
