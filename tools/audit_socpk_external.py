#!/usr/bin/env python3
"""Inspect linked Bilibili video metadata; does not download video streams.

This keeps an honest, reproducible inventory of the third-party content linked
by the SOCPK data, including duration and accessible public metadata responses.
"""
from __future__ import annotations

import concurrent.futures
import gzip
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "sites" / "socpk"


def inspect_video(item):
    bvid, links = item
    url = "https://api.bilibili.com/x/web-interface/view?bvid=" + bvid
    raw_file = SITE / "linked-video-metadata" / (bvid + ".json")
    try:
        if raw_file.exists():
            body = raw_file.read_bytes()
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/", "Accept-Encoding": "identity"})
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_bytes(body)
        parsed = json.loads(body)
        data = parsed.get("data") or {}
        return {"bvid": bvid, "links": sorted(links), "apiUrl": url,
                "metadataPath": raw_file.relative_to(SITE).as_posix(),
                "apiCode": parsed.get("code"), "title": data.get("title"),
                "durationSeconds": data.get("duration"), "pages": data.get("pages", []),
                "downloadFlag": data.get("rights", {}).get("download"),
                "videoStreamCaptured": False}
    except Exception as error:
        return {"bvid": bvid, "links": sorted(links), "apiUrl": url, "error": str(error), "videoStreamCaptured": False}


def main():
    links = {}
    for file in (SITE / "files" / "api").rglob("*.json"):
        text = file.read_text(encoding="utf-8")
        for url in re.findall(r'https?://[^\s"\\]+', text):
            match = re.search(r"bilibili\.com/video/(BV\w+)", url)
            if match:
                links.setdefault(match.group(1), set()).add(url)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        items = list(pool.map(inspect_video, sorted(links.items())))
    summary = {"capturedAt": datetime.now(timezone.utc).isoformat(),
               "scope": "Public metadata only. External video streams are not included in the APK snapshot.",
               "linkedVideoCount": len(items), "metadataSuccessCount": sum(i.get("apiCode") == 0 for i in items),
               "totalKnownDurationSeconds": sum(i.get("durationSeconds") or 0 for i in items),
               "videos": items}
    target = SITE / "external-audit.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "videos"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
