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
It writes JSON to `json/YYYY-WW.json` by default (year-week), or CSV to
`weekly_data.csv`; pass `-o -` to print to stdout instead. Each article includes
a `description` pulled from the
MediaWiki `pageterms` API.
Image metadata (filename, thumbnail URL, and license info) is fetched from the
MediaWiki pageimages API and Commons, including the Commons file page URL.
Each article also includes `daily_views` (per-day view counts) and a
`google_news_url` plus a `pageviews_url` to inspect the week in Pageviews
Analysis.

Optional filters:

- `--exclude-stopwords` (or `--exclude-special-pages`) drops `Pagina_principale`, `load.php`,
  and titles starting with `Progetto:`, `Wikipedia:`, `Aiuto:`, `Speciale:`,
  `Special:`, `File:`, `Categoria:`.

## Render reports

```bash
python render_wikicode.py json/2026-01.json
python render_markdown.py json/2026-01.json
```

By default, the wikicode renderer writes to `wikicode/YYYY-WW.wiki` and the
Markdown renderer writes to `markdown/YYYY-WW.md`. The Markdown table includes
an image column using the Commons thumbnail URL and an inline SVG bar chart for
daily views. Use `-o -` to write to stdout.
