"""Pexels の映像を、番号を指定してダウンロードする（背景素材のフォルダに p番号.mp4 で保存）。

    python song_tools/pexels_get.py notes/曲の動画/背景素材 p1234567 p7654321

縦長・横長どちらでも、短い辺が 1080 にいちばん近いファイル（なければいちばん大きいもの）を選ぶ。
作った人とページの URL は、同じフォルダの pexels_credits.json に残す（説明文にクレジットを書くとき用。必須ではない）。
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pexels_list import api_key  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
credits_path = out / "pexels_credits.json"
credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
H = {"Authorization": api_key(), "User-Agent": "fe-drill-song-mv/1.0"}

for arg in sys.argv[2:]:
    vid = arg.lstrip("p")
    dest = out / f"p{vid}.mp4"
    if dest.exists():
        print(f"p{vid}: もうあります")
        continue
    try:
        v = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.pexels.com/videos/videos/{vid}", headers=H), timeout=30).read())
    except Exception as e:
        print(f"p{vid}: 情報を取れません ({e})")
        continue
    files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")]
    if not files:
        print(f"p{vid}: mp4 がありません")
        continue
    best = min(files, key=lambda f: (abs(min(f["width"], f["height"]) - 1080), -f["width"] * f["height"]))
    data = urllib.request.urlopen(urllib.request.Request(best["link"], headers={"User-Agent": H["User-Agent"]}), timeout=180).read()
    dest.write_bytes(data)
    credits[f"p{vid}"] = {"by": v["user"]["name"], "page": v["url"], "license": "Pexels License"}
    print(f"p{vid}: {best['width']}x{best['height']} {len(data) // 1024} KB  （{v['user']['name']}）")

credits_path.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
