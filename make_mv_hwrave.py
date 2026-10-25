"""曲「ハードウェア・レイヴ」の MV（縦長 1080×1920・60fps）を作る。

EDM（レイヴ）の曲に、ハードウェアの用語（マルチコア・GPU・DRAM・SRAM・揮発性と不揮発性・フラッシュメモリ・SSD・HDD・
USB・ホットプラグ・バスパワー・Bluetooth・NFC・HDMI・RGB と CMYK・画素と解像度・dpi・センサ・アクチュエータ・
タッチパネル・3Dプリンタ・有機EL・液晶・クロック周波数）を重ねて、歌詞の1行ごとに図が1つ進む。
背景は本物の映像（Mixkit の Free の素材）。

デザイン（ui-ux-pro-max の Cyberpunk・Neon の提案をもとにした）:
- 深い紺（#0F0F23）の背景に、ネオンのアシッドグリーン（レイヴの色・カラオケ）・マゼンタ・シアン、補助の紫
- 見出しは RocknRoll One（Google Fonts、OFL。日本語が出せる太い字体）、英字のかけ声は Orbitron（提案の字体。英字だけ）
- 図と歌詞の文字は読みやすさのため BIZ UD ゴシックのまま

使うファイル（notes/曲の動画/ハードウェア・レイヴ/、公開しない）
- ハードウェア・レイヴ.mp3 / _歌詞.txt / _時間.json

    python make_mv_hwrave.py --jobs 4              # 縦長
    python make_mv_hwrave.py --safe --jobs 4       # リール・ショート用の配置（_MV_リール用.mp4）
    python make_mv_hwrave.py --youtube --jobs 4    # YouTube 用の横長
    python make_mv_hwrave.py --at 30 80            # その秒の静止画（確認用）
"""
import math
from pathlib import Path

from PIL import ImageFont

import mv_common as mc
from mv_common import W, arrow, ease, font, lerp, mix, off_pulse, rbox

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "ハードウェア・レイヴ"
FONTS = ROOT / "notes" / "曲の動画" / "フォント"
HEAD = FONTS / "RocknRollOne-Regular.ttf"
ORB = FONTS / "Orbitron.ttf"

# ---------- 色（この曲用。ほかの曲には関係しない） ----------
NAVY = (15, 15, 35)
mc.BG1, mc.BG2 = NAVY, (24, 18, 48)
WHITE = mc.CREAM = (226, 232, 240)
MUTED = mc.MUTED = (148, 163, 184)
ACID = mc.GOLD = (190, 242, 100)      # アシッドグリーン（カラオケの色・いちばん目立たせる色）
PINK = (255, 64, 160)                 # マゼンタ
CYAN = (34, 211, 238)
VIOLET = mc.PURPLE = (167, 139, 250)
ORANGE = (251, 146, 60)
GREEN = mc.GREEN = (74, 222, 128)
mc.RED, mc.BLUE = PINK, CYAN
CELL = mc.CELL = (30, 28, 58)
CELL_LINE = mc.CELL_LINE = (86, 70, 150)
mc.HOT = (60, 30, 70)
mc.HEAD_FONT = str(HEAD)

mc.configure(DIR / "ハードウェア・レイヴ.mp3", DIR / "ハードウェア・レイヴ_歌詞.txt", DIR / "ハードウェア・レイヴ_時間.json",
             "ハードウェア・レイヴ", words=ROOT / "notes" / "曲の動画" / "作業用" / "ハードウェア・レイヴ_認識.json")
# 同じ言葉をくり返す行（イントロの「ハードウェア・レイヴ!」・ドロップ2の最後・最後のドロップ）と、countdown の行は、
# 音声認識の言葉が乱れている（英語に聞きまちがえている）ので、言葉ごとのカラオケを使わない
for r in mc.ROWS:
    if r["s"] >= 193 or (r["block"], r["i"]) in {(0, 1), (8, 4), (3, 3), (7, 4), (10, 1)}:
        r["knots"] = None
# 曲は -15.0 LUFS（いちばん大きい音 -3.3 dB）。YouTube の目安 -14 LUFS に合わせて +1.0 dB
mc.AUDIO_GAIN_DB = 1.0
OUT = DIR / "ハードウェア・レイヴ_MV.mp4"
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"

_orb = {}


def orb_font(size):
    if size not in _orb:
        f = ImageFont.truetype(str(ORB), int(size))
        try:
            f.set_variation_by_name("Black")
        except Exception:
            pass
        _orb[size] = f
    return _orb[size]


def fade(c, q):
    return mix(NAVY, c, q)


def text(d, x, y, s, size, col, q=1.0, bold=True, anchor="mm"):
    if q > 0:
        d.text((x, y), s, font=font(size, bold), fill=fade(col, q), anchor=anchor)


def neon(d, x, y, s, size, col, q=1.0, anchor="mm"):
    """見出しの字体で、ネオンのような光のふちどりをつける。"""
    if q <= 0:
        return
    f = font(size, face=str(HEAD))
    d.text((x, y), s, font=f, fill=fade(col, q), anchor=anchor, stroke_width=max(3, size // 18), stroke_fill=fade(mix(NAVY, col, 0.35), q))


def shout(d, x, y, s, size, col, q=1.0, anchor="mm"):
    """英字のかけ声（Orbitron）。"""
    if q <= 0:
        return
    d.text((x, y), s, font=orb_font(size), fill=fade(col, q), anchor=anchor, stroke_width=max(3, size // 16), stroke_fill=fade(mix(NAVY, col, 0.35), q))


def box(d, cx, cy, w, h, s, col, q=1.0, size=44, fill=None, tcol=None, head=False):
    if q <= 0:
        return
    y = cy + 18 * (1 - q)
    rbox(d, cx - w / 2, y - h / 2, w, h, fade(fill or CELL, q), fade(col, q), 14, 4)
    if s:
        if head:
            neon(d, cx, y + 2, s, size, tcol or WHITE, q)
        else:
            text(d, cx, y + 2, s, size, tcol or WHITE, q)


def phase(c, i0, i1, length=0.5):
    """i0〜i1 行目のあいだだけ見える部分の濃さ。"""
    if c.li < i0:
        return 0.0
    q = c.p(i0, length)
    if c.li > i1:
        q *= 1 - ease(c.since(i1 + 1) / 0.35)
    return max(0.0, q)


def stagger(c, i, k, gap=0.15, length=0.35):
    """i 行目の歌い出しから、k 番目の部品を少しずつ遅らせて出す。"""
    if c.li < i:
        return 0.0
    return ease((c.since(i) - k * gap) / length)


def chip_icon(d, cx, cy, w, h, col, q, label="", size=40, pins=6):
    """IC チップ（足つきの四角）。"""
    if q <= 0:
        return
    for k in range(pins):
        x = cx - w / 2 + w * (k + 0.5) / pins
        d.line((x, cy - h / 2 - 20, x, cy - h / 2), fill=fade(MUTED, q), width=6)
        d.line((x, cy + h / 2, x, cy + h / 2 + 20), fill=fade(MUTED, q), width=6)
    rbox(d, cx - w / 2, cy - h / 2, w, h, fade(CELL, q), fade(col, q), 12, 5)
    if label:
        text(d, cx, cy, label, size, col, q)


def countdown(d, c, i, t):
    """「3、2、1…!」の行: 大きな数字が拍に合わせて変わる。"""
    if c.li < i:
        return
    r = c.rows[i]
    step = (r["e"] - r["s"]) / 3.2    # 歌う時間を3つに分ける（最後の「…!」の分を少し残す）
    k = min(2, int(max(0.0, c.since(i)) / step))
    n = "321"[k]
    pop = 1 + 0.25 * (1 - ease((c.since(i) - k * step) / 0.25))
    col = (PINK, CYAN, ACID)[k]
    shout(d, W / 2, 900, n, int(320 * pop), col, c.p(i, 0.2))


def sweep_q(c, i):
    """前の行の図を消すときに使う（i 行目に入ったら消える）。"""
    if c.li < i:
        return 1.0
    return 1 - ease(c.since(i) / 0.3)


# ---------- 場面 ----------

def sc_title(d, c, t):
    if mc.SAFE:
        return sc_hook(d, c, t)
    q = ease((t - 0.05) / 0.6)
    chip_icon(d, W / 2, 620, 300, 220, ACID, q, "CPU", 64, 7)
    neon(d, W / 2, 860, "ハードウェア", 110, CYAN, q)
    neon(d, W / 2, 1000, "レイヴ", 140, PINK, q)
    shout(d, W / 2, 1140, "HARDWARE RAVE", 52, ACID, ease((t - 0.4) / 0.6))
    text(d, W / 2, 1220, "CPU・メモリ・入出力の用語で上がる、EDM の歌", 36, MUTED, ease((t - 0.4) / 0.6), False)


def sc_hook(d, c, t):
    """リール・ショートの最初の画面（つかみ）。1枚目から問いかける。答え（SSD）は最初のドロップで歌われる。"""
    # イントロの場面の見出しが先に描かれているので、背景の色（＝透明）で消す
    d.rectangle((0, 90, W, 430), fill=NAVY)
    pulse = off_pulse(t)
    box(d, W / 2 - 220, 600, 340, 170, "SSD", CYAN, 1.0, 72, tcol=CYAN)
    box(d, W / 2 + 220, 600, 340, 170, "HDD", PINK, 1.0, 72, tcol=PINK)
    neon(d, W / 2, 600, "vs", 56 + int(8 * pulse), ACID)
    neon(d, W / 2, 800, "静かで速いのは", 92, WHITE)
    neon(d, W / 2, 930, "どっち？", 110, ACID)
    text(d, W / 2, 1070, "答えは、この歌で。", 48, VIOLET)
    neon(d, W / 2, 1200, "ハードウェア・レイヴ", 64, PINK)


def sc_intro(d, c, t):
    # リール・ショートでは、イントロの最初の行の終わりまで問いかけの画面を出して、つかみを長めにする
    if mc.SAFE and c.li < 1:
        return sc_hook(d, c, t)
    # 0行目: 電源ボタン → 起動の流れ
    q = c.p(0, 0.6) if c.li >= 0 else 0
    if c.li <= 0:
        r = 110
        on = q
        d.arc((W / 2 - r, 640 - r, W / 2 + r, 640 + r), -60, 240, fill=fade(ACID, on), width=16)
        d.line((W / 2, 640 - r - 20, W / 2, 640), fill=fade(ACID, on), width=16)
        steps = ["電源オン", "BIOS/UEFI", "OS を読み込む"]
        for k, s in enumerate(steps):
            rr = stagger(c, 0, k, 0.5)
            box(d, W / 2, 880 + k * 150, 520, 110, s, (ACID, CYAN, PINK)[k], rr, 44)
            if k:
                arrow(d, W / 2, 880 + (k - 1) * 150 + 58, W / 2, 880 + k * 150 - 58, fade(MUTED, rr), 6, 18)
        text(d, W / 2, 1330, "起動（ブート）：電源を入れてから OS が動くまで", 34, MUTED, q, False)
        return
    # 1行目: タイトル
    r = c.p(1, 0.4)
    pop = 1 + 0.06 * off_pulse(t)
    shout(d, W / 2, 620, "ARE YOU READY?", int(64 * pop), ACID, r)
    neon(d, W / 2, 820, "ハードウェア", 110, CYAN, r)
    neon(d, W / 2, 960, "レイヴ!", 140, PINK, r)
    # 光る帯（イコライザー）
    for k in range(15):
        h = 30 + 120 * abs(math.sin(t * 5 + k * 0.8)) * (0.6 + 0.4 * off_pulse(t))
        x = 150 + k * 56
        d.rounded_rectangle((x, 1260 - h, x + 36, 1260), radius=8, fill=fade((ACID, CYAN, PINK)[k % 3], r * 0.9))


def sc_cpu(d, c, t):
    # 0〜1行目: マルチコア
    qa = phase(c, 0, 1)
    if qa > 0:
        rbox(d, W / 2 - 300, 470, 600, 440, fade(CELL, qa), fade(ACID, qa), 18, 5)
        text(d, W / 2, 505, "CPU（マルチコア）", 34, ACID, qa)
        tasks = "ABCD"
        for k in range(4):
            x = W / 2 - 140 + (k % 2) * 280
            y = 620 + (k // 2) * 170
            busy = 0.5 + 0.5 * math.sin(t * 8 + k * 1.7)
            rbox(d, x - 120, y - 70, 240, 140, fade(mix(CELL, CYAN, 0.25 * busy), qa), fade(CYAN, qa), 12, 4)
            text(d, x, y - 22, f"コア{k + 1}", 34, WHITE, qa)
            text(d, x, y + 28, f"仕事 {tasks[k]}", 32, ACID, qa)
        text(d, W / 2, 960, "1つの CPU の中に、処理をする「コア」がいくつも", 34, WHITE, qa)
        if c.li >= 1:
            r = c.p(1, 0.6) * qa
            # 1コア（順番に）と 4コア（同時に）の比べ
            text(d, 150, 1070, "1コア", 36, MUTED, r, anchor="lm")
            for k in range(4):
                rr = ease((c.since(1) - k * 0.2) / 0.3) * qa
                d.rounded_rectangle((300 + k * 150, 1040, 440 + k * 150, 1100), radius=10, fill=fade(PINK, rr))
                text(d, 370 + k * 150, 1070, tasks[k], 32, NAVY, rr)
            text(d, 150, 1180, "4コア", 36, ACID, r, anchor="lm")
            for k in range(4):
                d.rounded_rectangle((300, 1135 + k * 28, 440, 1158 + k * 28), radius=6, fill=fade(ACID, r))
            text(d, 470, 1180, "← 同時に進む（並列処理）", 34, ACID, r, anchor="lm")
            text(d, W / 2, 1310, "コアが増えると、同時にできる仕事が増える", 34, MUTED, r, False)
    # 2〜3行目: GPU
    qb = phase(c, 2, 3)
    if qb > 0:
        neon(d, W / 2, 500, "GPU", 90, PINK, qb)
        text(d, W / 2, 590, "小さなコアが、とてもたくさん", 36, WHITE, qb)
        cols, rows = 16, 8
        lit = c.p(3, 0.8) if c.li >= 3 else 0
        for y in range(rows):
            for x in range(cols):
                cx, cy = 150 + x * 52, 680 + y * 52
                rr = ease((c.since(2) - (x + y) * 0.02) / 0.3) * qb
                on = lit * (0.6 + 0.4 * math.sin(t * 10 + x * 0.5 + y * 0.9))
                d.rectangle((cx, cy, cx + 40, cy + 40), fill=fade(mix(CELL, PINK, on), rr), outline=fade(CELL_LINE, rr))
        text(d, W / 2, 1150, "画像の表示（グラフィックス）も、計算も", 36, WHITE, qb)
        if c.li >= 3:
            r = c.p(3, 0.6) * qb
            box(d, W / 2, 1290, 860, 110, "同じ計算を、いっせいに（並列）", ACID, r, 44, tcol=ACID)
            text(d, W / 2, 1400, "画像処理や AI の学習に向いている", 34, MUTED, r, False)


def capacitor(d, cx, cy, level, q, col):
    """コンデンサ（電気をためる箱）。level 0〜1 がたまっている量。"""
    rbox(d, cx - 90, cy - 120, 180, 240, fade(CELL, q), fade(col, q), 14, 5)
    h = 220 * max(0.0, min(1.0, level))
    if h > 2:
        d.rounded_rectangle((cx - 80, cy + 110 - h, cx + 80, cy + 110), radius=10, fill=fade(col, q * 0.85))


def sc_memory(d, c, t):
    # 0〜1行目: DRAM とリフレッシュ
    qa = phase(c, 0, 1)
    if qa > 0:
        neon(d, W / 2, 500, "DRAM ＝ 主記憶", 76, CYAN, qa)
        # メモリのカード
        rbox(d, 140, 580, 800, 150, fade(mix(CELL, GREEN, 0.15), qa), fade(GREEN, qa), 10, 4)
        for k in range(8):
            rbox(d, 170 + k * 96, 605, 80, 80, fade(CELL, qa), fade(MUTED, qa), 6, 3)
        for k in range(30):
            d.rectangle((160 + k * 26, 712, 176 + k * 26, 730), fill=fade(ACID, qa * 0.8))
        text(d, W / 2, 780, "メインメモリ：CPU が今使うプログラムとデータを置く", 32, WHITE, qa)
        if c.li >= 1:
            r = c.p(1, 0.5) * qa
            # もれて減る → リフレッシュでもどる
            ph = (c.since(1) % 2.0) / 2.0
            lv = 1 - 0.6 * ph
            capacitor(d, 300, 1050, lv, r, CYAN)
            text(d, 300, 1210, "コンデンサ", 32, WHITE, r)
            for k in range(3):
                yy = 1100 + k * 30 + (ph * 60) % 30
                d.ellipse((400, yy, 412, yy + 12), fill=fade(CYAN, r * (1 - ph)))
            text(d, 470, 960, "電気をためて 0/1 を覚える", 34, WHITE, r, anchor="lm")
            text(d, 470, 1030, "→ 少しずつもれて消える", 34, PINK, r, anchor="lm")
            text(d, 470, 1100, "→ 定期的に書き直す", 34, ACID, r, anchor="lm")
            box(d, 680, 1200, 400, 90, "リフレッシュ", ACID, r, 44, tcol=ACID, head=True)
    # 2〜3行目: SRAM・キャッシュ
    qb = phase(c, 2, 3)
    if qb > 0:
        neon(d, W / 2, 500, "SRAM ＝ キャッシュ", 72, PINK, qb)
        items = [("CPU", ACID, 300), ("キャッシュ\n（SRAM）", PINK, 380), ("主記憶\n（DRAM）", CYAN, 460)]
        xs = [190, W / 2, 890]
        for k, (nm, col, w) in enumerate(items):
            rr = stagger(c, 2, k, 0.25) * qb
            rbox(d, xs[k] - 140, 600, 280, 170, fade(CELL, rr), fade(col, rr), 14, 5)
            for j, ln in enumerate(nm.split("\n")):
                text(d, xs[k], 660 + j * 50 + (20 if "\n" not in nm else 0), ln, 38 if j == 0 else 28, col if j else WHITE, rr)
        r2 = c.p(2, 0.6) * qb
        arrow(d, 330, 685, 395, 685, fade(ACID, r2), 6, 18)
        arrow(d, 750, 685, 685, 685, fade(MUTED, r2), 6, 18)
        text(d, xs[1], 820, "速い・小さい", 32, PINK, r2)
        text(d, xs[2], 820, "遅め・大きい", 32, CYAN, r2)
        text(d, W / 2, 900, "よく使うデータを CPU の近くに置いて、速く読む", 32, WHITE, r2)
        if c.li >= 3:
            r = c.p(3, 0.6) * qb
            text(d, W / 2, 1010, "フリップフロップ：電気が来ている間、0/1 を保つ回路", 32, ACID, r)
            rows = [("", "DRAM", "SRAM"), ("しくみ", "コンデンサ", "フリップフロップ"), ("リフレッシュ", "必要", "いらない"),
                    ("速さ", "遅め", "速い"), ("使う場所", "主記憶", "キャッシュ")]
            for i, (a, b2, s2) in enumerate(rows):
                rr = ease((c.since(3) - i * 0.12) / 0.3) * qb
                y = 1090 + i * 72
                if i:
                    d.line((120, y - 36, 960, y - 36), fill=fade(CELL_LINE, rr), width=2)
                text(d, 230, y, a, 30, MUTED, rr, False)
                text(d, 520, y, b2, 32 if i else 38, CYAN, rr)
                text(d, 810, y, s2, 32 if i else 38, PINK, rr)


def sc_volatile(d, c, t):
    # 0行目: RAM は電源を切ると消える
    qa = phase(c, 0, 0)
    if qa > 0:
        neon(d, W / 2, 500, "揮発性メモリ", 80, PINK, qa)
        chip_icon(d, W / 2, 720, 340, 190, PINK, qa, "RAM", 60)
        gone = ease((c.since(0) - 1.0) / 0.8)
        for k in range(8):
            v = "10110100"[k]
            text(d, 240 + k * 86, 920 - 60 * gone, v, 54, ACID, qa * (1 - gone))
        box(d, W / 2, 1080, 520, 110, "電源オフ → データが消える", PINK, qa * gone, 40)
    # 1行目: フラッシュメモリは消えない
    qb = phase(c, 1, 1)
    if qb > 0:
        neon(d, W / 2, 500, "不揮発性メモリ", 80, CYAN, qb)
        chip_icon(d, W / 2, 720, 400, 190, CYAN, qb, "フラッシュメモリ", 44)
        for k in range(8):
            text(d, 240 + k * 86, 920, "10110100"[k], 54, ACID, qb)
        box(d, W / 2, 1080, 560, 110, "電源オフでも、データが残る", CYAN, qb, 40)
        text(d, W / 2, 1210, "USBメモリ・SSD・SDカード に使われる", 34, MUTED, qb, False)
    # 2行目: 揮発・不揮発の分け
    qc = phase(c, 2, 2)
    if qc > 0:
        flip = int(max(0.0, c.since(2)) / (mc.BEAT * 2)) % 2
        for k, (nm, col, items) in enumerate([("揮発性", PINK, ["DRAM", "SRAM"]), ("不揮発性", CYAN, ["フラッシュメモリ", "ROM", "HDD・SSD"])]):
            x = W / 2 - 230 + k * 460
            hot = flip == k
            rbox(d, x - 210, 470, 420, 560, fade(mc.HOT if hot else CELL, qc), fade(col, qc), 18, 7 if hot else 4)
            neon(d, x, 550, nm, 60, col, qc)
            text(d, x, 630, "電源を切ると…", 30, MUTED, qc, False)
            text(d, x, 680, "消える" if k == 0 else "残る", 44, col, qc)
            for j, it in enumerate(items):
                rr = ease((c.since(2) - j * 0.2) / 0.3) * qc
                box(d, x, 790 + j * 100, 340, 80, it, col, rr, 34)
        text(d, W / 2, 1110, "RAM は作業台（速いけど消える）", 34, WHITE, qc)
        text(d, W / 2, 1170, "フラッシュメモリは引き出し（残る）", 34, WHITE, qc)
    countdown(d, c, 3, t)


def disk(d, cx, cy, r, ang, q, col):
    """回る円盤（HDD のプラッタ）。"""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fade(mix(CELL, col, 0.25), q), outline=fade(col, q), width=5)
    for k in (0.75, 0.5):
        d.ellipse((cx - r * k, cy - r * k, cx + r * k, cy + r * k), outline=fade(mix(CELL, col, 0.6), q), width=2)
    d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=fade(MUTED, q))
    for k in range(3):
        a = ang + k * 2.1
        d.line((cx + 40 * math.cos(a), cy + 40 * math.sin(a), cx + r * 0.95 * math.cos(a), cy + r * 0.95 * math.sin(a)),
               fill=fade(WHITE, q * 0.5), width=3)


def ssd_icon(d, cx, cy, q):
    rbox(d, cx - 260, cy - 130, 520, 260, fade(CELL, q), fade(CYAN, q), 16, 5)
    for k in range(4):
        x = cx - 190 + k * 125
        rbox(d, x - 50, cy - 70, 100, 110, fade(mix(CELL, CYAN, 0.2), q), fade(CYAN, q), 8, 3)
    text(d, cx, cy + 90, "フラッシュメモリ", 28, CYAN, q, False)


def sc_drop(d, c, t):
    pop = 1 + 0.1 * off_pulse(t)
    # 0〜1行目: SSD
    qa = phase(c, 0, 1)
    if qa > 0:
        shout(d, W / 2, 500, "SSD!", int(110 * pop), CYAN, qa)
        ssd_icon(d, W / 2, 750, qa)
        if c.li >= 1:
            for k, (s, col) in enumerate([("回る部品がない", WHITE), ("静か・速い", ACID), ("衝撃に強い", CYAN)]):
                rr = stagger(c, 1, k, 0.3) * qa
                box(d, W / 2, 990 + k * 125, 560, 100, s, col, rr, 42, tcol=col)
    # 2〜3行目: HDD
    qb = phase(c, 2, 3)
    if qb > 0:
        shout(d, W / 2, 500, "HDD!", int(110 * pop), PINK, qb)
        spin = c.since(2) * 9
        cx, cy = W / 2 - 60, 800
        disk(d, cx, cy, 230, spin, qb, PINK)
        if c.li >= 3:
            r = c.p(3, 0.5) * qb
            # ヘッドのアーム（左右にふれる）
            a = math.radians(208 + 12 * math.sin(c.since(3) * 3))
            px, py = cx + 330, cy + 180
            hx, hy = px + 240 * math.cos(a), py + 240 * math.sin(a)
            d.line((px, py, hx, hy), fill=fade(ACID, r), width=14)
            d.ellipse((px - 26, py - 26, px + 26, py + 26), fill=fade(ACID, r))
            d.rectangle((hx - 14, hy - 14, hx + 14, hy + 14), fill=fade(WHITE, r))
            text(d, px - 10, py + 70, "ヘッド", 34, ACID, r)
            text(d, W / 2, 1110, "円盤（プラッタ）を回して、ヘッドが磁気で読み書き", 32, WHITE, r)
        text(d, cx - 180, 560, "回る", 34, PINK, qb)
    # 4行目: くらべ
    qc = phase(c, 4, 4)
    if qc > 0:
        neon(d, W / 2, 500, "SSD と HDD", 72, ACID, qc)
        rows = [("", "SSD", "HDD"), ("しくみ", "フラッシュメモリ", "回る円盤と磁気"), ("速さ", "速い", "遅め"),
                ("音", "静か", "回る音がする"), ("同じ容量の値段", "高め", "安い")]
        for i, (a, s, h) in enumerate(rows):
            rr = ease((c.since(4) - i * 0.12) / 0.3) * qc
            y = 640 + i * 110
            if i:
                d.line((100, y - 55, 980, y - 55), fill=fade(CELL_LINE, rr), width=2)
            text(d, 230, y, a, 30, MUTED, rr, False)
            text(d, 540, y, s, 34 if i else 50, CYAN, rr)
            text(d, 830, y, h, 34 if i else 50, PINK, rr)
        shout(d, W / 2, 1270, "HARDWARE RAVE!", int(60 * pop), ACID, qc)


def plug(d, cx, cy, q, col, label="USB", s=1.0):
    """USB のプラグ（横向き。cx が先の位置）。"""
    rbox(d, cx - 150 * s, cy - 45 * s, 110 * s, 90 * s, fade(MUTED, q), fade(WHITE, q), 6, 3)
    rbox(d, cx - 300 * s, cy - 60 * s, 160 * s, 120 * s, fade(CELL, q), fade(col, q), 14, 4)
    text(d, cx - 220 * s, cy, label, int(32 * s), col, q)
    d.line((cx - 300 * s, cy, cx - 520 * s, cy), fill=fade(col, q), width=int(14 * s))


def pc(d, cx, cy, q, on=True):
    rbox(d, cx - 150, cy - 110, 300, 200, fade(CELL, q), fade(CYAN, q), 12, 5)
    d.rectangle((cx - 120, cy - 82, cx + 120, cy + 62), fill=fade(mix(NAVY, CYAN, 0.35 if on else 0.05), q))
    d.rectangle((cx - 40, cy + 90, cx + 40, cy + 120), fill=fade(MUTED, q))
    d.rectangle((cx - 90, cy + 120, cx + 90, cy + 132), fill=fade(MUTED, q))
    if on:
        text(d, cx, cy - 10, "ON", 40, ACID, q)


def sc_usb(d, c, t):
    # 0〜1行目: 抜き差し・ホットプラグ
    qa = phase(c, 0, 1)
    if qa > 0:
        neon(d, W / 2, 500, "USB", 90, CYAN, qa)
        pc(d, 820, 760, qa)
        port_x = 650
        d.rectangle((port_x - 10, 720, port_x + 4, 800), fill=fade(WHITE, qa))
        ins = 0.5 + 0.5 * math.sin(c.since(0) * 3) if c.li >= 0 else 0
        plug(d, port_x - 30 * (1 - ins) - 10, 760, qa, CYAN, s=0.9)
        text(d, W / 2, 920, "抜いたり差したりが、自由にできる", 36, WHITE, qa)
        if c.li >= 1:
            r = c.p(1, 0.5) * qa
            box(d, W / 2, 1060, 520, 110, "ホットプラグ", ACID, r, 52, tcol=ACID, head=True)
            text(d, W / 2, 1180, "パソコンの電源を入れたまま、抜き差しできる", 34, WHITE, r)
    # 2行目: バスパワー
    qb = phase(c, 2, 2)
    if qb > 0:
        neon(d, W / 2, 500, "バスパワー", 84, ACID, qb)
        pc(d, 230, 760, qb)
        rbox(d, 760, 680, 220, 160, fade(CELL, qb), fade(PINK, qb), 14, 4)
        text(d, 870, 740, "外付け", 30, WHITE, qb)
        text(d, 870, 790, "HDD", 40, PINK, qb)
        d.line((380, 760, 760, 760), fill=fade(CYAN, qb), width=12)
        for k in range(4):
            x = 380 + ((c.since(2) * 220 + k * 95) % 380)
            d.polygon([(x, 730), (x + 22, 760), (x, 790)], fill=fade(ACID, qb))
        text(d, 570, 700, "電気 ＋ データ", 32, ACID, qb)
        text(d, W / 2, 940, "USB のケーブルから電気をもらって動く", 36, WHITE, qb)
        text(d, W / 2, 1010, "（コンセントや電池がいらない）", 32, MUTED, qb, False)
    # 3行目: プラグアンドプレイ
    qc = phase(c, 3, 3)
    if qc > 0:
        neon(d, W / 2, 500, "プラグアンドプレイ", 76, PINK, qc)
        steps = [("つなぐ", CYAN), ("OS が見つける", VIOLET), ("設定を自動で", ACID), ("すぐ使える!", PINK)]
        for k, (s, col) in enumerate(steps):
            rr = stagger(c, 3, k, 0.35) * qc
            y = 640 + k * 150
            box(d, W / 2, y, 560, 110, s, col, rr, 44, tcol=col)
            if k:
                arrow(d, W / 2, y - 95, W / 2, y - 57, fade(MUTED, rr), 6, 16)
        text(d, W / 2, 1270, "ドライバなどの設定を、OS が自動でしてくれる", 32, MUTED, qc, False)


def waves_icon(d, cx, cy, q, col, n=3, r0=40, dr=40, ang=0):
    for k in range(n):
        r = r0 + k * dr
        d.arc((cx - r, cy - r, cx + r, cy + r), ang - 40, ang + 40, fill=fade(col, q * (1 - k * 0.2)), width=8)


def sc_wireless(d, c, t):
    # 0行目: Bluetooth
    qa = phase(c, 0, 0)
    if qa > 0:
        neon(d, W / 2, 500, "Bluetooth", 84, CYAN, qa)
        rbox(d, 170, 650, 170, 300, fade(CELL, qa), fade(WHITE, qa), 24, 5)
        text(d, 255, 800, "スマホ", 30, WHITE, qa)
        d.ellipse((790, 720, 900, 830), fill=fade(CELL, qa), outline=fade(CYAN, qa), width=5)
        text(d, 845, 880, "イヤホン", 30, WHITE, qa)
        ph = (c.since(0) * 1.5) % 1
        waves_icon(d, 360, 790, qa * (1 - ph * 0.5), CYAN, 3, 50 + ph * 80, 70, 0)
        text(d, W / 2, 1040, "近くの機器と、電波でつなぐ（ワイヤレス）", 36, WHITE, qa)
        text(d, W / 2, 1110, "数m〜数十mくらいまで", 32, MUTED, qa, False)
    # 1行目: NFC
    qb = phase(c, 1, 1)
    if qb > 0:
        neon(d, W / 2, 500, "NFC", 90, ACID, qb)
        tap = 0.5 + 0.5 * math.sin(c.since(1) * 4)
        rbox(d, 300, 960, 480, 180, fade(CELL, qb), fade(MUTED, qb), 18, 5)
        text(d, W / 2, 1050, "読み取り機", 36, WHITE, qb)
        cy = 720 + 110 * tap
        rbox(d, 380, cy - 110, 320, 200, fade(mix(CELL, ACID, 0.2), qb), fade(ACID, qb), 18, 5)
        text(d, W / 2, cy - 10, "IC カード", 36, ACID, qb)
        text(d, W / 2, 1220, "かざすだけで通信（およそ10cm 以内）", 36, WHITE, qb)
        text(d, W / 2, 1290, "交通系 IC カード・スマホの支払い", 32, MUTED, qb, False)
    # 2〜3行目: HDMI
    qc = phase(c, 2, 3)
    if qc > 0:
        neon(d, W / 2, 500, "HDMI", 90, PINK, qc)
        pc(d, 210, 760, qc)
        rbox(d, 650, 620, 340, 230, fade(CELL, qc), fade(PINK, qc), 12, 5)
        d.rectangle((675, 645, 965, 825), fill=fade(mix(NAVY, PINK, 0.3), qc))
        text(d, 820, 735, "テレビ", 40, WHITE, qc)
        d.line((360, 760, 650, 760), fill=fade(PINK, qc), width=16)
        text(d, 505, 720, "1本", 32, ACID, qc)
        text(d, W / 2, 940, "映像と音を、デジタルで送る", 36, WHITE, qc)
        if c.li >= 3:
            r = c.p(3, 0.5) * qc
            for k, (s, col) in enumerate([("映像", CYAN), ("音声", ACID)]):
                y = 1060 + k * 120
                x = 220 + ((c.since(3) * 260) % 520)
                box(d, x, y, 180, 90, s, col, r, 38, tcol=col)
                arrow(d, 140, y + 60, 940, y + 60, fade(mix(NAVY, col, 0.5), r), 4, 16)
            text(d, W / 2, 1330, "1本のケーブルで、まとめて届ける", 34, WHITE, c.p(3, 0.5) * qc)


def circles(d, cx, cy, cols, q, r=170, sep=110, mode="add"):
    """光の三原色（加法混色）・色の三原色（減法混色）の円。"""
    pos = [(cx, cy - sep * 0.65), (cx - sep * 0.75, cy + sep * 0.5), (cx + sep * 0.75, cy + sep * 0.5)]
    step = 6
    for y in range(int(cy - sep - r), int(cy + sep + r), step):
        for x in range(int(cx - sep - r), int(cx + sep + r), step):
            ins = [(x - px) ** 2 + (y - py) ** 2 <= r * r for px, py in pos]
            if not any(ins):
                continue
            if mode == "add":
                c = [0, 0, 0]
                for k, on in enumerate(ins):
                    if on:
                        c = [min(255, a + b) for a, b in zip(c, cols[k])]
            else:
                c = [255, 255, 255]
                for k, on in enumerate(ins):
                    if on:
                        c = [a * b // 255 for a, b in zip(c, cols[k])]
                if all(ins):
                    c = [40, 40, 40]
            d.rectangle((x, y, x + step, y + step), fill=fade(tuple(c), q))


def sc_color(d, c, t):
    # 0〜1行目: RGB
    qa = phase(c, 0, 1)
    if qa > 0:
        neon(d, W / 2, 500, "光の三原色 RGB", 72, WHITE, qa)
        sep = 110 if c.li < 1 else lerp(170, 110, c.p(1, 1.0))
        if c.li < 1:
            sep = 200
        circles(d, W / 2, 880, [(255, 40, 40), (40, 255, 40), (40, 40, 255)], qa, 170, sep)
        text(d, W / 2, 1180, "赤（R）・緑（G）・青（B）", 36, WHITE, qa)
        if c.li >= 1:
            r = c.p(1, 0.5) * qa
            box(d, W / 2, 1270, 760, 100, "まぜるほど明るく → 白（加法混色）", ACID, r, 38, tcol=ACID)
            text(d, W / 2, 1370, "ディスプレイの色", 32, MUTED, r, False)
    # 2〜3行目: CMYK
    qb = phase(c, 2, 3)
    if qb > 0:
        neon(d, W / 2, 500, "印刷は CMYK", 72, CYAN, qb)
        sep = 200 if c.li < 3 else lerp(200, 110, c.p(3, 1.0))
        circles(d, W / 2, 880, [(0, 200, 230), (235, 0, 140), (250, 225, 0)], qb, 170, sep, "sub")
        text(d, W / 2, 1180, "シアン（C）・マゼンタ（M）・イエロー（Y）", 34, WHITE, qb)
        if c.li >= 3:
            r = c.p(3, 0.5) * qb
            box(d, W / 2, 1270, 760, 100, "まぜるほど暗く → 黒に近づく（減法混色）", PINK, r, 36, tcol=PINK)
            text(d, W / 2, 1370, "K は黒。3色だけではきれいな黒にならないので足す", 30, MUTED, r, False)
    countdown(d, c, 4, t)


def sc_pixel(d, c, t):
    pop = 1 + 0.1 * off_pulse(t)
    # 0〜1行目: 画素と解像度
    qa = phase(c, 0, 1)
    if qa > 0:
        shout(d, W / 2, 500, "PIXEL!", int(100 * pop), PINK, qa)
        text(d, W / 2, 590, "画素（ピクセル）：画像をつくる小さな点", 34, WHITE, qa)

        def grid(cx, cy, n, size, q):
            cell = size / n
            for y in range(n):
                for x in range(n):
                    px = (x + 0.5) / n - 0.5
                    py = (y + 0.5) / n - 0.5
                    on = px * px + py * py < 0.16
                    col = ACID if on else CELL
                    d.rectangle((cx - size / 2 + x * cell, cy - size / 2 + y * cell, cx - size / 2 + (x + 1) * cell - 1,
                                 cy - size / 2 + (y + 1) * cell - 1), fill=fade(col, q))
        if c.li < 1:
            grid(W / 2, 880, 8, 420, qa)
            text(d, W / 2, 1140, "8 × 8 の画素", 34, MUTED, qa, False)
        else:
            r = c.p(1, 0.5) * qa
            grid(290, 850, 8, 360, qa)
            grid(790, 850, 32, 360, r)
            text(d, 290, 1070, "8 × 8", 36, MUTED, qa)
            text(d, 790, 1070, "32 × 32", 36, ACID, r)
            arrow(d, 490, 850, 590, 850, fade(ACID, r), 6, 20)
            box(d, W / 2, 1200, 800, 100, "解像度が高い ＝ 画素が多くて、くっきり", ACID, r, 36, tcol=ACID)
            text(d, W / 2, 1310, "フル HD：1920 × 1080 ＝ 約207万画素", 32, MUTED, r, False)
    # 2〜3行目: dpi
    qb = phase(c, 2, 3)
    if qb > 0:
        shout(d, W / 2, 500, "dpi!", int(100 * pop), CYAN, qb)
        text(d, W / 2, 590, "dots per inch：1インチの中の点の数", 34, WHITE, qb)
        if c.li == 2:
            r = c.p(2, 0.4) * qb
            box(d, W / 2, 820, 560, 170, "300 dpi", CYAN, r, 84, tcol=CYAN, head=True)
            text(d, W / 2, 990, "＝ 1インチ（2.54cm）に 300個の点", 40, WHITE, r)
            text(d, W / 2, 1070, "プリンタやスキャナの細かさを表す", 32, MUTED, r, False)
        if c.li >= 3:
            r = c.p(3, 0.5) * qb
            x0, x1 = 160, 920
            d.line((x0, 720, x1, 720), fill=fade(WHITE, r), width=4)
            d.line((x0, 700, x0, 740), fill=fade(WHITE, r), width=4)
            d.line((x1, 700, x1, 740), fill=fade(WHITE, r), width=4)
            text(d, W / 2, 680, "1インチ ＝ 2.54cm", 32, WHITE, r)
            for k, (n, col) in enumerate([(6, PINK), (24, ACID)]):
                y = 850 + k * 170
                for j in range(n):
                    rr = ease((c.since(3) - j * 0.02) / 0.2) * r
                    x = x0 + (x1 - x0) * (j + 0.5) / n
                    rad = (x1 - x0) / n * 0.4
                    d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=fade(col, rr))
                text(d, x0, y + 70, ("点が少ない → 粗い", "点が多い → 細かい")[k], 30, col, r, anchor="lm")
            box(d, W / 2, 1270, 820, 100, "dpi が大きいほど、細かく印刷できる", CYAN, r, 38, tcol=CYAN)
    # 4行目: 盛り上がり
    qc = phase(c, 4, 4)
    if qc > 0:
        for y in range(10):
            for x in range(10):
                on = (x * 3 + y * 5 + int(mc.beat(t) * 2)) % 4 == 0
                rr = ease((c.since(4) - (x + y) * 0.03) / 0.3) * qc
                col = (PINK, CYAN, ACID)[(x + y) % 3] if on else CELL
                d.rectangle((140 + x * 80, 480 + y * 80, 210 + x * 80, 550 + y * 80), fill=fade(col, rr))
        shout(d, W / 2, 1360, "HARDWARE RAVE!", int(66 * pop), ACID, qc)


def sc_bridge(d, c, t):
    # 0〜1行目: センサ → アクチュエータ
    qa = phase(c, 0, 1)
    if qa > 0:
        nodes = [("センサ", "光・温度・動きを\n電気の信号に", CYAN, 580), ("コンピュータ", "判断する", VIOLET, 830),
                 ("アクチュエータ", "信号を動きに\n（モーターなど）", PINK, 1080)]
        for k, (nm, sub, col, y) in enumerate(nodes):
            if k == 2 and c.li < 1:
                break
            rr = (c.p(0, 0.6) if k < 2 else c.p(1, 0.6)) * qa
            box(d, 330, y, 400, 130, nm, col, rr, 46, tcol=col, head=True)
            for j, ln in enumerate(sub.split("\n")):
                text(d, 560, y - 20 * (len(sub.split("\n")) - 1) + j * 44, ln, 32, WHITE, rr, anchor="lm")
            if k:
                arrow(d, 330, y - 185, 330, y - 70, fade(MUTED, rr), 6, 18)
        text(d, W / 2, 1290, "感じ取る → 考える → 動かす（IoT の機器）", 34, MUTED, c.p(1, 0.5) * qa, False)
    # 2行目: タッチパネル
    qb = phase(c, 2, 2)
    if qb > 0:
        neon(d, W / 2, 500, "タッチパネル", 80, ACID, qb)
        rbox(d, 340, 590, 400, 620, fade(CELL, qb), fade(WHITE, qb), 36, 6)
        ph = (c.since(2) * 1.2) % 1
        fx, fy = 540, 850
        for k in range(3):
            rr = 30 + (ph + k / 3) % 1 * 90
            d.ellipse((fx - rr, fy - rr, fx + rr, fy + rr), outline=fade(ACID, qb * (1 - (ph + k / 3) % 1)), width=4)
        d.ellipse((fx - 26, fy - 26, fx + 26, fy + 26), fill=fade(ACID, qb))
        text(d, W / 2, 1280, "スマホは静電容量方式：指の電気の変化で場所がわかる", 30, WHITE, qb)
    # 3行目: 3Dプリンタ
    qc = phase(c, 3, 3)
    if qc > 0:
        neon(d, W / 2, 500, "3Dプリンタ", 80, CYAN, qc)
        n = 12
        done = min(n, int(max(0.0, c.since(3)) * 6))
        for k in range(done):
            w = 420 - abs(k - 5) * 22
            y = 1080 - k * 36
            d.rounded_rectangle((W / 2 - w / 2, y - 32, W / 2 + w / 2, y), radius=8, fill=fade(mix(CYAN, VIOLET, k / n), qc))
        if done < n:
            y = 1080 - done * 36 - 60
            d.rectangle((W / 2 - 40, y - 60, W / 2 + 40, y), fill=fade(MUTED, qc))
            d.polygon([(W / 2 - 20, y), (W / 2 + 20, y), (W / 2, y + 30)], fill=fade(ACID, qc))
        text(d, W / 2, 1200, "うすい層を1枚ずつ積み重ねて、立体をつくる", 34, WHITE, qc)
    # 4〜5行目: 有機EL と 液晶
    qd = phase(c, 4, 5)
    if qd > 0:
        r4 = c.p(4, 0.5) * qd
        neon(d, W / 2, 490, "有機EL", 64, ACID, r4)
        for k in range(8):
            on = 0.6 + 0.4 * math.sin(t * 6 + k)
            col = (PINK, ACID, CYAN)[k % 3]
            d.rounded_rectangle((180 + k * 92, 570, 250 + k * 92, 650), radius=8, fill=fade(mix(NAVY, col, on), r4))
        text(d, W / 2, 700, "画素が自分で光る → 黒がしっかり黒・うすくできる", 30, WHITE, r4)
        if c.li >= 5:
            r5 = c.p(5, 0.5) * qd
            neon(d, W / 2, 820, "液晶", 64, CYAN, r5)
            layers = [("カラーフィルター", PINK), ("液晶（光を通す・止める）", CYAN), ("バックライト", ACID)]
            for k, (nm, col) in enumerate(layers):
                rr = stagger(c, 5, k, 0.25) * qd
                y = 920 + k * 110
                d.polygon([(260, y), (900, y), (840, y + 70), (200, y + 70)], fill=fade(mix(CELL, col, 0.35), rr), outline=fade(col, rr))
                text(d, 550, y + 35, nm, 32, WHITE, rr)
            for k in range(5):
                x = 300 + k * 120
                arrow(d, x, 1220, x, 900, fade(mix(NAVY, ACID, 0.5), r5), 3, 14)
            text(d, W / 2, 1300, "後ろのバックライトで照らして、液晶で光を調節する", 30, WHITE, r5)


def sc_clock(d, c, t):
    q = c.p(0, 0.5) if c.li >= 0 else 0
    if c.li <= 0:
        neon(d, W / 2, 500, "クロック周波数", 80, ACID, q)
        speed = 1 + 4 * ease(c.since(0) / 3) if c.li >= 0 else 1
        pts = []
        for i in range(0, 841, 4):
            ph = (i / 840 * 6 * speed + t * 2) % 1
            pts.append((120 + i, 780 if ph < 0.5 else 640))
        d.line(pts, fill=fade(CYAN, q), width=6)
        text(d, W / 2, 900, "CPU の動きをそろえる、合図の速さ", 36, WHITE, q)
        box(d, W / 2, 1040, 760, 110, "3GHz ＝ 1秒に 30億回", PINK, q, 50, tcol=PINK, head=True)
        text(d, W / 2, 1160, "Hz（ヘルツ）：1秒あたりの回数", 32, MUTED, q, False)
        shout(d, W / 2, 1290, "FULL POWER!", int(70 * (1 + 0.1 * off_pulse(t))), ACID, c.p(0, 0.5) * ease((c.since(0) - 1.0) / 0.4))
    countdown(d, c, 1, t)


def sc_final(d, c, t):
    pop = 1 + 0.12 * off_pulse(t)
    pairs = [("SSD", "HDD", CYAN, PINK, "フラッシュメモリ", "回る円盤"),
             ("DRAM", "SRAM", CYAN, PINK, "主記憶", "キャッシュ"),
             ("USB", "Bluetooth", ACID, CYAN, "ケーブル", "無線")]
    if c.li <= 2:
        for k in range(min(3, c.li + 1)):
            a, b, ca, cb, sa, sb = pairs[k]
            r = c.p(k, 0.4)
            y = 540 + k * 300
            shout(d, 290, y, a + "!", int((70 if len(a) < 5 else 56) * (pop if k == c.li else 1)), ca, r)
            shout(d, 790, y, b + "!", int((70 if len(b) < 5 else 50) * (pop if k == c.li else 1)), cb, r)
            text(d, 290, y + 80, sa, 30, WHITE, r, False)
            text(d, 790, y + 80, sb, 30, WHITE, r, False)
        return
    r = c.p(3, 0.4)
    words = ["SSD", "HDD", "DRAM", "SRAM", "USB", "NFC", "HDMI", "RGB", "CMYK", "dpi", "GPU", "CPU"]
    for k, w in enumerate(words):
        x = 200 + (k % 3) * 340
        y = 520 + (k // 3) * 120
        on = (k + int(mc.beat(t))) % 3 == 0
        col = (PINK, CYAN, ACID)[k % 3]
        box(d, x, y, 300, 96, w, col, ease((c.since(3) - k * 0.05) / 0.3), 40, fill=mc.HOT if on else None, tcol=col)
    neon(d, W / 2, 1080, "ハードウェア", 96, CYAN, r)
    neon(d, W / 2, 1210, "レイヴ!", 120, PINK, r)
    if c.li >= 4:
        shout(d, W / 2, 1360, "NEVER ENDING!", int(60 * pop), ACID, c.p(4, 0.4))


def sc_outro(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    off = ease(c.since(0) / 3.0) if c.li >= 0 else 0
    pc(d, W / 2, 720, q, on=off < 0.6)
    h = max(4, 140 * (1 - off))
    d.rectangle((W / 2 - 120 * (1 - off * 0.8), 700 - h / 2, W / 2 + 120 * (1 - off * 0.8), 700 + h / 2), fill=fade(WHITE, q * (0.2 + 0.6 * off)))
    shout(d, W / 2, 960, "SHUTDOWN", 72, PINK, q)
    text(d, W / 2, 1060, "また起動しよう", 40, WHITE, c.p(0, 0.6) * ease((c.since(0) - 1.5) / 0.6))


def sc_end(d, c, t):
    st = t - c.start
    q = ease((st - 0.3) / 1.0)
    chip_icon(d, W / 2, 600, 260, 180, ACID, q, "CPU", 56, 6)
    neon(d, W / 2, 800, "ハードウェア・レイヴ", 84, CYAN, q)
    q = ease((st - 1.2) / 1.0)
    if q > 0:
        d.rounded_rectangle((180, 1120, W - 180, 1390), radius=28, fill=mix(NAVY, (6, 6, 16), q))
    text(d, W / 2, 1180, "用語の復習は", 40, MUTED, q, False)
    text(d, W / 2, 1260, "fe.yogo-drill.com", 52, ACID, q)
    text(d, W / 2, 1335, "ip.yogo-drill.com", 52, ACID, q)


PLAN = [
    (sc_intro, "電源オン", "BOOT", 1),
    (sc_cpu, "マルチコアと GPU", "MULTI-CORE・GPU", 2),
    (sc_memory, "DRAM と SRAM", "MAIN MEMORY・CACHE", 3),
    (sc_volatile, "揮発性と不揮発性", "VOLATILE・FLASH MEMORY", 4),
    (sc_drop, "SSD と HDD", "SSD・HDD", 5),
    (sc_usb, "USB", "HOT PLUG・BUS POWER・PLUG AND PLAY", 6),
    (sc_wireless, "つなぐ技術", "BLUETOOTH・NFC・HDMI", 7),
    (sc_color, "RGB と CMYK", "ADDITIVE・SUBTRACTIVE COLOR", 8),
    (sc_pixel, "画素と dpi", "PIXEL・RESOLUTION・DPI", 9),
    (sc_bridge, "入出力の機器", "SENSOR・ACTUATOR・DISPLAY", 10),
    (sc_clock, "クロック", "CLOCK FREQUENCY", 11),
    (sc_final, "ハードウェア・レイヴ", "SSD・HDD・DRAM・SRAM・USB・BLUETOOTH", 12),
    (sc_outro, "シャットダウン", "SHUTDOWN", 13),
]
# 前のまとまりの最後の行と次のまとまりの最初の行の間が短い所（USB → つなぐ技術）があるので、場面は歌い出しの少し前に変える
mc.LEAD = 0.35
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=2.0)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・13のまとまり・締め）。Mixkit の Stock Video Free License の素材
CLIPS = [50449,   # タイトル: 暗い中のレーザーとダンサー（リールの1枚目なので、暗くて文字が読みやすい映像）
         3524,    # 電源オン: テレビのノイズ（起動）
         1140,    # マルチコア・GPU: マイクロチップのアップ
         28900,   # DRAM・SRAM: 暗闇のデジタル時計（基板の映像は細かく、暗い格子の映像は途中で大きな英字が出るのでやめた）
         3524,    # 揮発性: テレビのノイズ（消える）
         4188,    # SSD・HDD（ドロップ）: 電子音楽のフェスのステージ
         4126,    # USB: DJ のノートパソコンとターンテーブル
         42041,   # つなぐ技術: 夜の街の空撮（光の道がつながる）
         4344,    # RGB・CMYK: マゼンタの光のクラブ
         4187,    # 画素・dpi（ドロップ2）: LED の画面のステージの DJ
         4124,    # 入出力の機器（ブリッジ）: 星空
         50455,   # クロック: レーザーの下のサイバーパンクのダンサー
         4185,    # 最後のドロップ: フェスの観客
         3524,    # シャットダウン: テレビのノイズ
         49878]   # 締め: 夜の大きな街
if SCENES[-1][0] >= mc.DUR - 0.5:
    SCENES.pop()
    CLIPS.pop()

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS])
