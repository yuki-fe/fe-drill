"""曲「リカーシブルキング」の MV（縦長 1080×1920・60fps）を作る。

ヒップホップの曲に、アルゴリズムと開発の用語（再帰と呼び出しスタック・バブルソート・マージソート・ヒープ・計算量・
逆ポーランド記法・外部キー・インデックス・ビュー・射影・スタブとドライバ・テストの順番・テスト駆動開発・リファクタリング・
ブルートフォース攻撃・辞書攻撃・DDoS・パスワード・ペアプログラミング・スクラム）を重ねて、歌詞の1行ごとに図が1つ進む。
背景は本物の映像（Mixkit の Free の素材）。

デザイン（ui-ux-pro-max の Dark Mode（OLED）の提案をもとにした）:
- 濃い紺の背景に、ネオンのピンク（主役）・青（補助）・王様の金色（キング・頂点）
- 意味のある色: 赤＝失敗・攻撃、緑＝成功・通った
- 見出しは Dela Gothic One（Google Fonts、OFL）。図と歌詞の文字は読みやすさのため BIZ UD ゴシックのまま

使うファイル（notes/曲の動画/リカーシブルキング/、公開しない）
- リカーシブルキング.mp3          曲
- リカーシブルキング_歌詞.txt      歌詞（[見出し] でまとまりを分ける。演奏の説明の行は入れない）
- リカーシブルキング_時間.json     各行の [開始秒, 終了秒]

    python make_mv_recursive.py --jobs 4            # 縦長を4つに分けて同時に書き出す
    python make_mv_recursive.py --youtube --jobs 4  # YouTube 用の横長
    python make_mv_recursive.py --at 30 80          # その秒の静止画を大きく（確認用）
    python make_mv_recursive.py --safe --jobs 4     # リール・ショート用の配置（_MV_リール用.mp4。make_reel_cut.py がこれを使う）
"""
import math
from pathlib import Path

import mv_common as mc
from mv_common import W, arrow, check, cross, ease, font, lerp, mix, off_pulse, rbox

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "リカーシブルキング"
HEAD = ROOT / "notes" / "曲の動画" / "フォント" / "DelaGothicOne-Regular.ttf"

# ---------- 色（mv_common の色をこの曲用に入れかえる。ほかの曲には関係しない） ----------
NAVY = (15, 23, 42)
mc.BG1, mc.BG2 = NAVY, (24, 14, 40)
WHITE = mc.CREAM = (241, 245, 249)
MUTED = mc.MUTED = (148, 163, 184)
GOLD = mc.GOLD = (245, 179, 1)        # 王様の金色（カラオケの色にもなる）
PINK = (236, 72, 153)                 # ネオンのピンク（主役）
BLUE = mc.BLUE = (59, 130, 246)       # ネオンの青
RED = mc.RED = (239, 68, 68)          # 失敗・攻撃
GREEN = mc.GREEN = (34, 197, 94)      # 成功・通った
CELL = mc.CELL = (24, 33, 58)
CELL_LINE = mc.CELL_LINE = (70, 86, 130)
mc.HOT = (80, 28, 60)
mc.HEAD_FONT = str(HEAD)

# 音声認識の結果（言葉ごとの時間）を渡して、カラオケの色を歌っている言葉に合わせて進める
mc.configure(DIR / "リカーシブルキング.mp3", DIR / "リカーシブルキング_歌詞.txt", DIR / "リカーシブルキング_時間.json",
             "リカーシブルキング", words=ROOT / "notes" / "曲の動画" / "作業用" / "リカーシブルキング_認識.json")
# 曲は -15.8 LUFS（いちばん大きい音 -3.9 dB）。YouTube の目安 -14 LUFS に合わせて +1.8 dB（いちばん大きい音は -2.1 dB）
mc.AUDIO_GAIN_DB = 1.8
OUT = DIR / "リカーシブルキング_MV.mp4"
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"


def fade(c, q):
    return mix(NAVY, c, q)


def text(d, x, y, s, size, col, q=1.0, bold=True, anchor="mm"):
    if q > 0:
        d.text((x, y), s, font=font(size, bold), fill=fade(col, q), anchor=anchor)


def neon(d, x, y, s, size, col, q=1.0):
    """見出しの字体で、光のふちどりをつけた文字（ネオン）。"""
    if q <= 0:
        return
    f = font(size, face=str(HEAD))
    d.text((x, y), s, font=f, fill=fade(col, q), anchor="mm", stroke_width=max(3, size // 18), stroke_fill=fade(mix(NAVY, col, 0.35), q))


def box(d, cx, cy, w, h, s, col, q=1.0, size=44, fill=None, dash=False, tcol=None):
    """浮かび上がる箱。q（0〜1）で下から出てくる。"""
    if q <= 0:
        return
    y = cy + 20 * (1 - q)
    x0, y0 = cx - w / 2, y - h / 2
    if dash:
        d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=16, fill=fade(fill or CELL, q * 0.6))
        dash_rect(d, x0, y0, w, h, fade(col, q))
    else:
        rbox(d, x0, y0, w, h, fade(fill or CELL, q), fade(col, q), 16, 4)
    if s:
        text(d, cx, y + 2, s, size, tcol or WHITE, q)


def dash_rect(d, x, y, w, h, col, seg=18, width=4):
    for k in range(0, int(w), seg * 2):
        d.line((x + k, y, x + min(k + seg, w), y), fill=col, width=width)
        d.line((x + k, y + h, x + min(k + seg, w), y + h), fill=col, width=width)
    for k in range(0, int(h), seg * 2):
        d.line((x, y + k, x, y + min(k + seg, h)), fill=col, width=width)
        d.line((x + w, y + k, x + w, y + min(k + seg, h)), fill=col, width=width)


def crown(d, cx, cy, s, col, q=1.0):
    """王冠（cx, cy が底のまん中）。"""
    if q <= 0:
        return
    c = fade(col, q)
    w, h = 120 * s, 80 * s
    pts = [(cx - w / 2, cy), (cx - w / 2, cy - h * 0.55), (cx - w * 0.25, cy - h * 0.2), (cx, cy - h),
           (cx + w * 0.25, cy - h * 0.2), (cx + w / 2, cy - h * 0.55), (cx + w / 2, cy)]
    d.polygon(pts, fill=c)
    for px, py in ((cx - w / 2, cy - h * 0.55), (cx, cy - h), (cx + w / 2, cy - h * 0.55)):
        r = 9 * s
        d.ellipse((px - r, py - r, px + r, py + r), fill=c)


def cells(d, cx, cy, vals, q, cw=104, hl=None, col=BLUE, size=54, done=None):
    """配列のマス。hl＝光らせる番号、done＝確定した番号（緑）。"""
    x0 = cx - cw * len(vals) / 2
    for k, v in enumerate(vals):
        c = GOLD if hl and k in hl else (GREEN if done and k in done else col)
        box(d, x0 + cw * k + cw / 2, cy, cw - 12, cw - 12, str(v), c, q, size, fill=mc.HOT if hl and k in hl else None)


def phase(c, i0, i1, length=0.5):
    """i0〜i1 行目のあいだだけ見える部分の濃さ（次の部分に移るときは消える）。"""
    if c.li < i0:
        return 0.0
    q = c.p(i0, length)
    if c.li > i1:
        q *= 1 - ease(c.since(i1 + 1) / 0.35)
    return max(0.0, q)


# ---------- 場面 ----------

def sc_title(d, c, t):
    if mc.SAFE:
        return sc_hook(d, c, t)
    q = ease((t - 0.05) / 0.6)
    crown(d, W / 2, 640, 1.6 + 0.08 * off_pulse(t), GOLD, q)
    neon(d, W / 2, 770, "リカーシブル", 118, PINK, q)
    neon(d, W / 2, 910, "キング", 150, GOLD, q)
    q2 = ease((t - 0.4) / 0.6)
    text(d, W / 2, 1060, "Recursive King", 46, BLUE, q2)
    text(d, W / 2, 1140, "再帰・ソート・DB・テストの用語で刻む IT のラップ", 36, MUTED, q2, False)


def sc_hook(d, c, t):
    """リール・ショートの最初の画面（つかみ）: 1枚目から文字を出して、問いかける。答えはすぐ歌われる。"""
    crown(d, W / 2, 560, 1.3 + 0.08 * off_pulse(t), GOLD)
    neon(d, W / 2, 690, "自分で自分を呼ぶ", 84, PINK)
    neon(d, W / 2, 820, "関数、説明できる？", 84, WHITE)
    text(d, W / 2, 960, "答えは、この歌で。", 48, BLUE)
    neon(d, W / 2, 1120, "リカーシブルキング", 64, GOLD)


def sc_intro(d, c, t):
    # 関数が自分を呼ぶ（入れ子の箱）
    q = c.p(0, 0.8) if c.li >= 0 else 0
    rbox(d, 140, 470, 800, 190, fade(CELL, q), fade(BLUE, q), 18, 4)
    text(d, 180, 520, "f(n):", 44, BLUE, q, anchor="lm")
    text(d, 220, 575, "if n = 0: return", 40, GOLD, q, anchor="lm")
    text(d, 220, 625, "f(n − 1)", 40, PINK, q, anchor="lm")
    text(d, 700, 575, "← 終了条件", 32, GOLD, q, False, anchor="lm")
    text(d, 700, 625, "← 自分を呼ぶ", 32, PINK, q, False, anchor="lm")
    if c.li >= 0:
        r = c.p(0, 1.0)
        box(d, W / 2, 760, 420, 96, "f(3) を呼び出し", PINK, r, 44)
    # 入れ子: f(3) の中に f(2)、その中に f(1)…
    names = ["f(3)", "f(2)", "f(1)", "f(0)"]
    for k, nm in enumerate(names):
        r = ease((c.since(1) - k * 0.35) / 0.4) if c.li >= 1 else 0
        if r <= 0:
            continue
        w, h = 760 - k * 150, 560 - k * 120
        x0, y0 = W / 2 - w / 2, 880 + k * 60
        col = GOLD if k == 3 else PINK
        rbox(d, x0, y0, w, h, fade(CELL, r * 0.7), fade(col, r), 22, 4)
        text(d, x0 + 30, y0 + 40, nm, 40, col, r, anchor="lm")
    if c.li >= 1:
        r = c.p(1, 1.6)
        text(d, W / 2, 1490, "再帰：関数が、自分自身を呼び出すこと", 40, WHITE, r)


def chorus(d, c, t, final=False):
    """階乗 fact(3) の呼び出しスタック。積んで、終了条件で止まって、戻ってくる。"""
    q = c.p(0, 0.7) if c.li >= 0 else 0
    # プログラム（上）
    rbox(d, 120, 440, 840, 200, fade(CELL, q), fade(BLUE, q), 18, 4)
    text(d, 150, 485, "fact(n):", 40, BLUE, q, anchor="lm")
    base_q = c.p(2, 0.6) if c.li >= 2 else 0
    if base_q > 0:
        d.rounded_rectangle((170, 512, 940, 568), radius=10, fill=fade(mc.HOT, base_q))
    text(d, 190, 540, "if n ≦ 1: return 1", 38, GOLD, q, anchor="lm")
    text(d, 190, 600, "return n × fact(n − 1)", 38, PINK, q, anchor="lm")
    # スタック（下から積む）
    frames = [("fact(3)", "3 × fact(2)", 0), ("fact(2)", "2 × fact(1)", 1), ("fact(1)", "n ≦ 1 → 1", 4)]
    ret = c.p(7, 0.9) if c.li >= 7 else 0    # 戻る動き 0〜1（次の場面まで1.3秒ほどしかないので速く）
    vals = ["= 6", "= 2", "= 1"]
    for k, (nm, body, li) in enumerate(frames):
        r = c.p(li, 0.5) if c.li >= li else 0
        # 戻るときは上から消える（fact(1) → fact(2) → fact(3) の順）
        gone = ease((ret * 3 - (2 - k)) / 1.0) if ret > 0 else 0
        if r <= 0:
            continue
        y = 1390 - k * 150
        col = GOLD if k == 2 else PINK
        x0 = W / 2 - 300
        rbox(d, x0, y - 60 + 20 * (1 - r), 600, 120, fade(CELL, r * (1 - gone * 0.6)), fade(col, r * (1 - gone * 0.7)), 16, 4)
        text(d, x0 + 30, y + 20 * (1 - r), nm, 42, col, r * (1 - gone * 0.6), anchor="lm")
        text(d, x0 + 240, y + 20 * (1 - r), body, 36, WHITE, r * (1 - gone * 0.6), False, anchor="lm")
        if gone > 0:
            text(d, x0 + 640, y, vals[k], 44, GOLD, gone, anchor="lm")
    if c.li >= 0:
        text(d, W / 2 + 330, 1470, "スタック", 30, MUTED, q, False)
    # 説明（中ほど）
    msg = None
    if c.li in (2,):
        msg = ("終了条件（ベースケース）：ここで呼び出しが止まる", GOLD)
    elif c.li == 3:
        msg = ("終了条件がないと、呼び出しが終わらない（無限ループ）", RED)
    elif c.li in (4, 5):
        msg = ("呼ぶたびに、スタックに積まれていく", PINK)
    elif c.li == 6:
        msg = ("深すぎると、スタックがあふれる（スタックオーバーフロー）", RED)
    elif c.li >= 7:
        msg = ("終了条件から順に戻って、fact(3) = 3 × 2 × 1 = 6", GOLD)
    if msg:
        r = ease(c.since(c.li) / 0.4)
        size = 36
        while font(size).getlength(msg[0]) > 960 and size > 28:
            size -= 2
        text(d, W / 2, 720, msg[0], size, msg[1], r)
    if c.li == 3:
        r = ease(c.since(3) / 0.4)
        a = t * 5
        for k in range(8):
            ang = a + k * math.pi / 4
            d.ellipse((W / 2 + 120 * math.cos(ang) - 9, 830 + 60 * math.sin(ang) - 9, W / 2 + 120 * math.cos(ang) + 9, 830 + 60 * math.sin(ang) + 9), fill=fade(RED, r))
        text(d, W / 2, 830, "∞", 70, RED, r)
    if c.li == 6:
        r = ease(c.since(6) / 0.4)
        for k in range(4):
            box(d, W / 2, 1000 - k * 40, 600 - k * 30, 34, "", RED, r * (0.9 - k * 0.2))
    if c.li >= 7 and ret > 0.6:
        r = ease((ret - 0.6) / 0.4)
        crown(d, W / 2, 920, 1.3 if final else 1.0, GOLD, r)
        neon(d, W / 2, 990, "= 6", 72 if final else 60, GOLD, r)


def sc_chorus(d, c, t):
    chorus(d, c, t)


def sc_final(d, c, t):
    chorus(d, c, t, final=True)


def sc_sort(d, c, t):
    # ① バブルソート（0〜3 行目）
    qa = phase(c, 0, 3)
    if qa > 0:
        text(d, W / 2, 470, "バブルソート：隣どうしを比べて、入れかえる", 38, PINK, qa)
        steps = [([5, 3, 8, 1], (0, 1)), ([3, 5, 8, 1], (1, 2)), ([3, 5, 8, 1], (2, 3)), ([3, 5, 1, 8], None)]
        if c.li <= 0:
            k = min(3, int(max(0.0, c.since(0)) * 1.15))
            vals, pair = steps[k]
            cells(d, W / 2, 600, vals, qa, hl=pair, done={3} if k == 3 else None)
            text(d, W / 2, 700, "1回目の比べ方（大きい数が右へ）", 32, MUTED, qa, False)
        else:
            cells(d, W / 2, 600, [1, 3, 5, 8], qa, done={0, 1, 2, 3})
            text(d, W / 2, 700, "これを何回もくり返すと、順番にそろう", 32, MUTED, qa, False)
        if c.li >= 2:
            r = c.p(2, 0.6) * qa
            box(d, W / 2, 860, 420, 110, "計算量 O(n²)", RED, r, 50)
            text(d, W / 2, 950, "比べる回数が、データの数 n の2乗に近い", 32, WHITE, r, False)
        if c.li >= 3:
            r = c.p(3, 0.8) * qa
            for k, (n, v, w) in enumerate([("n = 10", "100 回", 60), ("n = 1000", "100万回", 560)]):
                y = 1110 + k * 140
                text(d, 140, y, n, 38, WHITE, r, anchor="lm")
                d.rounded_rectangle((340, y - 30, 340 + w * ease(r), y + 30), radius=12, fill=fade(RED, r))
                text(d, 340 + w * ease(r) + 20 if w < 300 else 360, y, v, 36, WHITE, r, anchor="lm")
            text(d, W / 2, 1420, "データが増えると、時間が一気にふくらむ", 34, RED, r, False)
    # ② マージソート（4〜5 行目）
    qb = phase(c, 4, 5)
    if qb > 0:
        text(d, W / 2, 470, "マージソート：分けて、並べながらまとめる", 38, BLUE, qb)
        rows = [[[5, 3, 8, 1]], [[5, 3], [8, 1]], [[3, 5], [1, 8]], [[1, 3, 5, 8]]]
        labels = ["", "分ける", "それぞれ並べる", "まとめる（統合）"]
        for k, groups in enumerate(rows):
            r = ease((c.since(4) - k * 0.45) / 0.4) * qb
            y = 590 + k * 160
            xs = [W / 2] if len(groups) == 1 else [W / 2 - 230, W / 2 + 230]
            for x, g in zip(xs, groups):
                cells(d, x, y, g, r, cw=96, col=GREEN if k == 3 else BLUE, size=48)
            if labels[k]:
                text(d, 960, y - 70, labels[k], 28, MUTED, r, False, anchor="rm")
        if c.li >= 5:
            r = c.p(5, 0.6) * qb
            box(d, W / 2, 1270, 460, 110, "計算量 O(n log n)", GREEN, r, 48)
            text(d, W / 2, 1380, "n = 1000 なら 約1万回（O(n²) は100万回）", 34, WHITE, r, False)
    # ③ ヒープ（6〜7 行目）
    qc = phase(c, 6, 7)
    if qc > 0:
        text(d, W / 2, 470, "ヒープ：親の値が、いつも子以上", 38, GOLD, qc)
        nodes = {0: (W / 2, 700, 9), 1: (W / 2 - 230, 920, 7), 2: (W / 2 + 230, 920, 5),
                 3: (W / 2 - 340, 1140, 3), 4: (W / 2 - 120, 1140, 6), 5: (W / 2 + 120, 1140, 2), 6: (W / 2 + 340, 1140, 4)}
        for a, b in ((0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)):
            r = ease((c.since(6) - 0.2 * (b > 2)) / 0.5) * qc
            d.line((nodes[a][0], nodes[a][1], nodes[b][0], nodes[b][1]), fill=fade(CELL_LINE, r), width=5)
        for k, (x, y, v) in nodes.items():
            r = ease((c.since(6) - 0.15 * k) / 0.4) * qc
            col = GOLD if k == 0 else BLUE
            d.ellipse((x - 62, y - 62, x + 62, y + 62), fill=fade(mc.HOT if k == 0 else CELL, r), outline=fade(col, r), width=5)
            text(d, x, y + 2, str(v), 56, WHITE, r)
        r = c.p(6, 0.8) * qc
        text(d, W / 2 - 330, 810, "親 ≧ 子", 32, GOLD, r, False)
        if c.li >= 7:
            r = c.p(7, 0.6) * qc
            crown(d, W / 2, 625, 1.0 + 0.06 * off_pulse(t), GOLD, r)
            text(d, W / 2, 1310, "いちばん大きい値が、いつも頂点（根）に来る", 36, GOLD, r)
            text(d, W / 2, 1380, "根を取り出して並べるのが「ヒープソート」", 32, WHITE, r, False)


def stack_col(d, x, y, items, q, col=BLUE, size=46):
    """縦に積むスタック（items の最後がいちばん上）。"""
    rbox(d, x - 110, y - 340, 220, 360, fade(NAVY, q * 0.5), fade(CELL_LINE, q), 14, 3)
    for k, v in enumerate(items):
        box(d, x, y - 40 - k * 84, 190, 72, str(v), col if k == len(items) - 1 else CELL_LINE, q, size)
    text(d, x, y + 50, "スタック", 28, MUTED, q, False)


def sc_rpn_db(d, c, t):
    # ① 逆ポーランド記法（0〜3 行目）
    qa = phase(c, 0, 3)
    if qa > 0:
        text(d, W / 2, 470, "逆ポーランド記法：演算子を後ろに書く", 38, PINK, qa)
        box(d, 300, 600, 300, 100, "A + B", CELL_LINE, qa, 52)
        arrow(d, 470, 600, 600, 600, fade(PINK, qa), 6, 22)
        box(d, 780, 600, 300, 100, "A B +", PINK, qa, 52)
        if c.li == 1:
            r = c.p(1, 0.5) * qa
            k = min(3, int(c.since(1) * 1.8))
            items = [[], ["A"], ["A", "B"], ["A+B"]][k]
            tokens = ["A", "B", "+"]
            for j, tk in enumerate(tokens):
                box(d, 220 + j * 130, 900, 110, 100, tk, GOLD if j == k - 1 else CELL_LINE, r, 50)
            text(d, 350, 1030, "左から読んで、数は積み、", 32, WHITE, r, False)
            text(d, 350, 1080, "演算子が来たら2つ取り出して計算", 32, WHITE, r, False)
            stack_col(d, 820, 1300, items, r)
        if c.li >= 2:
            r = c.p(2, 0.5) * qa
            box(d, 300, 780, 360, 100, "(A + B) × C", CELL_LINE, r, 44)
            arrow(d, 500, 780, 600, 780, fade(PINK, r), 6, 22)
            box(d, 780, 780, 320, 100, "A B + C ×", PINK, r, 44)
            text(d, W / 2, 880, "カッコがなくても、計算の順番が決まる", 34, GOLD, r, False)
        if c.li >= 3:
            r = c.p(3, 0.5) * qa
            seq = [("3", ["3"]), ("4", ["3", "4"]), ("+", ["7"]), ("2", ["7", "2"]), ("×", ["14"])]
            k = min(4, int(c.since(3) * 2.2))
            for j, (tk, _) in enumerate(seq):
                box(d, 140 + j * 112, 1030, 96, 96, tk, GOLD if j == k else CELL_LINE, r, 48)
            text(d, 360, 1140, "3 4 + 2 ×", 40, WHITE, r)
            text(d, 360, 1200, "＝ (3 + 4) × 2", 34, MUTED, r, False)
            stack_col(d, 820, 1440, seq[k][1], r, GOLD if k == 4 else BLUE)
            if k == 4:
                neon(d, 360, 1320, "答え 14", 64, GOLD, ease((c.since(3) * 2.2 - 4) / 0.6) * r)
    # ② データベース（4〜9 行目）
    qb = phase(c, 4, 9)
    if qb <= 0:
        return
    text(d, W / 2, 470, "データベース", 40, BLUE, qb)

    def table(x, y, title, cols, rows, colw, q, hl=(), fk=None, pk=None):
        text(d, x, y - 40, title, 32, MUTED, q, False, anchor="lm")
        cx = x
        for j, (name, w) in enumerate(zip(cols, colw)):
            col = GOLD if j in hl else (PINK if j == fk else (BLUE if j == pk else CELL_LINE))
            rbox(d, cx, y, w, 64, fade(mc.HOT if j in hl else CELL, q), fade(col, q), 8, 3)
            text(d, cx + w / 2, y + 32, name, 30, WHITE, q)
            for i, row in enumerate(rows):
                rbox(d, cx, y + 64 + i * 60, w, 60, fade(NAVY, q * 0.6), fade(CELL_LINE, q * 0.7), 6, 2)
                text(d, cx + w / 2, y + 94 + i * 60, str(row[j]), 30, WHITE, q, False)
            cx += w

    emp = (["社員ID", "名前", "部署ID"], [(1, "佐藤", 10), (2, "鈴木", 20)], [170, 170, 170])
    dep = (["部署ID", "部署名"], [(10, "営業"), (20, "開発")], [170, 200])
    if c.li in (4, 5):
        r = c.p(4, 0.5) * qb
        table(70, 600, "社員表", *emp, r, hl=(), fk=2, pk=0)
        table(650, 600, "部署表", *dep, r, pk=0)
        arrow(d, 495, 790, 700, 790, fade(PINK, r), 6, 22)
        text(d, 425, 900, "外部キー", 34, PINK, r)
        text(d, 735, 900, "主キー", 34, BLUE, r)
        if c.li >= 5:
            r2 = c.p(5, 0.6) * qb
            text(d, W / 2, 1060, "外部キー：ほかの表の主キーを参照する", 38, WHITE, r2)
            text(d, W / 2, 1130, "部署表にない部署ID（例 30）は入れられない", 32, MUTED, r2, False)
            text(d, W / 2, 1180, "（参照整合性）", 32, MUTED, r2, False)
    elif c.li == 6:
        r = c.p(6, 0.5) * qb
        text(d, W / 2, 560, "インデックス：検索を速くする索引", 38, GOLD, r)
        idx = [("伊藤", "→ 5行目"), ("佐藤", "→ 1行目"), ("鈴木", "→ 2行目"), ("田中", "→ 9行目")]
        for i, (k, v) in enumerate(idx):
            box(d, 330, 700 + i * 100, 220, 80, k, GOLD if k == "佐藤" else CELL_LINE, ease((c.since(6) - i * 0.15) / 0.4) * qb, 36)
            text(d, 470, 700 + i * 100, v, 34, WHITE, ease((c.since(6) - i * 0.15) / 0.4) * qb, False, anchor="lm")
        text(d, W / 2, 1150, "並べた索引で場所がすぐわかるので、", 34, WHITE, r, False)
        text(d, W / 2, 1205, "全部の行を順番に見なくてよい", 34, WHITE, r, False)
    else:
        r = c.p(7, 0.5) * qb
        if c.li == 7:
            dash_rect(d, 160, 640, 760, 260, fade(GOLD, r))
            text(d, W / 2, 600, "ビュー（仮想の表）", 38, GOLD, r)
            for i, (a, b) in enumerate([("佐藤", "営業"), ("鈴木", "開発")]):
                text(d, 380, 720 + i * 80, a, 36, WHITE, r)
                text(d, 700, 720 + i * 80, b, 36, WHITE, r)
            text(d, W / 2, 1000, "社員表と部署表から作った、見せ方だけの表", 34, WHITE, r, False)
            text(d, W / 2, 1060, "データそのものは持たない", 34, MUTED, r, False)
        else:
            r8 = c.p(8, 0.5) * qb
            table(70, 620, "社員表（部署名つき）", ["社員ID", "名前", "部署ID", "部署名"], [(1, "佐藤", 10, "営業"), (2, "鈴木", 20, "開発")],
                  [210, 210, 210, 300], r8, hl=(1, 3))
            text(d, W / 2, 900, "射影：必要な列だけを取り出す", 38, GOLD, r8)
            if c.li >= 9:
                r9 = c.p(9, 0.5) * qb
                arrow(d, W / 2, 960, W / 2, 1040, fade(GOLD, r9), 6, 22)
                table(330, 1080, "結果", ["名前", "部署名"], [("佐藤", "営業"), ("鈴木", "開発")], [200, 220], r9)
                text(d, W / 2, 1360, "（行を取り出すのは「選択」）", 32, MUTED, r9, False)


def sc_test(d, c, t):
    # ① スタブ・ドライバ・テストの順番（0〜3 行目）
    qa = phase(c, 0, 3)
    if qa > 0:
        if c.li <= 1:
            top = c.li == 0
            text(d, W / 2, 470, "トップダウンテスト" if top else "ボトムアップテスト", 40, PINK if top else BLUE, qa)
            r = ease(c.since(c.li) / 0.5) * qa
            # 部品の木: A が上、B・C が下
            if top:
                box(d, W / 2, 640, 300, 110, "上の部品 A", GREEN, r, 40)
                for k, x in enumerate((W / 2 - 230, W / 2 + 230)):
                    arrow(d, W / 2, 700, x, 830, fade(CELL_LINE, r), 5, 18)
                    box(d, x, 900, 300, 110, "スタブ", GOLD, r, 40, dash=True)
                text(d, W / 2, 1060, "上から順にテストする", 36, WHITE, r)
                text(d, W / 2, 1120, "まだない下の部品の代わり＝スタブ", 36, GOLD, r)
            else:
                box(d, W / 2, 640, 300, 110, "ドライバ", GOLD, r, 40, dash=True)
                for k, (x, nm) in enumerate(((W / 2 - 230, "下の部品 B"), (W / 2 + 230, "下の部品 C"))):
                    arrow(d, W / 2, 700, x, 830, fade(CELL_LINE, r), 5, 18)
                    box(d, x, 900, 300, 110, nm, GREEN, r, 40)
                text(d, W / 2, 1060, "下から順にテストする", 36, WHITE, r)
                text(d, W / 2, 1120, "まだない上の部品の代わり＝ドライバ", 36, GOLD, r)
        else:
            text(d, W / 2, 470, "テストの順番", 40, PINK, qa)
            sub = ["部品ひとつずつ", "部品をつないで", "全体が要件どおりか"]
            for k, nm in enumerate(["単体テスト", "結合テスト", "システムテスト"]):
                r = ease((c.since(2) - k * 0.4) / 0.4) * qa
                y = 640 + k * 250
                box(d, W / 2, y, 560, 160, "", (BLUE, PINK, GOLD)[k], r)
                text(d, W / 2, y - 22 + 20 * (1 - r), nm, 48, WHITE, r)
                text(d, W / 2, y + 40 + 20 * (1 - r), sub[k], 30, MUTED, r, False)
                if k < 2:
                    arrow(d, W / 2, y + 90, W / 2, y + 160, fade(WHITE, r), 6, 22)
    # ② テスト駆動開発とリファクタリング（4〜7 行目）
    qb = phase(c, 4, 7)
    if qb <= 0:
        return
    text(d, W / 2, 470, "テスト駆動開発（TDD）", 40, GREEN, qb)
    cx, cy, R = W / 2, 860, 260
    stages = [("レッド", "失敗するテストを先に書く", RED, 4), ("グリーン", "テストが通るコードを書く", GREEN, 5),
              ("リファクタリング", "動きはそのまま中身を整理", BLUE, 6)]
    for k, (nm, sub, col, li) in enumerate(stages):
        ang = math.radians(-90 + k * 120)
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        on = c.li >= li
        r = (c.p(li, 0.5) if on else 0.35) * qb
        hot = c.li == li or (c.li == 7 and k == 2)
        d.ellipse((x - 130, y - 130, x + 130, y + 130), fill=fade(mc.HOT if hot else CELL, r), outline=fade(col, r), width=6 if hot else 3)
        text(d, x, y, nm, 28 if len(nm) > 4 else 42, col, r)
        nxt = math.radians(-90 + (k + 1) * 120)
        mid = (ang + nxt) / 2 if k < 2 else math.radians(-90 + 300)
        ax, ay = cx + (R + 40) * math.cos(mid), cy + (R + 40) * math.sin(mid)
        d.ellipse((ax - 8, ay - 8, ax + 8, ay + 8), fill=fade(WHITE, 0.5 * qb))
    li = max(4, min(c.li, 7))
    msg = {4: ("テストを先に書く → まだ失敗する（赤）", RED), 5: ("コードを書いて、テストを通す（緑）", GREEN),
           6: ("外から見た動きは変えずに、中身を整理", BLUE), 7: ("読みやすく、直しやすいコードに", BLUE)}[li]
    r = ease(c.since(li) / 0.4) * qb
    text(d, W / 2, 1270, msg[0], 36, msg[1], r)
    if c.li >= 7:
        r = c.p(7, 0.6) * qb
        box(d, W / 2 - 220, 1410, 380, 110, "a×1.1 b×1.1", CELL_LINE, r, 38)
        arrow(d, W / 2 - 20, 1410, W / 2 + 30, 1410, fade(BLUE, r), 6, 20)
        box(d, W / 2 + 230, 1410, 380, 110, "税込(a) 税込(b)", BLUE, r, 36)


def sc_attack(d, c, t):
    # ① 総当たり・辞書攻撃（0〜1 行目）
    qa = phase(c, 0, 1)
    if qa > 0:
        rbox(d, 240, 560, 600, 300, fade(CELL, qa), fade(CELL_LINE, qa), 20, 3)
        text(d, W / 2, 610, "ログイン", 40, WHITE, qa)
        if c.li == 0:
            n = int(c.since(0) * 24)
            text(d, W / 2, 720, f"{n:04d}", 80, RED, qa)
            text(d, W / 2, 930, "ブルートフォース攻撃（総当たり）", 40, RED, qa)
            text(d, W / 2, 1000, "0000, 0001, 0002 … ありうる組み合わせを全部ためす", 32, WHITE, qa, False)
        else:
            words = ["password", "123456", "qwerty", "dragon"]
            k = int(c.since(1) * 2.5) % len(words)
            text(d, W / 2, 720, words[k], 66, RED, qa)
            text(d, W / 2, 930, "辞書攻撃", 40, RED, qa)
            text(d, W / 2, 1000, "よく使われる単語やパスワードの一覧でためす", 32, WHITE, qa, False)
            for j, w in enumerate(words):
                box(d, 200 + j * 227, 1150, 210, 80, w, RED if j == k else CELL_LINE, qa, 30)
    # ② DDoS（2〜3 行目）
    qb = phase(c, 2, 3)
    if qb > 0:
        text(d, W / 2, 470, "DDoS 攻撃", 44, RED, qb)
        sx, sy = W / 2, 1060
        down = c.li >= 3
        for k in range(12):
            ang = math.radians(200 + k * 12)
            bx, by = sx + 420 * math.cos(ang) * 1.0, 640 + (k % 4) * 70
            bx = 140 + (k % 6) * 160
            by = 620 + (k // 6) * 120
            r = ease((c.since(2) - k * 0.05) / 0.3) * qb
            box(d, bx, by, 110, 70, "bot", RED, r, 28)
            ph = (t * 1.5 + k * 0.13) % 1
            px, py = lerp(bx, sx, ph), lerp(by + 35, sy - 90, ph)
            d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=fade(RED, r * 0.9))
        r = qb
        col = RED if down else BLUE
        box(d, sx, sy, 300, 170, "サーバー", col, r, 46)
        if down:
            r3 = c.p(3, 0.4) * qb
            cross(d, sx + 170, sy - 80, fade(RED, r3), 1.5)
            text(d, W / 2, 1250, "アクセスが多すぎて、止まってしまう", 36, RED, r3)
        text(d, W / 2, 1340, "たくさんの機械から一斉に送りつけて、サービスを止める", 32, WHITE, ease(c.since(2) / 0.5) * qb, False)
    # ③ パスワード（4〜5 行目）
    qc = phase(c, 4, 5)
    if qc > 0:
        text(d, W / 2, 470, "パスワードの守り方", 40, GREEN, qc)
        if c.li == 4:
            r = c.p(4, 0.5) * qc
            box(d, W / 2, 640, 860, 120, "数字 4けた ＝ 1万通り", RED, r, 40)
            box(d, W / 2, 820, 860, 120, "英大小・数字 12文字 ＝ 約3×10²¹通り", GREEN, ease((c.since(4) - 0.5) / 0.5) * qc, 36)
            text(d, W / 2, 980, "長く、文字の種類を多くすると、", 36, WHITE, r)
            text(d, W / 2, 1040, "総当たりでは見つけにくくなる", 36, WHITE, r)
        else:
            r = c.p(5, 0.5) * qc
            box(d, W / 2, 640, 340, 110, "同じパスワード", RED, r, 40)
            for k, nm in enumerate(["サイト A", "サイト B", "サイト C"]):
                x = W / 2 + (k - 1) * 300
                arrow(d, W / 2, 700, x, 820, fade(RED, r), 5, 18)
                box(d, x, 880, 240, 100, nm, RED, ease((c.since(5) - 0.3 - k * 0.2) / 0.4) * qc, 36)
            text(d, W / 2, 1040, "1か所でもれると、ほかのサイトも破られる", 36, RED, r)
            text(d, W / 2, 1100, "（パスワードリスト攻撃）", 32, MUTED, r, False)
    # ④ ペアプロ・スクラム（6〜7 行目）
    qd = phase(c, 6, 7)
    if qd > 0:
        if c.li == 6:
            r = c.p(6, 0.5) * qd
            text(d, W / 2, 470, "ペアプログラミング", 40, BLUE, r)
            rbox(d, W / 2 - 150, 620, 300, 200, fade(CELL, r), fade(BLUE, r), 16, 4)
            text(d, W / 2, 720, "PC 1台", 40, WHITE, r)
            box(d, W / 2 - 280, 960, 300, 110, "ドライバ", PINK, r, 40)
            box(d, W / 2 + 280, 960, 300, 110, "ナビゲータ", GOLD, r, 40)
            text(d, W / 2 - 280, 1060, "コードを書く", 32, WHITE, r, False)
            text(d, W / 2 + 280, 1060, "見て、確かめる", 32, WHITE, r, False)
            text(d, W / 2, 1200, "2人で1台。役割はときどき交代する", 34, WHITE, r)
        else:
            r = c.p(7, 0.5) * qd
            text(d, W / 2, 470, "スクラム", 40, PINK, r)
            cx, cy, R = W / 2, 900, 280
            names = ["スプリント計画", "毎日の会議", "レビュー", "ふりかえり"]
            for k, nm in enumerate(names):
                ang = math.radians(-90 + k * 90 + (t * 20 % 360) * 0)
                x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
                rr = ease((c.since(7) - k * 0.25) / 0.4) * qd
                box(d, x, y, 290, 96, nm, (BLUE, PINK, GOLD, GREEN)[k], rr, 32)
            spin = t * 1.2
            for k in range(3):
                a = spin + k * 2.1
                d.ellipse((cx + 150 * math.cos(a) - 10, cy + 150 * math.sin(a) - 10, cx + 150 * math.cos(a) + 10, cy + 150 * math.sin(a) + 10), fill=fade(PINK, r))
            text(d, cx, cy, "1〜4週間", 36, WHITE, r)
            text(d, W / 2, 1290, "短い期間（スプリント）をくり返して、", 34, WHITE, r)
            text(d, W / 2, 1345, "少しずつ作って、確かめていく", 34, WHITE, r)


def sc_outro(d, c, t):
    # スタックが全部戻って return!
    items = ["f(3)", "f(2)", "f(1)"]
    q = c.p(0, 0.5) if c.li >= 0 else 0
    pop = c.p(1, 1.2) if c.li >= 1 else 0
    for k, nm in enumerate(items):
        gone = ease((c.since(0) - 1.0 - (2 - k) * 1.3) / 0.6) if c.li >= 0 else 0   # 上から1つずつ return
        r = q * (1 - gone)
        box(d, W / 2, 1300 - k * 140, 520, 110, nm + "  return", PINK if k < 2 else GOLD, r, 40)
    if c.li >= 1:
        crown(d, W / 2, 760, 1.6 + 0.08 * off_pulse(t), GOLD, pop)
        neon(d, W / 2, 880, "return!", 130, PINK, pop)
        text(d, W / 2, 1010, "呼び出したところへ、ちゃんと帰る", 36, WHITE, pop)


def sc_end(d, c, t):
    st = t - c.start
    q = ease((st - 0.3) / 1.0)
    crown(d, W / 2, 620, 1.2, GOLD, q)
    neon(d, W / 2, 740, "リカーシブルキング", 92, PINK, q)
    q = ease((st - 1.2) / 1.0)
    # 夜景が明るいので、文字の後ろに暗い板を敷いて読みやすくする
    if q > 0:
        d.rounded_rectangle((180, 1120, W - 180, 1390), radius=28, fill=mix(NAVY, (6, 10, 22), q))
    text(d, W / 2, 1180, "用語の復習は", 40, MUTED, q, False)
    text(d, W / 2, 1260, "fe.yogo-drill.com", 52, GOLD, q)
    text(d, W / 2, 1335, "ip.yogo-drill.com", 52, GOLD, q)


PLAN = [
    (sc_intro, "再帰", "RECURSION", 1),
    (sc_chorus, "再帰とスタック", "CALL STACK・BASE CASE", 2),
    (sc_sort, "ソートと計算量", "BUBBLE・MERGE・HEAP SORT", 3),
    (sc_chorus, "再帰とスタック", "CALL STACK・BASE CASE", 4),
    (sc_rpn_db, "逆ポーランドとDB", "RPN・FOREIGN KEY・INDEX・VIEW・PROJECTION", 5),
    (sc_test, "テスト", "STUB・DRIVER・TDD・REFACTORING", 6),
    (sc_attack, "攻撃と開発の進め方", "BRUTE FORCE・DDoS・PAIR PROGRAMMING・SCRUM", 7),
    (sc_final, "再帰とスタック", "RETURN OF THE KING", 8),
    (sc_outro, "return", "RETURN", 9),
]
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=2.0)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・9つのまとまり・締め）。Mixkit の Stock Video Free License の素材
CLIPS = [4447,    # タイトル: 日本語のネオンの看板
         830,     # イントロ: DJ のターンテーブル
         50998,   # サビ: 夜のロータリー（ぐるぐる回る）
         3621,    # ソート: ダンスバトル（比べて入れかえる）
         832,     # サビ2: クラブの DJ
         50748,   # 逆ポーランド・DB: 緑の文字が流れる画面
         42039,   # テスト: 夜の車窓（プログラムの画面は大きな英字が文字と重なるのでやめた）
         41161,   # 攻撃: 夜の大通りの車の流れ（押し寄せる）
         3628,    # 最後のサビ: ブレイクダンス
         40746,   # アウトロ: 夜の街を歩く
         42041]   # 締め: 夜の街の空撮
# 曲がアウトロのすぐあとで終わるときは、締めの場面を出さない（その映像も使わない）
if SCENES[-1][0] >= mc.DUR - 0.5:
    SCENES.pop()
    CLIPS.pop()

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS])
