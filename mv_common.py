"""歌詞に合わせた MV を作る共通の部品（make_mv_strategy.py などが使う）。

曲・歌詞・時間を configure() で読み込み、場面の関数を並べた PLAN で動画を作る。
- 歌詞のファイル: [見出し] か空行で「まとまり」を分ける。まとまりごとに場面が変わる
- 時間のファイル: 歌詞の各行の [開始秒, 終了秒]（音声認識と歌詞の突き合わせで作る。手で直してもよい）
- 場面の関数は fn(d, c, t)。c.li = まとまりの中の今の行（最初の行の前は -1）、c.p(i) = i 行目の歌い出しからの進み具合
- 歌詞は画面の下に出し、歌う時間に合わせて左から金色に変わる（カラオケ）
"""
import argparse
import json
import os
from pathlib import Path
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

W, H, FPS = 1080, 1920, 60
# 書き出す動画の大きさ。--youtube で横長（1920×1080）にする。図は W×H（縦長）で描いてから並べ直す
HZ = False
OW, OH = W, H
KARAOKE = True   # 歌詞を、歌う時間に合わせて左から金色に変える。--no-karaoke で白い文字のままにする
# Instagram リール・YouTube ショート用の配置（--safe）。アプリの表示（上の約14%・右下のボタンの列・下のユーザー名と
# 説明文の約400px）に文字が隠れないように、見出しと図を上下 SAFE_TOP〜SAFE_BOTTOM に縮めて収め、歌詞を上げる。
# 広告向けの目安（下の35%）まで避けると図の文字が小さくなりすぎる（0.63倍）ので、ふつうのリールの表示に合わせた（0.7倍）
SAFE = False
SAFE_TOP, SAFE_BOTTOM = 290, 1320
SAFE_LYRIC_Y = 1410          # 歌詞の帯のまん中（下は 1480 まで。下から約440px をあける）
SAFE_LYRIC_X = (90, 900)     # 歌詞の帯の左右（右は Instagram のボタンの列をよける）
# 曲の音量を、仕上げのときに何 dB 上げ下げするか（YouTube の目安 -14 LUFS に合わせるため。曲ごとに入れる）
AUDIO_GAIN_DB = 0.0
FONT_R = "C:/Windows/Fonts/BIZ-UDGothicR.ttc"
FONT_B = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"
# 見出し（場面のタイトル）だけに使う字体。曲ごとに make_mv_<曲>.py で TTF のパスを入れる。None なら FONT_B
HEAD_FONT = None
_fonts = {}

BG1, BG2 = (14, 32, 28), (22, 18, 30)
CREAM = (244, 234, 213)
MUTED = (150, 168, 158)
GOLD = (242, 193, 78)
RED = (228, 87, 70)
GREEN = (92, 190, 128)
BLUE = (110, 168, 230)
PURPLE = (190, 130, 230)
SEA = (40, 120, 150)
SAND = (214, 186, 130)
CELL = (34, 56, 50)
CELL_LINE = (88, 120, 108)
HOT = (70, 52, 22)

# configure() で入る
SONG = None
BPM = T0 = DUR = BEAT = 0.0
LEVEL = None
BLOCKS, ROWS = [], []
TITLE = ""


def font(size, bold=True, face=None):
    """face に TTF のパスを渡すと、その字体（見出し用など）。"""
    k = (int(size), bold, face)
    if k not in _fonts:
        if face:
            _fonts[k] = ImageFont.truetype(str(face), int(size))
        else:
            _fonts[k] = ImageFont.truetype(FONT_B if bold else FONT_R, int(size), index=1)
    return _fonts[k]


# ---------- 曲 ----------

def analyze(path):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    SR = 22050
    raw = subprocess.run([ff, "-v", "quiet", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
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


def read_lyrics(path):
    """[見出し] か空行でまとまりを分ける。[(見出し, [行...]), ...]"""
    blocks, name, cur = [], "", []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            if cur:
                blocks.append((name, cur))
            name, cur = s[1:-1], []
        elif s:
            cur.append(s)
        elif cur:
            blocks.append((name, cur))
            name, cur = "", []
    if cur:
        blocks.append((name, cur))
    return blocks


def row_knots(r, words):
    """音声認識の言葉ごとの時間から、その行を「どの時刻に、行の何割まで歌ったか」の折れ線にする。
    認識の文字と歌詞の文字は合わないことがあるので、文字の数の割合だけを使う。"""
    ws = [w for w in words if r["s"] - 0.15 <= w[0] <= r["e"] + 0.15]
    lens = [max(1, len("".join(ch for ch in w[2] if ch.strip() and ch not in "、。,.!?！？…"))) for w in ws]
    if len(ws) < 2:
        return None
    total, acc, ts, fs = sum(lens), 0, [], []
    for w, n in zip(ws, lens):
        ts.append(w[0])
        fs.append(acc / total)
        acc += n
    ts.append(max(ws[-1][1], ts[-1] + 0.05))
    fs.append(1.0)
    for i in range(1, len(ts)):          # 時刻が戻らないようにする
        ts[i] = max(ts[i], ts[i - 1] + 0.01)
    return ts, fs


def karaoke_prog(r, t):
    """歌詞の帯の色が進んだ割合（0〜1）。言葉ごとの時間があればそれに合わせる。"""
    if r.get("knots"):
        ts, fs = r["knots"]
        return float(np.interp(t, ts, fs))
    return ease((t - r["s"]) / max(0.5, r["e"] - r["s"]))


def configure(song, lyrics, times, title, words=None):
    """words: 音声認識の結果（song_tools/asr_run.py の JSON）。渡すと、カラオケの色が言葉ごとに進む。"""
    global SONG, BPM, T0, DUR, BEAT, LEVEL, BLOCKS, ROWS, TITLE
    SONG, TITLE = song, title
    BPM, T0, DUR, LEVEL = analyze(song)
    BEAT = 60 / BPM
    BLOCKS = read_lyrics(lyrics)
    tm = json.loads(times.read_text(encoding="utf-8"))
    ROWS, k = [], 0
    for b, (_, lines) in enumerate(BLOCKS):
        for i, text in enumerate(lines):
            s, e = tm[k]
            ROWS.append({"block": b, "i": i, "text": text, "s": s, "e": e})
            k += 1
    if k != len(tm):
        sys.exit(f"歌詞の行の数（{k}）と時間の数（{len(tm)}）が合いません")
    if words:
        ws = json.loads(Path(words).read_text(encoding="utf-8"))["words"]
        for r in ROWS:
            r["knots"] = row_knots(r, ws)


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


def fade(c, p):
    return mix(BG1, c, p)


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
        self.start = self.rows[0]["s"] if self.rows else 0.0

    def p(self, i, length=1.0):
        """i 行目の歌い出しからの、動きの進み具合 0〜1（その行の前は 0）。"""
        if i > self.li:
            return 0.0
        r = self.rows[min(i, len(self.rows) - 1)]
        return ease((self.t - r["s"] + 0.15) / length)

    def since(self, i):
        r = self.rows[min(i, len(self.rows) - 1)]
        return self.t - r["s"]


# ---------- 描く部品 ----------

def rbox(d, x, y, w, h, fill=CELL, line=CELL_LINE, r=18, width=4):
    d.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=fill, outline=line, width=width)


def label(d, x, y, s, size=56, fill=CREAM, bold=True, anchor="mm", face=None):
    d.text((x, y), s, font=font(size, bold, face), fill=fill, anchor=anchor)


def chip(d, cx, cy, s, w=150, h=110, fill=CELL, line=CELL_LINE, tcol=CREAM, size=52):
    rbox(d, cx - w / 2, cy - h / 2, w, h, fill, line)
    if s:
        label(d, cx, cy + 2, s, size, tcol)


def fchip(d, cx, cy, s, w, h, col, q, size=44, hot=False):
    """q（0〜1）で浮かび上がる箱。"""
    if q <= 0:
        return
    chip(d, cx, cy + 24 * (1 - q), s, w, h, fade(HOT if hot else CELL, q), fade(col, q), fade(CREAM, q), size)


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


def check(d, x, y, col, s=1.0):
    d.line((x - 18 * s, y, x - 4 * s, y + 14 * s, x + 20 * s, y - 14 * s), fill=col, width=int(8 * s), joint="curve")


def cross(d, x, y, col, s=1.0):
    r = 22 * s
    d.line((x - r, y - r, x + r, y + r), fill=col, width=int(9 * s))
    d.line((x - r, y + r, x + r, y - r), fill=col, width=int(9 * s))


def heart(d, x, y, s, col):
    pts = []
    for k in range(60):
        a = k / 60 * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((x + hx * s, y - hy * s))
    d.polygon(pts, fill=col)


def star(d, x, y, r, col):
    pts = []
    for k in range(10):
        a = math.radians(-90 + k * 36)
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col)


def palm(d, x, y, s, col_trunk, col_leaf, sway=0.0):
    """ヤシの木（x, y が根もと）。"""
    top = (x + 30 * s + sway * 20 * s, y - 220 * s)
    d.line((x, y, x + 12 * s, y - 110 * s, top[0], top[1]), fill=col_trunk, width=int(16 * s), joint="curve")
    for k in range(6):
        a = math.radians(-170 + k * 32 + sway * 8)
        ex, ey = top[0] + 120 * s * math.cos(a), top[1] + 70 * s * math.sin(a) + 40 * s
        mx, my = top[0] + 60 * s * math.cos(a), top[1] + 50 * s * math.sin(a) - 10 * s
        d.line((top[0], top[1], mx, my, ex, ey), fill=col_leaf, width=int(14 * s), joint="curve")


def island(d, x, y, w, col=SAND):
    d.ellipse((x - w / 2, y - w * 0.12, x + w / 2, y + w * 0.12), fill=col)


def waves(d, y, t, col, amp=10, k=0.02, width=5):
    pts = [(x, y + amp * math.sin(x * k + t * 2.2)) for x in range(0, W + 20, 20)]
    d.line(pts, fill=col, width=width, joint="curve")


# ---------- 背景・見出し・歌詞 ----------

_bg = None


def background():
    global _bg
    if _bg is None:
        g = np.linspace(0, 1, H)[:, None, None]
        arr = (np.array(BG1)[None, None, :] * (1 - g) + np.array(BG2)[None, None, :] * g).repeat(W, axis=1)
        _bg = Image.fromarray(arr.astype(np.uint8), "RGB")
    return _bg


DOTS = True   # 裏拍で光る点の格子。本物の映像を背景にするときは出さない（render_on が切る）


def draw_bg(d, t):
    p = off_pulse(t)
    for gy in range(6 if DOTS else 0):
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
    label(d, W / 2, 130, TITLE, 36, MUTED, bold=False)
    if num:
        label(d, W / 2, 215, f"#{num}", 42, GOLD)
    label(d, W / 2, 300, title, 84 if len(title) <= 9 else 66, CREAM, face=HEAD_FONT)
    label(d, W / 2, 382, sub, 34, MUTED, bold=False)


def lyric_band(img, t):
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
    while font(size).getlength(text) > 960 and size > 28:
        size -= 2
    f = font(size)
    tw = f.getlength(text)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 1590, W - 40, 1770), radius=34, fill=mix(BG1, (6, 14, 12), a))
    x0, y = (W - tw) / 2, 1680
    d.text((x0, y), text, font=f, fill=mix(BG1, CREAM, a), anchor="lm")
    prog = karaoke_prog(cur, t) if KARAOKE else 0
    if prog > 0:
        hl = Image.new("L", (W, 120), 0)
        ImageDraw.Draw(hl).text((x0, 60), text, font=f, fill=255, anchor="lm")
        hl.paste(0, (int(x0 + tw * prog), 0, W, 120))
        img.paste(Image.new("RGB", (W, 120), mix(BG1, GOLD, a)), (0, y - 60), hl)


# ---------- 組み立て・書き出し ----------

LEAD = 0.9    # 歌い出しの少し前に場面を出す
FADE = 0.45


def build_scenes(plan, title_fn, end_fn, end_gap=2.0):
    """plan: まとまりごとの (関数, タイトル, 英語, 番号)。タイトルが空なら見出しを出さない。[(開始秒, 終了秒, 関数, まとまりの番号)]"""
    starts = [min(r["s"] for r in ROWS if r["block"] == b) - LEAD for b in range(len(BLOCKS))]
    last_end = max(r["e"] for r in ROWS)
    out = [(0.0, starts[0], title_fn, None)]
    for b in range(len(BLOCKS)):
        end = starts[b + 1] if b + 1 < len(BLOCKS) else last_end + end_gap
        out.append((starts[b], end, plan[b][0], b))
    out.append((last_end + end_gap, DUR, end_fn, None))
    return out


def render(t, scenes, plan, lyrics=True, head=True):
    img = None
    for k, (st, en, fn, b) in enumerate(scenes):
        last = k == len(scenes) - 1
        if st <= t < en or (last and t >= st):
            layer = background().copy()
            ld = ImageDraw.Draw(layer)
            draw_bg(ld, t)
            if b is not None:
                _, title, sub, num = plan[b]
                if title and head:
                    header(ld, num, title, sub)
                fn(ld, Ctx(t, b), t)
            else:
                c = Ctx(t, 0)
                c.start = st
                fn(ld, c, t)
            a = min(1.0, (t - st) / FADE if st > 0 else 1.0, (en - t) / FADE if not last else 1.0)
            if last:
                a = min(a, (DUR - t) / 1.5)
            if a < 1:
                base = background().copy()
                draw_bg(ImageDraw.Draw(base), t)
                layer = Image.blend(base, layer, ease(a))
            img = layer
            break
    if img is None:
        img = background().copy()
        draw_bg(ImageDraw.Draw(img), t)
    if lyrics:
        lyric_band(img, t)
    return img


def scene_alpha(t, scenes):
    """t のときの場面と、その出入りの濃さ（0〜1）。"""
    for k, (st, en, fn, b) in enumerate(scenes):
        last = k == len(scenes) - 1
        if st <= t < en or (last and t >= st):
            a = min(1.0, (t - st) / FADE if st > 0 else 1.0, (en - t) / FADE if not last else 1.0)
            if last:
                a = min(a, (DUR - t) / 1.5)
            return b, ease(max(0.0, a))
    return None, 0.0


# ---------- 横長（YouTube）----------
HZ_CROP = (0, 420, W, 1580)   # 縦長の画面から切り出す、図の部分
HZ_FIG_H = 900                 # 横長の画面での図の高さ


def lyric_band_h(img, t):
    """横長の画面の下の歌詞（カラオケ）。"""
    cur = None
    for r in ROWS:
        if r["s"] - 0.35 <= t < r["e"] + 0.6:
            cur = r
    if not cur:
        return
    nxt = [r for r in ROWS if r["s"] > cur["s"]]
    a = ease(min((t - cur["s"] + 0.35) / 0.3, (cur["e"] + 0.6 - t) / 0.3 if not (nxt and nxt[0]["s"] - 0.35 <= t) else 1))
    text = cur["text"]
    size = 52
    while font(size).getlength(text) > 1500 and size > 28:
        size -= 2
    f = font(size)
    tw = f.getlength(text)
    d = ImageDraw.Draw(img)
    bw = max(tw + 120, 900)
    d.rounded_rectangle(((OW - bw) / 2, 952, (OW + bw) / 2, 1052), radius=40, fill=mix(BG1, (6, 14, 12), a))
    x0, y = (OW - tw) / 2, 1002
    d.text((x0, y), text, font=f, fill=mix(BG1, CREAM, a), anchor="lm")
    prog = karaoke_prog(cur, t) if KARAOKE else 0
    if prog > 0:
        hl = Image.new("L", (OW, 100), 0)
        ImageDraw.Draw(hl).text((x0, 50), text, font=f, fill=255, anchor="lm")
        hl.paste(0, (int(x0 + tw * prog), 0, OW, 100))
        img.paste(Image.new("RGB", (OW, 100), mix(BG1, GOLD, a)), (0, y - 50), hl)


def render_h(t, scenes, plan):
    """横長の1枚（BG1 の上に描く）: 左に見出し、右に図、下に歌詞。"""
    v = render(t, scenes, plan, lyrics=False, head=False)
    fig = v.crop(HZ_CROP)
    s = HZ_FIG_H / fig.height
    fig = fig.resize((int(fig.width * s), HZ_FIG_H), Image.LANCZOS)
    img = Image.new("RGB", (OW, OH), BG1)
    b, a = scene_alpha(t, scenes)
    has_head = b is not None and plan[b][1]
    x = OW - fig.width - 90 if has_head else (OW - fig.width) // 2
    img.paste(fig, (x, 30))
    d = ImageDraw.Draw(img)
    if has_head:
        _, title, sub, num = plan[b]
        cx = (x - 40) / 2 + 20
        label(d, cx, 250, TITLE if len(TITLE) <= 22 else TITLE.split("〜")[0].strip(), 30, mix(BG1, MUTED, a), bold=False)
        if num:
            label(d, cx, 360, f"#{num}", 52, mix(BG1, GOLD, a))
        size = 84
        while font(size, face=HEAD_FONT).getlength(title) > x - 120 and size > 40:
            size -= 4
        label(d, cx, 470, title, size, mix(BG1, CREAM, a), face=HEAD_FONT)
        size = 30
        while font(size, False).getlength(sub) > x - 120 and size > 18:
            size -= 2
        label(d, cx, 560, sub, size, mix(BG1, MUTED, a), bold=False)
    lyric_band_h(img, t)
    return img


# ---------- 本物の映像の背景 ----------
# 場面ごとの映像（Mixkit などの素材）をつないだ背景の動画を先に作り、その上に図を重ねる。
# 図は「何もない色（BG1）」の上に描いてから、BG1 との差を透明度にして重ねる。
# 文字や線ははっきり、BG1 に近い色の箱は半透明のガラスのように見える。
BG_FADE = 0.8     # 背景の映像の切り替え（秒）
BG_DIM = 0.5      # 背景の映像の明るさ（図を読みやすくするため暗くする）
_dim_mask = None
KEEP_DOTS = False


def build_bg_video(scenes, clips, path):
    """clips: scenes と同じ順の映像ファイル。scenes の時間に合わせて1本につなぐ。"""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    F = BG_FADE
    args, filt = [], []
    segs = []
    for k, ((st, en, _, _), clip) in enumerate(zip(scenes, clips)):
        en = DUR if k == len(scenes) - 1 else en
        a, b = max(0.0, st - F / 2), min(DUR, en + F / 2) if k < len(scenes) - 1 else DUR
        segs.append((a, b))
        args += ["-stream_loop", "-1", "-t", f"{b - a:.3f}", "-i", str(clip)]
        filt.append(f"[{k}:v]scale={OW}:{OH}:force_original_aspect_ratio=increase,crop={OW}:{OH},setsar=1,format=yuv420p,trim=duration={b - a:.3f},setpts=PTS-STARTPTS,fps={FPS}[v{k}]")
    last = "v0"
    for k in range(1, len(segs)):
        off = segs[k][0]
        filt.append(f"[{last}][v{k}]xfade=transition=fade:duration={F}:offset={off:.3f}[x{k}]")
        last = f"x{k}"
    cmd = [ff, "-y", "-loglevel", "error"] + args + ["-filter_complex", ";".join(filt), "-map", f"[{last}]",
                                                      "-t", f"{DUR:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-an", str(path)]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("背景の動画を作れませんでした")
    return path


def bg_reader(path, start):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.Popen([ff, "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    size = OW * OH * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, dtype=np.uint8).reshape(OH, OW, 3)


def compose(canvas, bg):
    """canvas（BG1 の上に描いた図）を、暗くした背景の映像 bg に重ねる。"""
    global _dim_mask
    if _dim_mask is None or _dim_mask.shape[0] != bg.shape[0]:
        y = np.linspace(0, 1, bg.shape[0])[:, None, None]
        # 上（見出し）と下（歌詞）を少し暗く、まん中は図のためにさらに暗く
        _dim_mask = (BG_DIM * (1 - 0.35 * np.exp(-((y - 0.5) / 0.28) ** 2)) * (1 - 0.25 / (1 + np.exp(-(y - 0.8) / 0.04)))).astype(np.float32)
    c = np.asarray(canvas, dtype=np.float32)
    base = np.array(BG1, dtype=np.float32)
    diff = c - base
    a = np.clip(np.abs(diff).max(axis=2, keepdims=True) / 36.0, 0, 1)
    un = np.clip(base + diff / np.maximum(a, 1e-3), 0, 255)
    b = bg.astype(np.float32) * _dim_mask
    out = b * (1 - a) + un * a
    return Image.fromarray(out.astype(np.uint8), "RGB")


def lyric_band_safe(img, t):
    """リール用の歌詞の帯（右のボタンの列をよけて、少し上に出す）。"""
    cur = None
    for r in ROWS:
        if r["s"] - 0.35 <= t < r["e"] + 0.6:
            cur = r
    if not cur:
        return
    nxt = [r for r in ROWS if r["s"] > cur["s"]]
    a = ease(min((t - cur["s"] + 0.35) / 0.3, (cur["e"] + 0.6 - t) / 0.3 if not (nxt and nxt[0]["s"] - 0.35 <= t) else 1))
    x0b, x1b = SAFE_LYRIC_X
    text = cur["text"]
    size = 50
    while font(size).getlength(text) > (x1b - x0b) - 60 and size > 26:
        size -= 2
    f = font(size)
    tw = f.getlength(text)
    d = ImageDraw.Draw(img)
    cy = SAFE_LYRIC_Y
    d.rounded_rectangle((x0b, cy - 70, x1b, cy + 70), radius=34, fill=mix(BG1, (6, 14, 12), a))
    x0 = (x0b + x1b - tw) / 2
    d.text((x0, cy), text, font=f, fill=mix(BG1, CREAM, a), anchor="lm")
    prog = karaoke_prog(cur, t) if KARAOKE else 0
    if prog > 0:
        hl = Image.new("L", (W, 120), 0)
        ImageDraw.Draw(hl).text((x0, 60), text, font=f, fill=255, anchor="lm")
        hl.paste(0, (int(x0 + tw * prog), 0, W, 120))
        img.paste(Image.new("RGB", (W, 120), mix(BG1, GOLD, a)), (0, cy - 60), hl)


def render_safe(t, scenes, plan):
    """リール用の1枚: 縦長の画面の見出しと図を縮めて SAFE_TOP〜SAFE_BOTTOM に収め、歌詞は lyric_band_safe。"""
    v = render(t, scenes, plan, lyrics=False, head=True)
    fig = v.crop((0, 100, W, 1570))
    s = (SAFE_BOTTOM - SAFE_TOP) / fig.height
    fig = fig.resize((int(fig.width * s), SAFE_BOTTOM - SAFE_TOP), Image.LANCZOS)
    img = Image.new("RGB", (W, H), BG1)
    img.paste(fig, ((W - fig.width) // 2, SAFE_TOP))
    lyric_band_safe(img, t)
    return img


def render_on(t, scenes, plan, bg):
    """背景の映像つきで1枚を描く。"""
    global _bg, DOTS
    keep, keep_dots = _bg, DOTS
    _bg = Image.new("RGB", (W, H), BG1)   # 図は何もない色の上に描く
    DOTS = KEEP_DOTS                       # 本物の映像の上では、ふだんは光る点の格子を出さない（--dots で出す）
    try:
        img = render_h(t, scenes, plan) if HZ else (render_safe(t, scenes, plan) if SAFE else render(t, scenes, plan))
    finally:
        _bg, DOTS = keep, keep_dots
    return compose(img, bg)


def main(scenes, plan, out_path, check_dir, clips=None):
    """clips を渡すと、場面ごとの本物の映像を背景にする（scenes と同じ順・同じ数）。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", action="store_true")
    ap.add_argument("--from", dest="start", type=float, default=0)
    ap.add_argument("--sec", type=float, default=None)
    ap.add_argument("--at", type=float, nargs="*", help="この秒の静止画を大きく出す（確認用）")
    ap.add_argument("--rebuild-bg", action="store_true", help="背景の動画を作り直す")
    ap.add_argument("--dots", action="store_true", help="本物の映像の背景でも、光る点の格子を出す")
    ap.add_argument("--name", default="", help="できあがりのファイル名の後ろに付ける言葉（例: _丸あり）")
    ap.add_argument("--youtube", action="store_true", help="YouTube 用の横長（1920×1080）で書き出す")
    ap.add_argument("--safe", action="store_true", help="リール・ショート用の配置（アプリの表示に隠れない）で書き出す。ファイル名は _MV_リール用")
    ap.add_argument("--no-karaoke", action="store_true", help="歌詞を白い文字のままにする（色が変わる動きをなくす）")
    ap.add_argument("--jobs", type=int, default=1, help="曲をいくつに分けて同時に書き出すか（速くなる）")
    ap.add_argument("--chunk", default="", help="（内部用）分けた1つ分を、音なしでこのファイルに書く")
    ap.add_argument("--f0", type=int, default=0, help="（内部用）書き出す最初のコマ")
    ap.add_argument("--fn", type=int, default=0, help="（内部用）書き出すコマの数")
    a = ap.parse_args()
    global KEEP_DOTS
    KEEP_DOTS = a.dots
    base_stem = out_path.stem   # 背景の動画は、名前の後ろの言葉に関係なく同じものを使う
    global HZ, OW, OH, KARAOKE
    KARAOKE = not a.no_karaoke
    global SAFE
    if a.safe:
        SAFE = True
        if not a.name:
            out_path = out_path.with_name(out_path.stem + "_リール用.mp4")
    if a.youtube:
        HZ, OW, OH = True, 1920, 1080
        out_path = out_path.with_name(out_path.stem.replace("_MV", "") + "_YouTube.mp4")
    if a.name:
        out_path = out_path.with_name(out_path.stem + a.name + ".mp4")
    print(f"テンポ {BPM:.2f} BPM・長さ {DUR:.1f} 秒")
    for st, en, fn, b in scenes:
        print(f"  {st:6.1f}〜{en:6.1f} 秒  {plan[b][1] or BLOCKS[b][0] if b is not None else fn.__name__}")
    check_dir.mkdir(exist_ok=True)
    bgv = None
    if clips:
        if len(clips) != len(scenes):
            sys.exit(f"背景の映像の数（{len(clips)}）と場面の数（{len(scenes)}）が合いません")
        bgv = check_dir / f"{base_stem}_背景{'横' if HZ else ''}.mp4"
        if a.rebuild_bg or not bgv.exists() or bgv.stat().st_size == 0:
            print("背景の動画を作っています…", flush=True)
            build_bg_video(scenes, clips, bgv)

    def frame_at(t):
        if bgv is None:
            return render(t, scenes, plan)
        return render_on(t, scenes, plan, next(bg_reader(bgv, t)))

    if a.at:
        sz = (960, 540) if HZ else (540, 960)
        ims = [frame_at(t).resize(sz) for t in a.at]
        sheet = Image.new("RGB", (sz[0], sz[1] * len(ims))) if HZ else Image.new("RGB", (540 * len(ims), 960))
        for i, im in enumerate(ims):
            sheet.paste(im, (0, i * 540) if HZ else (i * 540, 0))
        sheet.save(check_dir / "拡大.png")
        print(check_dir / "拡大.png")
        return
    if a.still:
        thumbs = []
        for b in range(len(BLOCKS)):
            for r in [r for r in ROWS if r["block"] == b][:6]:
                thumbs.append(frame_at(r["e"] - 0.1).resize((216, 384)))
            while len(thumbs) % 6:
                thumbs.append(Image.new("RGB", (216, 384)))
        thumbs.append(frame_at(max(0.5, scenes[0][1] - 1)).resize((216, 384)))
        thumbs.append(frame_at(DUR - 3).resize((216, 384)))
        rows = (len(thumbs) + 5) // 6
        sheet = Image.new("RGB", (216 * 6, 384 * rows), (0, 0, 0))
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % 6) * 216, (i // 6) * 384))
        sheet.save(check_dir / "場面の一覧.png")
        print(check_dir / "場面の一覧.png")
        return
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    # 本物の映像を背景にするときは、実写向けの設定で圧縮する
    tune, crf = ("film", "18") if bgv else ("animation", "16")
    if a.chunk:
        render_chunk(a.f0, a.fn, Path(a.chunk), scenes, plan, bgv, tune, crf)
        return
    if a.jobs > 1 and a.sec is None and a.start == 0:
        render_parallel(a.jobs, out_path, check_dir, tune, crf)
        return
    start = a.start
    end = DUR if a.sec is None else min(DUR, start + a.sec)
    out = out_path if a.sec is None else check_dir / f"{out_path.stem}_{int(start)}-{int(end)}秒.mp4"
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(SONG),
           "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-tune", tune, "-crf", crf, "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 2)] + gain_args() + ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    # 途中は「_作成中」に書き、できあがったら名前を入れ替える（前の版は「_前の版」として残す）
    work = out.with_name(out.stem + "_作成中.mp4")
    p = subprocess.Popen(cmd + [str(work)], stdin=subprocess.PIPE)
    n = int((end - start) * FPS)
    bgs = bg_reader(bgv, start) if bgv else None
    for i in range(n):
        t = start + i / FPS
        if bgs is not None:
            fr = next(bgs, None)
            img = render_on(t, scenes, plan, fr) if fr is not None else render(t, scenes, plan)
        else:
            img = render(t, scenes, plan)
        p.stdin.write(img.tobytes())
        if i % (FPS * 10) == 0:
            print(f"  {t:6.1f} 秒", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        sys.exit("動画の変換に失敗しました")
    if out.exists():
        out.replace(out.with_name(out.stem + "_前の版.mp4"))
    work.replace(out)
    print(out)


def gain_args():
    """AUDIO_GAIN_DB が 0 でなければ、曲の音量を変える ffmpeg の引数。"""
    return ["-af", f"volume={AUDIO_GAIN_DB:+.1f}dB"] if AUDIO_GAIN_DB else []


def render_chunk(f0, fn, path, scenes, plan, bgv, tune, crf):
    """f0 コマ目から fn コマを、音なしで path に書く（render_parallel が呼ぶ）。"""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-tune", tune, "-crf", crf, "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 2), "-an", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    bgs = bg_reader(bgv, f0 / FPS) if bgv else None
    for i in range(fn):
        t = (f0 + i) / FPS
        fr = next(bgs, None) if bgs is not None else None
        img = render_on(t, scenes, plan, fr) if fr is not None else render(t, scenes, plan)
        p.stdin.write(img.tobytes())
        if i % (FPS * 10) == 0:
            print(f"  [{path.stem}] {t:6.1f} 秒", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        sys.exit(f"動画の変換に失敗しました: {path.name}")


def part_seconds(path):
    """動画のファイルの長さ（秒）。読めなければ 0。"""
    import re
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True).stderr.decode("utf-8", "ignore")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def render_parallel(jobs, out, check_dir, tune, crf):
    """曲を jobs 個に分けて同時に書き出し、最後に1本につないで曲の音を入れる。"""
    total = int(DUR * FPS)
    edges = [round(total * k / jobs) for k in range(jobs + 1)]
    parts = [check_dir / f"{out.stem}_部分{k + 1}.mp4" for k in range(jobs)]
    procs = []
    for k in range(jobs):
        # 前に書き出して、最後までできている部分は飛ばす（途中で止まったときの続きから）
        if parts[k].exists() and part_seconds(parts[k]) >= (edges[k + 1] - edges[k]) / FPS - 0.05:
            print(f"  {parts[k].name} はできているので飛ばします", flush=True)
            continue
        args = [sys.executable, sys.argv[0], "--chunk", str(parts[k]), "--f0", str(edges[k]), "--fn", str(edges[k + 1] - edges[k])]
        if KEEP_DOTS:
            args.append("--dots")
        if HZ:
            args.append("--youtube")
        if SAFE:
            args.append("--safe")
        if not KARAOKE:
            args.append("--no-karaoke")
        procs.append(subprocess.Popen(args, env=dict(os.environ, PYTHONIOENCODING="utf-8")))
    if any(pr.wait() != 0 for pr in procs):
        sys.exit("分けた書き出しのどれかが失敗しました")
    lst = check_dir / f"{out.stem}_部分.txt"
    lst.write_text("".join(f"file '{pp.as_posix()}'\n" for pp in parts), encoding="utf-8")
    work = out.with_name(out.stem + "_作成中.mp4")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(SONG),
           "-map", "0:v", "-map", "1:a", "-c:v", "copy"] + gain_args() + ["-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(work)]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("つなぐのに失敗しました")
    if out.exists():
        out.replace(out.with_name(out.stem + "_前の版.mp4"))
    work.replace(out)
    for pp in parts + [lst]:
        pp.unlink(missing_ok=True)
    print(out)
