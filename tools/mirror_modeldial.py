#!/usr/bin/env python3
"""Archive the public ModelDial Radar page without changing source bytes.

Requests are replayed by their original URL in the Android container. This is
deliberately a dependency mirror, not a recursive mirror of other linked sites.
"""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import mimetypes
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'sites' / 'modeldial'
BASE = 'https://modeldial.com/'
ALLOWED = {'modeldial.com', 'www.modeldial.com', 'reference.modeldial.com',
           'raw.githubusercontent.com', 'alldonesites.com'}
EXTENSIONS = ('.js', '.css', '.json', '.svg', '.png', '.jpg', '.jpeg', '.webp',
              '.gif', '.woff', '.woff2', '.ttf', '.ico', '.map')
SEEDS = ['radar', 'en/radar', 'data/overview.json', 'data/traffic-counter.json',
         'api/v1/radar/latest.json', 'api/v1/radar/changes.json',
         'api/v1/radar/agent-profile.json', 'data/reference-snapshots/latest.json',
         'data/benchmark-snapshots/index.json', 'llms.txt', 'data-license',
         'https://reference.modeldial.com/model-display-names/current.json',
         'https://reference.modeldial.com/community/current.json',
         'https://raw.githubusercontent.com/ModelDialAI/.github/main/profile/README.md']
SEEDS += ['overview/' + name for name in (
    'styles-base.css', 'product-evaluations.css', 'styles-charts.css',
    'styles-content.css', 'styles-design.css', 'styles-design-radar.css',
    'styles-radar.css', 'styles-table.css', 'styles-boards.css')]


def normalize(url, base=BASE):
    url = html.unescape(url).replace('\\/', '/').strip()
    if '${' in url:
        return None
    if not url or url.startswith(('#', 'data:', 'javascript:', 'mailto:', 'tel:')):
        return None
    u = urlsplit(urljoin(base, url))
    if u.scheme not in ('http', 'https'):
        return None
    return urlunsplit((u.scheme, u.netloc.lower(), u.path or '/', u.query, ''))


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
        self.navigation = set()

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'a' and d.get('href'):
            self.navigation.add(d['href'])
        for key in ('src', 'poster'):
            if d.get(key):
                self.links.add(d[key])
        if tag == 'link' and d.get('href'):
            if d.get('rel', '') not in ('canonical', 'alternate'):
                self.links.add(d['href'])
        for item in d.get('srcset', '').split(','):
            if item.strip():
                self.links.add(item.strip().split()[0])


def discover(url, data, content_type):
    links, nav = set(), set()
    text = data.decode('utf-8', errors='replace')
    if 'html' in content_type:
        p = Resources()
        p.feed(text)
        links |= p.links
        nav |= p.navigation
    if any(t in content_type for t in ('javascript', 'css', 'json', 'html')):
        # Ordinary URL literals in scripts, CSS, and embedded serialized state.
        for value in re.findall(r'''["'`\s(](https?://[^\s<>"'`\\)]+)''', text):
            if urlsplit(value).path.lower().endswith(EXTENSIONS):
                links.add(value)
        for value in re.findall(r'''["'`](\/[^"'`\s<>\\]{1,240})["'`]''', text):
            if urlsplit(value).path.lower().endswith(EXTENSIONS):
                links.add(value)
        for value in re.findall(r'url\(\s*["\']?([^\s)"\']+)', text):
            links.add(value)
        # Turbopack chunk descriptors omit the /_next prefix.
        for value in re.findall(r'static/(?:chunks|media)/[A-Za-z0-9_./-]+\.(?:js|css|woff2?)', text):
            links.add('/_next/' + value)
        # Runtime brand lookup contains bare filenames and builds the prefix.
        if '/_next/static/chunks/' in url:
            for value in re.findall(r'''["']([A-Za-z0-9_-]+\.(?:svg|png|webp))["']''', text):
                if 'lobe' in value or 'official' in value or value == 'unknown-mark.svg':
                    links.add('/overview/assets/' + value)
    return {u for x in links if (u := normalize(x, url))}, \
           {u for x in nav if (u := normalize(x, url))}


def fetch(url):
    error = None
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=(15, 60), headers={
                'User-Agent': 'Mozilla/5.0 OfflinePagesArchive/1.0 (personal offline snapshot)',
                'Accept': '*/*',
            })
            if r.status_code >= 500 and attempt < 2:
                time.sleep(0.7 * (attempt + 1))
                continue
            return url, r
        except requests.RequestException as exc:
            error = str(exc)
            time.sleep(0.5)
    return url, error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true',
                        help='Fetch the website again instead of keeping a verified existing snapshot.')
    args = parser.parse_args()
    manifest_path = OUT / 'manifest.json'
    if not args.refresh and manifest_path.exists():
        try:
            cached = json.loads(manifest_path.read_text(encoding='utf-8'))
            cached_entries = cached['entries']
            valid = bool(cached_entries) and all(
                (OUT / e['path']).is_file() and
                hashlib.sha256((OUT / e['path']).read_bytes()).hexdigest() == e['sha256']
                for e in cached_entries)
            if valid:
                print(f"Keeping verified cached snapshot: {len(cached_entries)} resources. Use --refresh to fetch again.")
                return
        except (OSError, ValueError, KeyError):
            pass
    (OUT / 'files').mkdir(parents=True, exist_ok=True)
    pending = {normalize(u) for u in SEEDS}
    seen, entries, failures, navigation, discovered_external = set(), [], [], set(), set()
    while pending:
        batch = sorted(pending - seen)
        pending.clear()
        if not batch:
            break
        seen.update(batch)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for url, result in pool.map(fetch, batch):
                if isinstance(result, str):
                    failures.append({'url': url, 'error': result})
                    print('ERROR', url, result, flush=True)
                    continue
                r = result
                ct = r.headers.get('Content-Type', 'application/octet-stream')
                if r.status_code != 200:
                    failures.append({'url': url, 'status': r.status_code})
                    print(r.status_code, url, flush=True)
                    continue
                extension = mimetypes.guess_extension(ct.split(';')[0]) or '.bin'
                if len(extension) > 8:
                    extension = '.bin'
                local = 'files/' + hashlib.sha256(url.encode()).hexdigest()[:28] + extension
                (OUT / local).write_bytes(r.content)
                headers = {k: v for k, v in r.headers.items() if k.lower() in (
                    'content-type', 'access-control-allow-origin', 'cache-control',
                    'x-modeldial-publication', 'x-modeldial-seed', 'content-security-policy')}
                entries.append({'url': url, 'path': local, 'contentType': ct,
                                'status': 200, 'sha256': hashlib.sha256(r.content).hexdigest(),
                                'size': len(r.content), 'headers': headers})
                print('200', len(r.content), url, flush=True)
                links, nav = discover(url, r.content, ct)
                navigation |= nav
                # The public current community record may refer to an image.
                if url.endswith('/community/current.json'):
                    try:
                        def walk(value):
                            if isinstance(value, dict):
                                for v in value.values(): walk(v)
                            elif isinstance(value, list):
                                for v in value: walk(v)
                            elif isinstance(value, str) and value.startswith('/community/images/'):
                                links.add(normalize(value, url))
                        walk(r.json())
                    except ValueError:
                        pass
                for found in links:
                    if urlsplit(found).hostname in ALLOWED:
                        pending.add(found)
                    else:
                        discovered_external.add(found)
    entries.sort(key=lambda e: e['url'])
    manifest = {'schemaVersion': 1, 'siteId': 'modeldial',
                'entryUrl': BASE + 'radar', 'title': 'ModelDial 模型排行榜',
                'capturedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
                'scope': 'Radar page, Chinese and English, and its static/current-data dependencies',
                'entries': entries}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {'capturedCount': len(entries), 'capturedBytes': sum(e['size'] for e in entries),
              'failures': failures, 'excludedResourceUrls': sorted(discovered_external),
              'navigationLinksOutsideRadar': sorted(u for u in navigation if urlsplit(u).path not in ('/radar', '/en/radar')),
              'notes': ['Original response entity bytes are preserved; no HTML/JS/CSS rewriting.',
                        'Network telemetry is not required to view the saved rankings.',
                        'Non-Radar navigation, paid/model-check server actions, and live model execution are outside the requested scope.',
                        'The official GitHub organization publicly contains .github/open-source plans only; the website source was not found public.',
                        'Radar data is CC BY 4.0; page assets retain their original owners rights.']}
    (OUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SAVED', len(entries), report['capturedBytes'], 'bytes;', len(failures), 'failures')


if __name__ == '__main__':
    main()
