#!/usr/bin/env python3
"""Verify byte-preserved website mirrors and report static URL coverage.

This is deliberately a static audit, not a claim that every runtime-generated URL
has been exercised. Run the APK without network and inspect its missing-URL log as
well. The input manifest may be a list, or contain resources/entries/files lists.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import zipfile
from urllib.parse import unquote, urldefrag, urljoin, urlsplit, urlunsplit


IGNORED_SCHEMES = {"data", "blob", "javascript", "mailto", "tel", "about"}
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
CSS_IMPORT = re.compile(r"@import\s+['\"]([^'\"]+)['\"]", re.I)
JS_IMPORT = re.compile(r"(?:\bfrom\s*|\bimport\s*\(?|\brequire\s*\()\s*['\"]([^'\"]+)['\"]")
JS_ABSOLUTE = re.compile(r"['\"]((?:https?:)?//[^\s'\"<>]+)['\"]")
JS_ASSET = re.compile(r"['\"]((?:\.?\.?/|/)[^\s'\"<>]+\.(?:js|mjs|css|json|wasm|png|jpe?g|webp|gif|svg|woff2?|ttf|otf|ico|mp4|webm|mp3|ogg|pdf)(?:\?[^'\"]*)?)['\"]", re.I)


def canonical(url: str) -> str:
    parts = urlsplit(urldefrag(html.unescape(url))[0])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


class HTMLReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.base: str | None = None
        self.refs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "base" and values.get("href"):
            self.base = values["href"]
        for key in ("src", "poster", "data", "background"):
            value = values.get(key)
            if value:
                self.refs.append(("runtime", value))
        if values.get("href") and tag != "base":
            kind = "navigation" if tag in ("a", "area") else "runtime"
            if tag == "link" and values.get("rel", "").lower() in {"preconnect", "dns-prefetch", "canonical", "alternate"}:
                kind = "metadata"
            self.refs.append((kind, values["href"]))
        if values.get("srcset"):
            # data: URL candidates may contain commas; those are intentionally skipped.
            if not values["srcset"].lstrip().startswith("data:"):
                for candidate in values["srcset"].split(","):
                    if candidate.split():
                        self.refs.append(("runtime", candidate.split()[0]))
        if values.get("style"):
            self.refs.extend(("runtime", match[1]) for match in CSS_URL.findall(values["style"]))
        if tag == "form" and values.get("action"):
            self.refs.append(("navigation", values["action"]))


def manifest_entries(data: object) -> list[dict]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object or list")
    for field in ("resources", "entries", "files", "urls"):
        value = data.get(field)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [dict(item, url=url) if isinstance(item, dict) else {"url": url, "path": item}
                    for url, item in value.items()]
    raise ValueError("manifest has no resources/entries/files/urls collection")


def static_refs(text: str, mime: str, path: Path) -> tuple[str | None, list[tuple[str, str]]]:
    refs: list[tuple[str, str]] = []
    base = None
    is_html = "html" in mime or path.suffix.lower() in (".html", ".htm")
    is_css = "css" in mime or path.suffix.lower() == ".css"
    is_js = "javascript" in mime or path.suffix.lower() in (".js", ".mjs")
    if is_html:
        parser = HTMLReferences()
        parser.feed(text)
        refs.extend(parser.refs)
        base = parser.base
    if is_css or is_html:
        refs.extend(("runtime", match[1]) for match in CSS_URL.findall(text))
        refs.extend(("runtime", value) for value in CSS_IMPORT.findall(text))
    if is_js or is_html:
        refs.extend(("runtime", value) for value in JS_IMPORT.findall(text)
                    if value.startswith(("/", "./", "../", "http:", "https:")))
        refs.extend(("candidate", value) for value in JS_ABSOLUTE.findall(text))
        refs.extend(("candidate", value) for value in JS_ASSET.findall(text))
    return base, refs


def audit(manifest: Path) -> dict:
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    entries = manifest_entries(data)
    root = manifest.parent.resolve()
    errors: list[dict] = []
    sources: list[tuple[dict, Path]] = []
    available: set[str] = set()
    total_bytes = 0
    unique_paths: set[Path] = set()
    aliases = data.get("aliases", {}) if isinstance(data, dict) else {}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append({"error": "invalid entry", "entry": str(entry)})
            continue
        url = entry.get("url", "")
        relative = entry.get("path") or entry.get("localPath") or entry.get("file")
        if not url or not relative:
            errors.append({"error": "entry lacks url/path", "entry": entry})
            continue
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            errors.append({"error": "path escapes site directory", "url": url, "path": str(path)})
            continue
        if not path.is_file():
            errors.append({"error": "missing file", "url": url, "path": relative})
            continue
        content = path.read_bytes()
        expected = entry.get("sha256")
        actual = hashlib.sha256(content).hexdigest()
        if expected and actual != expected:
            errors.append({"error": "sha256 mismatch", "url": url, "path": relative, "expected": expected, "actual": actual})
        if path not in unique_paths:
            total_bytes += len(content)
            unique_paths.add(path)
        status = entry.get("status", entry.get("statusCode", 200))
        if isinstance(status, int) and status >= 400:
            errors.append({"error": "recorded HTTP failure", "url": url, "status": status})
        available.add(canonical(url))
        for alias in entry.get("aliases", []):
            available.add(canonical(alias))
        sources.append((entry, path))
    if isinstance(aliases, dict):
        for url, target in aliases.items():
            if isinstance(target, str) and (canonical(target) in available or (root / target).is_file()):
                available.add(canonical(url))
    missing: dict[tuple[str, str], dict] = {}
    covered: set[str] = set()
    for entry, path in sources:
        mime = entry.get("contentType", entry.get("mimeType", entry.get("mime", "")))
        if not any(value in mime for value in ("text/", "javascript", "json")) and path.suffix.lower() not in (".html", ".htm", ".js", ".mjs", ".css"):
            continue
        body = path.read_text(encoding="utf-8-sig", errors="replace")
        base, refs = static_refs(body, mime, path)
        source_url = entry["url"]
        base_url = urljoin(source_url, base) if base else source_url
        for kind, value in refs:
            value = value.strip().replace("\\/", "/")
            if not value or value.startswith("#") or urlsplit(value).scheme.lower() in IGNORED_SCHEMES:
                continue
            # Template expressions, regex fragments and interpolation are not concrete URLs.
            if any(token in value for token in ("${", "{{", "}}", "<%", "\\")):
                continue
            target = canonical(urljoin(base_url, value))
            if urlsplit(target).scheme not in ("http", "https"):
                continue
            if target in available:
                covered.add(target)
            else:
                key = (kind, target)
                item = missing.setdefault(key, {"kind": kind, "url": target, "sources": []})
                if source_url not in item["sources"] and len(item["sources"]) < 5:
                    item["sources"].append(source_url)
    missing_list = sorted(missing.values(), key=lambda item: (item["kind"], item["url"]))
    return {"site": root.name, "manifest": str(manifest), "entries": len(entries),
            "uniqueFiles": len(unique_paths), "bytes": total_bytes, "coveredStaticUrls": len(covered),
            "errors": errors, "missingRuntime": [item for item in missing_list if item["kind"] == "runtime"],
            "missingNavigation": [item for item in missing_list if item["kind"] == "navigation"],
            "unresolvedCandidates": [item for item in missing_list if item["kind"] == "candidate"],
            "unmirroredMetadata": [item for item in missing_list if item["kind"] == "metadata"],
            "limitation": "Static references only; exercise dynamic URLs in the offline APK and inspect its request log."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="*", type=Path)
    parser.add_argument("--output", type=Path, help="Write detailed JSON report")
    parser.add_argument("--strict", action="store_true", help="Also fail for uncovered concrete HTML/CSS/import runtime URLs")
    parser.add_argument("--apk", type=Path, help="Also verify the mirrored bytes inside this built APK")
    args = parser.parse_args()
    manifests = args.manifests or sorted((Path(__file__).resolve().parents[1] / "sites").glob("*/manifest.json"))
    reports = []
    for manifest in manifests:
        try:
            report = audit(manifest)
        except Exception as exc:
            report = {"manifest": str(manifest), "errors": [{"error": str(exc)}], "missingRuntime": []}
        reports.append(report)
        print(f"{report.get('site', manifest.parent.name)}: {report.get('entries', 0)} URLs, "
              f"{report.get('uniqueFiles', 0)} files, {report.get('bytes', 0):,} bytes; "
              f"{len(report['errors'])} integrity errors, {len(report['missingRuntime'])} uncovered runtime URLs, "
              f"{len(report.get('missingNavigation', []))} external/uncovered navigation URLs, "
              f"{len(report.get('unresolvedCandidates', []))} JS URL candidates")
    if args.apk:
        try:
            with zipfile.ZipFile(args.apk) as apk:
                for manifest, report in zip(manifests, reports):
                    checked = 0
                    for entry in manifest_entries(json.loads(manifest.read_text(encoding="utf-8-sig"))):
                        relative = entry.get("path") or entry.get("localPath") or entry.get("file")
                        if not relative:
                            continue
                        member = f"assets/sites/{manifest.parent.name}/{relative}".replace("\\", "/")
                        try:
                            actual = hashlib.sha256(apk.read(member)).hexdigest()
                            expected = entry.get("sha256") or hashlib.sha256((manifest.parent / relative).read_bytes()).hexdigest()
                            if actual != expected:
                                report["errors"].append({"error": "APK byte mismatch", "member": member})
                            checked += 1
                        except KeyError:
                            report["errors"].append({"error": "missing APK asset", "member": member})
                    report["apkCheckedEntries"] = checked
                    print(f"{manifest.parent.name}: verified {checked} mirrored entries inside {args.apk.name}")
        except Exception as exc:
            print(f"APK verification failed: {exc}", file=sys.stderr)
            return 2
    if not manifests:
        print("No manifests found", file=sys.stderr)
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"sites": reports}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(report["errors"] or (args.strict and report["missingRuntime"]) for report in reports))


if __name__ == "__main__":
    raise SystemExit(main())
