"""曲「Strategy Riddim 〜ストラテジ・アイランド〜」の MV（縦長 1080×1920・60fps）を作る。

歌詞のまとまり（13個）ごとに場面を変え、歌詞の1行ごとに図が1つ進む（mv_common.py の仕組み）。
南の島をテーマに、SWOT・3C・4P/4C・PPM・損益分岐点・ROE・KGI/KPI・ERP など、ストラテジ系の用語の意味を図で見せる。

使うファイル（notes/曲の動画/ワン・ラブ・ストラテジ/、公開しない）
- Strategy Riddim 〜ストラテジ・アイランド〜.mp3   曲
- ストラテジ・アイランド_歌詞.txt                  歌詞（[見出し] でまとまりを分ける）
- ストラテジ・アイランド_時間.json                 各行の [開始秒, 終了秒]

    python make_mv_strategy.py            # 全部（40分ほど）
    python make_mv_strategy.py --still    # 各場面の静止画（確認用）
    python make_mv_strategy.py --at 60 90 # その秒の静止画を大きく（確認用）
"""
import math
from pathlib import Path

import numpy as np

import mv_common as mc
from mv_common import (BLUE, CELL, CELL_LINE, CREAM, GOLD, GREEN, HOT, MUTED, PURPLE, RED, SAND, SEA, W,
                       arrow, check, chip, cross, ease, fade, fchip, heart, island, label, lerp, mix,
                       off_pulse, palm, rbox, star, waves)

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "ワン・ラブ・ストラテジ"
OLD_DIR = ROOT / "notes" / "曲の動画" / "ストラテジ・アイランド（商用不可）"   # 前の音源
# ORIGINAL = True で前の音源（Strategy Riddim、4分36秒・アウトロあり。商用で使えない）、
# False で新しい音源（ワン・ラブ・ストラテジ、4分8秒・アウトロの語りなし）
ORIGINAL = False
if ORIGINAL:
    mc.configure(OLD_DIR / "Strategy Riddim 〜ストラテジ・アイランド〜.mp3", OLD_DIR / "ストラテジ・アイランド_歌詞.txt",
                 OLD_DIR / "ストラテジ・アイランド_時間.json", "Strategy Riddim 〜ストラテジ・アイランド〜")
    OUT = OLD_DIR / "ストラテジ・アイランド_MV.mp4"
else:
    mc.configure(DIR / "ワン・ラブ・ストラテジ.mp3", DIR / "ワン・ラブ・ストラテジ_歌詞.txt",
                 DIR / "ワン・ラブ・ストラテジ_時間.json", "Strategy Riddim 〜ストラテジ・アイランド〜")
    OUT = DIR / "ワン・ラブ・ストラテジ_MV.mp4"
# 背景の本物の映像（Mixkit の Stock Video Free License の素材。notes/曲の動画/背景素材/ に番号.mp4 で置く）
# REAL = False にすると、前の版（絵だけの背景）で作る
REAL = True
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"
SKY = (255, 170, 90)
LEAF = (70, 160, 100)
TRUNK = (150, 105, 60)


def sun(d, x, y, r, col, q=1.0):
    d.ellipse((x - r, y - r, x + r, y + r), fill=fade(col, q))


def boat(d, x, y, s, col, q=1.0):
    d.polygon([(x - 70 * s, y), (x + 70 * s, y), (x + 50 * s, y + 30 * s), (x - 50 * s, y + 30 * s)], fill=fade(col, q))
    d.line((x, y, x, y - 110 * s), fill=fade(CREAM, q), width=int(5 * s))
    d.polygon([(x + 4 * s, y - 105 * s), (x + 4 * s, y - 15 * s), (x + 60 * s, y - 20 * s)], fill=fade(CREAM, q))


# ---------- 場面 ----------

def sc_title(d, c, t):
    st = t
    if not REAL:
        sun(d, W / 2, 900, 230, SKY, ease(st / 2.0) * 0.85)
        waves(d, 1060, t, fade(SEA, ease(st / 2)), 12, 0.018, 8)
        waves(d, 1110, t + 1, fade(SEA, ease(st / 2) * 0.7), 10, 0.022, 6)
        island(d, W / 2, 1060, 520, fade(SAND, ease((st - 1) / 1.5)))
        palm(d, W / 2 - 60, 1050, 1.3, fade(TRUNK, ease((st - 1.5) / 1.5)), fade(LEAF, ease((st - 1.5) / 1.5)), math.sin(t * 1.4))
    q = ease((st - 2.5) / 1.5)
    label(d, W / 2, 540, "Strategy Riddim", 92, fade(GOLD, q))
    label(d, W / 2, 650, "〜ストラテジ・アイランド〜", 58, fade(CREAM, q))
    q = ease((st - 4) / 1.5)
    label(d, W / 2, 1280, "経営戦略の用語を、島のリズムで", 42, fade(MUTED, q), False)


def sc_intro(d, c, t):
    q = c.p(0, 1.2) if c.li >= 0 else 1
    if not REAL:
        sun(d, W / 2, 760, 190, SKY, 0.85)
        waves(d, 920, t, SEA, 12, 0.018, 8)
        waves(d, 970, t + 1, mix(SEA, (14, 32, 28), 0.3), 10, 0.022, 6)
        island(d, W / 2, 920, 460)
        palm(d, W / 2 - 50, 912, 1.15, TRUNK, LEAF, math.sin(t * 1.4))
    label(d, W / 2, 470, "Strategy Riddim", 76, GOLD)
    label(d, W / 2, 560, "〜ストラテジ・アイランド〜", 50, CREAM)
    words = ["戦略", "経営", "マーケティング", "会計", "法務"]
    for k, s in enumerate(words):
        r = c.p(2, 0.5) if c.li >= 2 else (c.p(1, 0.5) if k < 2 and c.li >= 1 else 0)
        r = ease((c.since(max(c.li, 1)) - k * 0.3) / 0.4) if c.li >= 1 else 0
        x = 140 + k * 200
        fchip(d, x, 1170 - 12 * off_pulse(t) * (k % 2), s, 180 if len(s) < 5 else 190, 90, (GOLD, GREEN, BLUE, RED, PURPLE)[k], r, 30 if len(s) > 4 else 38)


def sc_swot(d, c, t):
    # 島とヤシの木（1行目）
    q = c.p(0, 1.0) if c.li >= 0 else 0
    small = c.p(1, 1.0)
    iy = lerp(900, 560, small)
    island(d, W / 2, iy + 40, lerp(520, 240, small), fade(SAND, q))
    palm(d, W / 2 - 20, iy + 34, lerp(1.2, 0.55, small), fade(TRUNK, q), fade(LEAF, q), math.sin(t * 1.4))
    if small > 0:
        label(d, W / 2 + 190, iy, "自分の島", 34, fade(CREAM, small), anchor="lm")
    # SWOT の4マス
    g = small
    if g > 0:
        x0, y0, s = 150, 700, 390
        cells = [("S", "強み", "Strength", GREEN, 2), ("W", "弱み", "Weakness", RED, 2),
                 ("O", "機会", "Opportunity", BLUE, 3), ("T", "脅威", "Threat", GOLD, 3)]
        for k, (ch, jp, en, col, li) in enumerate(cells):
            cx, cy = x0 + (k % 2) * (s + 10), y0 + (k // 2) * (s * 0.62 + 10)
            on = c.p(li, 0.6) * (1 if k % 2 == 0 else ease((c.since(li) - 0.9) / 0.5)) if c.li >= li else 0
            rbox(d, cx, cy, s, s * 0.62, fade(mix(CELL, HOT, on), g), fade(mix(CELL_LINE, col, on), g), 20, 5)
            label(d, cx + 60, cy + 70, ch, 80, fade(mix(MUTED, col, on), g))
            label(d, cx + 130, cy + 60, jp, 50, fade(CREAM, g), anchor="lm")
            label(d, cx + 130, cy + 120, en, 32, fade(MUTED, g), False, "lm")
        # 内側・外側
        a = c.p(2, 0.6)
        label(d, 90, y0 + s * 0.31, "内", 40, fade(GREEN, a))
        label(d, 90, y0 + 10 + s * 0.93, "外", 40, fade(BLUE, c.p(3, 0.6)))
        if c.li >= 3:
            waves(d, 1380, t, fade(SEA, c.p(3, 0.8)), 12, 0.02, 7)
            label(d, W / 2, 1450, "外の環境は「海の向こう」", 38, fade(MUTED, c.p(3, 0.8)), False)


def sc_3c(d, c, t):
    # ビーチ
    waves(d, 1300, t, fade(SEA, c.p(0, 1.0)), 14, 0.018, 8)
    d.rectangle((0, 1320, W, 1420), fill=fade(SAND, c.p(0, 1.0) * 0.5))
    items = [("Customer", "顧客", BLUE, 1, 0), ("Competitor", "競合", RED, 1, 1), ("Company", "自社", GREEN, 2, 0)]
    pos = [(W / 2, 640), (W / 2 - 230, 1010), (W / 2 + 230, 1010)]
    for k, (en, jp, col, li, part) in enumerate(items):
        x, y = pos[k]
        r =ease((c.since(li) - part * 1.0) / 0.6) if c.li >= li else 0
        R = 190
        d.ellipse((x - R, y - R, x + R, y + R), outline=fade(col, r), width=8, fill=fade(mix(CELL, col, 0.12), r))
        label(d, x, y - 30, jp, 64, fade(CREAM, r))
        label(d, x, y + 40, en, 34, fade(col, r), False)
    q = c.p(0, 1.0)
    label(d, W / 2, 470, "3C分析", 46, fade(GOLD, q))
    if c.li >= 3:
        q = c.p(3, 0.8)
        # 3つの視点から波を読む目
        for k, (x, y) in enumerate(pos):
            arrow(d, x, y + 190, lerp(x, W / 2, 0.3), 1270, fade(GOLD, q), 5, 18)
        label(d, W / 2, 1480, "三つの視点で 市場（波）を読む", 40, fade(GOLD, q))


def sc_4p(d, c, t):
    ps = [("Product", "製品"), ("Price", "価格"), ("Place", "流通"), ("Promotion", "販売促進")]
    cs = [("Customer Value", "顧客価値"), ("Cost", "顧客コスト"), ("Convenience", "利便性"), ("Communication", "コミュニケーション")]
    cols = [GOLD, GREEN, BLUE, RED]
    for k, (en, jp) in enumerate(ps):
        r = ease((c.since(0) - k * 0.55) / 0.4) if c.li >= 0 else 0
        y = 560 + k * 200 - 14 * off_pulse(t) * r * ((k + int(mc.beat(t))) % 2)
        rbox(d, 70, y - 70, 400, 140, fade(CELL, r), fade(cols[k], r), 20, 5)
        label(d, 270, y - 22, en, 44, fade(cols[k], r))
        label(d, 270, y + 34, jp, 34, fade(CREAM, r), False)
    q = c.p(1, 0.8)
    if q > 0:
        label(d, 270, 1400, "4P = マーケティングミックス", 34, fade(GOLD, q))
    q = c.p(2, 0.6)
    if q > 0:
        label(d, 270, 1460, "売り手の目線", 38, fade(CREAM, q))
    q3 = c.p(3, 0.6)
    for k, (en, jp) in enumerate(cs):
        r = ease((c.since(3) - k * 0.45) / 0.4) if c.li >= 3 else 0
        y = 560 + k * 200
        arrow(d, 480, y, lerp(480, 600, r), y, fade(MUTED, r), 6, 20)
        rbox(d, 610, y - 70, 400, 140, fade(CELL, r), fade(cols[k], r), 20, 5)
        label(d, 810, y - 22, jp, 40 if len(jp) < 7 else 30, fade(CREAM, r))
        label(d, 810, y + 34, en, 28, fade(cols[k], r), False)
    if q3 > 0:
        label(d, 810, 1460, "買い手の目線 = 4C", 38, fade(CREAM, q3))


def sc_ppm(d, c, t):
    x0, y0, s = 150, 520, 400
    # 軸
    q = c.p(0, 0.6) if c.li >= 0 else 0
    ax = c.p(4, 0.8)
    d.line((x0 - 20, y0 - 10, x0 - 20, y0 + 2 * s + 20), fill=fade(mix(MUTED, GOLD, ax), q), width=5)
    d.line((x0 - 20, y0 + 2 * s + 20, x0 + 2 * s + 20, y0 + 2 * s + 20), fill=fade(mix(MUTED, GOLD, ax), q), width=5)
    label(d, x0 - 50, y0 + s, "市場成長率", 32, fade(mix(MUTED, GOLD, ax), q), False, "mm")
    label(d, x0 + s, y0 + 2 * s + 60, "市場シェア（左ほど高い）", 32, fade(mix(MUTED, GOLD, ax), q), False)
    quads = [("花形", "スター", GOLD, 0, 0, 0), ("問題児", "", RED, 1, 0, 2), ("金のなる木", "", GREEN, 0, 1, 1), ("負け犬", "", MUTED, 1, 1, 3)]
    for name, sub, col, gx, gy, li in quads:
        cx, cy = x0 + gx * s + s / 2, y0 + gy * s + s / 2
        r = c.p(li, 0.6) if c.li >= li else 0
        base = 0.35 if c.li >= 0 else 0
        out = c.p(3, 1.5) if name == "負け犬" and c.li >= 3 else 0
        a = max(base, r) * (1 - 0.6 * out)
        R = 170
        island(d, cx, cy + 90, 300, fade(mix(CELL, SAND, 0.6), a))
        d.rounded_rectangle((cx - R, cy - R, cx + R, cy + R), radius=30, outline=fade(col, a), width=5)
        label(d, cx, cy + 20, name, 50 if len(name) < 4 else 40, fade(CREAM, a))
        if name == "花形" and r > 0:
            star(d, cx, cy - 80, 46 + 10 * off_pulse(t), fade(GOLD, r))
        if name == "金のなる木" and r > 0:
            for k in range(3):
                yy = cy - 120 + ((t * 60 + k * 40) % 90)
                label(d, cx - 60 + k * 60, yy, "$", 40, fade(GOLD, r * 0.9))
        if name == "負け犬" and out > 0:
            arrow(d, cx, cy + 40, cx + 120 * out + 10, cy + 40, fade(RED, out), 6, 20)
            label(d, cx, cy + 110, "撤退", 34, fade(RED, out))
    # 金のなる木 → 問題児 へ投資
    if c.li >= 2:
        f = ease(c.since(2) / 1.2)
        x1, y1 = x0 + s / 2 + 80, y0 + 1.5 * s - 60
        x2, y2 = x0 + 1.5 * s - 80, y0 + s / 2 + 60
        arrow(d, x1, y1, lerp(x1, x2, f), lerp(y1, y2, f), GOLD, 8, 28)
        label(d, x0 + s, y0 + s - 4, "投資", 34, fade(GOLD, f))
    if c.li >= 5:
        q = c.p(5, 0.6)
        a = math.radians((c.since(5) / (4 * mc.BEAT)) * 360 - 135)
        bx, by = x0 + s + 260 * math.cos(a), y0 + s + 260 * math.sin(a)
        boat(d, bx, by, 0.55, (180, 110, 60), q)
        label(d, W / 2, 1460, "PPM：4つの島（事業）をめぐって、お金を配る", 36, fade(GOLD, q))


def sc_bep(d, c, t):
    # グラフ: 横 = 売上高、縦 = 金額
    gx0, gy0, gw, gh = 140, 560, 820, 700
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 470, "損益分岐点売上高 ＝ 固定費 ÷（1 − 変動費率）", 36, fade(GOLD, q))
    g = c.p(1, 1.4)
    d.line((gx0, gy0, gx0, gy0 + gh), fill=fade(MUTED, max(q, g)), width=4)
    d.line((gx0, gy0 + gh, gx0 + gw, gy0 + gh), fill=fade(MUTED, max(q, g)), width=4)
    label(d, gx0 + gw, gy0 + gh + 40, "売上高 →", 30, fade(MUTED, g), False, "rm")
    fixed, vr = 0.3, 0.45   # 固定費（高さの割合）、変動費率
    P = lambda sx, sy: (gx0 + sx * gw, gy0 + gh - sy * gh)
    if g > 0:
        e = g
        d.line(P(0, fixed) + P(e, fixed), fill=BLUE, width=5)
        d.line(P(0, fixed) + P(e, fixed + vr * e), fill=RED, width=6)
        d.line(P(0, 0) + P(e, e), fill=GREEN, width=6)
        label(d, *P(0.02, fixed - 0.05), "固定費", 30, BLUE, anchor="lm")
        if e > 0.95:
            label(d, *P(0.62, fixed + vr * 0.98 + 0.03), "総費用", 30, RED, anchor="lm")
            label(d, *P(1.0, 1.04), "売上高", 30, GREEN, anchor="rm")
    be = fixed / (1 - vr)
    if g > 0.6:
        bx, by = P(be, be)
        r = 18 + 6 * off_pulse(t)
        d.ellipse((bx - r, by - r, bx + r, by + r), fill=GOLD)
        label(d, bx + 30, by + 50, "損益分岐点", 36, GOLD, anchor="lm")
    # 利益（夕焼け）と赤字（嵐）
    if c.li >= 2:
        a = c.p(2, 0.8)
        for k in range(18):
            sx = be + (1 - be) * (k + 0.5) / 18
            d.line(P(sx, fixed + vr * sx) + P(sx, sx), fill=mix(SKY, (14, 32, 28), 1 - a * 0.85), width=int(gw / 18 * (1 - be)) - 2)
        label(d, *P(0.7, 0.93), "利益 ↘", 40, fade(CREAM, a))
    if c.li >= 3:
        a = c.p(3, 0.8)
        for k in range(12):
            sx = be * (k + 0.5) / 12
            d.line(P(sx, sx) + P(sx, fixed + vr * sx), fill=mix((90, 70, 140), (14, 32, 28), 1 - a * 0.8), width=int(gw / 12 * be) - 2)
        label(d, *P(0.2, 0.62), "赤字", 40, fade(PURPLE, a))
        for k in range(4):
            yy = 600 + ((t * 300 + k * 90) % 300)
            d.line((180 + k * 60, yy, 170 + k * 60, yy + 30), fill=fade(BLUE, a * 0.7), width=4)


def sc_ratio(d, c, t):
    # ROE
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 500, "ROE（自己資本利益率）", 44, fade(GOLD, q))
    label(d, W / 2, 610, "当期純利益", 50, fade(GREEN, q))
    d.line((W / 2 - 230, 660, W / 2 + 230, 660), fill=fade(CREAM, c.p(1, 0.6)), width=5)
    label(d, W / 2, 715, "自己資本", 50, fade(BLUE, c.p(1, 0.6)))
    if c.li >= 1:
        r = ease((c.since(1) - 1.0) / 0.6)
        label(d, W / 2, 800, "例）100 ÷ 1,000 ＝ 10%　効率チェック", 34, fade(MUTED, r), False)
        check(d, W / 2 + 330, 800, fade(GREEN, r))
    # 流動比率
    q = c.p(2, 0.6)
    label(d, W / 2, 930, "流動比率", 44, fade(GOLD, q))
    label(d, W / 2, 1030, "流動資産", 50, fade(GREEN, q))
    q3 = c.p(3, 0.6)
    d.line((W / 2 - 230, 1080, W / 2 + 230, 1080), fill=fade(CREAM, q3), width=5)
    label(d, W / 2, 1135, "流動負債", 50, fade(RED, q3))
    if c.li >= 3:
        r = ease((c.since(3) - 0.9) / 0.6)
        # 安全の目安のメーター
        cx, cy, R = W / 2, 1420, 150
        d.arc((cx - R, cy - R, cx + R, cy + R), 180, 360, fill=fade(CELL_LINE, r), width=22)
        d.arc((cx - R, cy - R, cx + R, cy + R), 270, 360, fill=fade(GREEN, r), width=22)
        a = math.radians(180 + 135 * r)
        d.line((cx, cy, cx + (R - 30) * math.cos(a), cy + (R - 30) * math.sin(a)), fill=fade(GOLD, r), width=8)
        label(d, cx, cy - 40, "150%", 34, fade(CREAM, r))
        label(d, cx + R + 20, cy - 10, "100%以上が安心", 28, fade(MUTED, r), False, "lm")


def sc_kgi(d, c, t):
    # 灯台（KGI）
    q = c.p(0, 0.8) if c.li >= 0 else 0
    lx, ly = 860, 820
    d.polygon([(lx - 40, ly), (lx + 40, ly), (lx + 26, ly - 220), (lx - 26, ly - 220)], fill=fade(CREAM, q))
    for k in range(3):
        d.rectangle((lx - 38 + k * 4, ly - 60 - k * 60, lx + 38 - k * 4, ly - 40 - k * 60), fill=fade(RED, q))
    d.ellipse((lx - 30, ly - 270, lx + 30, ly - 210), fill=fade(GOLD, q * (0.6 + 0.4 * off_pulse(t))))
    if q > 0:
        a = math.radians(t * 70)
        d.polygon([(lx, ly - 240), (lx - 300 * math.cos(a) - 30, ly - 240 - 60), (lx - 300 * math.cos(a) - 30, ly - 240 + 60)], fill=mix((14, 32, 28), GOLD, 0.18 * q))
        label(d, lx, ly + 50, "KGI：ゴール", 38, fade(GOLD, q))
    waves(d, 900, t, fade(SEA, max(q, c.p(1, 0.6))), 12, 0.02, 7)
    # 船を漕ぐ回数（KPI）
    q = c.p(1, 0.6)
    if q > 0:
        n = int(max(0.0, c.since(1)) / mc.BEAT)
        bx = 240 + min(300, n * 30)
        boat(d, bx, 870, 0.7, (180, 110, 60), q)
        label(d, 260, 990, f"KPI：漕いだ回数 {n} 回", 36, fade(GREEN, q), anchor="lm")
    # バランススコアカード
    q = c.p(2, 0.6)
    if q > 0:
        names = [("財務", GOLD), ("顧客", BLUE), ("業務プロセス", GREEN), ("学習と成長", PURPLE)]
        label(d, W / 2, 1090, "バランススコアカード", 40, fade(CREAM, q))
        for k, (n, col) in enumerate(names):
            r = ease((c.since(3) - k * 0.55) / 0.4) if c.li >= 3 else 0
            x, y = 300 + (k % 2) * 480, 1210 + (k // 2) * 150
            chip(d, x, y - 10 * off_pulse(t) * r, n, 420, 120, fade(mix(CELL, HOT, r), q), fade(mix(CELL_LINE, col, r), q), fade(CREAM, q), 40)


def sc_erp(d, c, t):
    rows = [("ERP", "島（会社の資源）をひとつに"), ("SCM", "調達から販売まで船でつなぐ"), ("CRM", "お客さまを大事に"),
            ("コアコンピタンス", "誰にも真似できない強み"), ("BPR", "業務を根本から作り直す"), ("BPR", "新しい朝へ")]
    li = max(c.li, 0)
    name, desc = rows[li]
    q = c.p(li, 0.5) if c.li >= 0 else 0
    label(d, W / 2, 500, name, 60 if len(name) < 6 else 50, fade(GOLD, q))
    label(d, W / 2, 580, desc, 40, fade(CREAM, q), False)
    sec = max(0.0, c.since(li)) if c.li >= 0 else 0
    if li == 0:
        names = ["販売", "生産", "会計", "人事"]
        f = ease((sec - 0.5) / 1.6)
        for k, n in enumerate(names):
            a = math.radians(45 + k * 90)
            R = lerp(330, 150, f)
            x, y = W / 2 + R * math.cos(a), 1000 + R * 0.8 * math.sin(a)
            island(d, x, y + 40, lerp(220, 180, f), fade(SAND, q))
            label(d, x, y, n, 40, fade(CREAM, q))
        if f > 0.9:
            d.ellipse((W / 2 - 330, 760, W / 2 + 330, 1240), outline=GOLD, width=6)
    elif li == 1:
        names = ["調達", "生産", "物流", "販売"]
        for k, n in enumerate(names):
            x = 150 + k * 260
            island(d, x, 1050, 200, SAND)
            label(d, x, 1010, n, 38)
        waves(d, 1120, t, SEA, 10, 0.02, 6)
        f = (sec / 2.2) % 1
        boat(d, lerp(150, 930, f), 1100, 0.6, (180, 110, 60))
        for k in range(3):
            arrow(d, 230 + k * 260, 1160, 330 + k * 260, 1160, fade(GOLD, ease((sec - k * 0.4) / 0.4)), 5, 18)
    elif li == 2:
        heart(d, W / 2, 1000, 9 + 1.2 * off_pulse(t), RED)
        for k in range(5):
            a = math.radians(-90 + k * 72 + sec * 30)
            label(d, W / 2 + 330 * math.cos(a), 1000 + 300 * math.sin(a), "客", 46, fade(BLUE, ease((sec - k * 0.25) / 0.4)))
    elif li == 3:
        r = 120 + 12 * off_pulse(t)
        d.polygon([(W / 2, 1000 - r), (W / 2 + r * 0.8, 1000), (W / 2, 1000 + r), (W / 2 - r * 0.8, 1000)], fill=GOLD)
        for k in range(8):
            a = math.radians(k * 45 + sec * 40)
            d.line((W / 2 + 170 * math.cos(a), 1000 + 170 * math.sin(a), W / 2 + 230 * math.cos(a), 1000 + 230 * math.sin(a)), fill=GOLD, width=6)
        for k, n in enumerate(["まね", "まね"]):
            x = 200 + k * 680
            label(d, x, 1000, n, 40, MUTED, False)
            cross(d, x, 1060, RED, 0.9)
    elif li == 4:
        f = ease(sec / 1.2)
        for k in range(6):
            x, y = 330 + (k % 3) * 210, 900 + (k // 3) * 150
            dx, dy = (k % 3 - 1) * 200 * f, (k // 3 + 1) * 120 * f
            chip(d, x + dx, y + dy, "業務", 190, 130, CELL, mix(CELL_LINE, RED, f), mix(CREAM, (14, 32, 28), f * 0.6), 34)
    else:
        f = ease(sec / 1.6)
        sun(d, W / 2, lerp(1250, 1000, f), 160, SKY, 0.8 * f + 0.2)
        waves(d, 1120, t, SEA, 10, 0.02, 7)
        for k in range(3):
            chip(d, 330 + k * 210, 1260, "新しい業務", 200, 100, CELL, GREEN, CREAM, 26)


def sc_dub(d, c, t):
    echo = c.p(3, 2.0) if c.li >= 3 else 0
    # パレート図
    q = c.p(0, 0.8) if c.li >= 0 else 0
    vals = [40, 25, 15, 10, 6, 4]
    x0, y0, bw, gh = 140, 1000, 110, 440
    cum = 0
    pts = []
    for k, v in enumerate(vals):
        r = ease((c.since(0) - k * 0.25) / 0.4) if c.li >= 0 else 0
        h = gh * v / 100 * r
        abc = "A" if k < 2 else ("B" if k < 4 else "C")
        col = {"A": RED, "B": GOLD, "C": BLUE}[abc] if c.li >= 1 else GREEN
        col = mix(GREEN, col, c.p(1, 0.6))
        d.rectangle((x0 + k * (bw + 12), y0 - h, x0 + k * (bw + 12) + bw, y0), fill=fade(col, r * (1 - echo * 0.5)))
        cum += v
        pts.append((x0 + k * (bw + 12) + bw / 2, y0 - gh * cum / 100))
    if q > 0.5:
        d.line(pts, fill=fade(CREAM, q), width=5)
        for p in pts:
            d.ellipse((p[0] - 8, p[1] - 8, p[0] + 8, p[1] + 8), fill=fade(CREAM, q))
        label(d, W / 2, 500, "パレート図：大きい順の棒と、累積の線", 38, fade(GOLD, q))
    if c.li >= 1:
        r = c.p(1, 0.6)
        for k, (n, a, b) in enumerate([("A", 0, 2), ("B", 2, 4), ("C", 4, 6)]):
            xa, xb = x0 + a * (bw + 12), x0 + b * (bw + 12) - 12
            label(d, (xa + xb) / 2, y0 + 50, n, 44, fade({"A": RED, "B": GOLD, "C": BLUE}[n], r))
        label(d, W / 2, 1110, "ABC分析：A を重点管理", 40, fade(RED, r))
    # 特性要因図（魚の骨）
    if c.li >= 2:
        r = c.p(2, 1.0)
        y = 1300
        d.line((120, y, lerp(120, 860, r), y), fill=fade(CREAM, r), width=6)
        d.polygon([(860, y - 60), (1000, y), (860, y + 60)], fill=fade(GOLD, r))
        label(d, 930, y, "結果", 28, fade((14, 32, 28), r))
        for k in range(3):
            x = 260 + k * 220
            d.line((x, y - 110, x + 70, y), fill=fade(CREAM, r), width=4)
            d.line((x, y + 110, x + 70, y), fill=fade(CREAM, r), width=4)
        label(d, 160, y - 120, "要因", 28, fade(MUTED, r), False)
    if echo > 0:
        for k in range(3):
            a = echo * (0.5 - k * 0.15)
            off = 30 * (k + 1) * echo
            label(d, W / 2 + off, 1460 + k * 26, "エコー…", 34, fade(MUTED, a), False)


def sc_law(d, c, t):
    li = max(c.li, 0)
    rows = [("著作権", "創った瞬間に生まれる（届け出はいらない）"), ("特許権", "出願して、審査を通ると得られる"),
            ("PL法（製造物責任法）", "製品の欠陥による損害は、作った会社の責任"), ("不正アクセス禁止法", "他人のIDやパスワードを使ってはいけない")]
    for k, (n, s) in enumerate(rows):
        on = k == li and c.li >= 0
        r = c.p(k, 0.5) if c.li >= k else 0
        chip(d, 150 + k * 260, 480, n.split("（")[0], 240, 80, mix(CELL, HOT, 1 if on else 0), GOLD if on else fade(CELL_LINE, max(r, 0.4)), fade(CREAM, 1 if on else max(0.4, r)), 26 if len(n.split("（")[0]) > 5 else 34)
    if c.li < 0:
        return
    n, s = rows[li]
    label(d, W / 2, 610, s, 34, GOLD)
    sec = c.since(li)
    if li == 0:
        f = ease(sec / 1.0)
        rbox(d, W / 2 - 220, 720, 440, 380, (236, 226, 204), CREAM, 10, 3)
        d.line([(W / 2 - 160 + k * 30, 900 + 60 * math.sin(k * 0.8)) for k in range(int(12 * f) + 1)], fill=BLUE, width=8)
        if f >= 1:
            r = 70 + 10 * off_pulse(t)
            d.ellipse((W / 2 + 150 - r, 700 - r, W / 2 + 150 + r, 700 + r), fill=GOLD)
            label(d, W / 2 + 150, 700, "©", 80, (14, 32, 28))
        label(d, W / 2, 1180, "描いた瞬間に、著作権", 40, CREAM)
    elif li == 1:
        steps = ["出願", "審査", "特許"]
        for k, s2 in enumerate(steps):
            r = ease((sec - k * 0.9) / 0.5)
            x = 220 + k * 320
            fchip(d, x, 900, s2, 240, 130, (GREEN if k == 2 else BLUE), r, 48, hot=k == 2)
            if k:
                arrow(d, x - 310 + 130, 900, x - 130, 900, fade(GOLD, r), 6, 22)
        label(d, W / 2, 1100, "審査を越えて、権利になる", 40, fade(CREAM, ease((sec - 1.8) / 0.5)))
    elif li == 2:
        f = ease(sec / 1.0)
        rbox(d, 200, 760, 260, 300, CELL, BLUE, 20)
        label(d, 330, 910, "製品", 44)
        d.line((300, 780, 340, 860, 310, 940, 360, 1040), fill=fade(RED, f), width=8)
        arrow(d, 480, 910, lerp(480, 640, f), 910, fade(GOLD, f), 7, 24)
        fchip(d, 790, 910, "作った会社", 280, 130, GOLD, ease((sec - 0.8) / 0.5), 38, True)
        label(d, W / 2, 1150, "欠陥の責任は、作った側に", 40, fade(CREAM, f))
    else:
        rbox(d, W / 2 - 230, 740, 460, 280, CELL, BLUE, 20)
        label(d, W / 2, 820, "ID：tanaka", 40)
        label(d, W / 2, 900, "PW：●●●●", 40)
        r = ease((sec - 0.6) / 0.4)
        if r > 0:
            cross(d, W / 2, 880, fade(RED, r), 5)
        label(d, W / 2, 1130, "他人のIDは 使うなよ", 44, fade(RED, r))


def sc_last(d, c, t):
    li = max(c.li, 0)
    q0 = c.p(0, 0.6) if c.li >= 0 else 0
    # 上: CSR とコンプライアンス
    fchip(d, 300, 520, "CSR", 360, 110, GREEN, q0, 50)
    label(d, 300, 610, "社会への責任", 30, fade(MUTED, q0), False)
    q1 = c.p(1, 0.6)
    fchip(d, 780, 520, "コンプライアンス", 400, 110, BLUE, q1, 40)
    label(d, 780, 610, "法令やルールを守る", 30, fade(MUTED, q1), False)
    # 海を渡る船
    q2 = c.p(2, 0.8)
    if q2 > 0:
        waves(d, 1000, t, SEA, 14, 0.018, 8)
        waves(d, 1050, t + 1, mix(SEA, (14, 32, 28), 0.3), 10, 0.022, 6)
        f = ease(c.since(3) / 3.0) if c.li >= 3 else 0
        boat(d, lerp(180, 760, f), 980, 0.9, (180, 110, 60), q2)
        for k in range(3):
            x = lerp(60, 140, (t * 0.8 + k * 0.3) % 1)
            arrow(d, x - 60 + lerp(0, 580, f), 860 + k * 40, x + 20 + lerp(0, 580, f), 860 + k * 40, fade(CREAM, q2 * 0.5), 4, 14)
        label(d, 200, 1130, "ストラテジの風", 32, fade(MUTED, q2), False, "lm")
    # 合格のビーチ
    q4 = c.p(4, 0.8)
    if q4 > 0:
        island(d, 880, 1010, 300, fade(SAND, q4))
        d.line((900, 1000, 900, 840), fill=fade(CREAM, q4), width=6)
        d.polygon([(904, 840), (904, 900), (1000, 870)], fill=fade(RED, q4))
        label(d, 880, 1110, "合格のビーチ", 36, fade(GOLD, q4))
    q5 = c.p(5, 0.8)
    if q5 > 0:
        heart(d, W / 2, 1330, 6 + off_pulse(t), fade(RED, q5))
        label(d, W / 2, 1460, "One Love", 56, fade(GOLD, q5))


def sc_outro(d, c, t):
    q0 = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 500, "ストラテジは、得点源", 56, fade(GOLD, q0))
    terms = ["SWOT", "3C", "4P/4C", "PPM", "損益分岐点", "ROE", "流動比率", "KGI/KPI", "BSC", "ERP", "SCM", "CRM", "BPR", "パレート図", "ABC分析", "著作権", "特許", "PL法", "CSR"]
    for k, s in enumerate(terms):
        r = ease((c.since(0) - 0.6 - k * 0.12) / 0.4) if c.li >= 0 else 0
        row, col = divmod(k, 4)
        x, y = 160 + col * 253, 650 + row * 130 - 10 * off_pulse(t) * ((k + row) % 2)
        fchip(d, x, y, s, 233, 100, (GOLD, GREEN, BLUE, RED)[k % 4], r, 32 if len(s) < 6 else 26)


def sc_end(d, c, t):
    st = t - c.start
    if not REAL:
        sun(d, W / 2, 900, 200, SKY, ease(st / 1.5) * 0.8)
        waves(d, 1060, t, SEA, 12, 0.018, 8)
        island(d, W / 2, 1060, 460, SAND)
        palm(d, W / 2 - 50, 1050, 1.15, TRUNK, LEAF, math.sin(t * 1.4))
    q = ease((st - 0.5) / 1.2)
    label(d, W / 2, 520, "Strategy Riddim", 80, fade(GOLD, q))
    label(d, W / 2, 610, "〜ストラテジ・アイランド〜", 48, fade(CREAM, q))
    q = ease((st - 1.5) / 1.2)
    label(d, W / 2, 1250, "用語の復習は", 40, fade(MUTED, q), False)
    label(d, W / 2, 1330, "ip.yogo-drill.com", 50, fade(GOLD, q))
    label(d, W / 2, 1400, "fe.yogo-drill.com", 50, fade(GOLD, q))


PLAN = [
    (sc_intro, "", "", None),
    (sc_swot, "SWOT分析", "STRENGTH・WEAKNESS・OPPORTUNITY・THREAT", 1),
    (sc_3c, "3C分析", "CUSTOMER・COMPETITOR・COMPANY", 2),
    (sc_4p, "4Pと4C", "MARKETING MIX", 3),
    (sc_ppm, "PPM", "PRODUCT PORTFOLIO MANAGEMENT", 4),
    (sc_bep, "損益分岐点", "BREAK-EVEN POINT", 5),
    (sc_ratio, "ROEと流動比率", "FINANCIAL RATIOS", 6),
    (sc_kgi, "KGI・KPI・BSC", "GOALS & BALANCED SCORECARD", 7),
    (sc_erp, "ERP・SCM・CRM・BPR", "BUSINESS SYSTEMS", 8),
    (sc_dub, "品質管理の図", "PARETO・ABC・FISHBONE", 9),
    (sc_law, "法務", "COPYRIGHT・PATENT・PL・UNAUTHORIZED ACCESS", 10),
    (sc_last, "CSRとコンプライアンス", "ONE LOVE", 11),
]
if ORIGINAL:
    PLAN.append((sc_outro, "", "", None))   # 前の音源だけ、アウトロの語りがある
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=1.5)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・イントロ・12のまとまり・アウトロ・締め）
CLIPS = [5369,    # タイトル: 南の島の上を飛ぶ
         2890,    # イントロ: ターコイズの海の小島
         4645,    # SWOT: 晴れた日のヤシの木
         5016,    # 3C: 打ち寄せる波
         41541,   # 4P/4C: 大きな街の空撮
         2888,    # PPM: 楽園の島の空撮
         44373,   # 損益分岐点: 海の夕焼けの空撮
         42342,   # ROE・流動比率: 夜の街の空撮
         44370,   # KGI・KPI: 夕暮れの海の上を飛ぶ
         4011,    # ERP・SCM: コンテナ船
         2091,    # パレート図など（語り）: 泡立つターコイズの海
         49878,   # 法務: 夜の大都市の空撮
         4680,    # CSR・ラストサビ: 晴れた海の帆船
         44496,   # アウトロ: 静かなビーチの夕日（前の音源だけ）
         44499]   # 締め: ヤシの木と夕日
if not ORIGINAL:
    CLIPS.remove(44496)

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS] if REAL else None)
