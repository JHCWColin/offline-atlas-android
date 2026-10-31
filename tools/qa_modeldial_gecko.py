#!/usr/bin/env python3
"""Test the actual offline routing WebExtension in installed desktop Firefox.

Requires requests, Firefox and Mozilla geckodriver. All non-loopback network
traffic is deliberately sent to an unavailable proxy. No online fallback.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, urlunsplit
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--driver', type=Path, default=ROOT / 'tools/.cache/geckodriver.exe')
    p.add_argument('--firefox', default=r'C:\Program Files\Mozilla Firefox\firefox.exe')
    args = p.parse_args()
    if not args.driver.exists():
        p.error('Install geckodriver from https://github.com/mozilla/geckodriver/releases and pass --driver.')
    qa = ROOT / 'qa'
    qa.mkdir(exist_ok=True)
    folder = ROOT / 'sites/modeldial'
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    exact = {e['url']: e for e in manifest['entries']}
    def no_query(url):
        u = urlsplit(url)
        return urlunsplit((u.scheme, u.netloc, u.path, '', ''))
    paths = {no_query(e['url']): e for e in manifest['entries']}
    logs, missing = [], []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            logs.append(self.path)
            remote = self.path[9:].replace('/', '://', 1) if self.path.startswith('/_remote/') else 'https://modeldial.com' + self.path
            resource = exact.get(remote) or paths.get(no_query(remote))
            if resource:
                data = (folder / resource['path']).read_bytes()
                code, mime = 200, resource['contentType']
            else:
                missing.append(remote)
                data, code, mime = b'Offline URL not captured', 404, 'text/plain'
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
        def do_POST(self):
            self.send_response(200 if self.path == '/api/metrics/page-view' else 405)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{}')

    server = ThreadingHTTPServer(('127.0.0.1', 18082), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    addon = qa / 'offline-routing-test.xpi'
    with zipfile.ZipFile(addon, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in (ROOT / 'app/src/main/assets/bridge').iterdir():
            if f.is_file(): z.write(f, f.name)
    log = (qa / 'geckodriver.log').open('w', encoding='utf-8')
    process = subprocess.Popen([str(args.driver), '--port', '19444', '--log', 'warn'],
                               stdout=log, stderr=log,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    base = 'http://127.0.0.1:19444'
    sid = None
    client = requests.Session()
    client.trust_env = False
    def call(method, endpoint, body=None):
        r = client.request(method, base + endpoint, json=body, timeout=65)
        data = r.json()
        if r.status_code >= 400: raise RuntimeError(data)
        return data.get('value')
    try:
        for _ in range(100):
            try:
                client.get(base + '/status', timeout=0.3)
                break
            except requests.RequestException: time.sleep(0.1)
        caps = call('POST', '/session', {'capabilities': {'alwaysMatch': {
            'browserName': 'firefox', 'moz:firefoxOptions': {
                'binary': args.firefox, 'args': ['-headless', '-no-remote', '-new-instance'], 'prefs': {
                    'network.proxy.type': 1, 'network.proxy.http': '127.0.0.1',
                    'network.proxy.http_port': 9, 'network.proxy.ssl': '127.0.0.1',
                    'network.proxy.ssl_port': 9, 'network.proxy.no_proxies_on': '127.0.0.1,localhost',
                    'network.proxy.allow_hijacking_localhost': False,
                    'browser.shell.checkDefaultBrowser': False,
                }}}}})
        sid = caps['sessionId']
        endpoint = '/session/' + sid
        call('POST', endpoint + '/moz/addon/install', {'path': str(addon.resolve()), 'temporary': True})
        call('POST', endpoint + '/window/rect', {'width': 1280, 'height': 800})
        call('POST', endpoint + '/url', {'url': 'http://127.0.0.1:18082/radar'})
        def js(source): return call('POST', endpoint + '/execute/sync', {'script': source, 'args': []})
        time.sleep(2)
        initial = js('return {title:document.title, length:document.body.innerText.length, axes:[...document.querySelectorAll("[data-action=axis]")].map(x=>x.textContent.trim())}')
        interactions = []
        for i, name in enumerate(initial['axes']):
            js(f'document.querySelectorAll("[data-action=axis]")[{i}].click()')
            time.sleep(.35)
            interactions.append({'axis': name, **js('return {url:location.href,length:document.body.innerText.length}')})
        screenshot = call('GET', endpoint + '/screenshot')
        (qa / 'modeldial-firefox.png').write_bytes(base64.b64decode(screenshot))
        cross_origin = call('POST', endpoint + '/execute/async', {'script': '''
            const done=arguments[arguments.length-1];
            Promise.all([
              fetch('https://reference.modeldial.com/model-display-names/current.json').then(r=>r.json()),
              fetch('https://reference.modeldial.com/community/current.json').then(r=>r.json())
            ]).then(data=>done({ok:true,data})).catch(e=>done({ok:false,error:String(e)}));''', 'args': []})
        remote_hits = sorted(set(p for p in logs if p.startswith('/_remote/')))
        result = {'engine': caps['capabilities']['browserVersion'], 'initial': initial,
                  'interactions': interactions, 'crossOriginFetch': cross_origin,
                  'actualExtensionRedirects': remote_hits, 'missing': sorted(set(missing)),
                  'externalNetworkBlockedByProxy': True,
                  'passed': not missing and len(interactions) == 6 and cross_origin.get('ok') is True and
                      any('model-display-names/current.json' in p for p in remote_hits) and
                      any('community/current.json' in p for p in remote_hits)}
        (qa / 'modeldial-firefox.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result['passed'] else 1
    finally:
        if sid:
            try: call('DELETE', '/session/' + sid)
            except Exception: pass
        process.terminate()
        log.close()
        server.shutdown()
        server.server_close()
        addon.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
