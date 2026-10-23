"""FE用語ドリルの宣伝リール動画を作る（スキル ui-ux-pro-max のデザインを試したもの）。

デザイン: ふっくらした「クレイ」風（角の丸い厚みのあるカード・太めのふち・やわらかい二重の影）。
          色は勉強の紫（#7C3AED）と正解の緑（#059669）、背景はうすい紫（#FAF5FF）。
動き:     部品は少し小さい所から、はずむように出てくる（0.4秒・ずらして順に）。

作るもの（static/ig/promo/ に書き出す）:
  ・reel.mp4 / reel-cover.jpg   リール動画（1080×1920、60fps、約33秒、音なし）と表紙
  ・captions.txt               リールの投稿文、YouTube ショートのタイトルと説明

使い方:  python make_promo_media.py
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import make_b_media as mb
import media_fx as fx
from make_b_media import font, wrap
from make_intro_media import ICON, W

ROOT = Path(__file__).parent
OUT = ROOT / "static" / "ig" / "promo"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
URL = CFG["base_url"]
RH, FPS = 1920, 60
ENTER = 0.42   # 部品が出てくるのにかける秒数
FADE = 0.3     # 場面の切り替えにかける秒数

# 色（ui-ux-pro-max の「Study purple + correct green」）
PRIMARY, PRIMARY_SOFT, SECONDARY = "#7C3AED", "#EDE4FD", "#8B5CF6"
OK, OK_SOFT = "#059669", "#D7F5EA"
BG, CARD, INK, MUTED, LINE = "#FAF5FF", "#FFFFFF", "#0F172A", "#475569", "#E4D8FA"
HL = "#FFF1B8"
SHADOW = (76, 29, 149)   # 影の色（濃い紫）
TAGS = "#基本情報技術者試験 #基本情報 #FE #IT資格 #情報系学生 #IT用語 #資格勉強 #勉強垢 #プログラミング"

terms = json.loads((ROOT / "data" / "terms.json").read_text(encoding="utf-8"))
BY_NAME = {t["term"]: t for t in terms}
N_TERMS = len(terms)
B = {n: json.loads((ROOT / "data" / "b" / f"{n}.json").read_text(encoding="utf-8"))
     for n in ("trace", "fill", "algorithms", "security", "notation")}
N_FIGS = len(json.loads((ROOT / "data" / "figs.json").read_text(encoding="utf-8")))


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def back(x):
    """少し行きすぎてから戻る動き（0〜1）。"""
    x = min(1.0, max(0.0, x))
    return 1 + 2.4 * (x - 1) ** 3 + 1.4 * (x - 1) ** 2


# ---------- 部品と場面 ----------

class Part:
    """透明の画像に描いた部品。使うところだけ切り抜いて持つ。"""

    def __init__(self, draw_fn):
        img = Image.new("RGBA", (W, RH), (0, 0, 0, 0))
        draw_fn(img, ImageDraw.Draw(img))
        box = img.getbbox() or (0, 0, 1, 1)
        self.img, self.x, self.y = img.crop(box), box[0], box[1]

    def put(self, frame, p, scale=1.0, dy=0.0):
        if p <= 0:
            return
        im = self.img
        if scale != 1.0:
            im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BICUBIC)
        if p < 1:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * p)))
        cx, cy = self.x + self.img.width / 2, self.y + self.img.height / 2 + dy
        frame.alpha_composite(im, (round(cx - im.width / 2), round(cy - im.height / 2)))


def _background():
    """うすい紫の背景に、ぼかした大きな丸を2つ（奥行きを出す）。"""
    img = Image.new("RGB", (W, RH), BG)
    d = ImageDraw.Draw(img)
    d.ellipse((-260, -200, 640, 700), fill="#E6DAFC")
    d.ellipse((560, 1300, 1400, 2140), fill="#DDF5EA")
    return img.filter(ImageFilter.GaussianBlur(120)).convert("RGBA")


BACKGROUND = _background()


class Scene:
    def __init__(self, sec):
        self.sec = sec
        self.items = []

    def add(self, t0, draw_fn, rise=36):
        """t0 秒に、少し小さい所からはずむように出てくる部品。"""
        part = Part(draw_fn)

        def draw(f, t):
            p = (t - t0) / ENTER
            if p <= 0:
                return
            if p >= 1:
                part.put(f, 1)
                return
            part.put(f, ease(p * 1.6), scale=0.92 + 0.08 * back(p), dy=(1 - ease(p)) * rise)
        self.items.append(draw)
        return part

    def fade_in(self, t0, draw_fn, dur=0.3):
        part = Part(draw_fn)
        self.items.append(lambda f, t: part.put(f, ease((t - t0) / dur)))

    def custom(self, fn):
        self.items.append(fn)

    def render(self, t):
        frame = BACKGROUND.copy()
        for fn in self.items:
            fn(frame, t)
        return frame


# ---------- 描く道具 ----------

def clay(img, box, r=40, fill=CARD, border=LINE, bw=4, depth=18):
    """クレイ風のカード: 下にやわらかい影（遠い影・近い影の二重）、太めのふち、上のふちに明るい線。"""
    x1, y1, x2, y2 = box
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle((x1 + 6, y1 + depth + 10, x2 - 6, y2 + depth + 10), radius=r, fill=SHADOW + (46,))
    far = sh.filter(ImageFilter.GaussianBlur(26))
    sh2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh2).rounded_rectangle((x1, y1 + 8, x2, y2 + 8), radius=r, fill=SHADOW + (40,))
    img.alpha_composite(far)
    img.alpha_composite(sh2.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=r, fill=fill, outline=border, width=bw)
    if fill != CARD:   # 色のついたボタンには、明るい線を入れない
        return
    d.arc((x1 + bw + 6, y1 + bw + 6, x1 + bw + 6 + r * 2, y1 + bw + 6 + r * 2), 180, 270, fill=(255, 255, 255, 200), width=4)
    d.line((x1 + r + bw + 6, y1 + bw + 6, x2 - r - 10, y1 + bw + 6), fill=(255, 255, 255, 200), width=4)


def chip(d, x, y, text, color=PRIMARY, size=34, fg="#FFFFFF"):
    f = font(size, True)
    w = f.getlength(text)
    h = size + 30
    d.rounded_rectangle((x, y, x + w + 56, y + h), radius=h // 2, fill=color)
    d.text((x + 28, y + 13), text, font=f, fill=fg)
    return x + w + 56


def center_text(d, y, text, f, fill):
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)


def lines_at(d, x, y, lines, f, fill, gap=1.4):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def fe_icon(img, x, y, size):
    """FE用語ドリルのアイコン（紫の角丸に FE）。"""
    s = 4
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, size * s - 1, size * s - 1), radius=size * s * 0.26, fill=PRIMARY)
    f = font(int(size * s * 0.48), True)
    bb = d.textbbox((0, 0), "FE", font=f)
    d.text(((size * s - (bb[2] - bb[0])) / 2 - bb[0], (size * s - (bb[3] - bb[1])) / 2 - bb[1]), "FE", font=f, fill="#FFFFFF")
    img.alpha_composite(big.resize((size, size), Image.LANCZOS), (x, y))


def account_icon(img, x, y, size):
    if not ICON.exists():
        return
    im = Image.open(ICON).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    im.putalpha(mask)
    img.alpha_composite(im, (x, y))


def head(sc, label, color=PRIMARY):
    sc.add(0, lambda img, d: chip(d, 60, 190, label, color, 36), rise=20)


def check_mark(d, cx, cy, r, color):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    d.line((cx - r * 0.45, cy, cx - r * 0.1, cy + r * 0.38, cx + r * 0.5, cy - r * 0.35), fill="#FFFFFF", width=max(4, r // 4), joint="curve")


# ---------- 場面 ----------

def s_hook():
    sc = Scene(3.2)
    sc.add(0.0, lambda img, d: chip(d, 120, 520, "基本情報技術者試験", SECONDARY, 38))
    for i, ln in enumerate(["用語、", "覚えきれてる？"]):
        sc.add(0.2 + i * 0.18, lambda img, d, ln=ln, i=i: d.text((120, 650 + i * 150), ln, font=font(112, True), fill=INK))
    sc.add(0.9, lambda img, d: d.text((120, 1000), "スキマ時間に、スマホで。", font=font(56, True), fill=PRIMARY))
    # 下に、用語のカードを少し傾けて重ねる
    for k, (word, x, y, ang) in enumerate([("デッドロック", 110, 1260, 6), ("正規化", 560, 1330, -5), ("DNS", 300, 1500, -3),
                                            ("ハッシュ関数", 640, 1560, 7)]):
        def tile(img, d, word=word, x=x, y=y, ang=ang):
            f = font(48, True)
            w = int(f.getlength(word)) + 90
            t = Image.new("RGBA", (w + 80, 220), (0, 0, 0, 0))
            clay(t, (40, 30, 40 + w, 150), 36)
            ImageDraw.Draw(t).text((85, 62), word, font=f, fill=PRIMARY)
            t = t.rotate(ang, resample=Image.BICUBIC, expand=True)
            img.alpha_composite(t, (x, y))
        sc.add(1.1 + k * 0.12, tile)
    return sc


def s_title():
    sc = Scene(3.0)
    sc.add(0.0, lambda img, d: clay(img, (90, 380, W - 90, 1400), 56), rise=50)
    part = Part(lambda img, d: fe_icon(img, (W - 240) // 2, 470, 240))

    def pop(f, t):
        p = (t - 0.15) / 0.5
        if p > 0:
            part.put(f, ease(p * 1.5), scale=0.6 + 0.4 * back(p))
    sc.custom(pop)
    sc.add(0.35, lambda img, d: center_text(d, 790, "無料の学習サイト", font(48), MUTED))
    sc.add(0.5, lambda img, d: center_text(d, 880, "FE用語ドリル", font(124, True), PRIMARY))
    labels = ["登録なし", "スマホでOK", "無料"]
    f = font(40, True)
    total = sum(f.getlength(x) + 56 for x in labels) + 24 * (len(labels) - 1)
    x = (W - total) / 2
    for k, lab in enumerate(labels):
        sc.add(0.85 + k * 0.1, lambda img, d, x=x, lab=lab: chip(d, x, 1120, lab, OK_SOFT, 40, OK), rise=24)
        x += f.getlength(lab) + 56 + 24
    return sc


def s_numbers():
    sc = Scene(3.4)
    head(sc, "科目Aも科目Bも")
    rows = [(N_TERMS, "語", "科目Aの用語を、分野ごとに", PRIMARY),
            (len(B["trace"]) + len(B["fill"]), "問", "科目Bのトレース・穴埋め", OK)]
    nf = font(176, True, mono=True)
    for i, (n, unit, sub, c) in enumerate(rows):
        y = 380 + i * 560
        t0 = 0.15 + i * 0.3
        sc.add(t0, lambda img, d, y=y: clay(img, (60, y, W - 60, y + 480), 48))
        sc.add(t0 + 0.1, lambda img, d, y=y, sub=sub: d.text((120, y + 360), sub, font=font(46, True), fill=INK), rise=20)

        def count(f, t, y=y, n=n, t0=t0, unit=unit, c=c):
            if t < t0 + 0.15:
                return
            p = ease((t - t0 - 0.15) / 1.1)
            d = ImageDraw.Draw(f)
            d.text((120, y + 90), str(round(n * p)), font=nf, fill=c)
            d.text((120 + nf.getlength(str(n)) + 20, y + 210), unit, font=font(68, True), fill=INK)
        sc.custom(count)
    return sc


def card_face(side):
    t = BY_NAME["デッドロック"]
    x, y, w, h = 70, 560, W - 140, 720

    def draw(img, d):
        clay(img, (x, y, x + w, y + h), 52, border=LINE if side == "front" else PRIMARY_SOFT)
        tag = f"テクノロジ系・{t['sub']}"
        f = font(32, True)
        tw = f.getlength(tag)
        d.rounded_rectangle((x + (w - tw) / 2 - 26, y + 50, x + (w + tw) / 2 + 26, y + 112), radius=31, fill=PRIMARY_SOFT)
        d.text((x + (w - tw) / 2, y + 63), tag, font=f, fill=PRIMARY)
        df = font(48, True)
        yy = y + 200
        if side == "back":
            tf = font(108, True)
            d.text((x + (w - tf.getlength(t["term"])) / 2, y + 170), t["term"], font=tf, fill=PRIMARY)
            yy = y + 360
        for ln in wrap(t["desc"], df, w - 150):
            d.text((x + (w - df.getlength(ln)) / 2, yy), ln, font=df, fill=INK)
            yy += int(48 * 1.6)
        if side == "front":
            hint = "用語を思い浮かべて、タップ"
            d.text((x + (w - font(34).getlength(hint)) / 2, y + h - 110), hint, font=font(34), fill=MUTED)
    return Part(draw)


def s_card():
    sc = Scene(4.4)
    head(sc, "カードで覚える")
    sc.add(0.1, lambda img, d: lines_at(d, 60, 300, ["意味を読んで、", "用語を思い出す"], font(80, True), INK, 1.3))
    front, back_ = card_face("front"), card_face("back")
    T_IN, T_FLIP, DUR = 0.3, 2.0, 0.5

    def flip(f, t):
        if t < T_FLIP:
            p = (t - T_IN) / ENTER
            if p > 0:
                front.put(f, ease(p * 1.6), scale=0.92 + 0.08 * back(p), dy=(1 - ease(p)) * 36)
            return
        q = min(1.0, (t - T_FLIP) / DUR)
        part = front if q < 0.5 else back_
        sx = abs(math.cos(q * math.pi))
        if sx < 0.02:
            return
        im = part.img.resize((max(1, int(part.img.width * sx)), part.img.height), Image.LANCZOS)
        f.alpha_composite(im, (int(part.x + (part.img.width - im.width) / 2), part.y))
    sc.custom(flip)
    for k, (lab, c) in enumerate([("まだ", SECONDARY), ("覚えた", OK)]):
        bw = (W - 140) // 2 - 12
        bx = 70 + k * (bw + 24)

        def btn(img, d, bx=bx, bw=bw, lab=lab, c=c):
            clay(img, (bx, 1360, bx + bw, 1480), 60, fill=c, border=c, depth=10)
            d.text((bx + (bw - font(46, True).getlength(lab)) / 2, 1392), lab, font=font(46, True), fill="#FFFFFF")
        sc.add(T_FLIP + DUR + k * 0.12, btn, rise=24)
    return sc


def s_quiz():
    sc = Scene(4.6)
    t = BY_NAME["SQLインジェクション"]
    choices = ["クロスサイトスクリプティング", "SQLインジェクション", "ブルートフォース攻撃", "DDoS攻撃"]
    assert all(c in BY_NAME for c in choices)
    head(sc, "4択クイズ")
    sc.add(0.1, lambda img, d: lines_at(d, 60, 300, ["この説明に当てはまる", "用語は？"], font(74, True), INK, 1.3))
    f = font(46, True)
    desc = wrap(t["desc"], f, W - 240)
    box_h = len(desc) * int(46 * 1.6) + 90

    def desc_box(img, d):
        clay(img, (60, 540, W - 60, 540 + box_h), 40, fill=PRIMARY_SOFT, border=PRIMARY_SOFT)
        lines_at(d, 120, 585, desc, f, INK, 1.6)
    sc.add(0.3, desc_box)

    def choice(y, k, c, ok):
        def draw(img, d):
            clay(img, (60, y, W - 60, y + 124), 36, fill=OK_SOFT if ok else CARD, border=OK if ok else LINE, depth=10)
            if ok:
                check_mark(d, 124, y + 62, 30, OK)
            else:
                d.ellipse((94, y + 32, 154, y + 92), fill=PRIMARY_SOFT)
                d.text((124 - font(32, True).getlength("アイウエ"[k]) / 2, y + 44), "アイウエ"[k], font=font(32, True), fill=PRIMARY)
            d.text((190, y + 38), c, font=font(44, True), fill=OK if ok else INK)
        return draw

    y0 = 540 + box_h + 60
    for k, c in enumerate(choices):
        y = y0 + k * 150
        sc.add(0.55 + k * 0.1, choice(y, k, c, False), rise=24)
        if c == t["term"]:
            sc.fade_in(2.7, choice(y, k, c, True))
    return sc


def s_trace():
    """科目B: 1行ずつ再生して、変数の変化を見せる（trace.json の「配列の合計」）。"""
    q = next(x for x in B["trace"] if x["id"] == "t1")
    code = q["code"]
    # 実行する行（0から）と、そのあとの変数の値
    data = [3, 5, 2]
    steps, s = [(1, {"s": 0})], 0
    for i in range(1, len(data) + 1):
        steps.append((3, {"i": i}))
        s += data[i - 1]
        steps.append((4, {"s": s}))
    steps.append((6, {}))
    T0, STEP = 1.0, 0.55
    sc = Scene(T0 + STEP * len(steps) + 1.4)
    head(sc, "科目B", OK)
    sc.add(0.1, lambda img, d: lines_at(d, 60, 300, ["プログラムを", "1行ずつ再生"], font(80, True), INK, 1.3))
    cf = font(35, mono=True)
    LH, CX, CY = 70, 100, 640

    def code_card(img, d):
        clay(img, (60, 580, W - 60, 580 + LH * len(code) + 70), 40)
    sc.add(0.3, code_card)
    sc.add(0.3, lambda img, d: chip(d, 60, 1310, "data = {3, 5, 2}", PRIMARY_SOFT, 34, PRIMARY), rise=20)

    def band(f, t):
        if t < T0:
            return
        k = min(len(steps) - 1, int((t - T0) / STEP))
        u = ease(((t - T0) - k * STEP) / 0.18)
        prev = steps[k - 1][0] if k else steps[0][0]
        ln = prev + (steps[k][0] - prev) * u
        d = ImageDraw.Draw(f)
        y = CY + ln * LH - 8
        d.rounded_rectangle((80, y, W - 80, y + LH - 4), radius=18, fill=HL)
    sc.custom(band)

    def code_text(img, d):
        for i, ln in enumerate(code):
            d.text((CX, CY + i * LH + 8), ln, font=cf, fill=INK)
    # 帯の上に文字を描くため、文字は帯のあとに置く
    text_part = Part(code_text)
    sc.custom(lambda f, t: text_part.put(f, ease((t - 0.4) / ENTER)))

    # 変数のカード（値が変わると、ぴょんとはずむ）
    vf = font(96, True, mono=True)

    def vars_(f, t):
        if t < 0.6:
            return
        vals, changed = {"i": "-", "s": "-"}, {}
        for k, (_, v) in enumerate(steps):
            ts = T0 + k * STEP
            if t >= ts:
                for name, val in v.items():
                    vals[name], changed[name] = str(val), ts
        a = ease((t - 0.6) / ENTER)
        for j, name in enumerate(["i", "s"]):
            x = 60 + j * 500
            card = Image.new("RGBA", (W, RH), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            hop = 0
            if name in changed:
                p = (t - changed[name]) / 0.3
                if p < 1:
                    hop = -math.sin(p * math.pi) * 22
            clay(card, (x, 1420, x + 460, 1700), 44, fill=OK_SOFT if hop else CARD, border=OK if hop else LINE)
            cd.text((x + 50, 1450), f"変数 {name}", font=font(38, True), fill=MUTED)
            cd.text((x + 50, 1530 + hop), vals[name], font=vf, fill=OK if name == "s" else PRIMARY)
            if a < 1:
                card.putalpha(card.getchannel("A").point(lambda v: int(v * a)))
            f.alpha_composite(card)
    sc.custom(vars_)
    sc.fade_in(T0 + STEP * len(steps) + 0.1, lambda img, d: chip(d, W - 60 - font(36, True).getlength("答え 10") - 56, 1310, "答え 10", OK, 36))
    return sc


def s_more():
    sc = Scene(3.6)
    head(sc, "ほかにも")
    items = [("動く図", f"{N_FIGS}語を、ステップごとの図で"),
             ("用語タイピング", "用語と意味を打って覚える"),
             ("まちがえた用語の復習", "苦手だけを解き直す"),
             ("アルゴリズム図鑑", "探索・整列の動きを見る")]
    for i, (title, sub) in enumerate(items):
        y = 330 + i * 300

        def row(img, d, y=y, title=title, sub=sub, i=i):
            clay(img, (60, y, W - 60, y + 250), 44)
            c = [PRIMARY, OK, SECONDARY, OK][i]
            d.rounded_rectangle((110, y + 70, 220, y + 180), radius=32, fill=c)
            d.text((165 - font(56, True).getlength(str(i + 1)) / 2, y + 92), str(i + 1), font=font(56, True), fill="#FFFFFF")
            d.text((260, y + 60), title, font=font(58, True), fill=INK)
            d.text((260, y + 150), sub, font=font(38), fill=MUTED)
        sc.add(0.1 + i * 0.16, row)
    return sc


def s_outro():
    sc = Scene(4.2)
    sc.add(0, lambda img, d: clay(img, (70, 300, W - 70, 1500), 56), rise=50)

    def name(img, d):
        fe_icon(img, 130, 380, 170)
        d.text((330, 400), "FE用語ドリル", font=font(76, True), fill=PRIMARY)
        d.text((330, 500), "基本情報の学習サイト", font=font(40), fill=MUTED)
    sc.add(0.15, name)
    sc.add(0.35, lambda img, d: center_text(d, 680, "無料・登録なし", font(84, True), INK))
    url = URL.replace("https://", "")
    uf = font(54, True, mono=True)
    uw = uf.getlength(url) + 100

    def url_btn(img, d):
        clay(img, ((W - uw) / 2, 840, (W + uw) / 2, 970), 65, fill=PRIMARY, border=PRIMARY, depth=12)
        center_text(d, 875, url, uf, "#FFFFFF")
    sc.add(0.55, url_btn)
    sc.add(0.75, lambda img, d: center_text(d, 1050, "プロフィールのリンクから", font(52, True), PRIMARY))

    def account(img, d):
        d.line((140, 1200, W - 140, 1200), fill=LINE, width=4)
        account_icon(img, 140, 1250, 130)
        d.text((300, 1265), "@it_senpai_lab", font=font(46, True, mono=True), fill=INK)
        d.text((300, 1335), "IT用語クイズを投稿中", font=font(38), fill=MUTED)
    sc.add(1.0, account)
    return sc


# ---------- 動画にする ----------

def encode(scenes, path, ffmpeg):
    total = sum(round(sc.sec * FPS) / FPS for sc in scenes)
    wav = path.with_suffix(".wav")
    fx.write_track(wav, total, [], music=False)   # リールは音なし（無音の音声トラックだけ）
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{RH}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "16", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev_last, n = None, 0
    for sc in scenes:
        for i in range(round(sc.sec * FPS)):
            t = i / FPS
            img = sc.render(t).convert("RGB")
            if prev_last is not None and t < FADE:
                img = Image.blend(prev_last, img, ease(t / FADE))
            p.stdin.write(img.tobytes())
            n += 1
        prev_last = sc.render(sc.sec).convert("RGB")
        print(".", end="", flush=True)
    p.stdin.close()
    ok = p.wait() == 0
    wav.unlink(missing_ok=True)
    print()
    if not ok:
        sys.exit(f"動画の変換に失敗しました: {path.name}")
    return n / FPS


def caption():
    return ("【基本情報の用語、スキマ時間に覚えよう】\n"
            "基本情報技術者試験（FE）の無料の学習サイト「FE用語ドリル」です。\n\n"
            f"・科目A: 用語{N_TERMS}語をカード・4択・書いて答える問題で\n"
            "・科目B: 擬似言語のプログラムを1行ずつ再生して、変数の変化を見る\n"
            f"・動く図（{N_FIGS}語）、用語タイピング、まちがえた用語の復習\n\n"
            "無料・登録なしで、スマホでそのまま使えます。プロフィールのリンクから。\n\n" + TAGS)


def youtube():
    title = "【基本情報】用語とプログラムを無料で練習できるサイト #Shorts"
    desc = ("基本情報技術者試験（FE）の用語とプログラムを練習できる無料の学習サイト「FE用語ドリル」です。\n\n"
            f"・科目A: 用語{N_TERMS}語（カード・4択・書いて答える・復習）\n"
            "・科目B: 擬似言語のプログラムを1行ずつ再生して変数の変化を見る\n\n"
            f"▶ サイト（無料・登録なし）: {URL}/?utm_source=youtube&utm_medium=video&utm_campaign=promo\n\n"
            "#基本情報技術者試験 #IT資格 #情報系学生 #資格勉強 #Shorts")
    return title, desc


def scenes():
    return [s_hook(), s_title(), s_numbers(), s_card(), s_quiz(), s_trace(), s_more(), s_outro()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_scenes = scenes()
    if "--stills" in sys.argv:   # 各場面の最後の画面だけを書き出す（確かめる用）
        for k, sc in enumerate(all_scenes):
            sc.render(sc.sec).convert("RGB").save(OUT / f"still-{k + 1}.jpg", "JPEG", quality=85)
        print("static/ig/promo/ に still-*.jpg を書き出しました")
        return
    sec = encode(all_scenes, OUT / "reel.mp4", mb.find_ffmpeg())
    title = all_scenes[1]
    title.render(title.sec).convert("RGB").save(OUT / "reel-cover.jpg", "JPEG", quality=88)
    yt_title, yt_desc = youtube()
    (OUT / "captions.txt").write_text(
        "■ リールの投稿文\n\n" + caption() +
        "\n\n\n■ YouTube ショートのタイトル\n\n" + yt_title +
        "\n\n\n■ YouTube ショートの説明\n\n" + yt_desc + "\n", encoding="utf-8")
    print(f"static/ig/promo/ に書き出しました（リール {sec:.1f} 秒・{FPS}fps・音なし・表紙・投稿文）")


if __name__ == "__main__":
    main()
