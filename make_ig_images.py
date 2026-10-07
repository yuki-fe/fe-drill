"""Instagram 投稿用の画像（1080×1350 の2枚組: クイズ → 答え）と投稿文を作る。

使い方:  python make_ig_images.py        （最初の60投稿分＝約2か月分を作る）
         python make_ig_images.py 120    （120投稿分まで作る。足りなくなったら数を増やして実行する）
出力:    static/ig/〇〇〇〇-q.jpg（クイズ）、static/ig/〇〇〇〇-a.jpg（答え）、static/ig/posts.json（投稿の順番と投稿文）
         python build.py で docs/ig/ にコピーされ、GitHub Pages で公開される（Instagram はこの URL から画像を読み込む）
用語を追加・修正したときだけ、もう一度実行する。
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from build import BASE, FIELDS, KANA, masked, terms

OUT = Path(__file__).parent / "static" / "ig"
W, H = 1080, 1350
PAPER, BG, INK, MUTED, LINE = "#fbfcfa", "#f1f4f1", "#1d2a2e", "#5d6c6e", "#d5ddd8"
MARK, MARK_SOFT, OK, OK_SOFT = "#c0435a", "#f6dfe3", "#2b7a68", "#d9eee8"
FONT_R = "C:/Windows/Fonts/BIZ-UDGothicR.ttc"
FONT_B = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"
HASHTAGS = "#基本情報技術者試験 #基本情報 #IT資格 #情報系学生 #IT用語 #プログラミング学習 #資格勉強 #勉強垢"


def font(size, bold=False):
    # index=1 は BIZ UDPゴシック（文字幅が文字ごとに変わる版）
    return ImageFont.truetype(FONT_B if bold else FONT_R, size, index=1)


def wrap(text, f, width):
    """日本語を1文字ずつ詰めて折り返す。句読点や閉じ括弧が行頭に来ないようにする。"""
    lines, cur = [], ""
    for ch in text:
        if f.getlength(cur + ch) > width and cur:
            if ch in "、。，．）」』】・ー":
                cur += ch
                continue
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def fit(text, width, sizes, bold=True, max_lines=2):
    """幅に収まる一番大きい文字サイズを選ぶ。"""
    for s in sizes:
        f = font(s, bold)
        lines = wrap(text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(sizes[-1], bold)
    return f, wrap(text, f, width)


def base(label, label_color):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((48, 48, W - 48, H - 48), radius=36, fill=PAPER, outline=LINE, width=2)
    f = font(34, True)
    tw = f.getlength(label)
    d.rounded_rectangle((96, 100, 96 + tw + 56, 164), radius=32, fill=label_color)
    d.text((124, 113), label, font=f, fill=PAPER)
    d.text((96, H - 140), "FE用語ドリル", font=font(34, True), fill=INK)
    d.text((96, H - 92), "基本情報技術者試験の用語を毎日1つ", font=font(26), fill=MUTED)
    return img, d


def lines_block(d, x, y, lines, f, fill, gap=1.55):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def choices_for(t):
    rng = random.Random("ig-" + t["id"])
    pool = [x for x in terms if x["sub"] == t["sub"] and x["id"] != t["id"]]
    if len(pool) < 3:
        pool += [x for x in terms if x["field"] == t["field"] and x["sub"] != t["sub"]]
    choices = rng.sample(pool, 3) + [t]
    rng.shuffle(choices)
    return choices


def question_card(t, choices, no):
    img, d = base(f"今日のIT用語クイズ  No.{no}", MARK)
    d.text((96, 200), f"{FIELDS[t['field']]}・{t['sub']}", font=font(30), fill=MARK)
    d.text((96, 256), "この説明に当てはまる用語は？", font=font(52, True), fill=INK)
    f = font(36)
    desc = wrap(masked(t), f, W - 96 * 2 - 64)[:6]
    box_h = len(desc) * int(36 * 1.6) + 56
    d.rounded_rectangle((96, 352, W - 96, 352 + box_h), radius=20, fill=BG)
    lines_block(d, 128, 380, desc, f, INK, 1.6)
    y = 352 + box_h + 48
    for k, c in enumerate(choices):
        d.rounded_rectangle((96, y, W - 96, y + 104), radius=18, fill=PAPER, outline=LINE, width=2)
        d.ellipse((124, y + 30, 196, y + 74), outline=MARK, width=4)
        d.text((145, y + 33), KANA[k], font=font(32, True), fill=MARK)
        cf, cl = fit(c["term"], W - 96 * 2 - 150, [40, 36, 32, 28], max_lines=1)
        d.text((224, y + 52 - cf.size // 2 - 4), cl[0], font=cf, fill=INK)
        y += 124
    d.text((W - 96 - font(30, True).getlength("答えは次の画像 →"), H - 132), "答えは次の画像 →", font=font(30, True), fill=MARK)
    return img


def answer_card(t, choices, no):
    img, d = base(f"答え  No.{no}", OK)
    k = choices.index(t)
    d.ellipse((96, 214, 196, 278), outline=OK, width=5)
    d.text((126, 222), KANA[k], font=font(44, True), fill=OK)
    tf, tl = fit(t["term"], W - 96 * 2 - 130, [84, 72, 60, 52, 44], max_lines=2)
    y = lines_block(d, 226, 206, tl, tf, INK, 1.25)
    y = max(y, 300) + 24
    d.text((96, y), f"{FIELDS[t['field']]}・{t['sub']}", font=font(30), fill=MUTED)
    y += 70
    f = font(38)
    desc = wrap(t["desc"], f, W - 96 * 2 - 64)[:9]
    box_h = len(desc) * int(38 * 1.6) + 60
    d.rounded_rectangle((96, y, W - 96, y + box_h), radius=20, fill=OK_SOFT)
    lines_block(d, 128, y + 30, desc, f, INK, 1.6)
    y += box_h + 48
    others = [c for c in choices if c is not t]
    d.text((96, y), "ほかの選択肢", font=font(30, True), fill=MUTED)
    y += 56
    for c in others:
        cf, cl = fit(f"・{c['term']}", W - 96 * 2, [32, 28], bold=False, max_lines=1)
        d.text((96, y), cl[0], font=cf, fill=MUTED)
        y += 50
    d.rounded_rectangle((96, H - 330, W - 96, H - 190), radius=20, fill=BG)
    d.text((128, H - 304), "345語の単語帳・4択クイズ・科目B対策", font=font(32, True), fill=INK)
    d.text((128, H - 250), "プロフィールのリンクから無料で使えます", font=font(28), fill=MUTED)
    return img


def caption(t, choices, no):
    q = "\n".join(f"{KANA[k]} {c['term']}" for k, c in enumerate(choices))
    tag = "#" + t["sub"].replace(" ", "")
    return (f"【今日のIT用語クイズ No.{no}】\n"
            f"この説明に当てはまる用語はどれ？\n\n{masked(t)}\n\n{q}\n\n"
            "答えは2枚目の画像へ。コメントで答え合わせしてみてね。\n\n"
            "基本情報技術者試験（FE）によく出るIT用語を、毎日1つずつ紹介しています。\n"
            "345語の単語帳と4択クイズは、プロフィールのリンクから無料で使えます。\n\n"
            f"{HASHTAGS} {tag}")


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    OUT.mkdir(parents=True, exist_ok=True)
    order = sorted(terms, key=lambda t: random.Random("order-" + t["id"]).random())
    posts = []
    for no, t in enumerate(order[:count], 1):
        ch = choices_for(t)
        question_card(t, ch, no).save(OUT / f"{t['id']}-q.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        answer_card(t, ch, no).save(OUT / f"{t['id']}-a.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        posts.append({"no": no, "id": t["id"], "term": t["term"],
                      "images": [f"{BASE}/ig/{t['id']}-q.jpg", f"{BASE}/ig/{t['id']}-a.jpg"],
                      "caption": caption(t, ch, no)})
    (OUT / "posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    keep = {f"{p['id']}-{k}.jpg" for p in posts for k in "qa"}
    for old in OUT.glob("*.jpg"):
        if old.name not in keep:
            old.unlink()
    size = sum(p.stat().st_size for p in OUT.glob("*.jpg")) / 1024 / 1024
    print(f"static/ig/ に {len(posts)} 投稿分（画像 {len(posts) * 2} 枚、{size:.1f} MB）を書き出しました")


if __name__ == "__main__":
    main()
