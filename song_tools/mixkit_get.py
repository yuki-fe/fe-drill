"""Mixkit の映像を、ライセンスを確かめてからダウンロードする。

    python mixkit_get.py 出力フォルダ 番号:名前 番号:名前 ...
映像のページで "Free License" か "Restricted" かを調べ、Free のものだけ 1080p（なければ 720p）を保存する。
"""
import re
import sys
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


for arg in sys.argv[2:]:
    vid, slug = arg.split(":", 1)
    page = get(f"https://mixkit.co/free-stock-video/{slug}-{vid}/").decode("utf-8", "ignore")
    # ページの構造化データの copyrightNotice が "Free" のものだけ使う（"Mixkit Restricted License" は使わない）
    m = re.search(r'"copyrightNotice":"([^"]*)"', page)
    shown = m.group(1) if m else "?"
    dst = out / f"{vid}.mp4"
    if shown != "Free":
        print(f"{vid} {slug}: {shown} → 使わない")
        continue
    if dst.exists():
        print(f"{vid} {slug}: {shown}（保存済み）")
        continue
    for q in ("1080", "720"):
        try:
            data = get(f"https://assets.mixkit.co/videos/{vid}/{vid}-{q}.mp4")
            dst.write_bytes(data)
            print(f"{vid} {slug}: {shown} → {q}p {len(data) // 1024} KB")
            break
        except Exception as e:
            last = e
    else:
        print(f"{vid} {slug}: ダウンロードできません ({last})")
