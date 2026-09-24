#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

WEEK_FILE_PATTERN = re.compile(r"^(\d{4})-(\d{2})\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update docs/weeks.json and docs/index.html from weekly JSON files. docs/week.html, week.css and week.js are static and edited by hand."
    )
    parser.add_argument(
        "--json-dir",
        default="docs/json",
        help="Directory containing weekly JSON files (YYYY-WW.json)",
    )
    parser.add_argument("--docs-dir", default="docs", help="Directory for HTML output files")
    return parser.parse_args()


def discover_week_files(json_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in sorted(json_dir.glob("*.json")):
        if WEEK_FILE_PATTERN.match(path.name):
            files.append(path)
    return files


def write_weeks_file(week_ids: List[str], docs_dir: Path) -> None:
    weeks_path = docs_dir / "weeks.json"
    weeks_path.write_text(json.dumps(week_ids, indent=2) + "\n", encoding="utf-8")


def write_index_html(docs_dir: Path) -> None:
    content = """<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>it-wiki top weekly</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; }
  </style>
</head>
<body>
  <h1>it-wiki top weekly</h1>
  <p id="status">Caricamento ultima settimana...</p>
  <script>
    fetch("weeks.json")
      .then((response) => response.json())
      .then((weeks) => {
        if (Array.isArray(weeks) && weeks.length > 0) {
          const latest = weeks[weeks.length - 1];
          window.location.href = `week.html?week=${latest}`;
          return;
        }
        document.getElementById("status").textContent = "Nessuna settimana disponibile.";
      })
      .catch(() => {
        document.getElementById("status").textContent = "Errore nel caricamento di weeks.json";
      });
  </script>
</body>
</html>
"""
    (docs_dir / "index.html").write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    json_dir = Path(args.json_dir)
    docs_dir = Path(args.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    if not json_dir.exists():
        raise SystemExit(f"JSON directory not found: {json_dir}")

    week_files = discover_week_files(json_dir)
    week_ids = [path.stem for path in week_files]
    write_weeks_file(week_ids, docs_dir)
    write_index_html(docs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
