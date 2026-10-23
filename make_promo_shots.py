"""用語ドリル全体の宣伝動画（make_series_promo.py）に入れる、各サイトのスマホの画面を撮る。

各サイトのフォルダの docs/（ビルドしたもの）を、スマホの大きさ（390×844、3倍の細かさ）で開いて撮る。
少し覚えた状態（進み具合が0でない）にしてから撮る。撮った画面は notes/宣伝動画/画面/ に置く（公開しない）。

使い方:  ..\\yogo-drill\\.venv\\Scripts\\python make_promo_shots.py
         （playwright が要る。yogo-drill の .venv に入っている）
"""
import random
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
SITES = ROOT.parent
OUT = ROOT / "notes" / "宣伝動画" / "画面"

# (名前, フォルダ, 開くページ, 撮る前の操作)
SHOTS = [
    ("fe-home", "claude FE対策サイト", "index.html", "home"),
    ("ip-test", "ip-drill", "test.html", "test"),
    ("boki-term", "boki-drill", "terms/0005.html", "quiz"),
    ("iryo-abbr", "iryo-drill", "abbr.html", "abbr"),
]

SEED = """() => {
  const T = window.FE_TERMS || window.IP_TERMS || window.SITE_TERMS || [];
  const prefs = Object.keys(localStorage).find((k) => /-drill-prefs$/.test(k));
  if (!prefs || !T.length) return false;
  const pre = prefs.replace(/-prefs$/, "");
  const known = {};
  T.forEach((t, i) => { if ((i * 7) % 10 < 3) known[t.term] = 1; });   // 3割ほどを覚えた
  localStorage.setItem(pre + "-v1", JSON.stringify(known));
  return true;
}"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    random.seed(1)
    with sync_playwright() as pw:
        b = None
        for opts in ({"channel": "msedge"}, {}, {"channel": "chrome"}):
            try:
                b = pw.chromium.launch(**opts)
                break
            except Exception:
                continue
        for name, folder, path, act in SHOTS:
            ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True, color_scheme="light")
            pg = ctx.new_page()
            docs = SITES / folder / "docs"
            pg.goto((docs / "index.html").as_uri())
            pg.wait_for_timeout(800)
            pg.evaluate(SEED)
            pg.goto((docs / path).as_uri())
            pg.wait_for_timeout(1200)
            if act == "test":
                pg.click("#drill #start")
                pg.wait_for_timeout(300)
                for k in (0, 2, 1):
                    pg.locator("#drill .choice").nth(k).click()
                    pg.wait_for_timeout(250)
                pg.evaluate("document.querySelector('#drill').scrollIntoView({block: 'start'})")
                pg.evaluate("scrollBy(0, -70)")
            elif act == "quiz":
                pg.evaluate("scrollTo(0, 0)")
            elif act == "abbr":
                pg.locator("#drill .choice").first.click()
                pg.wait_for_timeout(300)
                pg.evaluate("document.querySelector('#drill').scrollIntoView({block: 'start'})")
                pg.evaluate("scrollBy(0, -70)")
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(OUT / f"{name}.png"))
            print("撮りました:", name)
            ctx.close()
        b.close()


if __name__ == "__main__":
    main()
