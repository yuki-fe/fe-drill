"""機能の提案（スキル /feature-scout）のために、サイトの画面をスマホとパソコンの大きさで撮る。

ビルドした docs/ を開いて撮り、ページで出たエラー（console・読み込めないファイル）も書き出す。
撮った画面は notes/機能の提案/画面/<日付>/ に置く（公開しない）。エージェントが Read で画像を見る。

使い方:  ..\\yogo-drill\\.venv\\Scripts\\python review_tools/site_shots.py
         ..\\yogo-drill\\.venv\\Scripts\\python review_tools/site_shots.py --site ip-drill index.html typing.html
         （playwright が要る。yogo-drill の .venv に入っている。先に build.py）
"""
import argparse
import datetime
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT.parent
OUT = ROOT / "notes" / "機能の提案" / "画面" / datetime.date.today().isoformat()

# 何も指定しないときに撮るページ
PAGES = ["index.html", "terms/0001.html", "typing.html", "b/index.html", "app.html", "about.html"]

VIEWS = {
    "sp": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True, "has_touch": True},
    "pc": {"viewport": {"width": 1280, "height": 800}, "device_scale_factor": 1},
}


def launch(pw):
    for opts in ({"channel": "msedge"}, {}, {"channel": "chrome"}):
        try:
            return pw.chromium.launch(**opts)
        except Exception:
            continue
    raise SystemExit("ブラウザが起動できません")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=ROOT.name, help="デスクトップの 02_個人開発 の下のフォルダ名")
    ap.add_argument("pages", nargs="*", default=PAGES)
    a = ap.parse_args()

    docs = SITES / a.site / "docs"
    out = OUT / a.site
    out.mkdir(parents=True, exist_ok=True)
    report = []
    with sync_playwright() as pw:
        b = launch(pw)
        for path in a.pages:
            f = docs / path
            if not f.exists():
                report.append({"page": path, "error": "ファイルがない"})
                continue
            for view, opts in VIEWS.items():
                ctx = b.new_context(color_scheme="light", **opts)
                pg = ctx.new_page()
                errors = []
                pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.on("requestfailed", lambda r: errors.append("読み込めない: " + r.url))
                pg.goto(f.as_uri())
                pg.wait_for_timeout(1000)
                name = path.replace("/", "_").replace(".html", "") + f"-{view}.png"
                pg.screenshot(path=str(out / name), full_page=True)
                report.append({"page": path, "view": view, "shot": str(out / name), "errors": errors})
                ctx.close()
        b.close()
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in report:
        mark = "NG" if r.get("error") or r.get("errors") else "OK"
        print(mark, r["page"], r.get("view", ""), r.get("error") or "; ".join(r.get("errors", []))[:200])
    print("画面:", out)


if __name__ == "__main__":
    main()
