"""スマホのホーム画面に置くアプリのアイコン（PWA 用）を static/ に作る。favicon.svg と同じ形（赤地に白の FE）。

作るもの:
  ・icon-192.png / icon-512.png   角の丸いアイコン（ふつうのアイコン）
  ・icon-maskable-512.png         Android が丸や角丸に切り抜く用（地の色をはみ出させ、文字を真ん中の安全な範囲に小さめに置く）

使い方:  python make_app_icons.py   （アイコンの形を変えたときだけ。ふだんは要らない）
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
RED, WHITE = "#c0435a", "#fbfcfa"
# favicon.svg の「F」と「E」（64×64 の座標。角の小さな丸みは省く）
F = [(0, 0), (16, 0), (16, 7.5), (9, 7.5), (9, 13), (15, 13), (15, 20), (9, 20), (9, 32), (0, 32)]
E = [(19, 0), (37, 0), (37, 7.5), (29, 7.5), (29, 12.5), (36, 12.5), (36, 19.5), (29, 19.5), (29, 24.5), (37, 24.5), (37, 32), (19, 32)]


def icon(size, maskable=False):
    s = 4                       # 大きく描いてから縮めて、ふちをなめらかにする
    S = size * s
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if maskable:
        d.rectangle((0, 0, S, S), fill=RED)
        k, ox, oy = S / 64 * 0.72, S * 0.14 + 13.5 * S / 64 * 0.72, S * 0.14 + 16 * S / 64 * 0.72
    else:
        d.rounded_rectangle((0, 0, S - 1, S - 1), radius=S * 14 / 64, fill=RED)
        k, ox, oy = S / 64, 13.5 * S / 64, 16 * S / 64
    for shape in (F, E):
        d.polygon([(ox + x * k, oy + y * k) for x, y in shape], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    icon(192).save(ROOT / "static" / "icon-192.png")
    icon(512).save(ROOT / "static" / "icon-512.png")
    icon(512, maskable=True).save(ROOT / "static" / "icon-maskable-512.png")
    print("static/ に icon-192.png・icon-512.png・icon-maskable-512.png を作りました")
