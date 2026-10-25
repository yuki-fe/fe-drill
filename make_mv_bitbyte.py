"""曲「ビットバイト・ダンス」の MV（縦長 1080×1920・60fps）を作る。

シンセとボコーダーの曲に、基礎理論の用語（ビットとバイト・2のn乗・16進数・基数の変換・AND/OR/NOT/XOR・シフト・
2の補数・パリティ・CRC・ハミング符号・情報量・期待値・正規分布・オートマトン・BNF）を重ねて、歌詞の1行ごとに図が1つ進む。
背景は本物の映像（Mixkit の Free の素材）。

デザイン（ui-ux-pro-max の Dark Mode と Arcade & Retro Game / Gaming の提案をもとにした）:
- 深い紫紺の背景に、0＝シアン・1＝ローズ（曲じゅうビットの色をそろえる）、補助の紫、正しい＝緑、カラオケ＝黄色
- 見出しとビットの数字はドット文字の DotGothic16（Google Fonts、OFL。提案の Press Start 2P は日本語が出せない）
- 図と歌詞の文字は読みやすさのため BIZ UD ゴシックのまま

使うファイル（notes/曲の動画/ビットバイト・ダンス/、公開しない）
- ビットバイト・ダンス.mp3 / _歌詞.txt / _時間.json

    python make_mv_bitbyte.py --jobs 4              # 縦長
    python make_mv_bitbyte.py --safe --jobs 4       # リール・ショート用の配置（_MV_リール用.mp4）
    python make_mv_bitbyte.py --youtube --jobs 4    # YouTube 用の横長
    python make_mv_bitbyte.py --at 30 80            # その秒の静止画（確認用）
"""
import math
from pathlib import Path

import mv_common as mc
from mv_common import W, arrow, ease, font, lerp, mix, off_pulse, rbox

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "ビットバイト・ダンス"
HEAD = ROOT / "notes" / "曲の動画" / "フォント" / "DotGothic16-Regular.ttf"

# ---------- 色（この曲用。ほかの曲には関係しない） ----------
NAVY = (17, 10, 36)
mc.BG1, mc.BG2 = NAVY, (28, 14, 52)
WHITE = mc.CREAM = (241, 245, 249)
MUTED = mc.MUTED = (160, 160, 200)
YELLOW = mc.GOLD = (250, 204, 21)     # カラオケの色
ZERO = (34, 211, 238)                 # 0 ＝ シアン
ONE = (244, 63, 94)                   # 1 ＝ ローズ
VIOLET = mc.PURPLE = (167, 139, 250)
GREEN = mc.GREEN = (34, 197, 94)
mc.RED, mc.BLUE = ONE, ZERO
CELL = mc.CELL = (30, 22, 60)
CELL_LINE = mc.CELL_LINE = (84, 70, 140)
mc.HOT = (70, 24, 60)
mc.HEAD_FONT = str(HEAD)

mc.configure(DIR / "ビットバイト・ダンス.mp3", DIR / "ビットバイト・ダンス_歌詞.txt", DIR / "ビットバイト・ダンス_時間.json",
             "ビットバイト・ダンス", words=ROOT / "notes" / "曲の動画" / "作業用" / "ビットバイト・ダンス_認識.json")
# 最後のサビ（195秒〜）とアウトロは、音声認識の言葉が乱れている（「&」がくり返し出る）ので、言葉ごとのカラオケを使わない
for r in mc.ROWS:
    if r["s"] >= 195:
        r["knots"] = None
# 曲は -15.7 LUFS（いちばん大きい音 -4.3 dB）。YouTube の目安 -14 LUFS に合わせて +1.7 dB
mc.AUDIO_GAIN_DB = 1.7
OUT = DIR / "ビットバイト・ダンス_MV.mp4"
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"


def fade(c, q):
    return mix(NAVY, c, q)


def text(d, x, y, s, size, col, q=1.0, bold=True, anchor="mm"):
    if q > 0:
        d.text((x, y), s, font=font(size, bold), fill=fade(col, q), anchor=anchor)


def dot(d, x, y, s, size, col, q=1.0, anchor="mm"):
    """ドット文字（見出しの字体）。うすい光のふちどりをつける。"""
    if q <= 0:
        return
    f = font(size, face=str(HEAD))
    d.text((x, y), s, font=f, fill=fade(col, q), anchor=anchor, stroke_width=max(2, size // 22), stroke_fill=fade(mix(NAVY, col, 0.3), q))


def box(d, cx, cy, w, h, s, col, q=1.0, size=44, fill=None, tcol=None, dotted=False):
    if q <= 0:
        return
    y = cy + 18 * (1 - q)
    rbox(d, cx - w / 2, y - h / 2, w, h, fade(fill or CELL, q), fade(col, q), 14, 4)
    if s:
        if dotted:
            dot(d, cx, y + 2, s, size, tcol or WHITE, q)
        else:
            text(d, cx, y + 2, s, size, tcol or WHITE, q)


def bit(d, cx, cy, v, q=1.0, s=96, hot=False):
    """1つのビット。0 はシアン、1 はローズ。"""
    if q <= 0:
        return
    col = ONE if str(v) == "1" else (ZERO if str(v) == "0" else VIOLET)
    y = cy + 16 * (1 - q)
    rbox(d, cx - s / 2, y - s / 2, s, s, fade(mc.HOT if hot else CELL, q), fade(col, q), 12, 4 if not hot else 6)
    dot(d, cx, y + 2, str(v), int(s * 0.62), col, q)


def bits(d, cx, cy, vals, q=1.0, s=96, gap=10, hot=None, dance=0.0, t=0.0):
    n = len(vals)
    x0 = cx - (n * s + (n - 1) * gap) / 2 + s / 2
    for k, v in enumerate(vals):
        dy = -dance * 18 * abs(math.sin(t * 6 + k * 0.7))
        bit(d, x0 + k * (s + gap), cy + dy, v, q, s, hot is not None and k in hot)


def phase(c, i0, i1, length=0.5):
    """i0〜i1 行目のあいだだけ見える部分の濃さ。"""
    if c.li < i0:
        return 0.0
    q = c.p(i0, length)
    if c.li > i1:
        q *= 1 - ease(c.since(i1 + 1) / 0.35)
    return max(0.0, q)


def msg(d, c, y, table, size=38):
    """行ごとの説明（table: {行: (文, 色)}）。"""
    if c.li in table:
        s, col = table[c.li]
        r = ease(c.since(c.li) / 0.4)
        while font(size).getlength(s) > 980 and size > 26:
            size -= 2
        text(d, W / 2, y, s, size, col, r)


# ---------- 場面 ----------

def sc_title(d, c, t):
    if mc.SAFE:
        return sc_hook(d, c, t)
    q = ease((t - 0.05) / 0.6)
    bits(d, W / 2, 600, list("10110010"), q, 100, dance=0.5, t=t)
    dot(d, W / 2, 800, "ビットバイト", 110, ZERO, q)
    dot(d, W / 2, 930, "ダンス", 130, ONE, q)
    text(d, W / 2, 1080, "Bit Byte Dance", 44, VIOLET, ease((t - 0.4) / 0.6))
    text(d, W / 2, 1150, "0 と 1 の基礎理論で踊る、エレクトロの歌", 36, MUTED, ease((t - 0.4) / 0.6), False)


def sc_hook(d, c, t):
    """リール・ショートの最初の画面（つかみ）。1枚目から問いかける。答え（256通り）は Verse 1 で歌われる。"""
    # イントロの場面の見出し（#1 0と1）が先に描かれているので、背景の色（＝透明）で消す
    d.rectangle((0, 90, W, 430), fill=NAVY)
    bits(d, W / 2, 560, list("????????"), 1.0, 96, dance=0.6, t=t)
    dot(d, W / 2, 740, "8ビットで", 96, ZERO)
    dot(d, W / 2, 870, "何通り？", 110, ONE)
    text(d, W / 2, 1010, "答えは、この歌で。", 48, VIOLET)
    dot(d, W / 2, 1150, "ビットバイト・ダンス", 64, YELLOW)


def sc_intro(d, c, t):
    # リール・ショートでは、イントロの最初の行（〜3.9秒）まで問いかけの画面を出して、つかみを長めにする
    if mc.SAFE and t < 3.9:
        return sc_hook(d, c, t)
    q = c.p(0, 0.6) if c.li >= 0 else 0
    flip = int(mc.beat(t)) % 2
    vals = [str((k + flip) % 2) for k in range(8)]
    bits(d, W / 2, 700, vals, q, 104, dance=1.0, t=t)
    if c.li >= 1:
        r = c.p(1, 0.6)
        box(d, W / 2, 1000, 520, 120, "POWER ON", GREEN, r, 56, dotted=True, tcol=GREEN)
        text(d, W / 2, 1140, "コンピュータの中は、0 と 1 だけ", 38, WHITE, r)


def sc_bitbyte(d, c, t):
    # 1ビット: 0 か 1 の2通り
    qa = phase(c, 0, 1)
    if qa > 0:
        v = str(int(mc.beat(t) * 2) % 2)
        bit(d, W / 2, 650, v, qa, 220)
        text(d, W / 2, 850, "1ビット ＝ 0 か 1 の 2通り", 44, WHITE, qa)
        if c.li >= 1:
            r = c.p(1, 0.5) * qa
            bit(d, W / 2 - 160, 1030, "0", r, 120)
            bit(d, W / 2 + 160, 1030, "1", r, 120)
            text(d, W / 2, 1030, "か", 44, MUTED, r)
            text(d, W / 2, 1180, "情報のいちばん小さな単位", 36, MUTED, r, False)
    # 8ビット ＝ 1バイト
    qb = phase(c, 2, 3)
    if qb > 0:
        bits(d, W / 2, 620, list("01001011"), qb, 104)
        x0, x1 = W / 2 - 4 * 114 + 5, W / 2 + 4 * 114 - 5
        d.line((x0, 700, x0, 730, x1, 730, x1, 700), fill=fade(YELLOW, qb), width=5)
        dot(d, W / 2, 790, "8ビット ＝ 1バイト", 64, YELLOW, qb)
        if c.li >= 3:
            r = c.p(3, 0.6) * qb
            box(d, W / 2, 960, 640, 130, "2の8乗 ＝ 256通り", ONE, r, 64, dotted=True)
            text(d, W / 2, 1100, "00000000 〜 11111111", 40, WHITE, r)
            text(d, W / 2, 1165, "10進数の 0 〜 255 を表せる", 36, MUTED, r, False)


def sc_hex(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    # 4ビット → 16進数1けた
    bits(d, W / 2 - 150, 600, list("1111"), q, 100)
    arrow(d, W / 2 + 90, 600, W / 2 + 190, 600, fade(VIOLET, q), 6, 22)
    box(d, W / 2 + 290, 600, 130, 110, "F", YELLOW, q, 70, dotted=True, tcol=YELLOW)
    text(d, W / 2, 710, "4ビットで、16進数の1けた（16通り）", 36, WHITE, q)
    if c.li >= 1:
        r = c.p(1, 0.8)
        digs = "0123456789ABCDEF"
        for k, ch in enumerate(digs):
            rr = ease((c.since(1) - k * 0.06) / 0.3)
            x = 105 + (k % 8) * 124
            y = 850 + (k // 8) * 120
            col = YELLOW if ch in "ABCDEF" else ZERO
            box(d, x, y, 104, 96, ch, col, rr, 50, dotted=True, tcol=col)
        text(d, W / 2, 1090, "A＝10, B＝11 … F＝15", 38, YELLOW, r)
    if c.li >= 2:
        r = c.p(2, 0.6)
        box(d, W / 2, 1240, 860, 120, "FF ＝ 15×16 ＋ 15 ＝ 255", ONE, r, 46)
        text(d, W / 2, 1350, "1111 1111（2進数）＝ FF（16進数）", 34, MUTED, r, False)
    if c.li >= 3:
        r = c.p(3, 0.6)
        dot(d, W / 2, 1450, "F ＝ 15", 64, YELLOW, r)


def sc_power(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    dot(d, W / 2, 520, "nビット → 2のn乗 通り", 72, YELLOW, q)
    rows = [(1, 2), (2, 4), (3, 8), (4, 16), (8, 256)]
    for k, (n, v) in enumerate(rows):
        r = ease((c.since(0) - k * 0.25) / 0.35) if c.li >= 0 else 0
        y = 680 + k * 130
        text(d, 230, y, f"{n} ビット", 44, ZERO, r, anchor="lm")
        w = 560 * (math.log2(v) / 8) * (ease(c.p(1, 1.0)) if c.li >= 1 else 0.15)
        d.rounded_rectangle((470, y - 32, 470 + max(20, w), y + 32), radius=10, fill=fade(ONE, r))
        text(d, 470 + max(20, w) + 20, y, f"{v} 通り", 40, WHITE, r, anchor="lm")
    if c.li >= 1:
        text(d, W / 2, 1400, "1ビット増えるたびに、2倍（倍々ゲーム）", 38, YELLOW, c.p(1, 0.6))


def chorus(d, c, t, final=False):
    flip = int(mc.beat(t)) % 2
    # 0行目: 踊るビット
    if c.li <= 0:
        q = c.p(0, 0.5) if c.li >= 0 else 0.3
        bits(d, W / 2, 760, [str((k + flip) % 2) for k in range(8)], q, 104, dance=1.0, t=t)
        dot(d, W / 2, 960, "BIT BYTE DANCE", 76, VIOLET, q)
        return
    # 1行目: AND OR NOT XOR
    if c.li == 1:
        r = c.p(1, 0.4)
        names = [("AND", "両方 1 → 1"), ("OR", "どちらか 1 → 1"), ("NOT", "0 と 1 を反転"), ("XOR", "ちがうとき → 1")]
        for k, (nm, sub) in enumerate(names):
            rr = ease((c.since(1) - k * 0.25) / 0.3)
            y = 560 + k * 220
            box(d, 300, y, 300, 150, nm, (ONE, ZERO, VIOLET, YELLOW)[k], rr, 66, dotted=True)
            text(d, 500, y, sub, 40, WHITE, rr, anchor="lm")
        return
    # 2〜3行目: 2進 10進 16進
    if c.li in (2, 3):
        r = c.p(2, 0.5)
        bits(d, W / 2, 620, list("1101"), r, 110)
        text(d, W / 2, 740, "8 ＋ 4 ＋ 0 ＋ 1", 40, MUTED, r, False)
        if c.li >= 3:
            for k, (nm, v, col) in enumerate([("2進数", "1101", ZERO), ("10進数", "13", WHITE), ("16進数", "D", YELLOW)]):
                rr = ease((c.since(3) - k * 0.3) / 0.35)
                y = 900 + k * 170
                text(d, 300, y, nm, 44, MUTED, rr, anchor="lm")
                box(d, 700, y, 360, 130, v, col, rr, 66, dotted=True, tcol=col)
        return
    # 4〜5行目: シフト（最後のサビは 2の補数）
    if c.li in (4, 5):
        if final:
            r = c.p(4, 0.5)
            text(d, W / 2, 500, "2の補数：マイナスの数の表し方", 40, YELLOW, r)
            text(d, 150, 640, "＋5", 52, WHITE, r, anchor="lm")
            bits(d, W / 2 + 90, 640, list("00000101"), r, 84, 6)
            if c.li >= 5:
                r5 = c.p(5, 0.5)
                text(d, 150, 820, "反転", 40, VIOLET, r5, anchor="lm")
                bits(d, W / 2 + 90, 820, list("11111010"), r5, 84, 6)
                r6 = ease((c.since(5) - 0.8) / 0.4)
                text(d, 150, 1000, "＋1", 40, GREEN, r6, anchor="lm")
                bits(d, W / 2 + 90, 1000, list("11111011"), r6, 84, 6, hot={7})
                dot(d, W / 2, 1180, "11111011 ＝ −5", 64, ONE, r6)
            return
        left = c.li == 4
        r = c.p(c.li, 0.5)
        src, dst, sv, dv = ("0011", "0110", 3, 6) if left else ("0110", "0011", 6, 3)
        text(d, W / 2, 500, "左シフト：けたを左へ1つ → 2倍" if left else "右シフト：けたを右へ1つ → 半分", 40, YELLOW, r)
        bits(d, W / 2 - 60, 680, list(src), r, 110)
        text(d, W / 2 + 230, 680, f"＝ {sv}", 52, WHITE, r, anchor="lm")
        s = ease((c.since(c.li) - 0.4) / 0.6)
        arrow(d, W / 2 - 60, 770, W / 2 - 60 + (-80 if left else 80), 770, fade(VIOLET, s), 6, 22)
        bits(d, W / 2 - 60, 900, list(dst), s, 110)
        text(d, W / 2 + 230, 900, f"＝ {dv}", 52, GREEN, s, anchor="lm")
        return
    # 6〜7行目: 0 と 1 でできた世界
    r = c.p(6, 0.6)
    for y in range(8):
        for x in range(9):
            v = (x * 7 + y * 3 + int(mc.beat(t) * 2)) % 3 == 0
            rr = ease((c.since(6) - (x + y) * 0.03) / 0.3)
            dot(d, 140 + x * 100, 520 + y * 105, "1" if v else "0", 54, ONE if v else ZERO, rr * 0.9)
    if c.li >= 7:
        dot(d, W / 2, 1420, "BIT BYTE DANCE!", 80, YELLOW, c.p(7, 0.4))


def sc_chorus(d, c, t):
    chorus(d, c, t)


def sc_final(d, c, t):
    chorus(d, c, t, final=True)


def sc_logic(d, c, t):
    # NOT
    qa = phase(c, 0, 1)
    if qa > 0:
        dot(d, W / 2, 500, "NOT：0 と 1 を反転", 64, VIOLET, qa)
        bits(d, W / 2, 680, list("0101"), qa, 120)
        s = ease((c.since(0) - 0.6) / 0.5) if c.li >= 0 else 0
        arrow(d, W / 2, 770, W / 2, 850, fade(VIOLET, s * qa), 6, 22)
        bits(d, W / 2, 950, list("1010"), s * qa, 120)
        if c.li >= 1:
            text(d, W / 2, 1120, "0 → 1、1 → 0（くるりとひっくり返す）", 38, WHITE, c.p(1, 0.5) * qa)

    def table(x, title, col, rows, q, hl):
        dot(d, x, 560, title, 60, col, q)
        for i, (a, b, o) in enumerate(rows):
            y = 680 + i * 120
            rr = ease((q - 0.2 - i * 0.1) / 0.4) if q < 1 else 1
            bit(d, x - 140, y, a, rr * q, 84)
            bit(d, x - 40, y, b, rr * q, 84)
            text(d, x + 40, y, "→", 40, MUTED, rr * q)
            bit(d, x + 120, y, o, rr * q, 84, hot=(i in hl))
    rows_and = [("0", "0", "0"), ("0", "1", "0"), ("1", "0", "0"), ("1", "1", "1")]
    rows_or = [("0", "0", "0"), ("0", "1", "1"), ("1", "0", "1"), ("1", "1", "1")]
    qb = phase(c, 2, 3)
    if qb > 0:
        table(W / 2 - 230, "AND", ONE, rows_and, c.p(2, 0.8) * qb, {3})
        if c.li >= 3:
            table(W / 2 + 250, "OR", ZERO, rows_or, c.p(3, 0.8) * qb, {1, 2, 3})
        msg(d, c, 1250, {2: ("AND：両方が 1 のときだけ 1", ONE), 3: ("OR：どちらかが 1 なら 1", ZERO)})


def sc_errors(d, c, t):
    # パリティ
    qa = phase(c, 0, 1)
    if qa > 0:
        dot(d, W / 2, 500, "パリティチェック", 64, YELLOW, qa)
        bits(d, W / 2 - 60, 660, list("1010001"), qa, 96, 8)
        pq = c.p(1, 0.5) * qa if c.li >= 1 else 0
        bit(d, W / 2 + 390, 660, "1", pq, 96, hot=True)
        text(d, W / 2 + 390, 760, "パリティ", 28, YELLOW, pq, False)
        text(d, W / 2, 820, "1 の数を数える → 3個（奇数）", 38, WHITE, qa)
        if c.li >= 1:
            text(d, W / 2, 920, "1 を足して 4個（偶数）にそろえて送る", 38, GREEN, pq)
            text(d, W / 2, 1010, "届いたとき奇数なら、どこかが化けている", 34, MUTED, pq, False)
    # CRC・ハミング符号
    qb = phase(c, 2, 3)
    if qb > 0:
        r2 = c.p(2, 0.5) * qb
        dot(d, W / 2, 500, "CRC", 72, ZERO, r2)
        box(d, W / 2, 660, 880, 110, "データ ÷ 決まった数 → 余りを付けて送る", ZERO, r2, 36)
        text(d, W / 2, 770, "受け取った側も割り算して、余りが合うか確かめる", 34, MUTED, r2, False)
        if c.li >= 3:
            r3 = c.p(3, 0.5) * qb
            dot(d, W / 2, 920, "ハミング符号", 64, ONE, r3)
            bits(d, W / 2, 1060, list("1011010"), r3, 96, 8, hot={4} if int(c.since(3) * 2) % 2 else None)
            text(d, W / 2, 1190, "検査用のビットで、まちがった場所がわかる", 36, WHITE, r3)
            text(d, W / 2, 1250, "1ビットの誤りなら、見つけて直せる", 36, GREEN, r3)


def sc_info(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    dot(d, W / 2, 500, "情報量：どれだけ意外か", 60, YELLOW, q)
    for k, (p, b, col, nm) in enumerate([("1/2", 1, ZERO, "コインの表"), ("1/8", 3, ONE, "8つのうちの1つ")]):
        r = ease((c.since(0) - k * 0.4) / 0.4) if c.li >= 0 else 0
        y = 680 + k * 220
        text(d, 170, y - 30, nm, 34, MUTED, r, False, anchor="lm")
        text(d, 170, y + 30, f"確率 {p}", 44, WHITE, r, anchor="lm")
        bits(d, 600, y, ["1"] * b, r, 96)
        text(d, 790, y, f"{b} ビット", 40, col, r, anchor="lm")
    text(d, W / 2, 1150, "起こりにくいことほど、情報量が大きい", 38, WHITE, q)
    if c.li >= 1:
        r = c.p(1, 0.6)
        box(d, W / 2, 1310, 640, 130, "I ＝ −log2 P", YELLOW, r, 64, dotted=True, tcol=YELLOW)
        text(d, W / 2, 1430, "P ＝ 1/8 なら −log2(1/8) ＝ 3 ビット", 34, MUTED, r, False)


def sc_bridge(d, c, t):
    # 期待値
    qa = phase(c, 0, 1)
    if qa > 0:
        dot(d, W / 2, 500, "期待値 ＝ Σ 値 × 確率", 60, YELLOW, qa)
        for k in range(6):
            r = ease((c.since(0) - k * 0.15) / 0.3) * qa if c.li >= 0 else 0
            x = 170 + k * 148
            box(d, x, 660, 120, 120, str(k + 1), ZERO, r, 60, dotted=True, tcol=ZERO)
            text(d, x, 760, "× 1/6", 28, MUTED, r, False)
        if c.li >= 1:
            r = c.p(1, 0.6) * qa
            text(d, W / 2, 900, "(1+2+3+4+5+6) × 1/6", 44, WHITE, r)
            dot(d, W / 2, 1020, "＝ 3.5", 80, ONE, r)
            text(d, W / 2, 1130, "サイコロ1回で出る目の、平均の予想", 36, MUTED, r, False)
    # 正規分布
    qb = phase(c, 2, 3)
    if qb > 0:
        dot(d, W / 2, 500, "正規分布", 64, VIOLET, qb)
        pts = []
        for i in range(0, 801, 8):
            x = (i - 400) / 120
            pts.append((140 + i, 1000 - 380 * math.exp(-x * x / 2)))
        k = int(len(pts) * c.p(2, 1.0)) if c.li >= 2 else 0
        if k > 1:
            d.line(pts[:k], fill=fade(VIOLET, qb), width=7)
        d.line((140, 1000, 940, 1000), fill=fade(CELL_LINE, qb), width=4)
        text(d, W / 2, 1060, "平均", 32, WHITE, qb)
        if c.li >= 3:
            r = c.p(3, 0.6) * qb
            d.rectangle((420, 760, 660, 1000), fill=fade(mix(NAVY, ONE, 0.35), r))
            text(d, W / 2, 870, "約68%", 44, WHITE, r)
            text(d, W / 2, 1150, "平均 ± 標準偏差の中に、約68%が入る", 36, ONE, r)
    # オートマトン（1 の数が偶数か奇数か）
    qc = phase(c, 4, 5)
    if qc > 0:
        dot(d, W / 2, 500, "オートマトン", 64, ZERO, qc)
        seq = "1011"
        k = min(len(seq), int(max(0.0, c.since(5)) * 1.6)) if c.li >= 5 else 0
        state = sum(int(ch) for ch in seq[:k]) % 2
        for j, (nm, x) in enumerate([("偶数", W / 2 - 230), ("奇数", W / 2 + 230)]):
            on = state == j
            d.ellipse((x - 110, 780 - 110, x + 110, 780 + 110), fill=fade(mc.HOT if on else CELL, qc), outline=fade(GREEN if on else CELL_LINE, qc), width=7 if on else 4)
            text(d, x, 780, nm, 48, WHITE, qc)
        arrow(d, W / 2 - 110, 720, W / 2 + 110, 720, fade(ONE, qc), 6, 22)
        arrow(d, W / 2 + 110, 840, W / 2 - 110, 840, fade(ONE, qc), 6, 22)
        text(d, W / 2, 685, "1", 40, ONE, qc)
        text(d, W / 2, 880, "1", 40, ONE, qc)
        text(d, W / 2 - 230, 630, "0 ならそのまま", 28, ZERO, qc, False)
        text(d, W / 2 + 230, 630, "0 ならそのまま", 28, ZERO, qc, False)
        text(d, W / 2, 1000, "入力しだいで、状態が移っていく", 38, WHITE, qc)
        if c.li >= 5:
            r = c.p(5, 0.5) * qc
            text(d, 250, 1120, "入力：", 40, MUTED, r, anchor="lm")
            for j, ch in enumerate(seq):
                bit(d, 460 + j * 110, 1120, ch, r, 90, hot=(j == k - 1))
            text(d, W / 2, 1260, "1 の数が偶数か奇数かを覚えておく機械", 34, MUTED, r, False)
    # BNF
    qd = phase(c, 6, 7)
    if qd > 0:
        dot(d, W / 2, 500, "BNF：文法の書き方", 60, YELLOW, qd)
        rbox(d, 90, 600, 900, 260, fade(CELL, qd), fade(CELL_LINE, qd), 16, 4)
        text(d, 130, 680, "<ビット> ::= 0 | 1", 46, WHITE, qd, anchor="lm")
        text(d, 130, 780, "<2進数> ::= <ビット> | <2進数><ビット>", 36, WHITE, qd, anchor="lm")
        if c.li >= 7:
            r = c.p(7, 0.5) * qd
            box(d, 330, 980, 300, 110, "::=", YELLOW, r, 60, dotted=True, tcol=YELLOW)
            text(d, 330, 1080, "「〜は次のように決める」", 30, WHITE, r, False)
            box(d, 750, 980, 300, 110, "|", ONE, r, 60, dotted=True, tcol=ONE)
            text(d, 750, 1080, "「または」", 30, WHITE, r, False)
            text(d, W / 2, 1200, "<2進数> の中に <2進数> が出てくる（再帰）", 32, MUTED, r, False)


def sc_outro(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    off = c.p(2, 1.2) if c.li >= 2 else 0
    flip = int(mc.beat(t)) % 2
    alive = 1 - off
    bits(d, W / 2, 700, [str((k + flip) % 2) for k in range(8)], q * alive, 104, dance=0.6 * alive, t=t)
    if c.li >= 1:
        dot(d, W / 2, 900, "BIT BYTE DANCE", 76, VIOLET, c.p(1, 0.6) * alive)
    if c.li >= 2:
        # 画面が消えるときの横線（ブラウン管）
        h = max(4, 300 * (1 - off))
        d.rectangle((W / 2 - 420 * (1 - off * 0.8), 1150 - h / 2, W / 2 + 420 * (1 - off * 0.8), 1150 + h / 2), fill=fade(WHITE, 0.25 + 0.6 * off))
        dot(d, W / 2, 1360, "SHUTDOWN", 72, ONE, c.p(2, 0.5))


def sc_end(d, c, t):
    st = t - c.start
    q = ease((st - 0.3) / 1.0)
    bits(d, W / 2, 600, list("01000010"), q, 90)
    dot(d, W / 2, 760, "ビットバイト・ダンス", 84, ZERO, q)
    q = ease((st - 1.2) / 1.0)
    if q > 0:
        d.rounded_rectangle((180, 1120, W - 180, 1390), radius=28, fill=mix(NAVY, (8, 4, 18), q))
    text(d, W / 2, 1180, "用語の復習は", 40, MUTED, q, False)
    text(d, W / 2, 1260, "fe.yogo-drill.com", 52, YELLOW, q)
    text(d, W / 2, 1335, "ip.yogo-drill.com", 52, YELLOW, q)


PLAN = [
    (sc_intro, "0 と 1", "BIT", 1),
    (sc_bitbyte, "ビットとバイト", "BIT・BYTE", 2),
    (sc_hex, "16進数", "HEXADECIMAL", 3),
    (sc_power, "2のn乗", "2^n COMBINATIONS", 4),
    (sc_chorus, "基数とビット演算", "AND・OR・NOT・XOR・SHIFT", 5),
    (sc_logic, "論理演算", "NOT・AND・OR", 6),
    (sc_errors, "誤りの検出と訂正", "PARITY・CRC・HAMMING CODE", 7),
    (sc_info, "情報量", "INFORMATION", 8),
    (sc_chorus, "基数とビット演算", "AND・OR・NOT・XOR・SHIFT", 9),
    (sc_bridge, "確率・オートマトン・BNF", "EXPECTED VALUE・AUTOMATON・BNF", 10),
    (sc_final, "基数・演算・2の補数", "AND・OR・NOT・XOR・TWO'S COMPLEMENT", 11),
    (sc_outro, "シャットダウン", "SHUTDOWN", 12),
]
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=2.0)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・12のまとまり・締め）。Mixkit の Stock Video Free License の素材
CLIPS = [4187,    # タイトル: LED の画面のステージの DJ（リールの1枚目なので、暗くて文字が読みやすい映像）
         28900,   # イントロ: 暗闇のデジタル時計
         28900,   # ビットとバイト: 暗闇のデジタル時計（暗くて文字が読みやすい）
         3615,    # 16進数: 青い光の中のダンス
         3618,    # 2のn乗: 青い光の中の2人のダンス
         3611,    # サビ: ポッピングのダンサー
         50748,   # 論理演算: 緑の文字が流れる画面
         830,     # 誤りの検出: DJ のターンテーブル
         4187,    # 情報量: LED の画面のステージの DJ
         3614,    # サビ2: 街のダンサー
         40654,   # ブリッジ: 夜の高層ビル
         3628,    # 最後のサビ: ブレイクダンス
         42343,   # アウトロ: 夜の街の空撮
         49878]   # 締め: 夜の大きな街
# ネオンの看板（4447）・電光掲示板（4128）・たくさんの画面（4192）は、明るく細かいので図の後ろには使わない
if SCENES[-1][0] >= mc.DUR - 0.5:
    SCENES.pop()
    CLIPS.pop()

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS])
