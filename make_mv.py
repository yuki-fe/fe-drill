"""曲「データ構造の心」の MV（縦長 1080×1920・60fps）を作る。

歌詞のまとまり（10個）ごとに場面を変え、歌詞の1行ごとに図が1つ進む。
歌詞は画面の下に出し、歌う時間に合わせて左から色が変わる（カラオケ）。
箱は曲のテンポで弾む（レゲエの裏拍）。

使うファイル（notes/動画のサンプル/、公開しない）
- データ構造の心.mp3          曲
- データ構造の心_歌詞.txt      歌詞（空行でまとまりを分ける）
- データ構造の心_時間.json     各行の [開始秒, 終了秒]（音声認識と歌詞の突き合わせで作る。手で直してもよい）

    python make_mv.py            # 全部（数十分かかる）
    python make_mv.py --still    # 各場面の静止画だけ（確認用）
    python make_mv.py --from 40 --sec 20   # 40秒目から20秒だけ（確認用）
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "データ構造の心"
WORK = ROOT / "notes" / "曲の動画" / "作業用"   # 確認用の静止画・短い書き出し
SONG = DIR / "データ構造の心.mp3"
LYRICS = DIR / "データ構造の心_歌詞.txt"
TIMES = DIR / "データ構造の心_時間.json"
OUT = DIR / "データ構造の心_MV.mp4"
W, H, FPS = 1080, 1920, 60

FONT_R = "C:/Windows/Fonts/BIZ-UDGothicR.ttc"
FONT_B = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"
_fonts = {}


def font(size, bold=True):
    k = (int(size), bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FONT_B if bold else FONT_R, int(size), index=1)
    return _fonts[k]


# 色: 夜の深い緑に、レゲエの金・赤・緑をすこし
BG1, BG2 = (14, 32, 28), (22, 18, 30)
CREAM = (244, 234, 213)
MUTED = (150, 168, 158)
GOLD = (242, 193, 78)
RED = (228, 87, 70)
GREEN = (92, 190, 128)
BLUE = (110, 168, 230)
PURPLE = (190, 130, 230)
CELL = (34, 56, 50)
CELL_LINE = (88, 120, 108)
HOT = (70, 52, 22)


# ---------- 曲 ----------

def analyze():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    SR = 22050
    raw = subprocess.run([ff, "-v", "quiet", "-i", str(SONG), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    dur = len(x) / SR
    fr = 512
    env = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, len(x) - fr, fr)])
    on = np.maximum(0, np.diff(env))
    on -= on.mean()
    ac = np.correlate(on, on, "full")[len(on) - 1:]
    fps = SR / fr
    bpm = max(np.arange(60, 181, 0.25), key=lambda b: np.interp(fps * 60 / b, np.arange(len(ac)), ac) + 0.5 * np.interp(fps * 120 / b, np.arange(len(ac)), ac))
    period = fps * 60 / bpm
    ph = max(np.arange(0, period, 0.25), key=lambda p: on[np.arange(p, len(on), period).astype(int)].sum())
    hop = SR // 30
    lv = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    return float(bpm), float(ph / fps), dur, lv / (np.percentile(lv, 95) + 1e-9)


BPM, T0, DUR, LEVEL = analyze()
BEAT = 60 / BPM


def beat(t):
    return (t - T0) / BEAT


def off_pulse(t):
    """裏拍（拍と拍のまん中）で 1 になって、すぐ消える。"""
    f = beat(t) % 1 - 0.5
    return max(0.0, 1 - abs(f) / 0.2) ** 2


def level(t):
    return float(LEVEL[min(max(int(t * 30), 0), len(LEVEL) - 1)])


def ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    p = min(max(p, 0.0), 1.0)
    return tuple(int(lerp(a, b, p)) for a, b in zip(c1, c2))


# ---------- 歌詞と時間 ----------

def load_lyrics():
    blocks, cur = [], []
    for ln in LYRICS.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            cur.append(ln.strip())
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    times = json.loads(TIMES.read_text(encoding="utf-8"))
    rows, k = [], 0
    for b, lines in enumerate(blocks):
        for i, text in enumerate(lines):
            s, e = times[k]
            rows.append({"block": b, "i": i, "text": text, "s": s, "e": e})
            k += 1
    return blocks, rows


BLOCKS, ROWS = load_lyrics()


class Ctx:
    """場面に渡す情報。li = 今の行の番号（まとまりの中で。最初の行の前は -1）、lp = その行の進み具合。"""

    def __init__(self, t, block):
        self.t = t
        self.rows = [r for r in ROWS if r["block"] == block]
        self.li, self.lp = -1, 0.0
        for r in self.rows:
            if t >= r["s"] - 0.15:
                self.li = r["i"]
                self.lp = ease((t - r["s"]) / max(0.6, r["e"] - r["s"]))
        self.start = self.rows[0]["s"]

    def p(self, i, length=1.0):
        """i 行目の歌い出しからの、動きの進み具合 0〜1。"""
        r = self.rows[min(i, len(self.rows) - 1)]
        return ease((self.t - r["s"] + 0.15) / length)

    def since(self, i):
        r = self.rows[min(i, len(self.rows) - 1)]
        return self.t - r["s"]


# ---------- 描く部品 ----------

def rbox(d, x, y, w, h, fill=CELL, line=CELL_LINE, r=18, width=4):
    d.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=fill, outline=line, width=width)


def label(d, x, y, s, size=56, fill=CREAM, bold=True, anchor="mm"):
    d.text((x, y), s, font=font(size, bold), fill=fill, anchor=anchor)


def chip(d, cx, cy, s, w=150, h=110, fill=CELL, line=CELL_LINE, tcol=CREAM, size=52):
    rbox(d, cx - w / 2, cy - h / 2, w, h, fill, line)
    if s:
        label(d, cx, cy + 2, s, size, tcol)


def arrow(d, x1, y1, x2, y2, col=CREAM, width=7, head=24):
    ang = math.atan2(y2 - y1, x2 - x1)
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 2:
        return
    head = min(head, L * 0.6)
    bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
    d.line((x1, y1, bx, by), fill=col, width=width)
    d.polygon([(x2, y2), (bx + head * 0.55 * math.sin(ang), by - head * 0.55 * math.cos(ang)),
               (bx - head * 0.55 * math.sin(ang), by + head * 0.55 * math.cos(ang))], fill=col)


def fade(c, p):
    return mix(BG1, c, p)


def key_icon(d, x, y, col, s=1.0):
    r = 22 * s
    d.ellipse((x - r, y - r, x + r, y + r), outline=col, width=int(9 * s))
    d.rectangle((x + r, y - 5 * s, x + r + 70 * s, y + 5 * s), fill=col)
    d.rectangle((x + r + 46 * s, y, x + r + 56 * s, y + 20 * s), fill=col)
    d.rectangle((x + r + 62 * s, y, x + r + 70 * s, y + 14 * s), fill=col)


def lock_icon(d, x, y, col, open_=0.0):
    d.arc((x - 26, y - 62 - 30 * open_, x + 26, y - 10 - 30 * open_), 180, 360, fill=col, width=9)
    d.line((x + 26, y - 36 - 30 * open_, x + 26, y - 14), fill=col, width=9)
    if open_ < 0.5:
        d.line((x - 26, y - 36 - 30 * open_, x - 26, y - 14), fill=col, width=9)
    d.rounded_rectangle((x - 40, y - 18, x + 40, y + 42), radius=10, fill=col)


def heart(d, x, y, s, col):
    pts = []
    for k in range(60):
        a = k / 60 * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((x + hx * s, y - hy * s))
    d.polygon(pts, fill=col)


def check(d, x, y, col, s=1.0):
    d.line((x - 18 * s, y, x - 4 * s, y + 14 * s, x + 20 * s, y - 14 * s), fill=col, width=int(8 * s), joint="curve")


# ---------- 背景 ----------

def make_bg():
    g = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(BG1)[None, None, :] * (1 - g) + np.array(BG2)[None, None, :] * g).repeat(W, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


BG = make_bg()


def draw_bg(d, t):
    p = off_pulse(t)
    for gy in range(6):
        for gx in range(9):
            x, y = 60 + gx * 120, 470 + gy * 170
            k = 0.2 + 0.6 * p * (0.5 + 0.5 * math.sin(gx * 1.3 + gy * 0.7 + beat(t) * 0.5))
            r = 4 + 3 * p
            d.ellipse((x - r, y - r, x + r, y + r), fill=mix(BG1, (60, 90, 80), k))
    lv = level(t)
    for i in range(36):
        x = 30 + i * 29
        h = 8 + 40 * lv * (0.55 + 0.45 * math.sin(i * 0.9 + t * 3.1)) + 18 * p * (0.5 + 0.5 * math.cos(i * 0.6))
        d.rounded_rectangle((x, 1890 - h, x + 16, 1890), radius=8, fill=mix(BG1, (GOLD, GREEN, RED)[i % 3], 0.5))


def header(d, num, title, sub):
    label(d, W / 2, 130, "データ構造の心", 38, MUTED, bold=False)
    label(d, W / 2, 215, f"#{num}", 42, GOLD)
    label(d, W / 2, 300, title, 88, CREAM)
    label(d, W / 2, 382, sub, 36, MUTED, bold=False)


def lyric_band(img, t):
    """今の行を出し、歌う時間に合わせて左から金色に変える。"""
    cur = None
    for r in ROWS:
        if r["s"] - 0.35 <= t < r["e"] + 0.6:
            cur = r
    if not cur:
        return
    nxt = [r for r in ROWS if r["s"] > cur["s"]]
    a = ease(min((t - cur["s"] + 0.35) / 0.3, (cur["e"] + 0.6 - t) / 0.3 if not (nxt and nxt[0]["s"] - 0.35 <= t) else 1))
    text = cur["text"]
    size = 54
    while font(size).getlength(text) > 960 and size > 30:
        size -= 2
    f = font(size)
    tw = f.getlength(text)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 1590, W - 40, 1770), radius=34, fill=mix(BG1, (6, 14, 12), a))
    x0, y = (W - tw) / 2, 1680
    d.text((x0, y), text, font=f, fill=mix(BG1, CREAM, a), anchor="lm")
    prog = ease((t - cur["s"]) / max(0.5, cur["e"] - cur["s"]))
    if prog > 0:
        hl = Image.new("L", (W, 120), 0)
        ImageDraw.Draw(hl).text((x0, 60), text, font=f, fill=255, anchor="lm")
        cut = int(x0 + tw * prog)
        hl.paste(0, (cut, 0, W, 120))
        img.paste(Image.new("RGB", (W, 120), mix(BG1, GOLD, a)), (0, y - 60), hl)


# ---------- 場面 ----------

def sc_intro(d, c, t):
    title = "データ構造の心"
    st = max(0.0, t - 0.4)
    for i, ch in enumerate(title):
        p = ease((st - i * BEAT * 0.5) / 0.5)
        if p <= 0:
            continue
        x = W / 2 + (i - (len(title) - 1) / 2) * 118
        label(d, x, 760 - 60 * (1 - p) - 14 * off_pulse(t) * (i % 2), ch, 118, fade(CREAM, p))
    p = ease((st - 4 * BEAT) / 1.0)
    label(d, W / 2, 900, "基本情報技術者試験のうた", 46, fade(GOLD, p))
    tags = ["CPU", "記憶", "スタック", "暗号", "OSI", "TCP", "稼働率", "SQL", "PDCA", "RAID"]
    for i, s in enumerate(tags):
        q = ease((st - (6 + i * 0.5) * BEAT) / 0.5)
        r_, k = divmod(i, 5)
        x, y = 150 + k * 195, 1110 + r_ * 150 - 12 * off_pulse(t) * ((i + r_) % 2)
        chip(d, x, y + 30 * (1 - q), s, 175, 110, fade(CELL, q), fade((GOLD, GREEN, BLUE, RED, PURPLE)[i % 5], q), fade(CREAM, q), 36)


def sc_boot(d, c, t):
    chain = ["電源", "POST", "BIOS", "OS"]
    xs = [150 + i * 260 for i in range(4)]
    y = 600
    lit = [c.p(0, 0.6), ease((c.since(0) - 1.6) / 0.5), c.p(1, 0.6), ease((c.since(1) - 1.8) / 0.5)]
    for i, s in enumerate(chain):
        q = lit[i]
        chip(d, xs[i], y - 10 * off_pulse(t) * q, s, 200, 120, mix(CELL, HOT, q), mix(CELL_LINE, GOLD, q), CREAM, 46)
        if i:
            arrow(d, xs[i - 1] + 104, y, xs[i] - 104, y, mix(CELL_LINE, GOLD, q), 6, 20)
    # POST の点検
    q = c.p(0, 0.6)
    for k, s in enumerate(["CPU", "メモリ", "キーボード"]):
        r = ease((c.since(0) - 0.4 - k * 0.35) / 0.3)
        label(d, 150, 730 + k * 56, s, 34, fade(MUTED, q), False, "lm")
        if r > 0:
            check(d, 340, 730 + k * 56, fade(GREEN, r), 0.9)
    # 命令の輪: フェッチ → 解読 → 実行
    q = c.p(2, 0.8)
    cx, cy, R = W / 2, 1180, 200
    if q > 0:
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=fade(CELL_LINE, q), width=6)
        names = ["フェッチ", "解読", "実行"]
        ang = [-90, 30, 150]
        loop = max(0.0, c.since(2)) / (2 * BEAT)
        now = int(loop) % 3
        for k, (n, a) in enumerate(zip(names, ang)):
            x, y2 = cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))
            on = k == now
            chip(d, x, y2, n, 200, 96, fade(HOT if on else CELL, q), fade(GOLD if on else CELL_LINE, q), fade(CREAM, q), 38)
        a = math.radians(-90 + loop * 120)
        d.ellipse((cx + (R - 70) * math.cos(a) - 16, cy + (R - 70) * math.sin(a) - 16, cx + (R - 70) * math.cos(a) + 16, cy + (R - 70) * math.sin(a) + 16), fill=fade(GOLD, q))
        label(d, cx, cy, "CPU", 54, fade(CREAM, q))
        if c.li >= 3:
            label(d, cx, cy + 56, f"{int(loop) // 3 + 1} 周目", 30, MUTED, False)


def sc_memory(d, c, t):
    layers = [("レジスタ", 300, GOLD), ("キャッシュ", 560, GREEN), ("主記憶", 820, BLUE)]
    for k, (n, w, col) in enumerate(layers):
        q = ease((c.since(0) - k * 0.45) / 0.5) if c.li >= 0 else 0
        y = 560 + k * 170
        chip(d, W / 2 - 40, y + 20 * (1 - q), n, w, 130, fade(CELL, q), fade(col, q), fade(CREAM, q), 48)
    q = c.p(1, 0.8)
    if q > 0:
        arrow(d, 1010, 940, 1010, 560, fade(GOLD, q), 7, 26)
        label(d, 1010, 520, "速い", 36, fade(GOLD, q))
        arrow(d, 70, 940, 70, 560, fade(RED, q), 7, 26)
        label(d, 70, 520, "高い", 36, fade(RED, q))
    # ヒットとミス
    q = c.p(2, 0.6)
    if q > 0:
        k = int(max(0.0, c.since(2)) / (2 * BEAT))
        hit = k % 4 != 3
        f = ease((max(0.0, c.since(2)) % (2 * BEAT)) / (BEAT * 1.2))
        ty = 730 if hit else 900
        x = lerp(W / 2 - 40, W / 2 + 330, f)
        label(d, W / 2 - 40, 1120, f"ヒット率 {min(99, 70 + k * 5)}%", 48, fade(GOLD, q))
        chip(d, W / 2 + 330, ty, "ヒット!" if hit else "ミス…", 200, 80, fade(HOT if hit else CELL, q * f), fade(GREEN if hit else RED, q * f), fade(CREAM, q * f), 36)
        d.ellipse((x - 14, ty - 14, x + 14, ty + 14), fill=fade(GOLD, q))
    # 駆け上がる
    q = c.p(3, 0.5)
    if q > 0:
        f = ease(c.since(3) / (4 * BEAT))
        y = lerp(1000, 520, f)
        x = W / 2 - 40 + 30 * math.sin(f * 12)
        label(d, x, y, "▲", 50, fade(GOLD, q))
        label(d, W / 2, 1230, "近いほど速い　小さいほど高い", 40, fade(MUTED, q), False)


def sc_stackqueue(d, c, t):
    # 左: スタック
    cx, bottom, sw, sh = 260, 1200, 280, 96
    q0 = c.p(0, 0.6) if c.li >= 0 else 0
    col_l = fade(CREAM, q0)
    d.line((cx - sw / 2 - 16, 640, cx - sw / 2 - 16, bottom + 12), fill=col_l, width=7)
    d.line((cx + sw / 2 + 16, 640, cx + sw / 2 + 16, bottom + 12), fill=col_l, width=7)
    d.line((cx - sw / 2 - 20, bottom + 12, cx + sw / 2 + 20, bottom + 12), fill=col_l, width=7)
    label(d, cx, 560, "スタック LIFO", 42, fade(GOLD, q0))
    ops = ["想", "い", "出", "-", "-", "君", "-", "-"]
    ops_q = ["君", "僕", "夢", "-", "-", "今", "-", "-"]
    cols = [GREEN, BLUE, GOLD, RED]

    def run(seq, sec, queue):
        k = int(max(0.0, sec) / (2 * BEAT))
        p = ease((max(0.0, sec) % (2 * BEAT)) / (BEAT * 1.0))
        k %= len(seq) + 2
        st = []
        for op in seq[:min(k, len(seq))]:
            if op != "-":
                st.append(op)
            elif st:
                st.pop(0 if queue else -1)
        cur = seq[k] if k < len(seq) else None
        return st, cur, p

    if c.li >= 0:
        st, cur, p = run(ops, c.since(0), False)
        for n, it in enumerate(st):
            y = bottom - (n + 1) * (sh + 8) + sh / 2
            if cur == "-" and n == len(st) - 1:
                chip(d, cx + 200 * p, lerp(y, 600, p), it, sw, sh, CELL, mix(cols[n % 4], BG1, p), mix(CREAM, BG1, p), 44)
            else:
                chip(d, cx, y - (8 * off_pulse(t) if n == len(st) - 1 else 0), it, sw, sh, CELL, cols[n % 4], CREAM, 44)
        if cur and cur != "-":
            chip(d, cx, lerp(520, bottom - (len(st) + 1) * (sh + 8) + sh / 2, p), cur, sw, sh, CELL, cols[len(st) % 4], CREAM, 44)
    # 右: キュー（縦に並べる。上が先頭）
    qx, w = 800, 280
    q1 = c.p(1, 0.6) if c.li >= 1 else 0
    label(d, qx, 560, "キュー FIFO", 42, fade(GOLD, q1))
    if q1 > 0:
        d.line((qx - w / 2 - 16, 640, qx - w / 2 - 16, 1212), fill=fade(CREAM, q1), width=7)
        d.line((qx + w / 2 + 16, 640, qx + w / 2 + 16, 1212), fill=fade(CREAM, q1), width=7)
        label(d, qx, 1250, "後ろから入る", 30, fade(MUTED, q1), False)
        label(d, qx, 615, "前から出る ↑", 30, fade(MUTED, q1), False)
        st, cur, p = run(ops_q, c.since(1), True)
        slot = lambda n: 700 + n * (sh + 8)
        for n, it in enumerate(st):
            if cur == "-":
                if n == 0:
                    chip(d, qx + 200 * p, lerp(slot(0), 520, p), it, w, sh, CELL, mix(cols[n % 4], BG1, p), mix(CREAM, BG1, p), 44)
                    continue
                y = lerp(slot(n), slot(n - 1), p)
            else:
                y = slot(n)
            chip(d, qx, y - 8 * off_pulse(t) * (n % 2), it, w, sh, CELL, cols[(n + 1) % 4], CREAM, 44)
        if cur and cur != "-":
            chip(d, qx, lerp(1400, slot(len(st)), p), cur, w, sh, CELL, cols[(len(st) + 1) % 4], CREAM, 44)
    q = c.p(3, 0.8)
    if q > 0:
        label(d, W / 2, 1400, "データ構造が　心を整理する", 46, fade(CREAM, q))


def sc_security(d, c, t):
    # C・I・A の3つの円
    q = c.p(0, 0.8) if c.li >= 0 else 0
    small = ease((c.since(2) + 0.2) / 0.8) if c.li >= 2 else 0
    cx, cy = W / 2, lerp(860, 600, small)
    R = lerp(150, 70, small)
    dist = lerp(140, 70, small)
    names = [("機密性", "C", BLUE), ("完全性", "I", GREEN), ("可用性", "A", GOLD)]
    for k, (n, s, col) in enumerate(names):
        r = ease((c.since(0) - k * 0.5) / 0.5) if c.li >= 0 else 0
        a = math.radians(-90 + k * 120)
        x, y = cx + dist * math.cos(a), cy + dist * math.sin(a)
        d.ellipse((x - R, y - R, x + R, y + R), outline=fade(col, r), width=7)
        label(d, x + 0.55 * R * math.cos(a), y + 0.55 * R * math.sin(a), s if small > 0.5 else n, lerp(46, 34, small), fade(col, r))
    hq = c.p(1, 0.6) * (1 - small)
    if hq > 0:
        heart(d, cx, cy + 8, 3.2 + 0.5 * off_pulse(t), fade(RED, hq))
    # 手紙・公開鍵・秘密鍵
    if c.li >= 2:
        y = 980
        sealed = c.p(2, 1.0)
        opened = c.p(3, 1.0) if c.li >= 3 else 0
        lx = lerp(260, 820, ease((c.since(2) - 0.8) / 1.5))
        rbox(d, lx - 110, y - 70, 220, 140, (236, 226, 204), CREAM, 10, 3)
        d.line((lx - 110, y - 70, lx, y + 5, lx + 110, y - 70), fill=(150, 140, 120), width=4)
        if sealed > 0:
            lock_icon(d, lx, y + 20, mix(RED, (120, 40, 30), 0.2), opened)
        key_icon(d, 170, y - 160, fade(GREEN, sealed), 1.0)
        label(d, 230, y - 110, "公開鍵", 32, fade(GREEN, sealed))
        if opened > 0:
            key_icon(d, 800, y - 160, fade(RED, opened), 1.0)
            label(d, 860, y - 110, "秘密鍵", 32, fade(RED, opened))
    # ハッシュ
    if c.li >= 4:
        q = c.p(4, 0.8)
        y = 1250
        label(d, 150, y, "手紙", 40, fade(CREAM, q), anchor="lm")
        arrow(d, 260, y, 400, y, fade(MUTED, q), 6, 20)
        label(d, 410, y, "h( ) →", 40, fade(MUTED, q), anchor="lm")
        label(d, 600, y, "7f3a…c9", 44, fade(GOLD, q), anchor="lm")
        r = ease((c.since(4) - 1.0) / 0.5)
        if r > 0:
            check(d, 900, y, fade(GREEN, r), 1.4)
            label(d, 950, y, "一致", 34, fade(GREEN, r), anchor="lm")
    # ディジタル署名
    if c.li >= 5:
        q = c.p(5, 0.6)
        s = 1 + 0.6 * (1 - q)
        x, y = 820, 1370
        d.ellipse((x - 70 * s, y - 70 * s, x + 70 * s, y + 70 * s), outline=fade(RED, q), width=8)
        label(d, x, y, "署名", int(40 * s), fade(RED, q))
        label(d, 160, 1370, "「僕だよ」", 52, fade(CREAM, q), anchor="lm")


def sc_osi(d, c, t):
    layers = ["物理", "データリンク", "ネットワーク", "トランスポート", "セッション", "プレゼンテーション", "アプリケーション"]
    cols = [RED, GOLD, GREEN, BLUE, PURPLE, GOLD, GREEN]
    lit_at = [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0)]
    base = 1330
    for k, n in enumerate(layers):
        y = base - k * 112
        q = ease((c.since(0) - k * 0.18) / 0.4) if c.li >= 0 else 0
        li, part = lit_at[k]
        on = 0.0
        if c.li >= li:
            on = ease((c.since(li) - part * 0.7) / 0.4)
        w = 640
        rbox(d, (W - w) / 2, y - 48 - 6 * off_pulse(t) * on, w, 96, fade(mix(CELL, HOT, on), q), fade(mix(CELL_LINE, cols[k], on), q), 16, 4)
        label(d, (W - w) / 2 - 30, y, str(k + 1), 44, fade(mix(MUTED, cols[k], on), q), anchor="rm")
        label(d, W / 2, y, n + "層", 42, fade(CREAM, q))
    # データが下から上へ
    if c.li >= 3:
        f = ease(c.since(3) / 2.4)
        y = lerp(base, base - 6 * 112, f)
        x = (W + 640) / 2 + 70
        rbox(d, x - 40, y - 30, 80, 60, HOT, GOLD, 10)
        label(d, x, y, "✉", 36, GOLD)
        if f >= 1:
            label(d, W / 2, 470, "届いた!", 52, GOLD)


def sc_net(d, c, t):
    # 4つの小さな場面を、行ごとに切り替える
    rows = [("DNS", "名前 → IPアドレス"), ("DHCP", "アドレスを配る"), ("TCP", "確かに届ける"), ("UDP", "速さで勝負")]
    for k, (n, s) in enumerate(rows):
        on = k == c.li
        q = 1.0 if on else 0.35
        chip(d, 140 + k * 267, 520, n, 230, 90, mix(CELL, HOT, 1 if on else 0), GOLD if on else CELL_LINE, fade(CREAM, q), 40)
    if c.li < 0:
        return
    p = c.lp
    sec = c.since(c.li)
    label(d, W / 2, 640, rows[c.li][1], 46, GOLD)
    if c.li == 0:
        chip(d, 250, 900, "fe.yogo-drill.com", 400, 100, CELL, BLUE, CREAM, 34)
        arrow(d, 460, 900, lerp(460, 600, ease(sec / 0.8)), 900, GOLD)
        q = ease((sec - 0.8) / 0.6)
        chip(d, 820, 900, "185.199.○.○", 380, 100, fade(CELL, q), fade(GREEN, q), fade(CREAM, q), 36)
        label(d, W / 2, 1100, "名前から、住所（IPアドレス）を調べる", 38, MUTED, False)
    elif c.li == 1:
        chip(d, W / 2, 820, "DHCPサーバ", 360, 110, CELL, BLUE, CREAM, 42)
        for k in range(3):
            x = 220 + k * 320
            q = ease((sec - k * 0.4) / 0.6)
            arrow(d, W / 2, 880, lerp(W / 2, x, q), lerp(880, 1060, q), fade(GOLD, q), 5, 18)
            chip(d, x, 1130, "PC", 160, 90, CELL, CELL_LINE, CREAM, 40)
            label(d, x, 1220, f"192.168.1.{10 + k}", 32, fade(GREEN, ease((sec - k * 0.4 - 0.6) / 0.4)))
    elif c.li == 2:
        chip(d, 170, 950, "送る", 180, 100, CELL, BLUE, CREAM, 40)
        chip(d, 910, 950, "受ける", 180, 100, CELL, GREEN, CREAM, 40)
        for k in range(3):
            f = (sec * 0.9 - k * 0.5)
            if 0 < f < 1:
                x = lerp(280, 800, ease(f))
                rbox(d, x - 36, 880, 72, 50, HOT, GOLD, 8)
            if f > 1:
                g = ease(f - 1)
                if g < 1:
                    x = lerp(800, 280, g)
                    label(d, x, 1040, "ACK", 32, GREEN)
                check(d, 250 + k * 60, 1150, GREEN, 0.9)
        label(d, W / 2, 1250, "届いたら「受け取ったよ」と返す", 38, MUTED, False)
    else:
        chip(d, 170, 950, "送る", 180, 100, CELL, BLUE, CREAM, 40)
        chip(d, 910, 950, "受ける", 180, 100, CELL, GREEN, CREAM, 40)
        for k in range(8):
            f = (sec * 2.2 - k * 0.35) % 2.4
            if f < 1:
                x = lerp(280, 800, f)
                yy = 950 + (k % 3 - 1) * 50
                lost = k % 5 == 3
                if lost and f > 0.6:
                    continue
                rbox(d, x - 26, yy - 18, 52, 36, (40, 50, 70), BLUE, 6)
        label(d, W / 2, 1250, "返事を待たずに、どんどん送る", 38, MUTED, False)


def sc_avail(d, c, t):
    # 時間の帯: 動いている時間（緑）と修理の時間（赤）
    segs = [(0, 3.2, 1), (3.2, 3.8, 0), (3.8, 7.6, 1), (7.6, 8.1, 0), (8.1, 10, 1)]
    x0, x1, y = 90, 990, 640
    show = c.p(0, 1.6) if c.li >= 0 else 0
    red = c.p(1, 0.6) if c.li >= 1 else 0
    for a, b, up in segs:
        xa, xb = lerp(x0, x1, a / 10), lerp(x0, x1, b / 10)
        if xa > lerp(x0, x1, show):
            continue
        xb = min(xb, lerp(x0, x1, show))
        col = GREEN if up else mix(GREEN, RED, red)
        d.rounded_rectangle((xa, y - 30, xb, y + 30), radius=8, fill=col)
    label(d, x0, y - 70, "MTBF：壊れずに動いた時間", 36, fade(GREEN, show), anchor="lm")
    label(d, x0, y + 80, "MTTR：直るまでの時間", 36, fade(RED, red), anchor="lm")
    q = c.p(2, 0.8) if c.li >= 2 else 0
    if q > 0:
        label(d, W / 2, 870, "稼働率 =", 50, fade(CREAM, q))
        label(d, W / 2, 960, "MTBF", 56, fade(GREEN, q))
        d.line((W / 2 - 290, 1010, W / 2 + 290, 1010), fill=fade(CREAM, q), width=5)
        label(d, W / 2, 1065, "MTBF ＋ MTTR", 56, fade(CREAM, q))
    q = c.p(3, 0.6) if c.li >= 3 else 0
    if q > 0:
        y = 1260
        chip(d, 130, y, "A", 90, 80, fade(CELL, q), fade(GOLD, q), fade(CREAM, q), 40)
        d.line((175, y, 245, y), fill=fade(CREAM, q), width=5)
        chip(d, 290, y, "A", 90, 80, fade(CELL, q), fade(GOLD, q), fade(CREAM, q), 40)
        label(d, 210, y + 90, "直列 0.9×0.9", 32, fade(MUTED, q), False)
        label(d, 210, y + 140, "= 0.81", 44, fade(GOLD, q))
        r = ease((c.since(3) - 1.0) / 0.6)
        x = 760
        d.line((600, y, 660, y), fill=fade(CREAM, r), width=5)
        d.line((660, y - 60, 660, y + 60), fill=fade(CREAM, r), width=5)
        d.line((860, y - 60, 860, y + 60), fill=fade(CREAM, r), width=5)
        d.line((860, y, 920, y), fill=fade(CREAM, r), width=5)
        for yy in (y - 60, y + 60):
            d.line((660, yy, 715, yy), fill=fade(CREAM, r), width=5)
            d.line((805, yy, 860, yy), fill=fade(CREAM, r), width=5)
            chip(d, x, yy, "A", 90, 70, fade(CELL, r), fade(GOLD, r), fade(CREAM, r), 36)
        label(d, x, y + 110, "並列 1−(1−0.9)²", 32, fade(MUTED, r), False)
        label(d, x, y + 160, "= 0.99", 44, fade(GOLD, r))


def sc_db(d, c, t):
    # 正規化: 1つの表 → 2つの表
    split = c.p(0, 1.2) if c.li >= 0 else 0
    dup = c.p(1, 0.8) if c.li >= 1 else 0
    y0 = 520
    rows = [("1", "君", "A組"), ("2", "僕", "A組"), ("3", "夢", "B組")]
    lx = lerp(160, 90, split)
    for k, r in enumerate(rows):
        y = y0 + k * 70
        for j, v in enumerate(r):
            x = lx + j * 150 + (split * 120 if j == 2 else 0)
            gone = dup if (j == 2 and k == 1) else 0
            col = GOLD if j == 0 and c.li >= 5 else CELL_LINE
            rbox(d, x, y, 140, 60, mix(CELL, BG1, gone), mix(col, BG1, gone), 8, 3)
            label(d, x + 70, y + 30, v, 32, mix(CREAM, BG1, gone))
    if c.li >= 5:
        key_icon(d, lx - 50 + 70, y0 - 40, GOLD, 0.6)
        label(d, lx, y0 + 240, "主キー：一意な存在", 34, GOLD, anchor="lm")
    if split > 0:
        label(d, 760, y0 - 40, "正規化", 36, fade(GREEN, split))
    # SQL を1行ずつ打つ
    sql = [(2, "SELECT 君"), (2, "FROM 僕の世界"), (3, "WHERE 条件 = 'ずっと一緒'")]
    y = 860
    for k, (li, s) in enumerate(sql):
        if c.li < li:
            continue
        sec = c.since(li) - (0.9 if k == 1 else 0)
        n = int(max(0.0, sec) * 16)
        if n <= 0:
            continue
        part = s[:n]
        kw, rest = (part.split(" ", 1) + [""])[:2]
        label(d, 90, y + k * 80, kw, 46, BLUE, anchor="lm")
        label(d, 90 + font(46).getlength(kw + " "), y + k * 80, rest, 46, CREAM, anchor="lm")
    # JOIN
    if c.li >= 4:
        q = c.p(4, 1.0)
        y = 1200
        for k, (n, col) in enumerate([("君テーブル", BLUE), ("僕テーブル", GREEN)]):
            x = lerp(160 + k * 520, 290 + k * 240, q)
            chip(d, x + 130, y, n, 260, 110, CELL, col, CREAM, 38)
        label(d, W / 2, y + 120, "JOIN", 46, fade(GOLD, q))
        if q >= 1:
            heart(d, W / 2, y - 6, 1.6 + 0.3 * off_pulse(t), RED)


def sc_dev(d, c, t):
    steps = ["要件定義", "設計", "実装", "テスト"]
    q = c.p(0, 1.0) if c.li >= 0 else 0
    for k, s in enumerate(steps):
        r = ease((c.since(0) - k * 0.45) / 0.5) if c.li >= 0 else 0
        x, y = 120 + k * 150, 520 + k * 110
        chip(d, x + 110, y, s, 230, 86, fade(CELL, r), fade(BLUE, r), fade(CREAM, r), 34)
        if k:
            arrow(d, x - 30, y - 70, x - 30, y - 46, fade(MUTED, r), 5, 16)
    if q > 0:
        label(d, 840, 600, "戻れない", 40, fade(RED, q))
        label(d, 840, 650, "ウォーターフォール", 32, fade(MUTED, q), False)
    # アジャイル: 小さな輪がくるくる
    q = c.p(1, 0.6) if c.li >= 1 else 0
    if q > 0:
        cx, cy, R = 820, 900, 110
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=fade(GREEN, q), width=7)
        a = math.radians(c.since(1) * 360 / (2 * BEAT))
        d.ellipse((cx + R * math.cos(a) - 18, cy + R * math.sin(a) - 18, cx + R * math.cos(a) + 18, cy + R * math.sin(a) + 18), fill=fade(GOLD, q))
        label(d, cx, cy, "短く回す", 34, fade(CREAM, q))
        label(d, cx, cy + 150, "アジャイル", 32, fade(MUTED, q), False)
    # PDCA
    q = c.p(2, 0.6) if c.li >= 2 else 0
    if q > 0:
        cx, cy, R = W / 2, 1270, 150
        names = [("Plan", BLUE), ("Do", GREEN), ("Check", GOLD), ("Act", RED)]
        now = int(max(0.0, c.since(2)) / BEAT) % 4
        for k, (n, col) in enumerate(names):
            a0 = -90 + k * 90
            on = k == now
            bb = (cx - R, cy - R, cx + R, cy + R)
            d.pieslice(bb, a0 + 2, a0 + 88, fill=fade(mix(CELL, col, 0.55 if on else 0.15), q))
            a = math.radians(a0 + 45)
            label(d, cx + R * 0.58 * math.cos(a), cy + R * 0.58 * math.sin(a), n, 34, fade(CREAM, q))
        if c.li >= 3:
            label(d, cx, cy + R + 60, "間違えたって、改善すればいい", 40, GOLD)


def sc_raid(d, c, t):
    # RAID1: 2台に同じデータ
    q = c.p(0, 0.6) if c.li >= 0 else 0
    blocks = ["君", "の", "デ", "ー", "タ"]
    n1 = int(max(0.0, c.since(0)) / (BEAT * 0.7)) if c.li >= 0 else 0
    for k in range(2):
        x = 110 + k * 230
        rbox(d, x, 500, 190, 420, fade(CELL, q), fade(BLUE, q), 18)
        label(d, x + 95, 960, f"ディスク{k + 1}", 30, fade(MUTED, q), False)
        for j in range(min(n1, 5)):
            chip(d, x + 95, 550 + j * 78, blocks[j], 150, 64, HOT, GOLD, CREAM, 34)
    label(d, 325, 470, "RAID1　ミラーリング", 36, fade(GOLD, q))
    # RAID5: データとパリティを分ける
    q = c.p(2, 0.6) if c.li >= 2 else 0
    broken = c.p(3, 0.5) if c.li >= 3 else 0
    fixed = ease((c.since(3) - 1.6) / 0.8) if c.li >= 3 else 0
    if q > 0:
        lay = [["A1", "A2", "P"], ["B1", "P", "B2"], ["P", "C1", "C2"]]
        for k in range(3):
            x = 600 + k * 150
            bad = k == 1
            line = mix(fade(GREEN, q), RED, broken * (1 - fixed)) if bad else fade(GREEN, q)
            rbox(d, x, 500, 130, 330, fade(CELL, q), line, 16)
            for j in range(3):
                s = lay[j][k]
                fill = mix(HOT, (50, 40, 60), 1 if s == "P" else 0)
                vis = 1 - broken * (1 - fixed) if bad else 1
                chip(d, x + 65, 560 + j * 100, s, 104, 76, mix(BG1, fill, q * vis), mix(BG1, PURPLE if s == "P" else GOLD, q * vis), mix(BG1, CREAM, q * vis), 30)
            if bad and broken > 0 and fixed < 1:
                d.line((x + 10, 510, x + 120, 820), fill=RED, width=10)
                d.line((x + 120, 510, x + 10, 820), fill=RED, width=10)
        label(d, 825, 470, "RAID5　パリティ", 36, fade(GOLD, q))
        if fixed > 0:
            label(d, 825, 880, "復元できた!", 40, fade(GREEN, fixed))
    # 午前も午後も → 合格
    if c.li >= 4:
        q = c.p(4, 0.6)
        for k, s in enumerate(["午前", "午後"]):
            r = ease((c.since(4) - k * 0.6) / 0.5)
            chip(d, 330 + k * 420, 1100, s, 260, 110, fade(CELL, r), fade(GREEN, r), fade(CREAM, r), 46)
            if r > 0.9:
                check(d, 450 + k * 420, 1060, GREEN, 1.2)
    if c.li >= 5:
        q = c.p(5, 0.8)
        s = 0.8 + 0.2 * q
        w, h = 620 * s, 230 * s
        rbox(d, W / 2 - w / 2, 1320 - h / 2, w, h, fade((60, 40, 20), q), fade(GOLD, q), 26, 6)
        label(d, W / 2, 1290, "合格通知", int(70 * s), fade(GOLD, q))
        label(d, W / 2, 1370, "おめでとう", int(38 * s), fade(CREAM, q), False)
        rng = np.random.default_rng(7)
        for k in range(40):
            fx = rng.uniform(80, W - 80)
            fy = (rng.uniform(0, 1) + c.since(5) * 0.25) % 1
            y = 1000 + fy * 560
            col = (GOLD, RED, GREEN, BLUE)[k % 4]
            d.rectangle((fx, y, fx + 14, y + 22), fill=fade(col, q))


def sc_outro(d, c, t):
    st = t - c.start
    tags = ["起動", "CPU", "記憶の階層", "スタック", "キュー", "暗号", "OSI", "TCP/UDP", "稼働率", "SQL", "PDCA", "RAID"]
    for i, s in enumerate(tags):
        q = ease((st - i * 0.25) / 0.5)
        r_, k = divmod(i, 3)
        x, y = 210 + k * 330, 540 + r_ * 150 - 10 * off_pulse(t) * ((i + r_) % 2)
        chip(d, x, y + 30 * (1 - q), s, 300, 110, fade(CELL, q), fade((GOLD, GREEN, BLUE, RED)[i % 4], q), fade(CREAM, q), 38)
    q = ease((st - 3.5) / 1.2)
    label(d, W / 2, 1220, "データ構造の心", 92, fade(CREAM, q))
    q = ease((st - 5) / 1.2)
    label(d, W / 2, 1340, "用語の復習は「FE用語ドリル」で", 44, fade(MUTED, q), False)
    label(d, W / 2, 1420, "fe.yogo-drill.com", 52, fade(GOLD, q))


# まとまりごとの場面（番号, タイトル, 英語）
PLAN = [
    (sc_boot, "起動とCPU", "BOOT & CPU"),
    (sc_memory, "記憶の階層", "MEMORY HIERARCHY"),
    (sc_stackqueue, "スタックとキュー", "STACK & QUEUE"),
    (sc_security, "セキュリティ", "SECURITY"),
    (sc_osi, "OSI基本参照モデル", "OSI 7 LAYERS"),
    (sc_net, "ネットワーク", "DNS・DHCP・TCP・UDP"),
    (sc_avail, "稼働率", "AVAILABILITY"),
    (sc_db, "データベース", "SQL & NORMALIZATION"),
    (sc_dev, "開発の進め方", "WATERFALL・AGILE・PDCA"),
    (sc_raid, "RAIDと合格", "RAID → PASS"),
]
LEAD = 0.9    # 歌い出しの少し前に場面を出す
FADE = 0.45


def scenes():
    """[(開始秒, 終了秒, 関数, まとまりの番号)]"""
    starts = [min(r["s"] for r in ROWS if r["block"] == b) - LEAD for b in range(len(BLOCKS))]
    last_end = max(r["e"] for r in ROWS)
    out = [(0.0, starts[0], sc_intro, None)]
    for b in range(len(BLOCKS)):
        end = starts[b + 1] if b + 1 < len(BLOCKS) else last_end + 2.0
        out.append((starts[b], end, PLAN[b][0], b))
    out.append((last_end + 2.0, DUR, sc_outro, None))
    return out


SCENES = scenes()


def render(t):
    img = None
    for st, en, fn, b in SCENES:
        if st <= t < en or (fn is sc_outro and t >= st):
            layer = BG.copy()
            ld = ImageDraw.Draw(layer)
            draw_bg(ld, t)
            if b is not None:
                header(ld, b + 1, PLAN[b][1], PLAN[b][2])
                fn(ld, Ctx(t, b), t)
            else:
                c = Ctx(t, 0)
                c.start = st
                fn(ld, c, t)
            a = min(1.0, (t - st) / FADE if st > 0 else 1.0, (en - t) / FADE if fn is not sc_outro else 1.0)
            if fn is sc_outro:
                a = min(a, (DUR - t) / 1.5)
            if a < 1:
                base = BG.copy()
                draw_bg(ImageDraw.Draw(base), t)
                layer = Image.blend(base, layer, ease(a))
            img = layer
            break
    if img is None:
        img = BG.copy()
        draw_bg(ImageDraw.Draw(img), t)
    lyric_band(img, t)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", action="store_true")
    ap.add_argument("--from", dest="start", type=float, default=0)
    ap.add_argument("--sec", type=float, default=None)
    a = ap.parse_args()
    print(f"テンポ {BPM:.2f} BPM・長さ {DUR:.1f} 秒")
    for st, en, fn, b in SCENES:
        print(f"  {st:6.1f}〜{en:6.1f} 秒  {PLAN[b][1] if b is not None else fn.__name__}")
    if a.still:
        out = WORK
        out.mkdir(exist_ok=True)
        # まとまりごとに、各行の終わりごろの静止画
        thumbs = []
        for b in range(len(BLOCKS)):
            rs = [r for r in ROWS if r["block"] == b]
            for r in rs[:6]:
                thumbs.append(render(r["e"] - 0.1).resize((216, 384)))
            while len(thumbs) % 6:
                thumbs.append(Image.new("RGB", (216, 384)))
        thumbs.append(render(2.0 if SCENES[0][1] > 3 else 0.5).resize((216, 384)))
        thumbs.append(render(DUR - 3).resize((216, 384)))
        rows = (len(thumbs) + 5) // 6
        sheet = Image.new("RGB", (216 * 6, 384 * rows), (0, 0, 0))
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % 6) * 216, (i // 6) * 384))
        sheet.save(out / "場面の一覧.png")
        print(out / "場面の一覧.png")
        return
    start = a.start
    end = DUR if a.sec is None else min(DUR, start + a.sec)
    out = OUT if a.sec is None else WORK / f"MV_{int(start)}-{int(end)}秒.mp4"
    out.parent.mkdir(exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(SONG),
           "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "16", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 2), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int((end - start) * FPS)
    for i in range(n):
        p.stdin.write(render(start + i / FPS).tobytes())
        if i % (FPS * 10) == 0:
            print(f"  {start + i / FPS:6.1f} 秒", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("動画の変換に失敗しました")
    print(out)


if __name__ == "__main__":
    main()
