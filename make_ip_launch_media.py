"""「ITパスポート用語ドリル」を公開したことを知らせるリール動画を作る。一度だけ使う。

作るもの（static/ig/ip-launch/ に書き出す）:
  ・reel.mp4 / reel-cover.jpg   リール動画（1080×1920、60fps、約34秒、効果音つき。BGM は入れない）と表紙
  ・captions.txt               リールの投稿文、YouTube ショートのタイトルと説明

動き: 場面ごとに、部品（枠・文字）を下から順に出す。場面の間はふわっと切り替える。
      数字はカウントアップ、カードはめくる、4択は正解の色がふわっと付く。

使い方:  python make_ip_launch_media.py
         用語のデータは、デスクトップの ip-drill/data/terms.json から読む。
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import make_b_media as mb
import media_fx as fx
from make_b_media import BG, INK, LINE, MUTED, OK, OK_SOFT, PAPER, font, pill, wrap
from make_intro_media import ICON, W

ROOT = Path(__file__).parent
OUT = ROOT / "static" / "ig" / "ip-launch"
IP_TERMS = ROOT.parent / "ip-drill" / "data" / "terms.json"
IP_URL = "https://ip.yogo-drill.com"
RH, FPS = 1920, 60   # Instagram のリールは 23〜60fps まで受け付ける
ENTER = 0.45   # 部品が出てくるのにかける秒数
RISE = 70      # 部品が下から上がってくる距離（px）
FADE = 0.35    # 場面の切り替えにかける秒数
BLUE, BLUE_SOFT = "#2d68a8", "#dde8f5"
FIELDS = {"S": "ストラテジ系", "M": "マネジメント系", "T": "テクノロジ系"}
TAGS = "#ITパスポート #ITパスポート試験 #iパス #IT資格 #情報系学生 #IT用語 #資格勉強 #勉強垢 #基本情報技術者試験"

terms = json.loads(IP_TERMS.read_text(encoding="utf-8"))
BY_NAME = {t["term"]: t for t in terms}
N_TERMS = len(terms)
N_ABBR = sum(1 for t in terms if t.get("abbr"))
N_FE = sum(1 for t in terms if t.get("fe"))


def ease(x):
    """0〜1 を、なめらかに減速する動きにする。"""
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


# ---------- 部品と場面 ----------

class Part:
    """透明の画像に描いた部品。使うところだけ切り抜いて持つ。"""

    def __init__(self, draw_fn):
        img = Image.new("RGBA", (W, RH), (0, 0, 0, 0))
        draw_fn(img, ImageDraw.Draw(img))
        box = img.getbbox() or (0, 0, 1, 1)
        self.img, self.x, self.y = img.crop(box), box[0], box[1]

    def put(self, frame, p, dx=0, dy=0):
        if p <= 0:
            return
        im = self.img
        if p < 1:
            a = im.getchannel("A").point(lambda v: int(v * p))
            im = im.copy()
            im.putalpha(a)
        x, y = self.x + dx, self.y + dy
        fx, fy = x - math.floor(x), y - math.floor(y)
        if fx > 0.01 or fy > 0.01:
            # 1ピクセルより細かくずらす（止まる直前のカクつきをなくす）
            im = im.transform((im.width + 1, im.height + 1), Image.AFFINE, (1, 0, -fx, 0, 1, -fy), resample=Image.BICUBIC)
        frame.alpha_composite(im, (math.floor(x), math.floor(y)))


class Scene:
    def __init__(self, sec):
        self.sec = sec
        self.items = []    # 描く関数(frame, t)
        self.sounds = []   # (秒, 効果音の名前, 音量)

    def sfx(self, t, name, vol=1.0):
        self.sounds.append((t, name, vol))

    def add(self, t0, draw_fn, rise=RISE, sound=None, vol=0.45):
        """t0 秒に、下から上がりながら出てくる部品。sound を渡すと、出るときに効果音を鳴らす（ふだんは鳴らさない）。"""
        part = Part(draw_fn)
        self.items.append(lambda f, t: part.put(f, ease((t - t0) / ENTER), dy=(1 - ease((t - t0) / ENTER)) * rise))
        if sound:
            self.sfx(t0, sound, vol)
        return part

    def fade_in(self, t0, draw_fn, dur=0.3):
        """t0 秒に、その場でふわっと出てくる部品（正解の色など）。"""
        part = Part(draw_fn)
        self.items.append(lambda f, t: part.put(f, ease((t - t0) / dur)))

    def chara(self, x, bottom, poses, t0=0.0, scale=2, hops=(), sound="pop"):
        """キャラクター。x: 左の位置、bottom: 足元の位置。poses: [(秒, ポーズの名前)]（ポーズを切り替える）。
        出てくるときは、ぴょこっと大きくなる。ふだんは2コマで小さく上下する（ドット絵のゲームのように）。
        hops の秒に、ぴょんと跳ねる。"""
        if not fx.available():
            return
        poses = sorted(poses)
        # 2枚目のシート（b_ で始まるポーズ）は絵が小さいので、1.5倍の大きさで使う
        sprites = {n: fx.sprite(n, scale * 3 // 2 if n.startswith("b_") else scale) for _, n in poses}
        swaps = [t for t, _ in poses[1:]]

        def draw(f, t):
            if t < t0:
                return
            im = sprites[[n for tt, n in poses if t >= tt][-1]]
            p = (t - t0) / 0.35
            dy = -4 * (int(t * 3) % 2)
            for th in hops:
                dy += fx.hop(t, th)
            for ts in swaps:
                dy += fx.hop(t, ts, 24, 0.2)
            if p < 1:
                back = 1 + 2.70158 * (p - 1) ** 3 + 1.70158 * (p - 1) ** 2
                s = max(0.05, 0.3 + 0.7 * back)
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.NEAREST)
            cx = x + sprites[poses[0][1]].width / 2
            f.alpha_composite(im, (int(cx - im.width / 2), int(bottom - im.height + dy)))
        self.items.append(draw)
        if sound:
            self.sfx(t0, sound, 0.8)
        for th in hops:
            self.sfx(th, "jump", 0.8)

    def say(self, t0, text, anchor, side="up", until=None, style="talk"):
        """キャラクターのふきだし。文字が1つずつ出て、2文字ごとに「ピッ」と鳴る（昔のゲームの会話のように）。
        anchor: ふきだしのしっぽの先（キャラクターの頭の近く）。(x, y) か、秒を受けて (x, y) を返す関数（歩くときについていく）。
        side: ふきだしを置く向き。up=上 / left=左 / right=右 / down=下。text の「\\n」で改行。
        style: ふきだしの形。talk=ふつうに話す（角の丸い四角） / think=考え中（もくもく雲・しっぽは小さな丸）
               / shout=びっくり・うれしい（ギザギザ。文字は青）"""
        if not fx.available():
            return
        lines = text.split("\n")
        n_chars = sum(len(ln) for ln in lines)
        bf = font(40 if style == "shout" else 38, True)
        lh = int(bf.size * 1.42)
        tw = int(max(bf.getlength(ln) for ln in lines))
        th = lh * (len(lines) - 1) + bf.size
        # 文字の四角のまわりに、形ごとのすきまをとる（ex, ey: 文字の四角から、ふきだしの外側までの幅）
        ex, ey = {"talk": (26, 26), "think": (44, 40), "shout": (int(tw * 0.2) + 34, int(th * 0.35) + 40)}[style]
        gap = {"talk": 22, "think": 60, "shout": 30}[style]
        bw, bh = tw + ex * 2, th + ey * 2
        speed = 0.05

        def draw(f, t):
            if t < t0 or (until is not None and t >= until):
                return
            ax, ay = anchor(t) if callable(anchor) else anchor
            if side == "up":
                x0, y0 = ax - bw / 2, ay - gap - bh
            elif side == "down":
                x0, y0 = ax - bw / 2, ay + gap
            elif side == "left":
                x0, y0 = ax - gap - bw, ay - bh / 2
            else:
                x0, y0 = ax + gap, ay - bh / 2
            m = 46 if style == "think" else 20   # 雲は丸がふちからはみ出すので、内側に寄せる
            x0 = min(max(x0, m), W - m - bw)
            cx, cy = x0 + bw / 2, y0 + bh / 2
            d = ImageDraw.Draw(f)
            # ふきだしの、キャラクターに近いふちの点（しっぽの付け根）
            if side in ("up", "down"):
                ox, oy = min(max(ax, x0 + 40), x0 + bw - 40), (y0 + bh if side == "up" else y0)
            else:
                ox, oy = (x0 + bw if side == "left" else x0), min(max(ay, y0 + 30), y0 + bh - 30)
            if style == "talk":
                if side in ("up", "down"):
                    tip = [(ox - 16, oy), (ox + 16, oy), (ax, ay)]
                else:
                    tip = [(ox, oy - 16), (ox, oy + 16), (ax, ay)]
                d.polygon(tip, fill=PAPER, outline=INK, width=5)
                d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=22, fill=PAPER, outline=INK, width=5)
                if side in ("up", "down"):   # しっぽの付け根のふちを消して、ふきだしとつなげる
                    d.line((ox - 12, oy, ox + 12, oy), fill=PAPER, width=7)
                else:
                    d.line((ox, oy - 12, ox, oy + 12), fill=PAPER, width=7)
            elif style == "think":
                # しっぽは、キャラクターに向かって小さくなる3つの丸
                for k, r in ((0.2, 13), (0.5, 9), (0.8, 6)):
                    px, py = ox + (ax - ox) * k, oy + (ay - oy) * k
                    d.ellipse((px - r, py - r, px + r, py + r), fill=PAPER, outline=INK, width=4)
                # 雲: ふちに沿って丸を並べる（先に黒い丸でふちを描き、上から白い丸と四角でぬる）
                bumps, step = [], 52
                ix0, iy0, ix1, iy1 = x0 + 22, y0 + 22, x0 + bw - 22, y0 + bh - 22
                for x in range(int(ix0), int(ix1) + 1, step):
                    bumps += [(x, iy0), (x, iy1)]
                for y in range(int(iy0), int(iy1) + 1, step):
                    bumps += [(ix0, y), (ix1, y)]
                bumps += [(ix1, iy0), (ix1, iy1)]
                for r, col in ((30, INK), (25, PAPER)):
                    for bx, by in bumps:
                        d.ellipse((bx - r, by - r, bx + r, by + r), fill=col)
                    if col == PAPER:
                        d.rectangle((ix0, iy0, ix1, iy1), fill=PAPER)
            else:
                # ギザギザ: だ円の上に、外と内の点を交互に置く。しっぽは1本の長いトゲ
                rx, ry = bw / 2, bh / 2
                ang = math.atan2(ay - cy, ax - cx)
                d.polygon([(cx + math.cos(ang - 0.18) * rx * 0.7, cy + math.sin(ang - 0.18) * ry * 0.7),
                           (cx + math.cos(ang + 0.18) * rx * 0.7, cy + math.sin(ang + 0.18) * ry * 0.7), (ax, ay)],
                          fill=PAPER, outline=INK, width=5)
                pts, n = [], 26
                for k in range(n):
                    a = 2 * math.pi * k / n
                    s = 1.0 if k % 2 == 0 else 0.8
                    pts.append((cx + math.cos(a) * rx * s, cy + math.sin(a) * ry * s))
                d.polygon(pts, fill=PAPER, outline=INK, width=5)
                # しっぽの付け根の線を消す
                bx, by = cx + math.cos(ang) * rx * 0.72, cy + math.sin(ang) * ry * 0.72
                d.ellipse((bx - 16, by - 16, bx + 16, by + 16), fill=PAPER)
            color = BLUE if style == "shout" else INK
            shown = int((t - t0) / speed)
            for i, ln in enumerate(lines):
                part = ln[:max(0, shown)]
                shown -= len(ln)
                if part:
                    # 行ごとに真ん中にそろえる
                    d.text((cx - bf.getlength(ln) / 2, cy - th / 2 + i * lh), part, font=bf, fill=color)
        self.items.append(draw)
        for k in range(0, n_chars, 2):
            self.sfx(t0 + k * speed, "talk", 0.6)

    def walk(self, y_bottom, t0, dur, x_from=W + 40, x_to=-260, scale=2):
        """右から左へ歩いて横切る（歩く・横向きの2コマを交互に）。"""
        if not fx.available():
            return
        a, b = fx.sprite("walk1", scale), fx.sprite("walk2", scale)

        def draw(f, t):
            if not t0 <= t <= t0 + dur:
                return
            u = (t - t0) / dur
            im = a if int((t - t0) / 0.16) % 2 == 0 else b
            x = x_from + (x_to - x_from) * u
            f.alpha_composite(im, (int(x), int(y_bottom - im.height - 6 * (int((t - t0) / 0.16) % 2))))
        self.items.append(draw)
        k = 0
        while k * 0.32 < dur:
            self.sfx(t0 + k * 0.32, "step", 0.9)
            k += 1

    def custom(self, fn):
        self.items.append(fn)

    def render(self, t):
        frame = Image.new("RGBA", (W, RH), BG)
        for fn in self.items:
            fn(frame, t)
        return frame


def center_text(d, y, text, f, fill):
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)


def lines_at(d, x, y, lines, f, fill, gap=1.4):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def ip_icon(img, x, y, size):
    """ITパスポート用語ドリルのアイコン（青い角丸に IP）。"""
    s = 4
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, size * s - 1, size * s - 1), radius=size * s * 0.22, fill=BLUE)
    f = font(int(size * s * 0.5), True)
    bb = d.textbbox((0, 0), "IP", font=f)
    d.text(((size * s - (bb[2] - bb[0])) / 2 - bb[0], (size * s - (bb[3] - bb[1])) / 2 - bb[1]), "IP", font=f, fill=PAPER)
    img.alpha_composite(big.resize((size, size), Image.LANCZOS), (x, y))


def account_icon(img, x, y, size):
    if not ICON.exists():
        return
    im = Image.open(ICON).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    im.putalpha(mask)
    img.alpha_composite(im, (x, y))


def box(x1, y1, x2, y2, r=32):
    return lambda img, d: d.rounded_rectangle((x1, y1, x2, y2), radius=r, fill=PAPER, outline=LINE, width=2)


def head(sc, label):
    sc.add(0, lambda img, d: pill(d, 60, 200, label, BLUE, 34), rise=30)


# ---------- 場面 ----------

def s_hook():
    sc = Scene(3.4)
    sc.add(0, box(60, 380, W - 60, 1360, 40), rise=40)
    sc.add(0.15, lambda img, d: pill(d, 120, 450, "お知らせ", BLUE, 36))
    for i, ln in enumerate(["ITパスポートの", "用語サイトを", "公開しました"]):
        sc.add(0.3 + i * 0.15, lambda img, d, ln=ln, i=i: d.text((120, 590 + i * 130), ln, font=font(96, True), fill=INK))
    sc.add(0.95, lambda img, d: d.text((120, 1010), "FE用語ドリルの姉妹サイトです", font=font(44), fill=MUTED))
    return sc


def s_title():
    sc = Scene(3.0)
    # アイコンは少し小さい所から、はずむように大きくなる
    part = Part(lambda img, d: ip_icon(img, (W - 260) // 2, 380, 260))

    def pop(f, t):
        p = min(1.0, max(0.0, t / 0.5))
        if p <= 0:
            return
        back = 1 + 2.70158 * (p - 1) ** 3 + 1.70158 * (p - 1) ** 2   # 少し大きくなりすぎてから戻る
        s = 0.6 + 0.4 * back
        im = part.img.resize((max(1, int(part.img.width * s)), max(1, int(part.img.height * s))), Image.LANCZOS)
        if p < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * ease(p * 1.5))))
        cx, cy = part.x + part.img.width / 2, part.y + part.img.height / 2
        f.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
    sc.custom(pop)
    sc.add(0.25, lambda img, d: center_text(d, 720, "無料の学習サイト", font(48), MUTED))
    sc.add(0.4, lambda img, d: center_text(d, 810, "ITパスポート", font(116, True), BLUE))
    sc.add(0.55, lambda img, d: center_text(d, 960, "用語ドリル", font(116, True), BLUE))
    sc.add(0.9, lambda img, d: center_text(d, 1160, "スマホでそのまま・登録なし", font(50, True), INK))
    sc.sfx(0.4, "idea", 0.5)   # サイト名が出るときだけ「ピコーン」
    return sc


def s_numbers():
    sc = Scene(3.6)
    head(sc, "収録している用語")
    rows = [(N_TERMS, "3つの分野の用語"), (N_ABBR, "略語（KPI・SLA・DNS…）"), (N_FE, "基本情報（FE）とつながる用語")]
    nf = font(150, True, mono=True)
    for i, (n, sub) in enumerate(rows):
        y = 360 + i * 380
        t0 = 0.15 + i * 0.25

        def card(img, d, y=y, sub=sub):
            d.rounded_rectangle((60, y, W - 60, y + 330), radius=32, fill=PAPER, outline=LINE, width=2)
            d.text((120, y + 240), sub, font=font(44, True), fill=INK)
        sc.add(t0, card)

        # 数字は 0 から数え上げる（最後の桁数で「語」の位置を決める）
        def count(f, t, y=y, n=n, t0=t0):
            p = ease((t - t0 - 0.15) / 1.1)
            if t < t0 + 0.15:
                return
            d = ImageDraw.Draw(f)
            v = str(round(n * p))
            d.text((120, y + 60), v, font=nf, fill=BLUE)
            d.text((120 + nf.getlength(str(n)) + 16, y + 150), "語", font=font(60, True), fill=INK)
        sc.custom(count)
        sc.sfx(t0 + 0.95, "pop", 0.6)   # 数字が止まったときに1回だけ「ポッ」
    return sc


def s_fields():
    sc = Scene(3.0)
    head(sc, "試験の3つの分野")
    sc.add(0.1, lambda img, d: lines_at(d, 60, 320, ["分野ごとに", "覚えられる"], font(84, True), INK, 1.3))
    counts = {k: sum(t["field"] == k for t in terms) for k in FIELDS}
    examples = {"S": "経営戦略・法律・会計", "M": "開発・プロジェクト管理", "T": "ネットワーク・セキュリティ"}
    for i, (k, v) in enumerate(FIELDS.items()):
        y = 620 + i * 300

        def row(img, d, y=y, k=k, v=v):
            d.rounded_rectangle((60, y, W - 60, y + 260), radius=28, fill=PAPER, outline=LINE, width=2)
            d.text((120, y + 50), v, font=font(64, True), fill=BLUE)
            n = f"{counts[k]}語"
            d.text((W - 120 - font(52, True, mono=True).getlength(n), y + 58), n, font=font(52, True, mono=True), fill=INK)
            d.text((120, y + 160), examples[k], font=font(40), fill=MUTED)
        sc.add(0.35 + i * 0.18, row)
    return sc


def card_face(side):
    """カード1枚（表: 意味だけ / 裏: 用語と意味）。"""
    t = BY_NAME["KPI"]
    x, y, w, h = 60, 580, W - 120, 700

    def draw(img, d):
        d.rounded_rectangle((x, y, x + w, y + h), radius=28, fill=PAPER, outline=LINE, width=3)
        tag = f"{FIELDS[t['field']]}・{t['sub']}"
        f = font(30)
        tw = f.getlength(tag)
        d.rounded_rectangle((x + (w - tw) / 2 - 22, y + 40, x + (w + tw) / 2 + 22, y + 94), radius=10, outline=BLUE, width=2)
        d.text((x + (w - tw) / 2, y + 50), tag, font=f, fill=BLUE)
        df = font(48, True)
        yy = y + 170 if side == "back" else y + 200
        if side == "back":
            tf = font(110, True)
            d.text((x + (w - tf.getlength(t["term"])) / 2, yy), t["term"], font=tf, fill=BLUE)
            d.text((x + (w - font(34, mono=True).getlength(t["abbr"])) / 2, yy + 140), t["abbr"], font=font(34, mono=True), fill=MUTED)
            yy += 230
        for ln in wrap(t["desc"], df, w - 140):
            d.text((x + (w - df.getlength(ln)) / 2, yy), ln, font=df, fill=INK)
            yy += int(48 * 1.6)
        if side == "front":
            hint = "用語を思い浮かべてからタップ"
            d.text((x + (w - font(32).getlength(hint)) / 2, y + h - 100), hint, font=font(32), fill=MUTED)
    return Part(draw)


def s_card():
    sc = Scene(4.8)
    head(sc, "カードで覚える")
    sc.add(0.1, lambda img, d: lines_at(d, 60, 310, ["意味を読んで、", "用語を思い出す"], font(76, True), INK, 1.3))
    front, back = card_face("front"), card_face("back")
    T_IN, T_FLIP, DUR = 0.3, 2.1, 0.5

    def flip(f, t):
        if t < T_FLIP:
            p = ease((t - T_IN) / ENTER)
            front.put(f, p, dy=(1 - p) * RISE)
            return
        q = min(1.0, (t - T_FLIP) / DUR)
        part = front if q < 0.5 else back
        sx = abs(math.cos(q * math.pi))   # 幅が 1 → 0 → 1 になる（くるっとめくる）
        if sx < 0.02:
            return
        im = part.img.resize((max(1, int(part.img.width * sx)), part.img.height), Image.LANCZOS)
        f.alpha_composite(im, (int(part.x + (part.img.width - im.width) / 2), part.y))
    sc.custom(flip)

    for k, (lab, c) in enumerate([("まだ", BLUE), ("覚えた", OK)]):
        bx = 60 + k * ((W - 120) // 2 + 10)
        bw = (W - 120) // 2 - 10

        def btn(img, d, bx=bx, bw=bw, lab=lab, c=c):
            d.rounded_rectangle((bx, 1330, bx + bw, 1440), radius=24, fill=c)
            d.text((bx + (bw - font(42, True).getlength(lab)) / 2, 1360), lab, font=font(42, True), fill=PAPER)
        sc.add(T_FLIP + DUR + 0.1 + k * 0.12, btn, rise=40)
    sc.sfx(T_FLIP, "flip", 1.0)
    return sc


def quiz_data():
    t = BY_NAME["ランサムウェア"]
    rnd = random.Random(7)
    others = [x for x in terms if x["sub"] == t["sub"] and x["id"] != t["id"] and len(x["term"]) <= 12]
    choices = rnd.sample(others, 3) + [t]
    rnd.shuffle(choices)
    return t, [c["term"] for c in choices]


def s_quiz():
    sc = Scene(5.0)
    t, choices = quiz_data()
    head(sc, "4択クイズ")
    sc.add(0.1, lambda img, d: lines_at(d, 60, 310, ["この説明に当てはまる", "用語は？"], font(72, True), INK, 1.3))
    f = font(44)
    desc = wrap(t["desc"], f, W - 200)
    box_h = len(desc) * int(44 * 1.6) + 70

    def desc_box(img, d):
        d.rounded_rectangle((60, 540, W - 60, 540 + box_h), radius=20, fill=PAPER, outline=LINE, width=2)
        lines_at(d, 100, 575, desc, f, INK, 1.6)
    sc.add(0.3, desc_box)

    def choice(y, k, c, ok):
        def draw(img, d):
            d.rounded_rectangle((60, y, W - 60, y + 110), radius=18, fill=OK_SOFT if ok else PAPER, outline=OK if ok else LINE, width=3)
            d.ellipse((88, y + 32, 160, y + 78), outline=OK if ok else BLUE, width=4)
            d.text((110, y + 35), "アイウエ"[k], font=font(32, True), fill=OK if ok else BLUE)
            d.text((190, y + 30), c, font=font(42, True), fill=INK)
            if ok:
                d.text((W - 190, y + 32), "正解", font=font(38, True), fill=OK)
        return draw

    y0 = 540 + box_h + 50
    for k, c in enumerate(choices):
        y = y0 + k * 130
        sc.add(0.55 + k * 0.12, choice(y, k, c, False), rise=40)
        if c == t["term"]:
            sc.fade_in(3.0, choice(y, k, c, True))
    sc.sfx(3.0, "correct", 1.0)
    return sc


def s_more():
    sc = Scene(3.4)
    head(sc, "ほかにも")
    for i, (title, sub) in enumerate([("書いて答える", "説明を読んで、用語を入力する"),
                                      ("復習", "まちがえた用語だけを解き直す"),
                                      ("ミニテスト", "3分野から20問・分野ごとの正答率"),
                                      ("略語クイズ", f"略語{N_ABBR}語の正式名を覚える")]):
        y = 360 + i * 290

        def row(img, d, y=y, title=title, sub=sub):
            d.rounded_rectangle((60, y, W - 60, y + 250), radius=28, fill=PAPER, outline=LINE, width=2)
            d.ellipse((110, y + 62, 140, y + 92), fill=BLUE)
            d.text((170, y + 50), title, font=font(60, True), fill=INK)
            lines_at(d, 170, y + 140, wrap(sub, font(38), W - 290), font(38), MUTED, 1.4)
        sc.add(0.1 + i * 0.2, row)
    return sc


def s_fe():
    sc = Scene(3.0)
    head(sc, "基本情報（FE）を目指す人へ")
    sc.add(0.1, lambda img, d: lines_at(d, 60, 340, ["ITパスポートの", "その先も"], font(96, True), INK, 1.3))
    y = 340 + 2 * int(96 * 1.3) + 60
    sc.add(0.4, box(60, y, W - 60, y + 520))
    for i, ln in enumerate([f"FEにも出る用語 {N_FE}語は、", "用語のページから", "FE用語ドリルの解説に", "そのまま進めます"]):
        sc.add(0.55 + i * 0.1, lambda img, d, i=i, ln=ln: d.text((120, y + 60 + i * int(52 * 1.55)), ln, font=font(52, True), fill=INK), rise=30)
    return sc


def s_outro():
    sc = Scene(4.4)
    sc.add(0, box(60, 300, W - 60, 1460, 40), rise=40)

    def name(img, d):
        ip_icon(img, 120, 370, 160)
        d.text((310, 390), "ITパスポート", font=font(64, True), fill=BLUE)
        d.text((310, 470), "用語ドリル", font=font(64, True), fill=BLUE)
    sc.add(0.15, name)
    sc.add(0.35, lambda img, d: center_text(d, 650, "無料・登録なし", font(80, True), INK))
    url = IP_URL.replace("https://", "")
    uf = font(56, True, mono=True)
    uw = uf.getlength(url) + 80

    def url_pill(img, d):
        d.rounded_rectangle(((W - uw) / 2, 800, (W + uw) / 2, 920), radius=60, fill=BLUE_SOFT)
        center_text(d, 828, url, uf, BLUE)
    sc.add(0.55, url_pill)
    sc.add(0.75, lambda img, d: center_text(d, 1010, "プロフィールのリンクから", font(54, True), BLUE))

    def account(img, d):
        d.line((120, 1150, W - 120, 1150), fill=LINE, width=3)
        account_icon(img, 120, 1200, 120)
        d.text((270, 1215), "@it_senpai_lab", font=font(44, True, mono=True), fill=INK)
        d.text((270, 1280), "IT用語クイズを投稿中", font=font(36), fill=MUTED)
    sc.add(1.0, account)
    sc.sfx(0.5, "fanfare", 1.0)
    return sc


# ---------- 動画にする ----------

def encode(scenes, path, ffmpeg):
    # 効果音を1本の音にまとめる（場面の切り替えには「シュッ」）
    events, start = [], 0.0
    for k, sc in enumerate(scenes):
        if k:
            events.append((start, "whoosh", 0.4))   # 場面の切り替えは小さめに
        events += [(start + t, name, vol) for t, name, vol in sc.sounds]
        start += round(sc.sec * FPS) / FPS
    wav = path.with_suffix(".wav")
    fx.write_track(wav, start, events)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{RH}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-shortest",
           # Instagram が受け取ったあとにもう一度圧縮するので、元はきれいに（CRF 16）作っておく
           "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "16", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev_last, n = None, 0
    for sc in scenes:
        frames = round(sc.sec * FPS)
        for i in range(frames):
            t = i / FPS
            img = sc.render(t).convert("RGB")
            if prev_last is not None and t < FADE:   # 前の場面の最後の画面から、ふわっと切り替える
                img = Image.blend(prev_last, img, ease(t / FADE))
            p.stdin.write(img.tobytes())
            n += 1
        prev_last = sc.render(sc.sec).convert("RGB")
    p.stdin.close()
    ok = p.wait() == 0
    wav.unlink(missing_ok=True)
    if not ok:
        sys.exit(f"動画の変換に失敗しました: {path.name}")
    return n / FPS


def caption():
    return ("【ITパスポートの用語サイトを公開しました】\n"
            "FE用語ドリルの姉妹サイト「ITパスポート用語ドリル」をつくりました。\n\n"
            f"・用語{N_TERMS}語を、ストラテジ・マネジメント・テクノロジの3分野ごとに\n"
            "・カード・4択・書いて答える・復習\n"
            "・3分野から20問のミニテスト、略語クイズ\n"
            f"・基本情報（FE）にも出る用語{N_FE}語は、FE用語ドリルの解説へ進める\n\n"
            "無料・登録なしで、スマホでそのまま使えます。プロフィールのリンクから。\n\n" + TAGS)


def youtube():
    title = "【ITパスポート】用語を無料で覚えられるサイトを公開しました #Shorts"
    desc = ("ITパスポート試験の用語を、カードと4択で覚えられる無料の学習サイト「ITパスポート用語ドリル」を公開しました。\n\n"
            f"・用語{N_TERMS}語（ストラテジ系・マネジメント系・テクノロジ系）\n"
            "・カード・4択・書いて答える・復習・ミニテスト・略語クイズ\n\n"
            f"▶ サイト（無料・登録なし）: {IP_URL}/?utm_source=youtube&utm_medium=video&utm_campaign=ip_launch\n\n"
            "#ITパスポート #IT資格 #情報系学生 #資格勉強 #Shorts")
    return title, desc


def scenes():
    return [s_hook(), s_title(), s_numbers(), s_fields(), s_card(), s_quiz(), s_more(), s_fe(), s_outro()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_scenes = scenes()
    sec = encode(all_scenes, OUT / "reel.mp4", mb.find_ffmpeg())
    title = all_scenes[1]
    title.render(title.sec).convert("RGB").save(OUT / "reel-cover.jpg", "JPEG", quality=88)
    yt_title, yt_desc = youtube()
    (OUT / "captions.txt").write_text(
        "■ リールの投稿文\n\n" + caption() +
        "\n\n\n■ YouTube ショートのタイトル\n\n" + yt_title +
        "\n\n\n■ YouTube ショートの説明\n\n" + yt_desc + "\n", encoding="utf-8")
    print(f"static/ig/ip-launch/ に書き出しました（リール {sec:.1f} 秒・{FPS}fps・表紙・投稿文）")


if __name__ == "__main__":
    main()
