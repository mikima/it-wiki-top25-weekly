#!/usr/bin/env python3
"""One-off: add "description_source" to existing docs/json descriptions.

Values: "manual" (already set by import_manual_descriptions.py, untouched),
"wikidata" (short description fetched by wiki-get-top-weekly-pages.py) or
"openai" (rewritten with OpenAI/ChatGPT).

The origin is reconstructed from git history, for each article's current
description:
1. equal to the article's current Wikidata description -> wikidata
2. snippet-like (starts lowercase, or short and ending with years) -> wikidata
3. introduced by replacing an earlier, different value -> openai
4. otherwise (long text present since the article appeared) -> openai

The model used for past OpenAI runs is not recorded anywhere, so no
"description_model" is added here.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parent
JSON_DIR = ROOT / "docs" / "json"
API = "https://it.wikipedia.org/w/api.php"
USER_AGENT = "it-wiki-top25-weekly (User:Mikima)"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def is_snippet(text: str) -> bool:
    """Same idea as is_stub_description in enrich_descriptions_openai.py."""
    text = text.strip()
    if text[:1].islower():  # OpenAI texts always start with a capital letter
        return True
    if len(text) <= 90 and re.search(r"\(\d{4}(?:-\d{4})?\)$", text):
        return True
    return False


def history(path: Path) -> List[Dict[str, Optional[str]]]:
    """Article -> description maps, oldest commit first."""
    rel = path.relative_to(ROOT).as_posix()
    versions = []
    for commit in reversed(git("log", "--format=%H", "--", rel).split()):
        try:
            data = json.loads(git("show", f"{commit}:{rel}"))
        except (subprocess.CalledProcessError, ValueError):
            continue
        versions.append({a["article"]: a.get("description", "") for a in data.get("articles", [])})
    return versions


def introduced_by_rewrite(versions: List[Dict[str, Optional[str]]], article: str, value: str) -> bool:
    """True if the current value replaced a different earlier value."""
    previous: Optional[str] = None
    rewrite = False
    for version in versions:
        current = version.get(article)
        if current == value:
            if previous != value:
                rewrite = bool(previous)  # earlier non-empty, different value
        previous = current
    return rewrite


def fetch_wikidata(titles: List[str]) -> Dict[str, str]:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    out: Dict[str, str] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i: i + 50]
        params = dict(action="query", format="json", formatversion="2", prop="pageterms",
                      wbptterms="description", titles="|".join(t.replace("_", " ") for t in batch))
        for attempt in range(6):
            resp = session.post(API, data=params, timeout=30)
            if resp.ok and resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
                break
            print(f"  HTTP {resp.status_code}, riprovo tra {2 ** attempt * 5}s")
            time.sleep(2 ** attempt * 5)
        else:
            raise SystemExit("API Wikipedia non raggiungibile.")
        norm = {n["to"]: n["from"] for n in data.get("query", {}).get("normalized", [])}
        for page in data.get("query", {}).get("pages", []):
            desc = (page.get("terms", {}).get("description") or [""])[0]
            title = norm.get(page.get("title"), page.get("title", ""))
            out[title.replace(" ", "_")] = desc
        time.sleep(0.2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cache", type=Path, help="JSON file to cache current Wikidata descriptions.")
    ap.add_argument("--samples", type=int, default=0, help="Print N examples per category.")
    args = ap.parse_args()

    files = sorted(JSON_DIR.glob("*.json"))
    loaded = {f: json.loads(f.read_text(encoding="utf-8")) for f in files}
    titles = sorted({a["article"] for d in loaded.values() for a in d["articles"]
                     if a.get("description") and a.get("description_source") != "manual"})
    print(f"Descrizioni Wikidata attuali per {len(titles)} articoli…")
    if args.cache and args.cache.exists():
        wikidata = json.loads(args.cache.read_text(encoding="utf-8"))
    else:
        wikidata = fetch_wikidata(titles)
        if args.cache:
            args.cache.write_text(json.dumps(wikidata, ensure_ascii=False), encoding="utf-8")

    stats: collections.Counter = collections.Counter()
    samples: Dict[str, list] = collections.defaultdict(list)
    for f in files:
        data = loaded[f]
        versions = None
        for a in data["articles"]:
            if a.get("description_source") == "manual":
                stats["manual"] += 1
                continue
            value = a.get("description", "")
            if not value:
                a["description_source"] = ""
                stats["vuota"] += 1
                continue
            if value == wikidata.get(a["article"]):
                source, why = "wikidata", "uguale a Wikidata"
            else:
                if versions is None:
                    versions = history(f)
                if is_snippet(value):
                    source, why = "wikidata", "snippet"
                elif introduced_by_rewrite(versions, a["article"], value):
                    source, why = "openai", "riscritta"
                else:
                    source, why = "openai", "testo lungo"
            a["description_source"] = source
            key = f"{source} ({why})"
            stats[key] += 1
            if len(samples[key]) < args.samples and hash((f.stem, a["article"])) % 7 == 0:
                samples[key].append(f"{f.stem} {a['article']}: {value[:110]}")
        if not args.dry_run:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    for k, lst in samples.items():
        print(f"\n== {k}")
        for line in lst:
            print("  " + line)
    if args.dry_run:
        print("--dry-run: nessun file modificato.")


if __name__ == "__main__":
    main()
