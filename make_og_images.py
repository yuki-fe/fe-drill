"""LINE・SNS に URL を貼ったときに出る画像（og:image、1200×630）を作る。

FE用語ドリル・ITパスポート用語ドリル・入り口（yogo-drill）の3つを、
それぞれのリポジトリの static/og.png に書き出す。書き出したら各サイトで build.py。
デザインはサイトと同じ「ミニマル・スイス」（Noto Sans JP、平らな面、上のふちに色の帯）。

    .venv\\Scripts\\python make_og_images.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DEV = ROOT.parent
PORTAL = json.loads((DEV / "yogo-drill" / "sites.json").read_text(encoding="utf-8"))
SITES = {s["key"]: s for s in PORTAL["sites"]}

W, H = 1200, 630
BG, PAPER, INK, MUTED, LINE = "#F1F4F1", "#FBFCFA", "#1D2A2E", "#5D6C6E", "#D5DDD8"
NOTO = "C:/Windows/Fonts/NotoSansJP-VF.ttf"
PAD = 80

_fonts = {}


def font(size, weight=700):
    key = (size, weight)
    if key not in _fonts:
        f = ImageFont.truetype(NOTO, size)
        f.set_variation_by_axes([weight])
        _fonts[key] = f
    return _fonts[key]


def fit(text, size, weight, width, minimum=40):
    """幅に収まるまで文字を小さくする。"""
    while size > minimum and font(size, weight).getlength(text) > width:
        size -= 2
    return font(size, weight)


def chip(d, x, y, text, color, size=26):
    """小さな札（ふちだけの四角に文字）。右の端の x を返す。"""
    f = font(size, 700)
    w = f.getlength(text) + 36
    d.rounded_rectangle((x, y, x + w, y + size + 24), radius=8, outline=color, width=3)
    d.text((x + 18, y + 10), text, font=f, fill=color)
    return x + w


def site_image(key, lead, points):
    """1つの用語サイトの画像。"""
    s = SITES[key]
    color = s["color"]
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 14), fill=color)
    d.rounded_rectangle((PAD - 30, 60, W - PAD + 30, H - 60), radius=18, fill=PAPER, outline=LINE, width=2)

    x = PAD + 20
    d.text((x, 100), lead, font=font(30, 700), fill=color)
    name = s["name"]
    d.text((x, 150), name, font=fit(name, 92, 900, W - 2 * PAD - 40), fill=INK)
    d.text((x, 290), "用語を、カード・4択・タイピングで覚える無料の単語帳", font=font(34, 500), fill=MUTED)

    cx = x
    for p in points:
        cx = chip(d, cx, 370, p, color) + 16

    d.line((x, 470, W - PAD - 20, 470), fill=LINE, width=2)
    d.text((x, 495), f"{s['terms']}語", font=font(44, 900), fill=INK)
    d.text((x + 170, 507), "無料・登録なし・スマホで使える", font=font(28, 500), fill=MUTED)
    url = s["url"].replace("https://", "").rstrip("/")
    f = font(30, 700)
    d.text((W - PAD - 20 - f.getlength(url), 505), url, font=f, fill=color)
    return im


def portal_image():
    """入り口（yogo-drill.com）の画像。上の帯と、サイトの札は各サイトの色。"""
    pub = [s for s in PORTAL["sites"] if s.get("public")]
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    bw = W / len(pub)
    for i, s in enumerate(pub):
        d.rectangle((round(i * bw), 0, round((i + 1) * bw), 14), fill=s["color"])
    d.rounded_rectangle((PAD - 30, 60, W - PAD + 30, H - 60), radius=18, fill=PAPER, outline=LINE, width=2)

    x = PAD + 20
    d.text((x, 100), "資格の用語の単語帳・無料・登録なし", font=font(30, 700), fill=MUTED)
    d.text((x, 150), PORTAL["site_name"], font=font(96, 900), fill=INK)
    d.text((x, 290), "すきま時間に、カード・4択・タイピングで覚える", font=font(34, 500), fill=MUTED)

    short = {"fe": "基本情報", "ip": "ITパスポート", "cloud": "クラウド", "genai": "生成AI",
             "dl": "ディープラーニング", "boki": "簿記", "iryo": "医療事務"}
    cx, cy = x, 360
    for s in pub:
        t = short.get(s["key"], s["name"])
        w = font(26, 700).getlength(t) + 36
        if cx + w > W - PAD - 20:
            cx, cy = x, cy + 64
        cx = chip(d, cx, cy, t, s["color"]) + 14

    total = sum(s["terms"] for s in pub)
    d.line((x, 490, W - PAD - 20, 490), fill=LINE, width=2)
    d.text((x, 508), f"{len(pub)}サイト・{total:,}語", font=font(36, 900), fill=INK)
    url = PORTAL["base_url"].replace("https://", "")
    f = font(30, 700)
    d.text((W - PAD - 20 - f.getlength(url), 512), url, font=f, fill=INK)
    return im


def main():
    out = [
        (ROOT / "static" / "og.png", site_image("fe", "基本情報技術者試験", ["科目A 用語", "科目B トレース練習", "アルゴリズム図鑑"])),
        (DEV / "ip-drill" / "static" / "og.png", site_image("ip", "ITパスポート試験", ["ストラテジ・マネジメント・テクノロジ", "略語クイズ"])),
        (DEV / "yogo-drill" / "static" / "og.png", portal_image()),
    ]
    for path, im in out:
        im.save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main()
