# it-wiki-top25-weekly

Python 3 scripts to extract the most viewed pages during a week and render reports.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Fetch weekly data

```bash
python wiki-get-top-weekly-pages.py --exclude-stopwords --format json --top 30 --year 2026 --week 1
```

The REST API script aggregates daily top-1000 lists into a weekly ranking.
It writes JSON to `docs/json/YYYY-WW.json` by default (year-week), or CSV to
`weekly_data.csv`; pass `-o -` to print to stdout instead. You can choose a
different JSON folder with `--json-dir`. Each article includes a `description`
pulled from the
MediaWiki `pageterms` API.
Image metadata (filename, thumbnail URL, and license info) is fetched from the
MediaWiki pageimages API and Commons, including the Commons file page URL.
Each article also includes `daily_views` (per-day view counts) and a
`google_news_url` plus a `pageviews_url` to inspect the week in Pageviews
Analysis.

When `--format json` is used, the script writes two JSON outputs:
- `docs/rawjson/YYYY-WW.json` (full sorted weekly ranking, no enrichment, no top limit)
- `docs/json/YYYY-WW.json` (enriched output, limited by `--top/--limit`)

You can change these directories with `--raw-json-dir` and `--json-dir`.

Optional filters:

- `--exclude-stopwords` (or `--exclude-special-pages`) drops `Pagina_principale`, `load.php`,
  and titles starting with `Progetto:`, `Wikipedia:`, `Aiuto:`, `Speciale:`,
  `Special:`, `File:`, `Categoria:`.

## Render reports

```bash
python render_wikicode.py docs/json/2026-01.json
python render_markdown.py docs/json/2026-01.json
python render_html.py
```

## Backfill storico

Per eseguire automaticamente tutte le settimane a ritroso (dalla settimana corrente fino al 2010):

```bash
python backfill_weeks.py
```

Opzioni utili:
- `--start-year` e `--start-week` per partire da una settimana specifica
- `--top 25` per cambiare il limite articoli
- `--dry-run` per vedere i comandi senza eseguirli
- salta automaticamente le settimane già presenti in `docs/json`
- `--force-rewrite` per rieseguire anche le settimane già presenti

By default, the wikicode renderer writes to `wikicode/YYYY-WW.wiki` and the
Markdown renderer writes to `markdown/YYYY-WW.md`. The Markdown table includes
an image column using the Commons thumbnail URL and an inline SVG bar chart for
daily views. Use `-o -` to write to stdout.

The HTML renderer builds a dynamic docs site:
- `docs/week.html` (single dynamic page reading JSON data)
- `docs/index.html` (redirects to latest available week)
- `docs/weeks.json` (list of available weeks)
- `docs/json/YYYY-WW.json` (weekly JSON data read directly by `week.html`)

The HTML page includes:
- title links to article pages
- inline SVG mini bar-chart (daily views with tooltip date+views)
- 60x60 cropped image and copyright below the thumbnail
- repeated week header (top and bottom) with links to previous/next week and
  same week in previous years

If you update a `docs/json/YYYY-WW.json` file, `week.html` reflects changes
automatically on reload.
