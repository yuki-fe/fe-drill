"""Pexels の映像を言葉で探して、番号・長さ・大きさ・作った人を一覧にする。

    python song_tools/pexels_list.py tunnel neon "server room"     # 言葉ごとに探す（縦長を優先）
    python song_tools/pexels_list.py --landscape tunnel            # 横長を探す

API キーは notes/曲の動画/pexels_api_key.txt（公開しないフォルダ。リポジトリに入れない）。
Pexels の映像は Pexels License（商用で無料・クレジット不要。ただし、映っている人を悪く見せる使い方や、
人やブランドが宣伝しているように見せる使い方はしない）。
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

KEY_FILE = Path(__file__).resolve().parent.parent / "notes" / "曲の動画" / "pexels_api_key.txt"


def api_key():
    if not KEY_FILE.exists():
        sys.exit(f"API キーのファイルがありません: {KEY_FILE}")
    return KEY_FILE.read_text(encoding="utf-8-sig").strip()


def search(query, orientation="portrait", per_page=30):
    q = urllib.parse.urlencode({"query": query, "orientation": orientation, "per_page": per_page})
    req = urllib.request.Request(f"https://api.pexels.com/videos/search?{q}",
                                 headers={"Authorization": api_key(), "User-Agent": "fe-drill-song-mv/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))


if __name__ == "__main__":
    args = sys.argv[1:]
    orient = "landscape" if "--landscape" in args else "portrait"
    for kw in [a for a in args if not a.startswith("--")]:
        res = search(kw, orient)
        vids = res.get("videos", [])
        print(f"## {kw} ({len(vids)} / 全{res.get('total_results', '?')})")
        for v in vids:
            slug = v["url"].rstrip("/").split("/")[-1]
            print(f"  p{v['id']:<9} {v['duration']:>3}秒 {v['width']}x{v['height']}  {v['user']['name'][:20]:<20} {slug[:60]}")
