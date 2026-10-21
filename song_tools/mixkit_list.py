"""Mixkit の検索ページから、映像の番号と名前を集める。"""
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
for kw in sys.argv[1:]:
    url = f"https://mixkit.co/free-stock-video/{kw}/"
    try:
        html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"## {kw}: {e}")
        continue
    items = sorted(set(re.findall(r'href="/free-stock-video/([a-z0-9-]+)-(\d+)/"', html)), key=lambda x: int(x[1]))
    print(f"## {kw} ({len(items)})")
    for slug, vid in items:
        print(f"  {vid:>6} {slug}")
