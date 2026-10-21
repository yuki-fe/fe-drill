"""曲「コミットしないで」の MV（縦長 1080×1920・60fps）を作る。

夏の夜の恋の歌に、コンピュータの用語（2進数・割り込み・3ウェイハンドシェイク・トランザクションのコミットとロールバック・
ACID 特性・キャッシュ・デッドロック・排他制御・二分探索・ping とタイムアウト・フルバックアップ・暗号化と秘密鍵）を重ねて、
歌詞の1行ごとに図が1つ進む（mv_common.py の仕組み）。背景は本物の映像（Mixkit の Free の素材）。

使うファイル（notes/曲の動画/コミットしないで/、公開しない）
- コミットしないで.mp3          曲
- コミットしないで_歌詞.txt      歌詞（[見出し] でまとまりを分ける。演奏の説明の行は入れない）
- コミットしないで_時間.json     各行の [開始秒, 終了秒]

    python make_mv_commit.py --jobs 4            # 縦長を4つに分けて同時に書き出す
    python make_mv_commit.py --youtube --jobs 4  # YouTube 用の横長
    python make_mv_commit.py --at 30 80          # その秒の静止画を大きく（確認用）
"""
import math
from pathlib import Path

import mv_common as mc
from mv_common import (BLUE, CELL, CELL_LINE, CREAM, GOLD, GREEN, HOT, MUTED, PURPLE, RED, W,
                       arrow, check, chip, cross, ease, fade, fchip, heart, label, lerp, mix, off_pulse, rbox)

ROOT = Path(__file__).parent
DIR = ROOT / "notes" / "曲の動画" / "コミットしないで"
mc.configure(DIR / "コミットしないで.mp3", DIR / "コミットしないで_歌詞.txt", DIR / "コミットしないで_時間.json",
             "コミットしないで")
OUT = DIR / "コミットしないで_MV.mp4"
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"
PINK = (240, 140, 170)
NIGHT = (150, 170, 230)


def bit(d, x, y, v, q, size=64, col=None):
    rbox(d, x - 40, y - 48, 80, 96, fade(CELL, q), fade(col or CELL_LINE, q), 14, 3)
    label(d, x, y + 2, v, size, fade(col or CREAM, q))


def heart_outline(d, x, y, s, col, width=6):
    pts = []
    for k in range(80):
        a = k / 80 * 2 * math.pi
        hx = 16 * math.sin(a) ** 3
        hy = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((x + hx * s, y - hy * s))
    d.line(pts + [pts[0]], fill=col, width=width, joint="curve")


# ---------- 場面 ----------

def sc_title(d, c, t):
    q = ease((t - 0.8) / 2.0)
    label(d, W / 2, 760, "コミットしないで", 104, fade(CREAM, q))
    q2 = ease((t - 2.5) / 2.0)
    label(d, W / 2, 880, "コンピュータの用語で歌う、夏の恋の歌", 40, fade(NIGHT, q2), False)
    for k in range(8):
        v = "1" if (k * 7 + int(t * 2)) % 3 == 0 else "0"
        bit(d, 230 + k * 88, 1100, v, ease((t - 3.5 - k * 0.15) / 0.5), 44)


def sc_binary(d, c, t):
    # 胸の中で 0 と 1 が揺れる（拍ごとに入れかわる）
    q = c.p(1, 0.8) if c.li >= 1 else 0
    flip = int(mc.beat(t)) % 2
    heart_outline(d, W / 2, 740, 12 + 0.6 * off_pulse(t), fade(PINK, max(q, c.p(0, 1.0) * 0.4)))
    if q > 0:
        label(d, W / 2, 720, "1" if flip else "0", 150, fade(GOLD if flip else NIGHT, q))
    q0 = c.p(0, 1.0) if c.li >= 0 else 0
    for k in range(8):
        v = "1" if (k * 5 + int(mc.beat(t))) % 3 == 0 else "0"
        bit(d, 230 + k * 88, 500, v, q0 * 0.8, 40)
    if c.li >= 2:
        r = c.p(2, 0.6)
        fchip(d, 300, 1060, "好き ＝ 1", 360, 110, GOLD, r, 46, hot=flip == 1)
        fchip(d, 780, 1060, "好きじゃない ＝ 0", 400, 110, NIGHT, r, 40, hot=flip == 0)
    if c.li >= 3:
        r = c.p(3, 0.8)
        label(d, W / 2, 1250, "2進数：0 と 1 だけで数を表す", 40, fade(CREAM, r))
        label(d, W / 2, 1330, "10進数の 5 ＝ 2進数の 101", 36, fade(MUTED, r), False)


def sc_interrupt(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 490, "割り込み：いまの処理を止めて、急ぎの処理を先にする", 30, fade(NIGHT, q), False)
    # 処理の帯（時間 →）
    x0, x1, y = 100, 980, 760
    d.line((x0, y + 60, x1, y + 60), fill=fade(MUTED, q), width=3)
    label(d, x1, y + 95, "時間 →", 28, fade(MUTED, q), False, "rm")
    tasks = [("宿題", 100, 380, BLUE), ("あなた", 380, 640, PINK), ("宿題", 640, 980, BLUE)]
    prog = ease(c.since(0) / 3.0) if c.li >= 0 else 0
    head = lerp(x0, x1, prog)
    for n, a, b, col in tasks:
        if a >= head:
            continue
        bb = min(b, head)
        is_you = n == "あなた"
        d.rounded_rectangle((a, y - 40, bb, y + 40), radius=12, fill=fade(mix(CELL, col, 0.5), q), outline=fade(col, q), width=3)
        if bb - a > 120:
            label(d, (a + bb) / 2, y, n, 38, fade(CREAM, q))
    if prog > 0.3:
        arrow(d, 380, 560, 380, 712, fade(RED, q), 8, 28)
        label(d, 380, 535, "あなたの声", 34, fade(PINK, q))
    if c.li >= 1:
        r = c.p(1, 0.8)
        label(d, 240, 870, "止まる…", 34, fade(RED, r))
    # 優先度
    if c.li >= 2:
        r = c.p(2, 0.6)
        label(d, 200, 990, "優先度", 36, fade(GOLD, r), anchor="lm")
        names = ["宿題", "ごはん", "ねむる", "あなた"] if c.li < 3 else ["あなた"] * 4
        for k, n in enumerate(names):
            rr = ease((c.since(max(2, c.li)) - k * 0.25) / 0.4)
            col = PINK if n == "あなた" else BLUE
            fchip(d, 300 + k * 160, 1110, n, 150, 90, col, rr * r, 30, hot=n == "あなた")
        label(d, 220, 1185, "高", 30, fade(MUTED, r), False)
        label(d, 860, 1185, "低", 30, fade(MUTED, r), False)
        if c.li >= 3:
            label(d, W / 2, 1300, "あなたのことばかり", 44, fade(PINK, c.p(3, 0.8)))


def sc_handshake(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 490, "TCP の 3ウェイハンドシェイク：3回のやりとりで つながる", 30, fade(NIGHT, q), False)
    lx, rx = 200, 880
    for x, n, col in ((lx, "あたし", PINK), (rx, "あなた", BLUE)):
        fchip(d, x, 600, n, 220, 100, col, q, 42)
        d.line((x, 660, x, 1300), fill=fade(CELL_LINE, q), width=4)
    msgs = [("① SYN", lx, rx, 760, 0, 0.0), ("② SYN＋ACK", rx, lx, 900, 0, 1.6), ("③ ACK", lx, rx, 1040, 1, 0.0)]
    for n, a, b, y, li, delay in msgs:
        if c.li < li:
            continue
        f = ease((c.since(li) - delay) / 1.0)
        if f <= 0:
            continue
        arrow(d, a, y, lerp(a, b, f), y + 60 * f, fade(GOLD, f), 6, 22)
        label(d, (a + b) / 2, y - 10, n, 34, fade(CREAM, f))
    if c.li >= 1:
        f = ease((c.since(1) - 1.4) / 0.8)
        if f > 0:
            label(d, W / 2, 1190, "つながった（はず）", 46, fade(GOLD, f))
            fade_out = ease((c.since(1) - 3.0) / 1.5)
            d.line((lx + 110, 1260, rx - 110, 1260), fill=fade(PINK, f * (1 - 0.7 * fade_out)), width=6)


def tx_scene(d, c, t, final=False):
    """トランザクション: コミットしないで終わる → ロールバック（最後のサビでは、もうできない）。"""
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 490, "トランザクション：まとめて確定（コミット）か、元にもどす（ロールバック）", 26, fade(NIGHT, q), False)
    steps = ["出会う", "話す", "約束"]
    for k, s in enumerate(steps):
        fchip(d, 230 + k * 220, 640, s, 190, 90, PINK, q, 36)
    rbox(d, 100, 570, 880, 150, None, fade(CELL_LINE, q), 20, 3)
    label(d, 120, 555, "BEGIN", 28, fade(MUTED, q), False, "lm")
    # COMMIT（されなかった）
    fchip(d, 900, 640, "COMMIT", 150, 90, GOLD, q * 0.6, 26)
    if c.li >= 0:
        cross(d, 900, 640, fade(RED, c.p(0, 0.8)), 1.8)
    if c.li >= 1:
        r = c.p(1, 1.2)
        if not final:
            # ロールバックで「あの夏の夜」まで戻る
            arrow(d, 900, 760, lerp(900, 180, r), 760, fade(GOLD, r), 8, 28)
            label(d, W / 2, 805, "ROLLBACK", 36, fade(GOLD, r))
        else:
            arrow(d, 900, 760, lerp(900, 560, r), 760, fade(MUTED, r), 6, 22)
            cross(d, 560, 760, fade(RED, r), 1.6)
            label(d, W / 2, 815, "ロールバックは もうできない", 36, fade(RED, r))
    if not final and c.li >= 2:
        r = c.p(2, 1.0)
        rbox(d, 110, 860, 300, 80, fade(mix(CELL, HOT, 1), r), fade(GOLD, r), 16, 4)
        label(d, 260, 900, "あの夏の夜", 34, fade(CREAM, r))
    if not final and c.li >= 3:
        acid = [("A", "原子性", "全部か、何もなしか"), ("C", "一貫性", "矛盾しない"), ("I", "独立性", "ほかに じゃまされない"), ("D", "永続性", "確定したら消えない")]
        broken = c.p(4, 1.2) if c.li >= 4 else 0
        for k, (ch, n, s) in enumerate(acid):
            r = ease((c.since(3) - k * 0.4) / 0.5)
            x, y = 290 + (k % 2) * 500, 1040 + (k // 2) * 150
            a = r * (1 - 0.65 * broken)
            rbox(d, x - 230, y - 60, 460, 120, fade(CELL, a), fade(PURPLE, a), 16, 3)
            label(d, x - 170, y, ch, 64, fade(PURPLE, a))
            label(d, x + 30, y - 22, n, 36, fade(CREAM, a))
            label(d, x + 30, y + 26, s, 24, fade(MUTED, a), False)
        label(d, W / 2, 965, "ACID 特性（トランザクションの4つの性質）", 30, fade(PURPLE, c.p(3, 0.6)), False)
        if broken > 0:
            label(d, W / 2, 1360, "確かなものなんて、なかった", 40, fade(MUTED, broken), False)
    if final:
        # 暗号化した気持ちと、あたしだけが持つ秘密鍵
        if c.li >= 2:
            r = c.p(2, 1.0)
            locked = ease((c.since(2) - 0.6) / 0.8)
            heart(d, 300, 1050, 5.5, fade(mix(PINK, (60, 50, 70), locked), r))
            if locked > 0:
                rbox(d, 250, 1035, 100, 80, fade(RED, locked), None, 12, 0)
                d.arc((265, 985, 335, 1055), 180, 360, fill=fade(RED, locked), width=10)
            arrow(d, 400, 1050, 560, 1050, fade(MUTED, r), 5, 18)
            label(d, 760, 1050, "8f3a 0c91 …", 44, fade(GOLD, locked))
            label(d, W / 2, 940, "暗号化：鍵がないと読めない形にする", 30, fade(NIGHT, r), False)
        if c.li >= 3:
            r = c.p(3, 0.8)
            mc.label(d, 300, 1230, "秘密鍵", 36, fade(RED, r))
            d.ellipse((230, 1270, 280, 1320), outline=fade(RED, r), width=9)
            d.rectangle((280, 1290, 380, 1300), fill=fade(RED, r))
            label(d, 650, 1290, "あたしだけが持ってる", 38, fade(CREAM, r))
        if c.li >= 4:
            r = c.p(4, 0.8)
            label(d, W / 2, 1420, "誰にも 復号できない", 40, fade(MUTED, r), False)
    if c.li >= 5:
        r = c.p(5, 1.0)
        heart(d, W / 2, 1470 if final else 1440, 4 + 0.6 * off_pulse(t), fade(PINK, r))


def sc_chorus(d, c, t):
    tx_scene(d, c, t, final=False)


def sc_final(d, c, t):
    tx_scene(d, c, t, final=True)


def sc_cache(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 490, "キャッシュ：よく使うデータを、近くの速い記憶に置いておく", 28, fade(NIGHT, q), False)
    fchip(d, 180, 760, "あたし", 230, 110, PINK, q, 40)
    rbox(d, 380, 650, 300, 220, fade(CELL, q), fade(GREEN, q), 20, 4)
    label(d, 530, 625, "キャッシュ", 34, fade(GREEN, q))
    rbox(d, 760, 650, 260, 220, fade(CELL, q), fade(BLUE, q), 20, 4)
    label(d, 890, 625, "主記憶", 34, fade(BLUE, q))
    glow = 0.7 + 0.3 * off_pulse(t)
    fchip(d, 530, 760, "あなたの笑顔", 250, 100, GOLD, q, 34, hot=True)
    if c.li >= 1:
        r = c.p(1, 0.6)
        n = 1 + int(max(0.0, c.since(1)) / mc.BEAT)
        arrow(d, 410, 790, 300, 790, fade(GOLD, r), 6, 22)
        label(d, 530, 930, f"ヒット × {min(n, 99)}", 44, fade(GOLD, r))
    if c.li >= 2:
        r = c.p(2, 0.8)
        label(d, 890, 760, "（もう いない）", 32, fade(MUTED, r), False)
    if c.li >= 3:
        r = c.p(3, 0.8)
        d.rounded_rectangle((395, 700, 665, 820), radius=20, outline=fade(GOLD, r * glow), width=6)
        label(d, W / 2, 1100, "いちばん近くで 光ってる", 44, fade(PINK, r))


def sc_deadlock(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 490, "デッドロック：おたがいが相手を待って、どちらも進めない", 28, fade(NIGHT, q), False)
    fchip(d, 230, 640, "あたし", 240, 100, PINK, q, 40)
    fchip(d, 850, 640, "あなた", 240, 100, BLUE, q, 40)
    gone = c.p(3, 1.2) if c.li >= 3 else 0
    fchip(d, 230, 1000, "時間", 240, 100, GREEN, q, 40)
    fchip(d, 850, 1000, "気持ち", 240, 100, GREEN, q, 40)
    if q > 0:
        arrow(d, 230, 948, 230, 696, fade(GREEN, q), 6, 22)
        arrow(d, 850, 948, 850, 696, fade(GREEN, q * (1 - gone)), 6, 22)
    if c.li >= 1:
        r = c.p(1, 0.8)
        arrow(d, 350, 680, 730, 960, fade(GOLD, r), 6, 22)
        arrow(d, 730, 680, 350, 960, fade(GOLD, r * (1 - gone)), 6, 22)
        label(d, W / 2, 780, "待つ", 34, fade(GOLD, r))
    if c.li >= 2:
        r = c.p(2, 0.8)
        rbox(d, 90, 560, 900, 520, None, fade(RED, r * (1 - gone)), 20, 4)
        label(d, W / 2, 1150, "動けない", 44, fade(RED, r * (1 - gone)))
    if gone > 0:
        label(d, W / 2, 1250, "先に手を離したのは あなた", 42, fade(CREAM, gone))


def sc_mutex(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    label(d, W / 2, 490, "排他制御：一度に一人だけが使えるように、鍵をかける", 28, fade(NIGHT, q), False)
    rbox(d, 330, 640, 420, 420, fade(CELL, q), fade(PINK, q), 30, 5)
    label(d, 540, 700, "あなたのこころ", 38, fade(CREAM, q))
    # 鍵
    d.arc((490, 760, 590, 860), 180, 360, fill=fade(GOLD, q), width=12)
    rbox(d, 470, 810, 140, 110, fade(GOLD, q), None, 14, 0)
    for k, n in enumerate(["だれか", "だれか"]):
        y = 760 + k * 160
        fchip(d, 170, y, n, 190, 80, MUTED, q * 0.8, 30)
        cross(d, 280, y, fade(RED, q * 0.8), 0.8)
    if c.li >= 1:
        r = c.p(1, 1.0)
        fchip(d, 540, 990, "あたしだけ", 280, 90, PINK, r, 36, hot=True)
        label(d, W / 2, 1180, "…だったら よかったのに", 38, fade(MUTED, r), False)


def sc_bridge(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    li = max(c.li, 0)
    if li <= 1:
        label(d, W / 2, 490, "二分探索：並んだデータの真ん中を見て、半分ずつ しぼる", 28, fade(NIGHT, q), False)
        days = ["4月", "5月", "6月", "7月", "8月", "9月", "10月"]
        lo, hi = 0, 6
        stepn = int(max(0.0, c.since(0)) / 1.4) if c.li >= 0 else 0
        for _ in range(min(stepn, 2)):
            mid = (lo + hi) // 2
            lo = mid + 1
        mid = (lo + hi) // 2
        for k, s in enumerate(days):
            on = lo <= k <= hi
            col = GOLD if k == mid else (CELL_LINE if on else (40, 50, 50))
            fchip(d, 130 + k * 137, 760, s, 120, 100, col, q * (1 if on else 0.4), 30, hot=k == mid)
        label(d, 130 + mid * 137, 860, "↑ 真ん中", 30, fade(GOLD, q))
        if c.li >= 1:
            r = c.p(1, 0.8)
            cross(d, 130 + mid * 137, 760, fade(RED, r), 1.6)
            label(d, W / 2, 1000, "あなたは いない", 44, fade(PINK, r))
    elif li <= 3:
        label(d, W / 2, 490, "ping：相手に届くか、返事が来るかを確かめる", 28, fade(NIGHT, q), False)
        rbox(d, 100, 600, 880, 500, fade((10, 16, 18), 1), fade(CELL_LINE, 1), 14, 3)
        lines = ["> ping あなた"] + ["要求がタイムアウトしました。"] * 4
        n = int(max(0.0, c.since(2)) / 0.9) + 1
        for k, s in enumerate(lines[:n]):
            label(d, 140, 660 + k * 80, s, 34, GREEN if k == 0 else RED, anchor="lm")
        if c.li >= 3:
            r = c.p(3, 1.5)
            d.rectangle((100, 1180, 980, 1200), fill=fade(mix(GOLD, (230, 120, 80), 0.5), r))
            label(d, W / 2, 1260, "タイムアウトの 夜が明ける", 42, fade(GOLD, r))
    else:
        label(d, W / 2, 490, "フルバックアップ：全部のデータを、まるごと別に保存する", 28, fade(NIGHT, q), False)
        r = c.p(4, 0.8)
        rbox(d, 380, 640, 320, 380, fade(CELL, r), fade(BLUE, r), 24, 4)
        label(d, 540, 700, "バックアップ", 34, fade(CREAM, r))
        label(d, 540, 850, "空っぽ", 50, fade(MUTED, r), False)
        cross(d, 540, 940, fade(RED, r), 1.4)
        if c.li >= 5:
            r = c.p(5, 1.0)
            for k in range(6):
                x = 170 + k * 148
                rbox(d, x - 60, 1120, 120, 150, fade((236, 230, 214), r * 0.7), fade(CREAM, r * 0.7), 8, 3)
                heart(d, x, 1195, 1.6, fade(PINK, r * 0.7))
            label(d, W / 2, 1340, "あなたと笑った 全部の日", 40, fade(CREAM, r))


def sc_outro(d, c, t):
    q = c.p(0, 1.0) if c.li >= 0 else 0
    flip = int(mc.beat(t)) % 2
    heart_outline(d, W / 2, 820, 13 + 0.6 * off_pulse(t), fade(PINK, q))
    label(d, W / 2 - 120, 800, "0", 140, fade(NIGHT, q * (1.0 if not flip else 0.35)))
    label(d, W / 2 + 120, 800, "1", 140, fade(GOLD, q * (1.0 if flip else 0.35)))
    if c.li >= 1:
        label(d, W / 2, 1150, "あたしは今も 揺れてる", 44, fade(CREAM, c.p(1, 1.0)))
    # 曲がアウトロのすぐあとで終わるので、サイトの案内もここで出す
    r = ease((c.since(0) - 1.5) / 1.5) if c.li >= 0 else 0
    label(d, W / 2, 1330, "用語の復習は　fe.yogo-drill.com　ip.yogo-drill.com", 30, fade(GOLD, r))


def sc_end(d, c, t):
    st = t - c.start
    q = ease((st - 0.3) / 1.5)
    label(d, W / 2, 700, "コミットしないで", 96, fade(CREAM, q))
    label(d, W / 2, 810, "コンピュータの用語で歌う、夏の恋の歌", 38, fade(NIGHT, q), False)
    q = ease((st - 2.0) / 1.5)
    label(d, W / 2, 1150, "用語の復習は", 40, fade(MUTED, q), False)
    label(d, W / 2, 1230, "fe.yogo-drill.com", 50, fade(GOLD, q))
    label(d, W / 2, 1300, "ip.yogo-drill.com", 50, fade(GOLD, q))


PLAN = [
    (sc_binary, "2進数", "BINARY", 1),
    (sc_interrupt, "割り込みと優先度", "INTERRUPT・PRIORITY", 2),
    (sc_handshake, "3ウェイハンドシェイク", "TCP 3-WAY HANDSHAKE", 3),
    (sc_chorus, "コミットとロールバック", "COMMIT・ROLLBACK・ACID", 4),
    (sc_cache, "キャッシュ", "CACHE HIT", 5),
    (sc_deadlock, "デッドロック", "DEADLOCK", 6),
    (sc_mutex, "排他制御", "MUTUAL EXCLUSION", 7),
    (sc_chorus, "コミットとロールバック", "COMMIT・ROLLBACK・ACID", 8),
    (sc_bridge, "二分探索・ping・バックアップ", "BINARY SEARCH・PING・BACKUP", 9),
    (sc_final, "暗号化と秘密鍵", "ENCRYPTION・PRIVATE KEY", 10),
    (sc_outro, "0と1のあいだ", "BETWEEN 0 AND 1", 11),
]
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=2.0)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・11のまとまり・締め）。Mixkit の Stock Video Free License の素材
CLIPS = [3978,    # タイトル: 窓から見る夜
         3977,    # 2進数: 窓とカーテン（窓をあけたまま）
         38,      # 割り込み: またたく光のぼけ
         30,      # 3ウェイハンドシェイク: 夜の車の光のぼけ
         4064,    # サビ: 夜空の花火
         34379,   # キャッシュ: 夜の水面に映る光
         2846,    # デッドロック: 雨の日の窓
         4433,    # 排他制御: かすんだ満月
         4151,    # サビ2: 花火
         1704,    # ブリッジ: 湖の星空（夜が明ける）
         682,     # 最後のサビ: 手に持つ花火
         39770,   # アウトロ: 星でいっぱいの夜空
         1086]    # 締め: 海の朝日
# 曲がアウトロのすぐあとで終わるときは、締めの場面を出さない（その映像も使わない）
if SCENES[-1][0] >= mc.DUR - 0.5:
    SCENES.pop()
    CLIPS.pop()

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS])
