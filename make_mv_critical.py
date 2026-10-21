"""曲「クリティカルパス 〜完了しなかったプロジェクト〜」の MV（縦長 1080×1920・60fps）を作る。

冬の失恋の歌に、プロジェクトマネジメントの用語（ガントチャート・WBS・スラック・クリティカルパス・
クラッシング・ファストトラッキング・リスク対応・SLA・インシデント・問題管理・EVM・BCP・変更管理・監査証跡）を重ねて、
歌詞の1行ごとに図が1つ進む（mv_common.py の仕組み）。背景は本物の映像（Mixkit の Free の素材）。
コーラスと最後は、静かに雪が降る。

使うファイル（notes/曲の動画/クリティカルパス/、公開しない）
- クリティカルパス.mp3          曲
- クリティカルパス_歌詞.txt      歌詞（[見出し] でまとまりを分ける。演奏の説明の行は入れない）
- クリティカルパス_時間.json     各行の [開始秒, 終了秒]

    python make_mv_critical.py --jobs 4     # 全部を4つに分けて同時に書き出す
    python make_mv_critical.py --still      # 各場面の静止画（確認用）
    python make_mv_critical.py --at 75 160  # その秒の静止画を大きく（確認用）
"""
import math
from pathlib import Path

import numpy as np

import mv_common as mc
from mv_common import (BLUE, CELL, CELL_LINE, CREAM, GOLD, GREEN, HOT, MUTED, PURPLE, RED, W,
                       arrow, check, chip, cross, ease, fade, fchip, heart, label, lerp, mix, off_pulse, rbox)

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "クリティカルパス"
mc.configure(DIR / "クリティカルパス.mp3", DIR / "クリティカルパス_歌詞.txt", DIR / "クリティカルパス_時間.json",
             "クリティカルパス 〜完了しなかったプロジェクト〜")
OUT = DIR / "クリティカルパス_MV.mp4"
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"
SNOW = (236, 242, 250)
ICE = (150, 190, 230)
_rng = np.random.default_rng(12)
FLAKES = [(_rng.uniform(0, W), _rng.uniform(0, 1920), _rng.uniform(1.5, 4.5), _rng.uniform(40, 110), _rng.uniform(0, 6.28))
          for _ in range(90)]


def snow(d, t, q=1.0, top=0, bottom=1580):
    """静かに降る雪（大きさ・速さがばらばらの小さな粒が、ゆれながら落ちる）。"""
    if q <= 0:
        return
    for x0, y0, r, sp, ph in FLAKES:
        y = (y0 + t * sp) % (bottom - top + 40) + top - 20
        x = x0 + 18 * math.sin(t * 0.6 + ph)
        d.ellipse((x - r, y - r, x + r, y + r), fill=fade(SNOW, q * (0.45 + 0.12 * r)))


def tree(d, x, y, s, q, t):
    """駅前のツリー（三角を重ねて、明かりがまたたく）。"""
    for k in range(3):
        w, h = (120 - k * 28) * s, 90 * s
        yy = y - k * 62 * s
        d.polygon([(x - w, yy), (x + w, yy), (x, yy - h)], fill=fade((40, 110, 70), q))
    d.rectangle((x - 14 * s, y, x + 14 * s, y + 34 * s), fill=fade((110, 80, 50), q))
    for k in range(10):
        a = k * 2.4
        lx, ly = x + math.sin(a) * (16 + k * 9) * s, y - 20 * s - k * 17 * s
        on = 0.5 + 0.5 * math.sin(t * 3 + k)
        d.ellipse((lx - 6 * s, ly - 6 * s, lx + 6 * s, ly + 6 * s), fill=fade((GOLD, RED, CREAM)[k % 3], q * on))
    star_y = y - 3 * 62 * s - 60 * s
    d.ellipse((x - 12 * s, star_y - 12 * s, x + 12 * s, star_y + 12 * s), fill=fade(GOLD, q))


def bar(d, x0, x1, y, h, col, q, dashed=False):
    if x1 <= x0 or q <= 0:
        return
    if not dashed:
        d.rounded_rectangle((x0, y - h / 2, x1, y + h / 2), radius=h / 2.5, fill=fade(col, q))
    else:
        x = x0
        while x < x1:
            d.rounded_rectangle((x, y - h / 2, min(x + 26, x1), y + h / 2), radius=6, fill=fade(col, q))
            x += 40


def progress(d, y, pct, q, label_text="二人のプロジェクト"):
    x0, x1 = 120, 960
    rbox(d, x0, y - 30, x1 - x0, 60, fade(CELL, q), fade(CELL_LINE, q), 30, 3)
    d.rounded_rectangle((x0 + 6, y - 24, x0 + 6 + (x1 - x0 - 12) * pct, y + 24), radius=24, fill=fade(mix(RED, GOLD, 0.3), q))
    label(d, x0, y - 62, label_text, 34, fade(CREAM, q), anchor="lm")
    label(d, x1, y - 62, f"進捗 {int(pct * 100)}%　未完了", 34, fade(RED, q), anchor="rm")


# ---------- 場面 ----------

def sc_title(d, c, t):
    snow(d, t, ease(t / 3))
    q = ease((t - 1.0) / 2.0)
    label(d, W / 2, 760, "クリティカルパス", 104, fade(CREAM, q))
    label(d, W / 2, 880, "〜完了しなかったプロジェクト〜", 50, fade(MUTED, q), False)
    q = ease((t - 4) / 2)
    label(d, W / 2, 1100, "プロジェクトマネジメントの用語で歌う、冬の歌", 38, fade(ICE, q), False)


def sc_gantt(d, c, t):
    snow(d, t, 0.7)
    x0, x1, y0 = 230, 1000, 760
    q = c.p(0, 1.2) if c.li >= 0 else 0
    mw = (x1 - x0) / 12
    for m in range(12):
        x = x0 + m * mw
        d.line((x, y0 - 40, x, y0 + 470), fill=fade(mix(CELL_LINE, (14, 32, 28), 0.4), q), width=2)
        label(d, x + mw / 2, y0 - 70, str(m + 1), 30, fade(RED if m == 11 else MUTED, q), False)
    label(d, x0, y0 - 130, "ガントチャート（月）", 36, fade(ICE, q), anchor="lm")
    tree(d, 930, 700, 0.55, c.p(1, 1.0), t)
    tasks = [("出会う", 0, 2), ("話す", 1, 5), ("旅行", 5, 8), ("約束", 7, 11), ("ずっと一緒に", 9, 12)]
    for k, (n, a, b) in enumerate(tasks):
        y = y0 + 30 + k * 95
        r = ease((c.since(2) - k * 0.5) / 0.8) if c.li >= 2 else 0
        label(d, x0 - 20, y, n, 32, fade(CREAM, max(r, q * 0.5)), anchor="rm")
        if k < 4:
            bar(d, x0 + a * mw, x0 + lerp(a, b, r) * mw, y, 40, (BLUE, GREEN, GOLD, PURPLE)[k], r)
        else:
            # 十二月のところで、線が途切れる
            br = c.p(3, 1.6) if c.li >= 3 else 0
            end = lerp(a, 11.3, r)
            bar(d, x0 + a * mw, x0 + end * mw, y, 40, RED, r * (1 - 0.5 * br))
            if br > 0:
                bar(d, x0 + 11.4 * mw, x0 + 12 * mw, y, 40, MUTED, br * 0.5, dashed=True)
                label(d, x0 + 11.5 * mw, y + 60, "途切れたまま", 30, fade(RED, br))


def sc_wbs(d, c, t):
    q = c.p(0, 0.8) if c.li >= 0 else 0
    fchip(d, W / 2, 560, "未来", 260, 100, ICE, q, 48)
    kids = [("仕事", 200, 220), ("住む場所", 470, 220), ("二人で", 800, 360)]
    for k, (n, x, w) in enumerate(kids):
        r = ease((c.since(0) - 0.6 - k * 0.3) / 0.5) if c.li >= 0 else 0
        big = n == "二人で"
        g = c.p(1, 0.8) if big else 0
        d.line((W / 2, 610, x, 700), fill=fade(CELL_LINE, r), width=4)
        h = 110 + 60 * g
        rbox(d, x - w / 2, 700, w, h, fade(mix(CELL, HOT, g), r), fade(GOLD if big else BLUE, r), 18, 5 if big else 4)
        label(d, x, 700 + h / 2, n, 44 + 14 * g, fade(CREAM, r))
    if c.li >= 1:
        label(d, 800, 920, "いちばん大きな作業", 32, fade(GOLD, c.p(1, 0.8)))
    # 小さく分けていく
    subs = ["会う", "話す", "笑う", "支える", "待つ", "迎える"]
    for k, n in enumerate(subs):
        r = ease((c.since(2) - k * 0.35) / 0.4) if c.li >= 2 else 0
        x, y = 640 + (k % 3) * 150, 1010 + (k // 3) * 110
        if r > 0:
            d.line((800, 880, x, y - 40), fill=fade(CELL_LINE, r * 0.7), width=3)
        fchip(d, x, y, n, 135, 80, GOLD, r, 32)
    label(d, 330, 1070, "WBS：作業を小さく分ける", 34, fade(ICE, c.p(2, 0.8)) if c.li >= 2 else fade(ICE, 0), anchor="mm")
    if c.li >= 3:
        r = c.p(3, 1.2)
        arrow(d, 330, 1340, 330, lerp(1340, 1160, r), fade(GOLD, r), 7, 26)
        label(d, 330, 1390, "いつか届く…と思ってた", 34, fade(CREAM, r))


def sc_slack(d, c, t):
    q = c.p(0, 0.8) if c.li >= 0 else 0
    x0, y = 140, 700
    label(d, W / 2, 520, "スラック（余裕）= 0", 54, fade(GOLD, q))
    delay = c.p(1, 1.4) if c.li >= 1 else 0
    shift = 90 * delay
    tasks = [(0, 260, BLUE), (260, 500, GREEN), (500, 760, PURPLE)]
    for k, (a, b, col) in enumerate(tasks):
        s = 0 if k == 0 else shift
        bb = b + (shift if k == 0 else 0)
        bar(d, x0 + a + s, x0 + bb + s - 10, y + k * 110, 60, col, q)
    # 締め切りの線
    dl = x0 + 760
    d.line((dl, y - 80, dl, y + 300), fill=fade(CREAM, q), width=5)
    label(d, dl, y - 110, "締め切り", 32, fade(CREAM, q))
    if delay > 0:
        label(d, x0 + 130, y - 70, "少しの遅れ", 34, fade(RED, delay))
        d.rectangle((dl, y + 220 - 30, dl + shift, y + 220 + 30), fill=fade(RED, delay * 0.8))
        label(d, W / 2, y + 420, "→ 後ろの作業が、全部遅れる", 40, fade(RED, delay))


NODES = [(110, 820), (330, 640), (330, 1000), (600, 820), (820, 640), (980, 820)]
EDGES = [(0, 1, "出会い", True), (1, 3, "君", True), (3, 4, "約束", True), (4, 5, "冬", True),
         (0, 2, "仕事", False), (2, 3, "季節", False), (3, 5, "日常", False)]


def network(d, q, crit_q, t, warm=1.0):
    for a, b, n, crit in EDGES:
        (x1, y1), (x2, y2) = NODES[a], NODES[b]
        col = mix(CELL_LINE, RED, crit_q) if crit else CELL_LINE
        arrow(d, x1 + (x2 - x1) * 0.18, y1 + (y2 - y1) * 0.18, x2 - (x2 - x1) * 0.18, y2 - (y2 - y1) * 0.18, fade(col, q), 8 if crit else 5, 24)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 40
        if n == "君":
            r = 38 + 6 * off_pulse(t) * crit_q
            d.ellipse((mx - r, my - r + 30, mx + r, my + r + 30), fill=fade(mix(CELL, RED, 0.5 * crit_q * warm), q))
            label(d, mx, my + 30, n, 40, fade(CREAM, q))
        else:
            label(d, mx, my, n, 30, fade(MUTED if not crit else mix(MUTED, CREAM, crit_q), q), False)
    for k, (x, y) in enumerate(NODES):
        d.ellipse((x - 30, y - 30, x + 30, y + 30), fill=fade(CELL, q), outline=fade(CREAM, q), width=4)
    label(d, NODES[0][0], NODES[0][1] + 60, "開始", 28, fade(MUTED, q), False)
    label(d, NODES[5][0], NODES[5][1] + 60, "完了", 28, fade(MUTED, q), False)


def sc_chorus(d, c, t):
    snow(d, t, 0.6 + 0.4 * c.p(4, 1.5))
    q = c.p(0, 0.8) if c.li >= 0 else 0
    network(d, q, c.p(0, 1.2), t)
    label(d, W / 2, 500, "クリティカルパス：いちばん長い経路。遅れると全体が遅れる", 30, fade(ICE, q), False)
    if c.li >= 1:
        r = c.p(1, 0.8)
        x, y = NODES[5]
        label(d, x, y + 105, "+1日", 44, fade(RED, r))
        label(d, W / 2, 1075, "完了日も、1日遅れる", 38, fade(RED, r))
    if c.li >= 2:
        r = c.p(2, 0.8)
        no = c.p(3, 0.8) if c.li >= 3 else 0
        y = 1230
        # クラッシング: 人や費用を足して、作業を短く
        fchip(d, 290, y - 80, "クラッシング", 380, 80, GOLD, r, 36)
        bar(d, 130, lerp(450, 340, ease((c.since(2) - 0.4) / 1.0)), y + 10, 40, GOLD, r)
        label(d, 290, y + 70, "費用をかけて短く", 28, fade(MUTED, r), False)
        # ファストトラッキング: 作業を重ねて並行に
        fchip(d, 790, y - 80, "ファストトラッキング", 420, 80, BLUE, r, 32)
        f = ease((c.since(2) - 0.8) / 1.0)
        bar(d, 600, 760, y - 5, 28, BLUE, r)
        bar(d, lerp(770, 690, f), lerp(930, 850, f), y + 30, 28, BLUE, r)
        label(d, 790, y + 70, "作業を重ねて並行に", 28, fade(MUTED, r), False)
        if no > 0:
            cross(d, 290, y, fade(RED, no), 2.2)
            cross(d, 790, y, fade(RED, no), 2.2)
            label(d, W / 2, y + 125, "間に合わない", 44, fade(RED, no))
    if c.li >= 5:
        r = c.p(5, 1.0)
        progress(d, 1515, 0.92, r)


def sc_risk(d, c, t):
    q = c.p(0, 0.8) if c.li >= 0 else 0
    label(d, W / 2, 500, "リスク対応の4つ", 50, fade(ICE, q))
    names = [("回避", "リスクの元を断つ"), ("転嫁", "保険などで、ほかに移す"), ("軽減", "起きにくく、小さくする"), ("受容", "起きたら受け入れる")]
    for k, (n, s) in enumerate(names):
        r = ease((c.since(1) - k * 0.75) / 0.5) if c.li >= 1 else 0
        x, y = 300 + (k % 2) * 480, 680 + (k // 2) * 230
        rbox(d, x - 220, y - 90, 440, 180, fade(mix(CELL, HOT, r), max(q, r)), fade(mix(CELL_LINE, (BLUE, GREEN, GOLD, PURPLE)[k], r), max(q, r)), 20, 5)
        label(d, x, y - 30, n, 56, fade(CREAM, max(q * 0.6, r)))
        label(d, x, y + 40, s, 28, fade(MUTED, r), False)
    if c.li >= 2:
        r = c.p(2, 0.8)
        # 「君がいなくなる」リスク。受容の箱に入れようとして、はじき返される
        bx, by = 780, 910
        f = ease((c.since(3) - 0.2) / 0.8) if c.li >= 3 else 0
        back = ease((c.since(3) - 1.2) / 0.6) if c.li >= 3 else 0
        x = lerp(W / 2, bx, f * (1 - back))
        y = lerp(1260, by, f * (1 - back))
        fchip(d, x, y, "君がいなくなる", 420, 100, RED, r, 40, hot=True)
        if back > 0:
            label(d, W / 2, 1400, "受け入れられないまま", 44, fade(RED, back))


def sc_sla(d, c, t):
    q = c.p(0, 0.8) if c.li >= 0 else 0
    # SLA の紙
    rbox(d, 140, 500, 380, 420, fade((236, 230, 214), q), fade(CREAM, q), 10, 3)
    label(d, 330, 560, "SLA", 50, fade((40, 50, 60), q))
    label(d, 330, 620, "サービスレベル合意書", 26, fade((70, 80, 90), q), False)
    for k in range(4):
        d.line((180, 680 + k * 40, 480, 680 + k * 40), fill=fade((170, 170, 160), q), width=3)
    d.line((180, 860, 480, 860), fill=fade((120, 120, 110), q), width=3)
    label(d, 330, 890, "署名：（なし）", 26, fade(RED, q), False)
    if c.li >= 1:
        r = c.p(1, 0.8)
        label(d, 760, 620, "「ずっと」", 56, fade(CREAM, r))
        label(d, 760, 720, "は合意じゃなかった", 34, fade(MUTED, r), False)
        cross(d, 760, 820, fade(RED, r), 1.6)
    # インシデント → すぐ復旧
    if c.li >= 2:
        r = c.p(2, 0.8)
        fix = ease((c.since(2) - 1.0) / 0.6)
        chip(d, 330, 1080, "インシデント", 380, 100, fade(mix(CELL, (80, 30, 30), 1 - fix), r), fade(mix(RED, GREEN, fix), r), fade(CREAM, r), 38)
        if fix > 0:
            label(d, 330, 1170, "すぐ復旧（元にもどす）", 30, fade(GREEN, fix))
    # 根本原因（水の下に隠れた氷山）
    if c.li >= 3:
        r = c.p(3, 1.0)
        x, y = 780, 1110
        d.line((560, y, 1000, y), fill=fade(ICE, r), width=4)
        d.polygon([(x - 50, y), (x + 50, y), (x, y - 90)], fill=fade(SNOW, r))
        d.polygon([(x - 170, y), (x + 170, y), (x + 90, y + 220), (x - 110, y + 230)], fill=fade(mix(ICE, (14, 32, 28), 0.55), r))
        label(d, x, y + 120, "根本の原因", 36, fade(CREAM, r))
        label(d, x, y + 180, "？", 50, fade(GOLD, r))


def sc_problem(d, c, t):
    q = c.p(0, 0.8) if c.li >= 0 else 0
    label(d, W / 2, 520, "問題管理", 64, fade(GOLD, q))
    label(d, W / 2, 610, "根本の原因をつきとめて、同じことが起きないようにする", 30, fade(ICE, q), False)
    # くり返すインシデント（涙）
    cx, cy, R = W / 2, 980, 230
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=fade(CELL_LINE, q), width=6)
    n = 5
    for k in range(n):
        a = math.radians(-90 + k * 72 + t * 25)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        r = 22
        d.polygon([(x, y - r * 1.6), (x - r, y), (x + r, y)], fill=fade(ICE, q))
        d.ellipse((x - r, y - r, x + r, y + r), fill=fade(ICE, q))
    label(d, cx, cy - 20, "同じ涙を", 44, fade(CREAM, q))
    label(d, cx, cy + 40, "くり返す", 44, fade(CREAM, q))
    if c.li >= 1:
        r = c.p(1, 1.0)
        label(d, W / 2, 1320, "していれば、止められたのに", 40, fade(RED, r))


def sc_evm(d, c, t):
    gx0, gy0, gw, gh = 140, 560, 820, 560
    q = c.p(0, 0.8) if c.li >= 0 else 0
    d.line((gx0, gy0, gx0, gy0 + gh), fill=fade(MUTED, q), width=4)
    d.line((gx0, gy0 + gh, gx0 + gw, gy0 + gh), fill=fade(MUTED, q), width=4)
    label(d, gx0 + gw, gy0 + gh + 40, "時間 →", 30, fade(MUTED, q), False, "rm")
    label(d, W / 2, 490, "EVM（アーンドバリュー・マネジメント）", 38, fade(ICE, q))
    P = lambda sx, sy: (gx0 + sx * gw, gy0 + gh - sy * gh)

    def curve(fn, upto, col, width=7):
        pts = [P(k / 40, fn(k / 40)) for k in range(int(40 * upto) + 1)]
        if len(pts) > 1:
            d.line(pts, fill=col, width=width, joint="curve")

    pv = lambda x: 0.92 * x ** 0.9
    ev = lambda x: 0.22 * x ** 0.5
    ac = lambda x: 1.0 * x ** 1.2
    if c.li >= 1:
        r = c.p(1, 1.6)
        curve(pv, r, BLUE)
        label(d, *P(0.03, 0.97), "━ PV 計画", 32, fade(BLUE, r), anchor="lm")
    if c.li >= 2:
        r = c.p(2, 1.6)
        curve(ev, r, GREEN)
        label(d, *P(0.03, 0.89), "━ EV 出来高", 32, fade(GREEN, r), anchor="lm")
    if c.li >= 3:
        r = c.p(3, 1.6)
        curve(ac, r * 0.95, RED)
        label(d, *P(0.03, 0.81), "━ AC 実コスト", 32, fade(RED, r), anchor="lm")
    if c.li >= 4:
        r = c.p(4, 0.8)
        rbox(d, 160, 1210, 360, 230, fade((236, 230, 214), r), fade(CREAM, r), 10, 3)
        label(d, 340, 1260, "BCP", 44, fade((40, 50, 60), r))
        label(d, 340, 1310, "事業継続計画", 26, fade((70, 80, 90), r), False)
        for k in range(2):
            d.line((210, 1350 + k * 36, 470, 1350 + k * 36), fill=fade((170, 170, 160), r), width=3)
    if c.li >= 5:
        r = c.p(5, 1.0)
        label(d, 760, 1260, "想定外：", 36, fade(MUTED, r), False)
        label(d, 760, 1330, "君のいない朝", 48, fade(CREAM, r))
        d.ellipse((700, 1390, 820, 1510), fill=fade(mix(GOLD, (14, 32, 28), 0.5), r))


def sc_final(d, c, t):
    snow(d, t, 0.7 + 0.3 * c.p(4, 1.5))
    q = c.p(0, 0.8) if c.li >= 0 else 0
    cold = c.p(1, 1.5) if c.li >= 1 else 0
    network(d, q * (1 - 0.4 * cold), c.p(0, 1.2), t, warm=1 - cold)
    if c.li >= 1:
        label(d, W / 2, 500, "今さら気づいても、もう遅い", 38, fade(ICE, c.p(1, 0.8)))
    if c.li >= 2:
        r = c.p(2, 0.8)
        steps = ["変更要求", "承認", "実施"]
        for k, s in enumerate(steps):
            rr = ease((c.since(2) - k * 0.5) / 0.4)
            x = 220 + k * 320
            fchip(d, x, 1130, s, 240, 90, BLUE, rr * r, 36)
            if k:
                arrow(d, x - 300 + 125, 1130, x - 125, 1130, fade(MUTED, rr * r), 5, 18)
        label(d, W / 2, 1040, "変更管理", 40, fade(GOLD, r))
    if c.li >= 3:
        r = c.p(3, 1.2)
        y = 1260
        bar(d, 140, 940, y, 10, ICE, r, dashed=True)
        label(d, W / 2, y + 50, "ベースライン（あの冬の日の計画）", 32, fade(ICE, r), False)
        arrow(d, 900, y - 60, lerp(900, 200, r), y - 60, fade(GOLD, r), 6, 22)
    if c.li >= 5:
        r = c.p(5, 1.0)
        progress(d, 1460, 0.92, r)


def sc_audit(d, c, t):
    snow(d, t, 0.6)
    q = c.p(0, 0.8) if c.li >= 0 else 0
    label(d, W / 2, 500, "Merry Christmas", 72, fade(GOLD, q))
    label(d, W / 2, 590, "監査証跡（だれが・いつ・何をしたかの記録）", 30, fade(ICE, q), False)
    logs = [("12/01 09:12", "計画を作成"), ("12/08 21:40", "予定を更新"), ("12/15 19:03", "コメントを追加"),
            ("12/20 22:18", "予約を確定"), ("12/24 18:30", "待ち合わせ")]
    for k, (ts, act_) in enumerate(logs):
        r = ease((c.since(0) - 0.5 - k * 0.5) / 0.4) if c.li >= 0 else 0
        y = 700 + k * 100
        rbox(d, 100, y - 38, 880, 76, fade(CELL, r), fade(CELL_LINE, r), 12, 2)
        label(d, 130, y, ts, 32, fade(MUTED, r), False, "lm")
        label(d, 400, y, act_, 34, fade(CREAM, r), anchor="lm")
        hl = c.p(1, 1.0) if c.li >= 1 else 0
        label(d, 950, y, "君", 38, fade(mix(CREAM, GOLD, hl), r), anchor="rm")
    if c.li >= 1:
        r = c.p(1, 1.0)
        rbox(d, 860, 650, 110, 520, None, fade(GOLD, r), 16, 4)
        heart(d, W / 2, 1310, 3.5, fade(RED, r))


def sc_end(d, c, t):
    st = t - c.start
    snow(d, t, 0.8)
    q = ease((st - 0.3) / 1.5)
    label(d, W / 2, 700, "クリティカルパス", 96, fade(CREAM, q))
    label(d, W / 2, 810, "〜完了しなかったプロジェクト〜", 46, fade(MUTED, q), False)
    q = ease((st - 2.0) / 1.5)
    label(d, W / 2, 1150, "用語の復習は", 40, fade(MUTED, q), False)
    label(d, W / 2, 1230, "fe.yogo-drill.com", 50, fade(GOLD, q))
    label(d, W / 2, 1300, "ip.yogo-drill.com", 50, fade(GOLD, q))


PLAN = [
    (sc_gantt, "ガントチャート", "GANTT CHART", 1),
    (sc_wbs, "WBS", "WORK BREAKDOWN STRUCTURE", 2),
    (sc_slack, "スラック", "SLACK / FLOAT", 3),
    (sc_chorus, "クリティカルパス", "CRITICAL PATH", 4),
    (sc_risk, "リスク対応", "AVOID・TRANSFER・MITIGATE・ACCEPT", 5),
    (sc_sla, "SLAとインシデント", "SERVICE LEVEL AGREEMENT", 6),
    (sc_problem, "問題管理", "PROBLEM MANAGEMENT", 7),
    (sc_chorus, "クリティカルパス", "CRITICAL PATH", 8),
    (sc_evm, "EVMとBCP", "EARNED VALUE・BUSINESS CONTINUITY", 9),
    (sc_final, "変更管理", "CHANGE MANAGEMENT・BASELINE", 10),
    (sc_audit, "監査証跡", "AUDIT TRAIL", 11),
]
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=2.0)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・11のまとまり・締め）。Mixkit の Stock Video Free License の素材
CLIPS = [40654,   # タイトル: 夜の高層ビル街
         4240,    # ガントチャート: 夜の道の光の流れ（街灯）
         4010,    # WBS: 建設中のビルの空撮
         28901,   # スラック: 落ちていく砂時計
         50989,   # コーラス: 夜の街を走る車から
         2846,    # リスク対応: 雨の日の窓
         914,     # SLA・インシデント: オフィス
         4331,    # 問題管理: 雨の夜の道
         28893,   # コーラス2: 時計の針のアップ
         3971,    # EVM・BCP: 建設中のビルと夕日
         608,     # 変更管理: 街を走る人のシルエット
         1086,    # 監査証跡: 海の朝日
         52452]   # 締め: 夜明けの静かな道

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS])
