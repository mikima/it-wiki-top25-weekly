# it-wiki-top25-weekly

Python 3 script to extract the most viewed pages during a week. The script can output the data as CSV, JSON or as formatted wikicode.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python wiki-get-top-weekly-pages.py --year 2026 --week 1 --format wikicode
```

## Usage (REST API version)

```bash
python get-top-weekly-pages-new.py --year 2026 --week 4 --format json
```

The REST API script aggregates daily top-1000 lists into a weekly ranking.
It writes to `weekly_data.json` or `weekly_data.csv` by default; pass `-o -` to
print to stdout instead. Each article includes a `description` pulled from the
MediaWiki `pageterms` API.
Image metadata (filename, thumbnail URL, and license info) is fetched from the
MediaWiki pageimages API and Commons, including the Commons file page URL.
Each article also includes `daily_views` (per-day view counts) and a
`google_news_url` for the same date range.

Optional filters:
- `--exclude-stopwords` (or `--exclude-special-pages`) drops `Pagina_principale`, `load.php`,
  and titles starting with `Progetto:`, `Wikipedia:`, `Aiuto:`, `Speciale:`,
  `Special:`, `File:`, `Categoria:`.
