"""曲「デュプレックス・ハート」の MV（縦長 1080×1920・60fps）を作る。

80年代ハードロックのパワーバラードに、システム構成と OS の用語（クライアントサーバ・シンクライアント・P2P・
集中処理と分散処理・OS・カーネル・デバイスドライバ・デュプレックスシステム・デュアルシステム・稼働率・
スプーリング・絶対パスと相対パス・レスポンスタイム・ターンアラウンドタイム・スループット・
ホットスタンバイとコールドスタンバイ・フェイルオーバー・バッチ処理とリアルタイム処理・オープンソース）を重ねて、
歌詞の1行ごとに図が1つ進む。背景は本物の映像（Mixkit の Free の素材）。

デザイン（ui-ux-pro-max の Retro-Futurism（80年代・ネオン）の提案をもとにした）:
- 黒に近い紫（#100A18）の背景に、ホットピンク（主系・カラオケ）とエレクトリックブルー（待機系）の2色で「二重化」を表す
- 見出しは Rampart One（Google Fonts、OFL。80年代の立体文字のような日本語の字体）、英字のかけ声は Audiowide（OFL）
- 図と歌詞の文字は読みやすさのため BIZ UD ゴシックのまま

使うファイル（notes/曲の動画/デュプレックス・ハート/、公開しない）
- デュプレックス・ハート.mp3 / _歌詞.txt / _時間.json / _asr.json

    python make_mv_duplex.py --jobs 4              # 縦長
    python make_mv_duplex.py --safe --jobs 4       # リール・ショート用の配置（_MV_リール用.mp4）
    python make_mv_duplex.py --youtube --jobs 4    # YouTube 用の横長
    python make_mv_duplex.py --at 30 80            # その秒の静止画（確認用）
"""
import math
from pathlib import Path

from PIL import ImageFont

import mv_common as mc
from mv_common import W, arrow, ease, font, mix, off_pulse, rbox

ROOT = Path(__file__).parent
NAME = "デュプレックス・ハート"
DIR = ROOT / "notes" / "曲の動画" / NAME
FONTS = ROOT / "notes" / "曲の動画" / "フォント"
HEAD = FONTS / "RampartOne-Regular.ttf"
AUDIO = FONTS / "Audiowide-Regular.ttf"

# ---------- 色（この曲用。ほかの曲には関係しない） ----------
DARK = (16, 10, 24)
mc.BG1, mc.BG2 = DARK, (30, 14, 40)
WHITE = mc.CREAM = (236, 232, 244)
MUTED = mc.MUTED = (160, 150, 184)
PINK = mc.GOLD = (255, 46, 136)       # ホットピンク（主系・カラオケの色）
BLUE = (64, 156, 255)                 # エレクトリックブルー（待機系）
CYAN = (0, 229, 255)
VIOLET = mc.PURPLE = (150, 110, 255)
ORANGE = (255, 150, 50)               # ホット（熱い）
ICE = (170, 214, 255)                 # コールド（冷たい）
GREEN = mc.GREEN = (60, 240, 140)
RED = mc.RED = (255, 70, 70)
mc.BLUE = BLUE
CELL = mc.CELL = (34, 22, 52)
CELL_LINE = mc.CELL_LINE = (96, 70, 140)
mc.HOT = (70, 22, 56)
mc.HEAD_FONT = str(HEAD)

mc.configure(DIR / f"{NAME}.mp3", DIR / f"{NAME}_歌詞.txt", DIR / f"{NAME}_時間.json", NAME, words=DIR / f"{NAME}_asr.json")
# 曲は -14.2 LUFS（いちばん大きい音 -2.5 dB）。YouTube の目安 -14 LUFS とほぼ同じなので、そのまま
mc.AUDIO_GAIN_DB = 0.0
OUT = DIR / f"{NAME}_MV.mp4"
BG_DIR = ROOT / "notes" / "曲の動画" / "背景素材"

_au = {}


def au_font(size):
    if size not in _au:
        _au[size] = ImageFont.truetype(str(AUDIO), int(size))
    return _au[size]


def fade(c, q):
    return mix(DARK, c, q)


def text(d, x, y, s, size, col, q=1.0, bold=True, anchor="mm"):
    if q > 0:
        d.text((x, y), s, font=font(size, bold), fill=fade(col, q), anchor=anchor)


def neon(d, x, y, s, size, col, q=1.0, anchor="mm"):
    """見出しの字体（Rampart One）に、光のふちどりをつける。"""
    if q <= 0:
        return
    f = font(size, face=str(HEAD))
    d.text((x, y), s, font=f, fill=fade(col, q), anchor=anchor, stroke_width=max(2, size // 24), stroke_fill=fade(mix(DARK, col, 0.3), q))


def shout(d, x, y, s, size, col, q=1.0, anchor="mm"):
    """英字のかけ声（Audiowide）。"""
    if q <= 0:
        return
    d.text((x, y), s, font=au_font(size), fill=fade(col, q), anchor=anchor, stroke_width=max(2, size // 18), stroke_fill=fade(mix(DARK, col, 0.3), q))


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


def heart(d, x, y, s, col, q):
    if q > 0:
        mc.heart(d, x, y, s, fade(col, q))


def xmark(d, x, y, r, col, q):
    if q > 0:
        d.line((x - r, y - r, x + r, y + r), fill=fade(col, q), width=max(6, int(r / 4)))
        d.line((x - r, y + r, x + r, y - r), fill=fade(col, q), width=max(6, int(r / 4)))


def server(d, cx, cy, col, q, label="", t=0.0, down=False, on=True, w=210, h=280, busy=False):
    """サーバー（ラック）。down で赤い×、on=False で電源が入っていない（ランプが消えている）。"""
    if q <= 0:
        return
    rbox(d, cx - w / 2, cy - h / 2, w, h, fade(CELL, q), fade(RED if down else col, q), 14, 5)
    n = 4
    for k in range(n):
        y = cy - h / 2 + 22 + k * (h - 44) / n
        uh = (h - 44) / n - 12
        rbox(d, cx - w / 2 + 18, y, w - 36, uh, fade(mix(CELL, col, 0.12), q), fade(mix(CELL, col, 0.5), q), 6, 2)
        for j in range(3):
            blink = on and not down and (math.sin(t * (7 + j * 3) + k * 1.9 + j) > -0.2 or busy)
            lc = GREEN if j == 0 else col
            d.ellipse((cx + w / 2 - 40 - j * 26, y + uh / 2 - 7, cx + w / 2 - 26 - j * 26, y + uh / 2 + 7),
                      fill=fade(lc if blink else mix(CELL, MUTED, 0.3), q))
        d.line((cx - w / 2 + 34, y + uh / 2, cx - 10, y + uh / 2), fill=fade(mix(CELL, MUTED, 0.6), q), width=3)
    if down:
        xmark(d, cx, cy, w * 0.32, RED, q)
    if label:
        text(d, cx, cy + h / 2 + 42, label, 34, RED if down else col, q)


def monitor(d, cx, cy, col, q, label="", w=200, h=140, glow=0.3):
    """端末（パソコンの画面）。"""
    if q <= 0:
        return
    rbox(d, cx - w / 2, cy - h / 2, w, h, fade(CELL, q), fade(col, q), 10, 5)
    d.rectangle((cx - w / 2 + 16, cy - h / 2 + 16, cx + w / 2 - 16, cy + h / 2 - 16), fill=fade(mix(DARK, col, glow), q))
    d.rectangle((cx - 16, cy + h / 2, cx + 16, cy + h / 2 + 24), fill=fade(MUTED, q))
    d.rectangle((cx - 60, cy + h / 2 + 24, cx + 60, cy + h / 2 + 34), fill=fade(MUTED, q))
    if label:
        text(d, cx, cy + h / 2 + 70, label, 32, col, q)


def cylinder(d, cx, cy, w, h, col, q, label=""):
    """ディスク（円柱）。"""
    if q <= 0:
        return
    e = h * 0.22
    d.rectangle((cx - w / 2, cy - h / 2 + e / 2, cx + w / 2, cy + h / 2 - e / 2), fill=fade(CELL, q))
    d.line((cx - w / 2, cy - h / 2 + e / 2, cx - w / 2, cy + h / 2 - e / 2), fill=fade(col, q), width=5)
    d.line((cx + w / 2, cy - h / 2 + e / 2, cx + w / 2, cy + h / 2 - e / 2), fill=fade(col, q), width=5)
    d.arc((cx - w / 2, cy + h / 2 - e, cx + w / 2, cy + h / 2), 0, 180, fill=fade(col, q), width=5)
    d.ellipse((cx - w / 2, cy - h / 2, cx + w / 2, cy - h / 2 + e), fill=fade(mix(CELL, col, 0.25), q), outline=fade(col, q), width=5)
    if label:
        text(d, cx, cy + 10, label, 32, col, q)


def paper(d, cx, cy, q, col=WHITE, s=1.0):
    """書類1枚。"""
    if q <= 0:
        return
    w, h = 70 * s, 90 * s
    d.polygon([(cx - w / 2, cy - h / 2), (cx + w / 2 - 18 * s, cy - h / 2), (cx + w / 2, cy - h / 2 + 18 * s),
               (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)], fill=fade(col, q))
    for k in range(3):
        y = cy - h / 2 + 30 * s + k * 18 * s
        d.line((cx - w / 2 + 12 * s, y, cx + w / 2 - 14 * s, y), fill=fade(MUTED, q), width=max(2, int(4 * s)))


def printer(d, cx, cy, col, q, label=""):
    if q <= 0:
        return
    rbox(d, cx - 70, cy - 120, 140, 70, fade(mix(CELL, WHITE, 0.15), q), fade(col, q), 6, 4)
    rbox(d, cx - 130, cy - 60, 260, 130, fade(CELL, q), fade(col, q), 16, 5)
    d.rectangle((cx - 90, cy + 40, cx + 90, cy + 52), fill=fade(DARK, q))
    d.ellipse((cx + 80, cy - 34, cx + 100, cy - 14), fill=fade(GREEN, q))
    if label:
        text(d, cx, cy + 120, label, 32, col, q)


def ecg(d, x0, x1, y, t, col, q, amp=70, speed=1.0, flat=False):
    """心電図の線（ハートビート）。flat で止まった線。"""
    if q <= 0:
        return
    pts = []
    for x in range(int(x0), int(x1), 4):
        u = ((x - x0) / 220 - t * speed) % 1
        if flat:
            v = 0
        elif 0.40 < u < 0.44:
            v = (u - 0.40) / 0.04
        elif 0.44 <= u < 0.50:
            v = 1 - (u - 0.44) / 0.06 * 1.8
        elif 0.50 <= u < 0.54:
            v = -0.8 + (u - 0.50) / 0.04 * 0.8
        else:
            v = 0
        pts.append((x, y - v * amp))
    d.line(pts, fill=fade(col, q), width=6, joint="curve")


# ---------- 場面 ----------

def duo(d, t, q, y=640, gap=250):
    """主系（ピンク）と待機系（ブルー）のサーバー2台とハート。タイトルや締めで使う。"""
    server(d, W / 2 - gap, y, PINK, q, "", t)
    server(d, W / 2 + gap, y, BLUE, q, "", t)
    beat = 1 + 0.12 * off_pulse(t)
    heart(d, W / 2, y - 10, 5.2 * beat, PINK, q)
    heart(d, W / 2, y - 10, 3.0 * beat, mix(PINK, WHITE, 0.4), q)


def sc_title(d, c, t):
    if mc.SAFE:
        return sc_hook(d, c, t)
    q = ease((t - 0.05) / 0.8)
    duo(d, t, q)
    neon(d, W / 2, 920, "デュプレックス", 104, PINK, q)
    neon(d, W / 2, 1050, "ハート", 140, BLUE, q)
    r = ease((t - 0.6) / 0.8)
    shout(d, W / 2, 1190, "DUPLEX HEART", 60, CYAN, r)
    text(d, W / 2, 1275, "システム構成と OS の用語で歌う、80年代ロック", 36, MUTED, r, False)


def sc_hook(d, c, t):
    """リール・ショートの最初の画面（つかみ）。1枚目から問いかける。答え（デュプレックスシステム）はサビで歌われる。"""
    d.rectangle((0, 90, W, 430), fill=DARK)   # 見出しを背景の色（＝透明）で消す
    down = 0.5 + 0.5 * math.sin(t * 2.4) > 0.5
    server(d, W / 2 - 220, 640, PINK, 1.0, "サーバー", t, down=down)
    server(d, W / 2 + 220, 640, BLUE, 1.0, "もう1台", t, busy=down)
    if down:
        arrow(d, W / 2 - 90, 640, W / 2 + 90, 640, BLUE, 10, 34)
    neon(d, W / 2, 910, "1台が倒れても", 86, WHITE)
    neon(d, W / 2, 1030, "止まらない仕組みは？", 76, PINK)
    text(d, W / 2, 1160, "答えは、この歌のサビで。", 46, CYAN)
    neon(d, W / 2, 1280, "デュプレックス・ハート", 58, BLUE)


def sc_server(d, c, t):
    # 0行目: サーバールーム
    qa = phase(c, 0, 0)
    if qa > 0:
        for k in range(3):
            rr = stagger(c, 0, k, 0.2) * qa
            server(d, W / 2 - 290 + k * 290, 700, (PINK, VIOLET, BLUE)[k], rr, "", t)
        # ファン
        for k in range(3):
            fx, fy = W / 2 - 290 + k * 290, 960
            ang = t * 9 + k
            d.ellipse((fx - 60, fy - 60, fx + 60, fy + 60), outline=fade(MUTED, qa), width=4)
            for j in range(4):
                a = ang + j * math.pi / 2
                d.line((fx, fy, fx + 50 * math.cos(a), fy + 50 * math.sin(a)), fill=fade(MUTED, qa), width=10)
        neon(d, W / 2, 1120, "サーバー", 80, PINK, qa)
        text(d, W / 2, 1220, "ほかのコンピュータに、サービスを提供する", 36, WHITE, qa)
        text(d, W / 2, 1290, "熱を出すので、ファンで冷やしている", 32, MUTED, qa, False)
    # 1行目: クライアントサーバシステム
    qb = phase(c, 1, 1)
    if qb > 0:
        neon(d, W / 2, 500, "クライアントサーバ", 70, PINK, qb)
        monitor(d, 250, 760, CYAN, qb, "クライアント")
        server(d, 820, 740, PINK, qb, "サーバー", t)
        ph = (c.since(1) % 2.4) / 2.4
        ra = ease(c.since(1) / 0.5) * qb
        arrow(d, 380, 690, 690, 690, fade(CYAN, ra), 8, 28)
        text(d, 535, 650, "要求（頼む）", 32, CYAN, ra)
        rb = ease((c.since(1) - 0.8) / 0.5) * qb
        arrow(d, 690, 800, 380, 800, fade(PINK, rb), 8, 28)
        text(d, 535, 845, "応答（応える）", 32, PINK, rb)
        if ph < 0.5:
            x = 380 + 310 * ease(ph / 0.5)
            d.ellipse((x - 14, 676, x + 14, 704), fill=fade(WHITE, ra))
        else:
            x = 690 - 310 * ease((ph - 0.5) / 0.5)
            d.ellipse((x - 14, 786, x + 14, 814), fill=fade(WHITE, rb))
        text(d, W / 2, 1010, "サービスを頼む側 ＝ クライアント", 38, CYAN, qb)
        text(d, W / 2, 1080, "サービスを提供する側 ＝ サーバー", 38, PINK, qb)
        text(d, W / 2, 1190, "例：Webブラウザ（クライアント）と Webサーバー", 32, MUTED, qb, False)
    # 2〜3行目: シンクライアント
    qc = phase(c, 2, 3)
    if qc > 0:
        neon(d, W / 2, 500, "シンクライアント", 76, CYAN, qc)
        monitor(d, 240, 760, CYAN, qc, "端末（画面・入力だけ）")
        server(d, 830, 740, PINK, qc, "サーバー", t, busy=True)
        text(d, 240, 640, "シン ＝ thin（うすい）", 28, MUTED, qc, False)
        if c.li >= 3:
            r = c.p(3, 0.5) * qc
            items = [("処理", PINK), ("データ", BLUE), ("アプリ", VIOLET)]
            for k, (s, col) in enumerate(items):
                rr = stagger(c, 3, k, 0.3, 0.6) * qc
                x = 240 + (830 - 240) * rr
                y = 700 + k * 60 - 60 * math.sin(math.pi * rr)
                box(d, x, y, 150, 56, s, col, min(1.0, rr * 3) * qc, 30, tcol=col)
            text(d, W / 2, 1010, "処理もデータも、サーバーに置く", 38, WHITE, r)
            box(d, W / 2, 1130, 860, 100, "端末にデータが残らない → 情報が漏れにくい", PINK, r, 34, tcol=PINK)
            text(d, W / 2, 1250, "端末をなくしても、中にデータがない", 32, MUTED, r, False)


def mesh(d, cx, cy, rad, n, col, q, t, hot=-1):
    pts = [(cx + rad * math.cos(-math.pi / 2 + k * 2 * math.pi / n), cy + rad * math.sin(-math.pi / 2 + k * 2 * math.pi / n)) for k in range(n)]
    for a in range(n):
        for b in range(a + 1, n):
            d.line((*pts[a], *pts[b]), fill=fade(mix(CELL, col, 0.6), q), width=4)
    for k, (x, y) in enumerate(pts):
        monitor(d, x, y - 10, PINK if k == hot else col, q, "", 120, 86)
    return pts


def sc_p2p(d, c, t):
    # 0〜1行目: ピアツーピア
    qa = phase(c, 0, 1)
    if qa > 0:
        neon(d, W / 2, 500, "ピアツーピア（P2P）", 66, CYAN, qa)
        pts = mesh(d, W / 2, 800, 230, 5, CYAN, qa, t, hot=int(c.since(0) * 1.5) % 5)
        # データが仲間から仲間へ
        ph = (c.since(0) * 0.8) % 1
        a, b = int(c.since(0) * 0.8) % 5, (int(c.since(0) * 0.8) + 2) % 5
        x = pts[a][0] + (pts[b][0] - pts[a][0]) * ph
        y = pts[a][1] + (pts[b][1] - pts[a][1]) * ph
        d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=fade(PINK, qa))
        text(d, W / 2, 1110, "専用のサーバーを置かない", 38, WHITE, qa)
        if c.li >= 1:
            r = c.p(1, 0.5) * qa
            box(d, W / 2, 1220, 840, 100, "対等な仲間（ピア）どうしで、直接やり取り", CYAN, r, 36, tcol=CYAN)
            text(d, W / 2, 1330, "どのコンピュータも、頼む側にも応える側にもなる", 32, MUTED, r, False)
    # 2〜3行目: 集中処理と分散処理
    qb = phase(c, 2, 3)
    if qb > 0:
        hot = 0 if c.li < 3 else 1
        for k, (nm, col) in enumerate([("集中処理", PINK), ("分散処理", BLUE)]):
            x = W / 2 - 240 + k * 480
            rr = stagger(c, 2, k, 0.4) * qb
            on = (k == hot)
            rbox(d, x - 220, 470, 440, 820, fade(mc.HOT if on else CELL, rr), fade(col, rr), 18, 7 if on else 4)
            neon(d, x, 545, nm, 56, col, rr)
            if k == 0:
                server(d, x, 760, PINK, rr, "", t, w=170, h=230, busy=True)
                for j in range(3):
                    tx = x - 140 + j * 140
                    d.line((x, 875, tx, 960), fill=fade(MUTED, rr), width=3)
                    rbox(d, tx - 45, 960, 90, 60, fade(CELL, rr), fade(MUTED, rr), 6, 3)
                text(d, x, 1080, "1台のコンピュータが", 30, WHITE, rr)
                text(d, x, 1125, "全部の処理をする", 30, WHITE, rr)
                text(d, x, 1200, "○ 管理しやすい", 30, GREEN, rr)
                text(d, x, 1245, "× 1台が止まると全部止まる", 28, RED, rr)
            else:
                ps = [(x - 110, 700), (x + 110, 700), (x - 110, 900), (x + 110, 900)]
                for a in range(4):
                    for b in range(a + 1, 4):
                        d.line((*ps[a], *ps[b]), fill=fade(mix(CELL, BLUE, 0.6), rr), width=3)
                for j, (px, py) in enumerate(ps):
                    server(d, px, py, BLUE, rr, "", t + j, w=110, h=150)
                text(d, x, 1080, "何台ものコンピュータで", 30, WHITE, rr)
                text(d, x, 1125, "処理を分け合う", 30, WHITE, rr)
                text(d, x, 1200, "○ 1台が止まっても動ける", 28, GREEN, rr)
                text(d, x, 1245, "× 管理がむずかしい", 30, RED, rr)
        text(d, W / 2, 1360, "一台に任す（集中）か、みんなで分ける（分散）か", 32, MUTED, qb, False)


def sc_os(d, c, t):
    q = c.p(0, 0.5) if c.li >= 0 else 0
    neon(d, W / 2, 500, "OS（オペレーティングシステム）", 54, VIOLET, q)
    layers = [("アプリケーション", CYAN, 620), ("OS", VIOLET, 830), ("ハードウェア", BLUE, 1160)]
    for k, (nm, col, y) in enumerate(layers):
        rr = stagger(c, 0, k, 0.2) * q
        hh = 220 if k == 1 else 110
        rbox(d, 120, y - hh / 2 if k != 1 else y - 60, 840, hh, fade(mix(CELL, col, 0.15), rr), fade(col, rr), 16, 5)
        if k != 1:
            text(d, W / 2, y, nm, 40, col, rr)
    # アプリの箱
    for k, s in enumerate(["ブラウザ", "メール", "ゲーム"]):
        rbox(d, 170 + k * 260, 595, 220, 50, fade(CELL, q), fade(CYAN, q), 8, 3)
        text(d, 280 + k * 260, 620, s, 28, WHITE, q, False)
    text(d, 170, 800, "OS", 40, VIOLET, q, anchor="lm")
    text(d, 260, 800, "＝ 裏方：コンピュータ全体を管理する", 30, WHITE, q, anchor="lm")
    # 1行目: タスク管理・メモリ管理
    r1 = c.p(1, 0.5) if c.li >= 1 else 0
    if r1 > 0:
        box(d, 330, 880, 380, 80, "", VIOLET, r1)
        text(d, 230, 880, "タスク管理", 28, VIOLET, r1)
        k = int(c.since(1) * 3) % 3
        for j in range(3):
            d.rounded_rectangle((330 + j * 52, 862, 370 + j * 52, 898), radius=6, fill=fade((CYAN if j == k else CELL_LINE), r1))
        box(d, 750, 880, 380, 80, "", VIOLET, r1)
        text(d, 650, 880, "メモリ管理", 28, VIOLET, r1)
        for j in range(4):
            col = (CYAN, PINK, GREEN, CELL_LINE)[j]
            d.rectangle((742 + j * 44, 860, 778 + j * 44, 900), fill=fade(col, r1))
        text(d, 330, 950, "CPU を順番に回す", 26, MUTED, r1, False)
        text(d, 750, 950, "メモリを配って回収", 26, MUTED, r1, False)
    # 2行目: カーネル・デバイスドライバ
    r2 = c.p(2, 0.5) if c.li >= 2 else 0
    if r2 > 0:
        beat = 1 + 0.15 * off_pulse(t)
        heart(d, 160, 880 - 5, 1.5 * beat, PINK, r2)
        text(d, W / 2, 1010, "カーネル ＝ OS の中心（心臓）", 34, PINK, r2)
        box(d, W / 2, 1075, 520, 64, "デバイスドライバ", ORANGE, r2, 34, tcol=ORANGE)
        for k, s in enumerate(["プリンタ", "キーボード", "ディスク"]):
            rbox(d, 170 + k * 260, 1192, 220, 50, fade(CELL, r2), fade(BLUE, r2), 8, 3)
            text(d, 280 + k * 260, 1217, s, 28, WHITE, r2, False)
    # 3行目: ハードとソフトをつなぐ
    r3 = c.p(3, 0.5) if c.li >= 3 else 0
    if r3 > 0:
        for k in range(3):
            x = 280 + k * 260
            arrow(d, x, 1108, x, 1188, fade(ORANGE, r3), 6, 18)
            arrow(d, x - 40, 1188, x - 40, 1108, fade(ORANGE, r3 * 0.6), 4, 14)
        text(d, W / 2, 1310, "周辺機器を動かすソフト：ハードと OS の通訳", 32, ORANGE, r3)


def chorus_duplex(d, c, t, q, i0):
    """i0 行目: 主系が倒れる → i0+1 行目: 待機系が引き継ぐ。"""
    neon(d, W / 2, 500, "デュプレックスシステム", 64, PINK, q)
    down = c.li >= i0 and c.since(i0) > 1.2
    take = c.li >= i0 + 1
    server(d, 300, 760, PINK, q, "主系（現用系）", t, down=down, busy=not down)
    server(d, 780, 760, BLUE, q, "待機系", t, busy=take, on=True)
    # 仕事（入ってくる処理）
    k = (c.since(i0) * 1.2) % 1
    tx = 780 if take else 300
    d.ellipse((tx - 16, 560 + 40 * k - 16, tx + 16, 560 + 40 * k + 16), fill=fade(WHITE, q * (1 - k)))
    if take:
        r = c.p(i0 + 1, 0.4) * q
        arrow(d, 430, 760, 650, 760, fade(BLUE, r), 10, 34)
        text(d, 540, 710, "切り替え", 32, BLUE, r)
        heart(d, 780, 760, 2.4 * (1 + 0.15 * off_pulse(t)), PINK, r)
    text(d, W / 2, 1010, "ふだんは主系が処理、待機系は待っている", 36, WHITE, q)
    box(d, W / 2, 1130, 860, 100, "主系が故障 → 待機系に切り替えて続ける", BLUE, c.p(i0 + 1, 0.4) * q if take else 0, 36, tcol=BLUE)


def chorus_dual(d, c, t, q, i0):
    neon(d, W / 2, 500, "デュアルシステム", 72, CYAN, q)
    y0 = 650
    text(d, W / 2, 580, "入力", 32, MUTED, q)
    for k, col in enumerate((PINK, BLUE)):
        x = 300 + k * 480
        arrow(d, W / 2, 600, x, y0 - 30, fade(MUTED, q), 5, 18)
        server(d, x, y0 + 110, col, q, "", t, busy=True, w=180, h=230)
        text(d, x + (k * 2 - 1) * 150, y0 + 110, "系" + "AB"[k], 36, col, q)
        arrow(d, x, y0 + 270, W / 2 + (k * 2 - 1) * 90, 990, fade(col, q), 6, 20)
    r = c.p(i0 + 1, 0.4) * q if c.li >= i0 + 1 else 0
    box(d, W / 2, 1020, 260, 90, "照合", WHITE, q, 44, head=True)
    if r > 0:
        text(d, W / 2 - 200, 1020, "結果", 30, PINK, r)
        text(d, W / 2 + 200, 1020, "結果", 30, BLUE, r)
        text(d, W / 2, 1090, "同じなら OK", 30, GREEN, r)
    text(d, W / 2, 1160, "2つの系が、同じ処理を同時にする", 36, WHITE, q)
    text(d, W / 2, 1230, "結果を照らし合わせて、正しいか確かめる", 36, CYAN, r)
    text(d, W / 2, 1310, "片方が故障しても、もう片方で続けられる", 30, MUTED, r, False)


def chorus_nonstop(d, c, t, q, i0):
    """i0〜i0+3 行目（1回目のサビ）: 止まらない ＝ 24時間 365日。"""
    pop = 1 + 0.08 * off_pulse(t)
    neon(d, W / 2, 500, "止まらない", 96, PINK, q)
    ecg(d, 110, 970, 720, t, PINK, q, 90)
    r1 = c.p(i0 + 1, 0.4) * q if c.li >= i0 + 1 else 0
    text(d, W / 2, 880, "二重化：同じ役目のものを2つ用意する", 36, WHITE, r1)
    text(d, W / 2, 940, "→ 1つが壊れても、システム全体は止まらない", 34, CYAN, r1)
    r2 = c.p(i0 + 2, 0.4) * q if c.li >= i0 + 2 else 0
    shout(d, W / 2 - 220, 1080, "24h", int(110 * pop), PINK, r2)
    shout(d, W / 2 + 200, 1080, "365d", int(110 * pop), BLUE, r2)
    text(d, W / 2, 1180, "サービスを止めない ＝ 無停止で動き続ける", 34, WHITE, r2)
    r3 = c.p(i0 + 3, 0.4) * q if c.li >= i0 + 3 else 0
    box(d, W / 2, 1300, 760, 96, "信頼性（止まりにくさ）を高める", GREEN, r3, 38, tcol=GREEN)


def chorus_avail(d, c, t, q, i0):
    """i0〜i0+3 行目（2回目のサビ）: 稼働率と、2台を並列にしたときの稼働率。"""
    neon(d, W / 2, 500, "稼働率", 96, PINK, q)
    text(d, W / 2, 610, "動いている時間の割合（1 に近いほど止まらない）", 32, WHITE, q)
    box(d, W / 2, 720, 900, 110, "MTBF ÷ (MTBF ＋ MTTR)", PINK, q, 50, tcol=PINK)
    text(d, W / 2 - 220, 820, "MTBF：故障から故障までの平均", 28, MUTED, q, False)
    text(d, W / 2 + 230, 820, "MTTR：修理の平均時間", 28, MUTED, q, False)
    r1 = c.p(i0 + 1, 0.4) * q if c.li >= i0 + 1 else 0
    text(d, W / 2, 890, "例：990時間 ÷ (990 ＋ 10)時間 ＝ 0.99", 34, CYAN, r1)
    r2 = c.p(i0 + 2, 0.4) * q if c.li >= i0 + 2 else 0
    if r2 > 0:
        # 並列（二重化）
        for k, col in enumerate((PINK, BLUE)):
            y = 1010 + k * 90
            d.line((180, y, 330, y), fill=fade(MUTED, r2), width=4)
            d.line((530, y, 640, y), fill=fade(MUTED, r2), width=4)
            box(d, 430, y, 200, 70, "0.9", col, r2, 38, tcol=col)
        d.line((180, 1010, 180, 1100), fill=fade(MUTED, r2), width=4)
        d.line((640, 1010, 640, 1100), fill=fade(MUTED, r2), width=4)
        text(d, 820, 1030, "2台を並列に", 32, WHITE, r2)
        text(d, 820, 1080, "どちらかが動けばよい", 28, MUTED, r2, False)
    r3 = c.p(i0 + 3, 0.4) * q if c.li >= i0 + 3 else 0
    box(d, W / 2, 1230, 900, 100, "1 −（1 − 0.9）×（1 − 0.9）＝ 0.99", GREEN, r3, 40, tcol=GREEN)
    text(d, W / 2, 1335, "1台で 0.9 → 2台で 0.99 に上がる", 32, GREEN, r3)


def chorus_open(d, c, t, q, i0):
    neon(d, W / 2, 500, "オープンソース", 84, GREEN, q)
    rbox(d, W / 2 - 170, 590, 340, 300, fade(CELL, q), fade(GREEN, q), 12, 5)
    lines = ["def heart():", "  while True:", "    beat()", "  # 公開中"]
    for k, s in enumerate(lines):
        d.text((W / 2 - 140, 630 + k * 60), s, font=font(30), fill=fade(GREEN if k < 3 else MUTED, q))
    text(d, W / 2, 940, "ソースコード（プログラムの中身）を公開", 36, WHITE, q)
    r = c.p(i0 + 1, 0.4) * q if c.li >= i0 + 1 else 0
    if r > 0:
        for k in range(6):
            a = -math.pi / 2 + k * math.pi / 3 + c.since(i0 + 1) * 0.3
            rr = ease((c.since(i0 + 1) - k * 0.12) / 0.5) * q
            x, y = W / 2 + 390 * math.cos(a) * rr, 740 + 130 * math.sin(a) * rr
            paper(d, x, y, rr * 0.9, mix(GREEN, WHITE, 0.6), 0.7)
        for k, (s, col) in enumerate([("自由に使える", CYAN), ("改良できる", PINK), ("配れる", BLUE)]):
            rr = stagger(c, i0 + 1, k, 0.25) * q
            box(d, 220 + k * 320, 1060, 280, 84, s, col, rr, 36, tcol=col)
        text(d, W / 2, 1170, "ライセンス（使うときの決まり）は守る", 32, MUTED, r, False)
        text(d, W / 2, 1240, "例：Linux（OS）", 32, GREEN, r)


def chorus_finale(d, c, t, q, i0):
    pop = 1 + 0.1 * off_pulse(t)
    duo(d, t, q, 640, 260)
    words = ["デュプレックス", "デュアル", "ホットスタンバイ", "稼働率", "P2P", "スプーリング"]
    for k, w in enumerate(words):
        rr = stagger(c, i0, k, 0.1) * q
        x = 230 + (k % 3) * 310
        y = 900 + (k // 3) * 100
        col = (PINK, BLUE, CYAN)[(k + int(mc.beat(t))) % 3]
        box(d, x, y, 290, 80, w, col, rr, 30, tcol=col)
    r2 = c.p(i0 + 2, 0.4) * q if c.li >= i0 + 2 else 0
    shout(d, W / 2 - 220, 1180, "24h", int(100 * pop), PINK, r2)
    shout(d, W / 2 + 200, 1180, "365d", int(100 * pop), BLUE, r2)
    r3 = c.p(i0 + 3, 0.4) * q if c.li >= i0 + 3 else 0
    neon(d, W / 2, 1320, "ダウンしない想い", 64, PINK, r3)


def make_chorus(kind):
    def sc(d, c, t):
        qa = phase(c, 0, 1)
        if qa > 0:
            if kind == "final":
                chorus_duplex(d, c, t, qa, 0)
            else:
                chorus_duplex(d, c, t, qa, 0)
        qb = phase(c, 2, 3)
        if qb > 0:
            (chorus_open if kind == "final" else chorus_dual)(d, c, t, qb, 2)
        qc = phase(c, 4, 7)
        if kind == 2 and c.li >= 7 and c.since(7) > SOLO_AT:
            qc *= 1 - ease((c.since(7) - SOLO_AT) / 0.4)
        if qc > 0:
            {1: chorus_nonstop, 2: chorus_avail, "final": chorus_finale}[kind](d, c, t, qc, 4)
        if kind == 2 and c.li >= 7 and c.since(7) > SOLO_AT:
            solo(d, c, t, ease((c.since(7) - SOLO_AT - 0.2) / 0.5), c.since(7) - SOLO_AT)
    return sc


def solo(d, c, t, q, st):
    """ギターソロ: フェイルオーバー（主系 → 待機系）とフェイルバック（直ったら元にもどす）をくり返して見せる。"""
    if q <= 0:
        return
    shout(d, W / 2, 500, "GUITAR SOLO", int(76 * (1 + 0.08 * off_pulse(t))), PINK, q)
    cyc = 8.0
    u = (st % cyc) / cyc
    down = 0.15 < u < 0.6
    back = u >= 0.6
    server(d, 300, 760, PINK, q, "主系", t, down=down, busy=not down)
    server(d, 780, 760, BLUE, q, "待機系", t, busy=down)
    if down:
        arrow(d, 430, 760, 650, 760, fade(BLUE, q), 10, 34)
        neon(d, W / 2, 1010, "フェイルオーバー", 72, BLUE, q)
        text(d, W / 2, 1110, "故障したら、待機系に自動で切り替える", 36, WHITE, q)
    elif back:
        arrow(d, 650, 760, 430, 760, fade(PINK, q), 10, 34)
        neon(d, W / 2, 1010, "フェイルバック", 72, PINK, q)
        text(d, W / 2, 1110, "直ったら、元の主系にもどす", 36, WHITE, q)
    else:
        neon(d, W / 2, 1010, "ふだんは主系", 72, PINK, q)
        text(d, W / 2, 1110, "待機系はいつでも代われるように待つ", 36, WHITE, q)
    ecg(d, 110, 970, 1260, t, PINK, q, 60)


def sc_spool(d, c, t):
    q = c.p(0, 0.5) if c.li >= 0 else 0
    neon(d, W / 2, 500, "スプーリング", 90, CYAN, q)
    # CPU・ディスク・プリンタ
    box(d, 200, 700, 220, 140, "CPU", PINK, q, 56, head=True)
    printer(d, 860, 720, BLUE, q, "プリンタ（遅い）")
    for k in range(4):
        paper(d, 200 + k * 14, 850 - k * 10, q * (1 if c.li < 1 else 0.0), WHITE, 0.8)
    text(d, 200, 940, "印刷待ちの書類", 28, MUTED, q * (1 if c.li < 1 else 0), False)
    r1 = c.p(1, 0.5) if c.li >= 1 else 0
    if r1 > 0:
        cylinder(d, 530, 720, 200, 170, VIOLET, r1, "ディスク")
        for k in range(4):
            rr = ease((c.since(1) - k * 0.2) / 0.5)
            x = 260 + (530 - 260) * rr
            paper(d, x, 720 - 120 * math.sin(math.pi * rr), r1 * (1 - rr * 0.0) if rr < 1 else 0, WHITE, 0.6)
        text(d, 530, 860, "いったん ためる", 30, VIOLET, r1)
        # ディスクからプリンタへ、ゆっくり
        ph = (c.since(1) % 2.5) / 2.5
        paper(d, 630 + 130 * ph, 720, r1 * (1 - ph), WHITE, 0.5)
    r2 = c.p(2, 0.5) if c.li >= 2 else 0
    if r2 > 0:
        # 時間の帯で比べる
        text(d, 140, 1010, "なし", 32, MUTED, r2, anchor="lm")
        segs = [(0, 2, PINK, "処理"), (2, 6, CELL_LINE, "印刷が終わるまで待つ"), (6, 8, PINK, "次")]
        for a, b, col, s in segs:
            d.rounded_rectangle((260 + a * 85, 985, 260 + b * 85 - 6, 1035), radius=8, fill=fade(col, r2))
            text(d, 260 + (a + b) / 2 * 85, 1010, s, 26, WHITE, r2, False)
        text(d, 140, 1100, "あり", 32, CYAN, r2, anchor="lm")
        segs = [(0, 2, PINK, "処理"), (2, 2.6, VIOLET, ""), (2.6, 4.6, PINK, "次の仕事"), (4.6, 6.6, PINK, "その次")]
        for a, b, col, s in segs:
            d.rounded_rectangle((260 + a * 85, 1075, 260 + b * 85 - 6, 1125), radius=8, fill=fade(col, r2))
            text(d, 260 + (a + b) / 2 * 85, 1100, s, 26, WHITE, r2, False)
        text(d, 260 + 2.3 * 85, 1155, "ためる", 24, VIOLET, r2, False)
    r3 = c.p(3, 0.5) if c.li >= 3 else 0
    box(d, W / 2, 1260, 880, 100, "CPU が待たされない → 全体が速く進む", CYAN, r3, 38, tcol=CYAN)
    text(d, W / 2, 1360, "遅い機器への出力を、ディスクにためてから送る", 30, MUTED, r3, False)


TREE = {  # 名前: (x, y, 親)
    "/": (W / 2, 560, None),
    "home": (W / 2 - 180, 690, "/"),
    "etc": (W / 2 + 220, 690, "/"),
    "yuki": (W / 2 - 180, 820, "home"),
    "docs": (W / 2 - 360, 950, "yuki"),
    "pics": (W / 2, 950, "yuki"),
    "song.mp3": (W / 2 - 360, 1080, "docs"),
}


def tree(d, q, hot=(), cur=None, t=0.0):
    for nm, (x, y, par) in TREE.items():
        if par:
            px, py = TREE[par][:2]
            col = PINK if (nm in hot and par in hot) else CELL_LINE
            d.line((px, py + 30, px, (py + y) / 2, x, (py + y) / 2, x, y - 30), fill=fade(col, q), width=6 if col == PINK else 4)
    for nm, (x, y, par) in TREE.items():
        col = PINK if nm in hot else (CYAN if nm == "song.mp3" else WHITE)
        w = 70 if nm == "/" else 40 + 24 * len(nm)
        rbox(d, x - w / 2, y - 30, w, 60, fade(mc.HOT if nm in hot else CELL, q), fade(col, q), 10, 3)
        text(d, x, y, nm, 32, col, q)
    if cur:
        x, y = TREE[cur][:2]
        bob = 6 * math.sin(t * 5)
        w = 40 + 24 * len(cur)
        d.polygon([(x + w / 2 + 20 + bob, y), (x + w / 2 + 50 + bob, y - 18), (x + w / 2 + 50 + bob, y + 18)], fill=fade(GREEN, q))
        text(d, x + w / 2 + 60 + bob, y, "今いる場所", 26, GREEN, q, anchor="lm")


def sc_path(d, c, t):
    q = c.p(0, 0.5) if c.li >= 0 else 0
    li = max(0, c.li)
    if li == 0:
        hot, cur = ("/", "home", "yuki", "docs", "song.mp3"), None
        neon(d, W / 2, 470, "絶対パス", 70, PINK, q)
        path, note = "/home/yuki/docs/song.mp3", "ルート（いちばん上の / ）から、たどる"
    elif li == 1:
        hot, cur = ("yuki", "docs", "song.mp3"), "yuki"
        neon(d, W / 2, 470, "相対パス", 70, CYAN, q)
        path, note = "docs/song.mp3", "今いる場所（カレント）から、たどる"
    elif li == 2:
        hot, cur = ("docs", "yuki"), "docs"
        neon(d, W / 2, 470, "..（ドットドット）", 66, VIOLET, q)
        path, note = "..  → yuki", ".. は親ディレクトリ（1つ上）、. は今の場所"
    else:
        hot, cur = ("pics", "yuki", "docs", "song.mp3"), "pics"
        neon(d, W / 2, 470, "帰り道", 70, GREEN, q)
        path, note = "../docs/song.mp3", "1つ上にもどって、docs の中へ"
    r = c.p(li, 0.4) if c.li >= 0 else 0
    tree(d, q, hot if r > 0.3 else (), cur, t)
    box(d, W / 2, 1210, 880, 100, path, PINK if li == 0 else (CYAN if li == 1 else (VIOLET if li == 2 else GREEN)), r, 46, tcol=WHITE)
    text(d, W / 2, 1320, note, 32, WHITE, r)


def sc_perf(d, c, t):
    q = c.p(0, 0.5) if c.li >= 0 else 0
    # 時間の帯: 入力 → 処理 → 出力
    x0, xa, xb, x1 = 130, 330, 650, 950
    y = 640
    for a, b, col, s in [(x0, xa, CYAN, "入力"), (xa, xb, VIOLET, "処理"), (xb, x1, PINK, "出力")]:
        d.rounded_rectangle((a, y - 40, b - 6, y + 40), radius=10, fill=fade(mix(CELL, col, 0.6), q))
        text(d, (a + b) / 2, y, s, 34, WHITE, q)
    arrow(d, x0, y + 70, x1 + 20, y + 70, fade(MUTED, q), 4, 16)
    text(d, x1 + 10, y + 100, "時間", 26, MUTED, q, False)
    r0 = c.p(0, 0.5) if c.li >= 0 else 0
    if r0 > 0:
        d.line((xa, y - 70, xa, y - 130), fill=fade(CYAN, r0), width=4)
        d.line((xb, y - 70, xb, y - 130), fill=fade(CYAN, r0), width=4)
        arrow(d, xa, y - 100, xb, y - 100, fade(CYAN, r0), 5, 18)
        text(d, (xa + xb) / 2, y - 145, "レスポンスタイム", 34, CYAN, r0)
        text(d, W / 2, 890, "レスポンスタイム：入力が終わってから、応答が始まるまで", 30, CYAN, r0)
    r1 = c.p(1, 0.5) if c.li >= 1 else 0
    if r1 > 0:
        d.line((x0, y + 110, x0, y + 170), fill=fade(PINK, r1), width=4)
        d.line((x1, y + 110, x1, y + 170), fill=fade(PINK, r1), width=4)
        arrow(d, x0, y + 140, x1, y + 140, fade(PINK, r1), 5, 18)
        text(d, W / 2, y + 185, "ターンアラウンドタイム", 34, PINK, r1)
        text(d, W / 2, 950, "ターンアラウンドタイム：頼んでから、結果が全部出るまで", 30, PINK, r1)
    r2 = c.p(2, 0.5) if c.li >= 2 else 0
    if r2 > 0:
        n = int(c.since(2) * 4)
        for k in range(min(n, 14)):
            d.rounded_rectangle((150 + k * 56, 1030, 196 + k * 56, 1076), radius=6, fill=fade(GREEN, r2))
        text(d, W / 2, 1120, "スループット：決まった時間に、こなせる仕事の量", 30, GREEN, r2)
    r3 = c.p(3, 0.5) if c.li >= 3 else 0
    if r3 > 0:
        box(d, 300, 1260, 460, 90, "レスポンス・ターンアラウンド", CYAN, r3, 28)
        text(d, 300, 1335, "短いほどよい", 30, CYAN, r3)
        box(d, 790, 1260, 420, 90, "スループット", GREEN, r3, 32)
        text(d, 790, 1335, "多いほどよい", 30, GREEN, r3)


def sc_standby(d, c, t):
    # 0〜1行目: ホットとコールド
    qa = phase(c, 0, 1)
    if qa > 0:
        for k, (nm, col, sub) in enumerate([("ホット", ORANGE, "待機系も動いている"), ("コールド", ICE, "待機系は止めてある")]):
            x = W / 2 - 240 + k * 480
            rr = c.p(k, 0.5) * qa if c.li >= k else 0
            if rr <= 0:
                continue
            on = c.li == k
            rbox(d, x - 220, 470, 440, 860, fade(mc.HOT if on else CELL, rr), fade(col, rr), 18, 7 if on else 4)
            neon(d, x, 545, nm, 60, col, rr)
            text(d, x, 615, "スタンバイ", 34, col, rr)
            server(d, x, 820, col, rr, "", t, on=(k == 0), w=170, h=230)
            text(d, x, 970, sub, 28, WHITE, rr)
            if k == 0:
                # すぐに切り替え
                text(d, x, 1060, "故障 → すぐ切り替え", 30, ORANGE, rr)
                d.rounded_rectangle((x - 170, 1110, x + 170, 1150), radius=10, fill=fade(ORANGE, rr))
                text(d, x, 1200, "数秒〜", 34, ORANGE, rr)
            else:
                text(d, x, 1060, "故障 → 起動から", 30, ICE, rr)
                prog = min(1.0, max(0.0, c.since(1)) / 6.0)
                d.rounded_rectangle((x - 170, 1110, x + 170, 1150), radius=10, outline=fade(ICE, rr), width=3)
                d.rounded_rectangle((x - 170, 1110, x - 170 + 340 * prog + 1, 1150), radius=10, fill=fade(ICE, rr))
                text(d, x, 1200, "時間がかかる", 34, ICE, rr)
            text(d, x, 1275, "早い・費用は高め" if k == 0 else "遅い・費用は安め", 26, MUTED, rr, False)
    # 2〜3行目: 冷えた心 → 熱いハート
    qb = phase(c, 2, 3)
    if qb > 0:
        hot = c.li >= 3
        warm = ease(c.since(3) / 0.8) if hot else 0
        col = mix(ICE, ORANGE, warm)
        beat = 1 + (0.15 * off_pulse(t) if hot else 0)
        heart(d, W / 2, 780, 13 * beat, col, qb)
        if not hot:
            for k in range(6):   # 氷のかけら
                a = k * math.pi / 3 + t * 0.4
                x, y = W / 2 + 280 * math.cos(a), 780 + 220 * math.sin(a)
                d.polygon([(x, y - 22), (x + 14, y), (x, y + 22), (x - 14, y)], fill=fade(ICE, qb))
            neon(d, W / 2, 1080, "コールド ＝ 間に合わない", 60, ICE, qb)
        else:
            for k in range(10):   # 炎
                ph = (t * 1.2 + k / 10) % 1
                x = W / 2 - 300 + k * 66
                d.ellipse((x - 18, 1000 - ph * 160 - 18, x + 18, 1000 - ph * 160 + 18), fill=fade(mix(ORANGE, PINK, ph), qb * (1 - ph)))
            neon(d, W / 2, 1080, "いつでもホット", 72, ORANGE, qb * warm)
        text(d, W / 2, 1200, "待機系がすぐ代われる ＝ ホットスタンバイ", 34, WHITE, qb * warm if hot else 0)
    # 4〜5行目: バッチ処理とリアルタイム処理
    qc = phase(c, 4, 5)
    if qc > 0:
        neon(d, W / 2, 500, "バッチ処理", 72, VIOLET, qc)
        n = min(8, int(max(0.0, c.since(4)) * 4))
        rbox(d, 140, 580, 520, 230, fade(CELL, qc), fade(VIOLET, qc), 14, 4)
        for k in range(n):
            paper(d, 200 + (k % 4) * 120, 640 + (k // 4) * 110, qc, WHITE, 0.8)
        text(d, 820, 660, "ためて", 34, VIOLET, qc)
        text(d, 820, 730, "まとめて処理", 34, VIOLET, qc)
        text(d, W / 2, 860, "例：1か月分の給与計算を、夜にまとめて", 30, MUTED, qc, False)
        if c.li >= 5:
            r = c.p(5, 0.5) * qc
            neon(d, W / 2, 980, "リアルタイム処理", 66, PINK, r)
            ph = (c.since(5) * 1.5) % 1
            monitor(d, 220, 1150, CYAN, r, "", 160, 110)
            server(d, 860, 1150, PINK, r, "", t, busy=True, w=150, h=180)
            x = 320 + 420 * ph
            paper(d, x, 1150, r, WHITE, 0.6)
            text(d, 540, 1080, "すぐ処理", 30, PINK, r)
            text(d, W / 2, 1320, "例：駅の改札・銀行の ATM（その場で処理）", 30, MUTED, r, False)


def sc_outro(d, c, t):
    q = c.p(0, 0.6) if c.li >= 0 else 0
    rows = ["主系", "待機系", "OS", "ネットワーク", "ハート"]
    rbox(d, 160, 480, 760, 560, fade(CELL, q), fade(GREEN, q), 18, 5)
    shout(d, W / 2, 540, "STATUS", 48, GREEN, q)
    for k, s in enumerate(rows):
        rr = ease((c.since(0) - k * 0.25) / 0.4) * q if c.li >= 0 else 0
        y = 630 + k * 85
        text(d, 260, y, s, 38, WHITE, rr, anchor="lm")
        d.ellipse((740, y - 18, 776, y + 18), fill=fade(GREEN, rr))
        text(d, 800, y, "OK", 36, GREEN, rr, anchor="lm")
    r = ease((c.since(0) - 1.4) / 0.5) * q if c.li >= 0 else 0
    pop = 1 + 0.1 * off_pulse(t)
    neon(d, W / 2, 1160, "システム", 90, GREEN, r)
    shout(d, W / 2, 1290, "ALL GREEN!", int(84 * pop), GREEN, r)


def sc_end(d, c, t):
    st = t - c.start
    q = ease((st - 0.3) / 1.0)
    duo(d, t, q, 580, 240)
    neon(d, W / 2, 860, "デュプレックス・ハート", 76, PINK, q)
    q = ease((st - 1.2) / 1.0)
    if q > 0:
        d.rounded_rectangle((180, 1120, W - 180, 1390), radius=28, fill=mix(DARK, (6, 4, 10), q))
    text(d, W / 2, 1180, "用語の復習は", 40, MUTED, q, False)
    text(d, W / 2, 1260, "fe.yogo-drill.com", 52, PINK, q)
    text(d, W / 2, 1335, "ip.yogo-drill.com", 52, PINK, q)


# 2回目のサビの最後の行の歌い出しから、何秒でギターソロの図に変えるか（行を歌い終わって少しあと）
_r = [r for r in mc.ROWS if r["block"] == 7][-1]
SOLO_AT = (_r["e"] - _r["s"]) + 1.5

PLAN = [
    (sc_server, "クライアントとサーバー", "CLIENT SERVER・THIN CLIENT", 1),
    (sc_p2p, "ピアツーピア", "PEER TO PEER・CENTRALIZED・DISTRIBUTED", 2),
    (sc_os, "OS の仕事", "TASK・MEMORY・KERNEL・DEVICE DRIVER", 3),
    (make_chorus(1), "デュプレックス・ハート", "DUPLEX SYSTEM・DUAL SYSTEM", 4),
    (sc_spool, "印刷を待たせない", "SPOOLING", 5),
    (sc_path, "絶対パスと相対パス", "ABSOLUTE PATH・RELATIVE PATH", 6),
    (sc_perf, "性能の指標", "RESPONSE・TURNAROUND・THROUGHPUT", 7),
    (make_chorus(2), "デュプレックス・ハート", "AVAILABILITY・FAILOVER", 8),
    (sc_standby, "ホットとコールド", "HOT STANDBY・COLD STANDBY・BATCH", 9),
    (make_chorus("final"), "デュプレックス・ハート", "OPEN SOURCE", 10),
    (sc_outro, "オールグリーン", "ALL GREEN", 11),
]
SCENES = mc.build_scenes(PLAN, sc_title, sc_end, end_gap=2.0)
# 場面ごとの背景の映像（SCENES と同じ順: タイトル・11のまとまり・締め）。Mixkit の Stock Video Free License の素材
CLIPS = [28900,   # タイトル（イントロ）: 暗闇のデジタル時計（真夜中。リールの1枚目なので暗い映像）
         1140,    # クライアントとサーバー: マイクロチップのアップ
         42041,   # ピアツーピア: 夜の街の空撮（光の道がつながる）
         38,      # OS: またたく光のぼけ（緑の文字の画面は、メーカーのロゴが映るのでやめた）
         44154,   # サビ: 赤い背景のロックのギタリストのシルエット
         40654,   # スプーリング: 夜の高層ビル（オフィスの映像は明るくて文字が読みにくいのでやめた）
         50267,   # 絶対パスと相対パス: 夕暮れの道（帰り道）
         28901,   # 性能の指標: 落ちていく砂時計（時計の針の映像は明るくて文字が読みにくいのでやめた）
         44166,   # サビ2・ギターソロ: ピンクの背景のギタリストのシルエット
         52312,   # ホットとコールド: 黒い背景の炎
         682,     # 最後のサビ: 手に持つ花火（フェスの観客の映像は明るくて文字が読みにくいのでやめた）
         1086,    # オールグリーン: 海の朝日（夜が明ける）
         4064]    # 締め: 夜空の花火
if SCENES[-1][0] >= mc.DUR - 0.5:
    SCENES.pop()
    CLIPS.pop()

if __name__ == "__main__":
    mc.main(SCENES, PLAN, OUT, ROOT / "notes" / "曲の動画" / "作業用", [BG_DIR / f"{n}.mp4" for n in CLIPS])
