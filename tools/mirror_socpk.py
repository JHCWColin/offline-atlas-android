#!/usr/bin/env python3
"""Capture the public SOCPK site without rewriting any response body.

The Android container resolves original URLs through manifest.json. Run from
any directory: python tools/mirror_socpk.py [--refresh] [--workers 6].
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sites" / "socpk"
ORIGIN = "https://www.socpk.com"
HOSTS = {"www.socpk.com", "socpk.com"}
EXTENSIONS = r"(?:js|css|json|png|jpe?g|gif|webp|svg|ico|woff2?|ttf|otf|wasm|mp4|webm|csv|pdf)"
STATIC_REF = re.compile(r"(?:/assets/|assets/|\.{1,2}/)[\w./@-]+\." + EXTENSIONS + r"(?:\?[^\s\"'`<>)]*)?", re.I)
HTTP_REF = re.compile(r'''https?://[^\s"'`<>\\]+''')
LINK = re.compile(r'''(?:src|href|poster)\s*=\s*["']([^"']+)["']''', re.I)
CSS_URL = re.compile(r'''url\(\s*["']?([^\s'"\)]+)''', re.I)


def canonical(url: str, base: str = ORIGIN + "/") -> str | None:
    url = urllib.parse.urljoin(base, url)
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return None
    if p.hostname.lower() in HOSTS:
        return urllib.parse.urlunsplit(("https", "www.socpk.com", p.path or "/", p.query, ""))
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))


def local_path(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.hostname in HOSTS:
        name = p.path.strip("/") or "index.html"
        if not Path(name).suffix:
            name += ".json" if name.startswith("api/") else "/index.html"
        if p.query:
            a = Path(name)
            name = str(a.with_name(a.stem + "-q" + hashlib.sha256(p.query.encode()).hexdigest()[:12] + a.suffix))
        return "files/" + name.replace("\\", "/")
    suffix = Path(p.path).suffix or ".bin"
    return "files/external/" + p.netloc + "/" + hashlib.sha256(url.encode()).hexdigest() + suffix


def fetch(url: str, refresh: bool, existing: dict) -> tuple[dict, bytes | None]:
    rel = local_path(url)
    dest = OUT / rel
    old = existing.get(url)
    if not refresh and old and dest.exists():
        b = dest.read_bytes()
        if hashlib.sha256(b).hexdigest() == old.get("sha256"):
            return old, b
    error = ""
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SOCPK-OfflineSnapshot/1.0", "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=45) as response:
                b = response.read()
                content_type = response.headers.get("Content-Type", mimetypes.guess_type(dest.name)[0] or "application/octet-stream")
                entry = {"url": url, "path": rel, "contentType": content_type, "status": response.status,
                         "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b),
                         "finalUrl": response.url, "fetchedAt": datetime.now(timezone.utc).isoformat(),
                         "headers": {key: response.headers[key] for key in ("ETag", "Last-Modified", "Content-Security-Policy") if key in response.headers}}
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b)
                return entry, b
        except (OSError, urllib.error.URLError) as exc:
            error = str(exc)
            if attempt < 3:
                time.sleep(0.5 * (attempt + 1))
    return {"url": url, "path": rel, "status": 0, "error": error}, None


def json_strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from json_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from json_strings(item)
    elif isinstance(value, str):
        yield value


def discover(url: str, entry: dict, body: bytes) -> tuple[set[str], set[str]]:
    candidates = set()
    external = set()
    content_type = entry["contentType"]
    if not any(t in content_type for t in ("text/", "javascript", "json", "svg")):
        return candidates, external
    text = body.decode("utf-8", errors="replace")
    raw = set()
    if "html" in content_type:
        raw.update(LINK.findall(text))
    if "css" in content_type or "html" in content_type:
        raw.update(CSS_URL.findall(text))
    if "json" in content_type:
        try:
            raw.update(json_strings(json.loads(body)))
        except (ValueError, UnicodeDecodeError):
            pass
    else:
        # Search paths independently of JavaScript quote tokens: regular
        # expressions and translated strings may themselves contain quotes.
        raw.update(STATIC_REF.findall(text))
        raw.update(HTTP_REF.findall(text))
    for value in raw:
        if "${" in value or value.startswith(("data:", "blob:", "#")):
            continue
        # Vite's __vite__mapDeps table contains app-root-relative "assets/..."
        # strings, even though the table itself lives in /assets/index-*.js.
        target = canonical("/" + value if value.startswith("assets/") else value, url)
        if not target:
            continue
        parts = urllib.parse.urlsplit(target)
        is_site = parts.hostname in HOSTS
        is_asset = re.search(r"\." + EXTENSIONS + r"$", parts.path, re.I)
        if is_site and (parts.path.startswith("/assets/") or is_asset):
            candidates.add(target)
        elif not is_site:
            external.add(target)
            if is_asset:
                candidates.add(target)
    return candidates, external


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refetch already captured bytes")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    existing = {}
    if (OUT / "manifest.json").exists():
        existing = {e["url"]: e for e in json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["entries"]}
    # ChartPage computes these watermark names from two themes and the chart
    # category at runtime; no complete filename occurs in the compiled bundle.
    computed_assets = [ORIGIN + f"/assets/logos/{brand}-wm-{theme}.png"
                       for brand in ("bbpcslogo", "gkwlogo") for theme in ("dark", "light")]
    pending = deque([ORIGIN + "/", ORIGIN + "/api/site", ORIGIN + "/api/chips", *computed_assets])
    seen = set(pending)
    entries = {}
    failures = {}
    external_links = set()
    categories, pages, chips = [], [], []
    data_versions = {}
    while pending:
        batch = [pending.popleft() for _ in range(min(args.workers, len(pending)))]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for url, (entry, body) in zip(batch, pool.map(lambda u: fetch(u, args.refresh, existing), batch)):
                if body is None:
                    failures[url] = entry
                    print("FAILED", url, entry["error"], flush=True)
                    continue
                entries[url] = entry
                print(entry["status"], entry["bytes"], url, flush=True)
                discovered, external = discover(url, entry, body)
                external_links.update(external)
                if url == ORIGIN + "/api/site":
                    site = json.loads(body)
                    categories = [c["key"] for c in site.get("categories", [])]
                    pages = [p["slug"] for c in site.get("categories", []) for p in c.get("pages", [])]
                    for slug in pages:
                        discovered.add(ORIGIN + "/api/pages/" + slug)
                        discovered.add(ORIGIN + "/api/pages/" + slug + "/data")
                elif url == ORIGIN + "/api/chips":
                    data = json.loads(body)
                    chips = [str(c["id"]) for b in data.get("brands", []) for c in b.get("chips", [])]
                elif url.startswith(ORIGIN + "/api/pages/"):
                    data_versions[url] = json.loads(body).get("dataVersion")
                for found in sorted(discovered):
                    if found not in seen:
                        seen.add(found)
                        pending.append(found)
        # Persist after each batch so an interrupted mirror can resume.
        manifest = {"siteId": "socpk", "title": "SOCPK", "entryUrl": ORIGIN + "/",
                    "capturedAt": datetime.now(timezone.utc).isoformat(), "hostAliases": sorted(HOSTS),
                    "spaFallback": "files/index.html", "ignoreCacheBustQuery": True,
                    "spaRoutes": ["/", "/category/", "/chart/", "/chips", "/admin"],
                    "entries": [entries[k] for k in sorted(entries)]}
        (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit = {"siteId": "socpk", "capturedAt": datetime.now(timezone.utc).isoformat(),
             "entryCount": len(entries), "totalBytes": sum(e["bytes"] for e in entries.values()),
             "categories": categories, "chartSlugs": pages, "chipIds": chips,
             "dataVersionMismatches": [slug for slug in pages if data_versions.get(ORIGIN + "/api/pages/" + slug) != data_versions.get(ORIGIN + "/api/pages/" + slug + "/data")],
             "failed": list(failures.values()), "externalLinks": sorted(external_links),
             "scope": "All public /api/site chart metadata/data, /api/chips, and recursively referenced static runtime assets; original response bodies are unchanged.",
             "unavailableOffline": ["Authenticated administration and write operations (feedback, uploads, edits)",
                                    "Third-party linked websites/videos are external destinations, not part of the SOCPK origin snapshot; see externalLinks."],
             "compatibility": "Original Vite/Vue ES modules use optional chaining, nullish coalescing, Unicode-property RegExp and WebAssembly; original Android 8.1 WebView is too old. Use bundled modern GeckoView without rewriting site code."}
    (OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"entries": len(entries), "bytes": audit["totalBytes"], "charts": len(pages), "chips": len(chips), "failures": len(failures)}, ensure_ascii=False), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
