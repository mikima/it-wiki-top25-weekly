#!/usr/bin/env python3
"""Local visual editor for the weekly JSON files.

    python3 editor.py            # then open http://localhost:8766

Edit descriptions (saved as description_source "manual", so OpenAI never
rewrites them), image framing (image_focus; for the large views image_crop,
0 = full height .. 100 = full width, with image_aspect) and add or replace
images from Wikimedia Commons (image_source "manual", with license data).
Only for local use: it writes docs/json/YYYY-WW.json directly.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
JSON_DIR = ROOT / "docs" / "json"
STATIC_DIR = ROOT / "editor"
CONTEXT_DIR = ROOT / "context"
WEEK_RE = re.compile(r"^\d{4}-\d{2}$")
FITS = {"cover", "width", "height"}
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "it-wiki-top25-weekly editor (User:Mikima)"
IMAGE_FIELDS = (
    "image_filename", "image_url", "image_commons_url", "image_license",
    "image_license_url", "image_copyrighted", "image_artist", "image_source",
)


def strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def commons_filename(raw: str) -> str:
    """Accept a Commons/Wikipedia file page URL, an upload.wikimedia.org URL or a file name."""
    text = unquote(raw.strip())
    if "upload.wikimedia.org" in text:
        parts = urlparse(text).path.split("/")
        if "thumb" in parts:  # .../thumb/a/ab/Name.jpg/1280px-Name.jpg
            name = parts[parts.index("thumb") + 3]
        else:
            name = parts[-1]
    else:
        if "://" in text:
            parsed = urlparse(text)
            query = parse_qs(parsed.query)
            text = query.get("title", [parsed.path.rsplit("/", 1)[-1]])[0]
        name = re.sub(r"^(?:File|Image|Immagine|Archivo|Datei|Fichier):", "", text.split("#")[0], flags=re.I)
    return name.replace(" ", "_").strip("_")


def commons_info(raw: str) -> dict:
    name = commons_filename(raw)
    if not name or "." not in name:
        raise ValueError("Non riconosco un nome di file. Incolla il link alla pagina del file su Commons.")
    params = {
        "action": "query", "format": "json", "formatversion": "2",
        "titles": "File:" + name, "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": "1280",
    }
    req = Request(COMMONS_API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    page = (payload.get("query", {}).get("pages") or [{}])[0]
    info = (page.get("imageinfo") or [None])[0]
    if page.get("missing") or not info:
        raise ValueError(f"Il file {name} non esiste su Wikimedia Commons.")
    meta = {k: (v or {}).get("value", "") for k, v in (info.get("extmetadata") or {}).items()}
    license_short = strip_html(meta.get("LicenseShortName", ""))
    non_free = str(meta.get("NonFree", "")).lower() == "true"
    restrictions = strip_html(meta.get("Restrictions", ""))
    usage_terms = strip_html(meta.get("UsageTerms", ""))
    lic = (license_short + " " + usage_terms).lower()
    warnings = []
    if non_free:
        warnings.append("Commons la segnala come non libera.")
    if not license_short:
        warnings.append("Licenza non indicata nei metadati: controlla la pagina del file.")
    if re.search(r"\bnc\b|non.?commercial", lic):
        warnings.append("Licenza non commerciale.")
    if re.search(r"\bnd\b|no.?deriv", lic):
        warnings.append("Licenza senza opere derivate: il ritaglio potrebbe non essere ammesso.")
    notes = []
    for r in [x.strip() for x in re.split(r"[|,]", restrictions) if x.strip()]:
        if r.lower() == "trademarked":
            notes.append("Marchio registrato: la licenza riguarda l'immagine, non il marchio. Va bene per illustrare la voce.")
        elif r.lower() == "personality":
            notes.append("Persona riconoscibile: valgono i diritti della personalità (va bene per illustrare la voce).")
        else:
            warnings.append("Restrizione: " + r)
    if not str(info.get("mime", "")).startswith("image/"):
        warnings.append("Non è un'immagine.")
    title = page.get("title", "File:" + name)
    filename = title.split(":", 1)[1].replace(" ", "_")
    return {
        "image_filename": filename,
        "image_url": (info.get("thumburl") or info.get("url", "")).split("?")[0],
        "image_commons_url": "https://commons.wikimedia.org/wiki/File:" + quote(filename, safe="_.-()"),
        "image_license": license_short,
        "image_license_url": meta.get("LicenseUrl", ""),
        "image_copyrighted": str(meta.get("Copyrighted", "")),
        "image_artist": strip_html(meta.get("Artist", ""))[:200],
        "image_source": "manual",
        "attribution_required": str(meta.get("AttributionRequired", "")).lower() == "true",
        "credit": strip_html(meta.get("Credit", ""))[:200],
        "width": info.get("width"),
        "height": info.get("height"),
        "free": not non_free and bool(license_short) and not warnings,
        "warnings": warnings,
        "notes": notes,
    }


def week_path(week_id: str) -> Path:
    if not WEEK_RE.match(week_id):
        raise ValueError("settimana non valida")
    return JSON_DIR / f"{week_id}.json"


def write_json_atomic(path: Path, data: dict) -> None:
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    json.loads(encoded)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(encoded + "\n", encoding="utf-8")
    os.replace(tmp, path)


def apply_changes(data: dict, changes: list) -> int:
    by_article = {a.get("article"): a for a in data.get("articles", []) if isinstance(a, dict)}
    applied = 0
    for change in changes:
        item = by_article.get(change.get("article"))
        if item is None:
            continue
        if "description" in change:
            text = re.sub(r"\s+", " ", str(change["description"])).strip()
            if text != item.get("description", ""):
                item["description"] = text
                item["description_source"] = "manual"
                item.pop("description_model", None)
                applied += 1
        if "image_focus" in change:
            focus = change["image_focus"]
            if focus is None:
                item.pop("image_focus", None)
            else:
                item["image_focus"] = {
                    "x": max(0, min(100, round(float(focus["x"])))),
                    "y": max(0, min(100, round(float(focus["y"])))),
                }
            applied += 1
        if "image" in change:
            image = change["image"] or {}
            for key in IMAGE_FIELDS:
                if image.get(key):
                    item[key] = image[key]
                elif key in ("image_license_url", "image_artist", "image_source"):
                    item.pop(key, None)  # optional fields
                else:
                    item[key] = ""  # fields every article has
            # a new image starts from the default framing
            for key in ("image_focus", "image_fit", "image_crop", "image_aspect"):
                item.pop(key, None)
            applied += 1
        if "image_fit" in change:
            fit = change["image_fit"]
            if fit in (None, "cover"):
                item.pop("image_fit", None)
            elif fit in FITS:
                item["image_fit"] = fit
            applied += 1
        if "image_crop" in change:
            crop = change["image_crop"]
            if crop is None:
                item.pop("image_crop", None)
                item.pop("image_aspect", None)
            else:
                item["image_crop"] = max(0, min(100, round(float(crop))))
                aspect = change.get("image_aspect") or item.get("image_aspect")
                if aspect:
                    item["image_aspect"] = round(float(aspect), 4)
                item.pop("image_fit", None)  # the percentage replaces the old fit modes
            applied += 1
    return applied


class Handler(BaseHTTPRequestHandler):
    server_version = "Top25Editor/1.0"

    def log_message(self, fmt: str, *args) -> None:  # quieter log
        print("  " + fmt % args)

    def send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/weeks":
            weeks = sorted(p.stem for p in JSON_DIR.glob("*.json") if WEEK_RE.match(p.stem))
            return self.send_json({"weeks": weeks})
        if path == "/api/commons":
            raw = parse_qs(urlparse(self.path).query).get("file", [""])[0]
            try:
                return self.send_json(commons_info(raw))
            except ValueError as exc:
                return self.send_json({"error": str(exc)}, 400)
            except OSError as exc:
                return self.send_json({"error": f"Commons non raggiungibile: {exc}"}, 502)
        if path.startswith("/api/context/"):
            week_id = path.rsplit("/", 1)[1]
            if not WEEK_RE.match(week_id):
                return self.send_json({"error": "settimana non valida"}, 400)
            file = CONTEXT_DIR / f"{week_id}.json"
            data = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {"articles": {}}
            return self.send_json(data)
        if path.startswith("/api/week/"):
            try:
                file = week_path(path.rsplit("/", 1)[1])
            except ValueError as exc:
                return self.send_json({"error": str(exc)}, 400)
            if not file.exists():
                return self.send_json({"error": "settimana non trovata"}, 404)
            return self.send_json({
                "data": json.loads(file.read_text(encoding="utf-8")),
                "mtime": str(file.stat().st_mtime_ns),
            })
        # static files
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        file = (STATIC_DIR / rel).resolve()
        if STATIC_DIR not in file.parents or not file.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/week/"):
            return self.send_json({"error": "not found"}, 404)
        try:
            file = week_path(path.rsplit("/", 1)[1])
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error": str(exc)}, 400)
        if not file.exists():
            return self.send_json({"error": "settimana non trovata"}, 404)
        if str(body.get("mtime")) != str(file.stat().st_mtime_ns) and not body.get("force"):
            return self.send_json({
                "error": "Il file è stato modificato da un altro programma dopo l'apertura. "
                         "Ricarica la settimana (le modifiche non salvate andranno perse) "
                         "oppure salva comunque sovrascrivendo."
            }, 409)
        data = json.loads(file.read_text(encoding="utf-8"))
        applied = apply_changes(data, body.get("changes", []))
        write_json_atomic(file, data)
        return self.send_json({"ok": True, "applied": applied, "mtime": str(file.stat().st_mtime_ns), "data": data})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--json-dir", type=Path, help="Weekly JSON folder (default docs/json)")
    ap.add_argument("--context-dir", type=Path, help="Context folder (default context)")
    args = ap.parse_args()
    global JSON_DIR, CONTEXT_DIR
    if args.json_dir:
        JSON_DIR = args.json_dir.resolve()
    if args.context_dir:
        CONTEXT_DIR = args.context_dir.resolve()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Editor su http://localhost:{args.port}  (Ctrl+C per chiudere)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
