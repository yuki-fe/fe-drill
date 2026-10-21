"""用語の「動く図」を作る。

static/figs/<用語id>.svg と、data/figs.json（図のタイトルと手順の文）を書き出す。
build.py が、用語ページの「図で見る」と、クイズの答えのあとの「図で見る」に使う。
図はステップに分かれていて、利用者が「前へ」「次へ」で切り替える（static/assets/fig.js）。
SVG の data-step を変えると、部品が CSS の transition でなめらかに動く。
data-step がないとき（画像として開いたときなど）は、最後のステップの図が出る。

    python make_figs.py
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "static" / "figs"
MOVE = 0.6   # ステップを切り替えたときに動く時間（秒）
W, H = 640, 350

FONT = "'BIZ UDPGothic','Hiragino Sans','Hiragino Kaku Gothic ProN','Yu Gothic','Meiryo',sans-serif"
COLORS = {
    "bg": ("#fbfcfa", "#1c2528"), "ink": ("#1d2a2e", "#e5ece9"), "muted": ("#5d6c6e", "#9aaaa9"),
    "line": ("#b9c6c0", "#4a5b5e"), "mark": ("#c0435a", "#ec7d91"), "soft": ("#f6dfe3", "#3d2229"),
    "ok": ("#2b7a68", "#6cc6ae"), "oksoft": ("#e3f2ee", "#1d3832"), "blue": ("#2f5f8a", "#8fb8e0"),
    "bluesoft": ("#e6eef6", "#1f2f40"), "warn": ("#b86a12", "#f0b45e"), "warnsoft": ("#fbecd7", "#3a2c17"),
}


def css_vars(i):
    return ";".join(f"--{k}:{v[i]}" for k, v in COLORS.items())


class Fig:
    def __init__(self, tid, title, steps):
        self.id, self.title, self.steps = tid, title, steps
        self.n = len(steps)
        self.parts = []      # (markup, states)
        self.static = []     # 動かない部品

    def fixed(self, markup):
        self.static.append(markup)

    def el(self, markup, *keys):
        """keys: (ステップ, x, y, 不透明度)。抜けたステップは前の値を引き継ぐ。最初のキーより前は、そのキーの値。"""
        keys = sorted(keys)
        states, k = [], 0
        cur = keys[0][1:]
        for i in range(self.n):
            while k < len(keys) and keys[k][0] <= i:
                cur = keys[k][1:]
                k += 1
            states.append(cur)
        self.parts.append((markup, states))

    def show(self, markup, frm, to=None, x=0, y=0):
        """frm のステップから（to のステップの前まで）表示する。"""
        keys = [(0, x, y, 0), (frm, x, y, 1)]
        if to is not None:
            keys.append((to, x, y, 0))
        self.el(markup, *keys)

    def svg(self):
        css, body = [], []
        for j, (markup, st) in enumerate(self.parts):
            last = st[-1]
            base = f"transform:translate({last[0]}px,{last[1]}px);opacity:{last[2]}"
            if len(set(st)) == 1:
                body.append(f'<g style="{base}">{markup}</g>')
                continue
            name = f"e{j}"
            css.append(f".fig-{self.id} .{name}{{{base};transition:transform {MOVE}s ease-in-out,opacity {MOVE}s ease-in-out}}")
            for i, (x, y, op) in enumerate(st):
                css.append(f'.fig-{self.id}[data-step="{i}"] .{name}{{transform:translate({x}px,{y}px);opacity:{op}}}')
            body.append(f'<g class="{name}">{markup}</g>')
        r = f".fig-{self.id}"
        head = (f"{r}{{{css_vars(0)}}}"
                f"@media (prefers-color-scheme:dark){{{r}{{{css_vars(1)}}}}}"
                f"{r} text{{font-family:{FONT};fill:var(--ink)}}"
                f"{r} .lbl{{font-size:17px;fill:var(--muted)}}{r} .big{{font-size:22px;font-weight:700}}"
                f"{r} .mono{{font-family:Consolas,'Courier New',monospace;font-weight:700}}"
                + "".join(f"{r} .f-{k}{{fill:var(--{k})}}{r} .s-{k}{{stroke:var(--{k})}}{r} .t-{k}{{fill:var(--{k})}}" for k in COLORS)
                + "".join(css)
                + f"@media (prefers-reduced-motion:reduce){{{r} g{{transition:none!important}}}}")
        defs = "".join(
            f'<marker id="ar-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0L10 5L0 10z" class="f-{k}"/></marker>' for k in ("ink", "mark", "ok", "blue", "muted", "warn"))
        steps = escape(json.dumps(self.steps, ensure_ascii=False), quote=True)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" class="fig-svg fig-{self.id}" viewBox="0 0 {W} {H}" role="img" '
                f'aria-label="{escape(self.title)}" data-steps="{steps}">'
                f"<style>{head}</style><defs>{defs}</defs>"
                f'<rect width="{W}" height="{H}" rx="18" class="f-bg"/>'
                + "".join(self.static) + "".join(body) + "</svg>\n")


# ---------- 部品 ----------

def box(x, y, w, h, text, fill="bluesoft", stroke="blue", size=22, tcls="", rx=8):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="f-{fill} s-{stroke}" stroke-width="2.5"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + size * 0.36}" text-anchor="middle" font-size="{size}" font-weight="700" class="{tcls}">{escape(text)}</text>')


def text(x, y, s, cls="lbl", anchor="middle", size=None):
    fs = f' font-size="{size}"' if size else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}"{fs}>{escape(s)}</text>'


def arrow(x1, y1, x2, y2, color="ink", dash=False, width=3):
    d = ' stroke-dasharray="8 6"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="s-{color}" stroke-width="{width}" marker-end="url(#ar-{color})"{d}/>'


def person(x, y, name, color="blue"):
    return (f'<circle cx="{x}" cy="{y}" r="17" class="f-{color}"/>'
            f'<path d="M{x - 28} {y + 58}q0-34 28-34t28 34z" class="f-{color}"/>'
            + text(x, y + 84, name, "lbl"))


def key(color, label=""):
    """原点に、横向きの鍵。"""
    return (f'<circle cx="12" cy="12" r="11" class="f-{color}"/><circle cx="12" cy="12" r="4.5" class="f-bg"/>'
            f'<rect x="21" y="9" width="32" height="6" rx="2" class="f-{color}"/>'
            f'<rect x="42" y="13" width="5" height="9" class="f-{color}"/><rect x="49" y="13" width="4" height="7" class="f-{color}"/>'
            + (text(30, 46, label, "lbl", size=14) if label else ""))


def doc(locked=False):
    """原点に、書類（鍵がかかっているときは南京錠つき）。"""
    s = ('<rect x="0" y="0" width="54" height="68" rx="5" class="f-bg s-ink" stroke-width="2.5"/>'
         + "".join(f'<line x1="10" y1="{y}" x2="44" y2="{y}" class="s-muted" stroke-width="3"/>' for y in (16, 28, 40, 52)))
    if locked:
        s += ('<rect x="0" y="0" width="54" height="68" rx="5" class="f-soft" opacity=".85"/>'
              '<path d="M18 30v-7a9 9 0 0 1 18 0v7" fill="none" class="s-mark" stroke-width="4"/>'
              '<rect x="13" y="29" width="28" height="22" rx="4" class="f-mark"/>')
    return s


FIGS = []


def fig(tid, title, steps):
    f = Fig(tid, title, steps)
    FIGS.append(f)
    return f


# ---------- 図 ----------

def stack():
    f = fig("0027", "スタックに入れて取り出す様子", [
        "空のスタック（上だけが開いている）",
        "push(A)：いちばん下に入る",
        "push(B)：A の上に積む",
        "push(C)：いちばん上に積む",
        "pop()：最後に入れた C が出る",
        "pop()：次は B。入れた順の逆に出る（LIFO）",
    ])
    f.fixed('<path d="M250 60V296H390V60" fill="none" class="s-ink" stroke-width="4" stroke-linejoin="round"/>')
    f.fixed(text(320, 326, "スタック", "lbl"))
    f.fixed(text(500, 74, "取り出したもの", "lbl"))
    for i, (name, step, out) in enumerate([("A", 1, None), ("B", 2, 5), ("C", 3, 4)]):
        y = 244 - i * 50
        keys = [(0, 0, -150 - y + 40, 0), (step, 0, 0, 1)]
        if out:
            keys.append((out, 190, 90 + 50 * (out - 4) - y, 1))
        f.el(box(262, y, 116, 44, name, "oksoft" if name != "C" else "warnsoft", "ok" if name != "C" else "warn"), *keys)
    f.show(arrow(320, 30, 320, 70, "ok"), 1, 4)
    f.show(text(360, 42, "push", "lbl", "start"), 1, 4)
    f.show(arrow(400, 110, 440, 100, "mark"), 4)
    f.show(text(410, 140, "pop", "lbl", "start"), 4)


def queue():
    f = fig("0028", "キューに入れて取り出す様子", [
        "空のキュー（後ろから入れて、前から出す）",
        "A を入れる（エンキュー）",
        "B を入れる。A の後ろに並ぶ",
        "C を入れる。いちばん後ろに並ぶ",
        "取り出す（デキュー）：最初に入れた A が出る",
        "次は B。入れた順に出る（FIFO）",
    ])
    f.fixed('<path d="M150 120H530M150 220H530" class="s-ink" stroke-width="4"/>')
    f.fixed(text(160, 250, "前（先頭）", "lbl", "start"))
    f.fixed(text(520, 250, "後ろ（末尾）", "lbl", "end"))
    f.fixed(text(70, 108, "出る", "lbl"))
    f.fixed(text(590, 108, "入る", "lbl"))
    f.fixed(arrow(140, 170, 40, 170, "mark"))
    f.fixed(arrow(620, 170, 545, 170, "ok"))
    slot = lambda k: 170 + k * 120
    for name, step in (("A", 1), ("B", 2), ("C", 3)):
        idx = "ABC".index(name)
        keys = [(0, 530 - slot(idx), 0, 0), (step, 0, 0, 1)]
        # 取り出すと、前に詰める。先頭から出たものは左下に置く
        for d in (4, 5):
            pos = idx - (d - 3)
            if pos >= 0:
                keys.append((d, slot(pos) - slot(idx), 0, 1))
            else:
                keys.append((d, 20 - slot(idx), 100, 1 if pos == -1 else 0))
        f.el(box(slot(idx), 146, 100, 48, name, "oksoft" if name != "A" else "warnsoft", "ok" if name != "A" else "warn"), *keys)


def complement():
    f = fig("0001", "2の補数で −5 を作る様子（4ビット）", [
        "5 を4ビットで書くと 0101",
        "すべてのビットを反転する → 1010",
        "1 を加える → 1011",
        "1011 が −5。5 と足すと 0000（あふれた桁は捨てる）",
    ])
    bx = lambda i: 250 + i * 64

    def bits(s, y, fill, stroke):
        return "".join(box(bx(i), y, 52, 52, c, fill, stroke, 28, "mono") for i, c in enumerate(s))

    f.fixed(text(200, 92, "5", "big", "end"))
    f.fixed(bits("0101", 60, "bluesoft", "blue"))
    f.show(text(200, 162, "反転", "lbl", "end") + bits("1010", 130, "warnsoft", "warn")
           + "".join(arrow(bx(i) + 26, 114, bx(i) + 26, 128, "warn", width=2) for i in range(4)), 1)
    f.show(text(200, 226, "+1", "big", "end") + box(bx(3), 196, 52, 44, "1", "bg", "line", 26, "mono"), 2)
    f.show('<line x1="230" y1="252" x2="510" y2="252" class="s-ink" stroke-width="3"/>'
           + text(200, 294, "−5", "big", "end") + bits("1011", 262, "soft", "mark"), 2)


def public_key():
    f = fig("0158", "公開鍵暗号方式で送る様子", [
        "受け取る B さんが、公開鍵と秘密鍵のペアを作る",
        "公開鍵だけを A さんに渡す（知られてもよい）",
        "A さんは、B さんの公開鍵で暗号化する",
        "暗号文を送る。途中で見られても読めない",
        "B さんは、自分の秘密鍵で復号する",
    ])
    f.fixed(person(90, 70, "送る A さん", "blue"))
    f.fixed(person(550, 70, "受け取る B さん", "ok"))
    f.fixed(text(320, 300, "インターネット", "lbl"))
    f.fixed('<line x1="170" y1="280" x2="470" y2="280" class="s-line" stroke-width="3" stroke-dasharray="6 6"/>')
    # 公開鍵（緑）: B → A
    f.el(key("ok", "公開鍵"), (0, 470, 190, 1), (1, 70, 190, 1))
    # 秘密鍵（赤）: B に残る
    f.el(key("mark", "秘密鍵"), (0, 560, 190, 1))
    f.el(doc(False), (0, 150, 180, 1), (2, 150, 180, 0))
    f.el(doc(True), (0, 150, 180, 0), (2, 150, 180, 1), (3, 455, 180, 1), (4, 455, 180, 0))
    f.el(doc(False), (0, 455, 180, 0), (4, 455, 180, 1))
    f.show(text(320, 256, "暗号文", "lbl"), 3, 4)
    f.show(arrow(215, 236, 440, 236, "ink", dash=True), 3, 4)


def deadlock():
    f = fig("0092", "デッドロックが起きる様子", [
        "処理1 が資源X を、処理2 が資源Y を使っている",
        "処理1 は、続けるために資源Y を待つ",
        "処理2 は、続けるために資源X を待つ",
        "お互いに相手を待ち、どちらも進めない（デッドロック）",
    ])
    f.fixed(box(70, 70, 150, 56, "処理1", "bluesoft", "blue"))
    f.fixed(box(420, 70, 150, 56, "処理2", "bluesoft", "blue"))
    f.fixed(box(70, 230, 150, 56, "資源X", "oksoft", "ok"))
    f.fixed(box(420, 230, 150, 56, "資源Y", "oksoft", "ok"))
    f.fixed(arrow(145, 228, 145, 130, "ok") + text(135, 184, "使用中", "lbl", "end"))
    f.fixed(arrow(495, 228, 495, 130, "ok") + text(505, 184, "使用中", "lbl", "start"))
    f.show(arrow(222, 112, 416, 238, "warn", dash=True) + text(360, 150, "待つ", "lbl", "start"), 1)
    f.show(arrow(418, 112, 224, 238, "warn", dash=True) + text(280, 150, "待つ", "lbl", "end"), 2)
    f.show('<rect x="56" y="54" width="528" height="248" rx="16" fill="none" class="s-mark" stroke-width="4"/>'
           + text(320, 40, "止まったまま", "big", size=22), 3)


def critical_path():
    f = fig("0238", "クリティカルパスの求め方", [
        "作業をつないだ図（数字は日数）",
        "A → C → E の経路：3 + 2 + 2 = 7日",
        "B → D → E の経路：5 + 4 + 2 = 11日",
        "いちばん長い B → D → E がクリティカルパス（全体は11日）",
    ])
    node = {1: (70, 170), 2: (240, 80), 3: (240, 260), 4: (420, 170), 5: (580, 170)}
    edges = {"A": (1, 2, 3), "B": (1, 3, 5), "C": (2, 4, 2), "D": (3, 4, 4), "E": (4, 5, 2)}

    def edge(name, color, width):
        a, b, d = edges[name]
        (x1, y1), (x2, y2) = node[a], node[b]
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** .5
        ux, uy = dx / L, dy / L
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # 日数の文字は、図の外側（中心から遠いほう）に置く
        nx, ny = -uy, ux
        if (mx + nx * 30 - 325) ** 2 + (my + ny * 30 - 170) ** 2 < (mx - nx * 30 - 325) ** 2 + (my - ny * 30 - 170) ** 2:
            nx, ny = -nx, -ny
        if abs(dy) < 1:
            nx, ny = 0, -1
        return (arrow(x1 + ux * 28, y1 + uy * 28, x2 - ux * 30, y2 - uy * 30, color, width=width)
                + f'<text x="{mx + nx * 30}" y="{my + ny * 30 + 7}" text-anchor="middle" font-size="19" font-weight="700" class="t-{color}">{name} {d}日</text>')

    for name in edges:
        f.fixed(edge(name, "muted", 3))
    for k, (x, y) in node.items():
        f.fixed(f'<circle cx="{x}" cy="{y}" r="26" class="f-bg s-ink" stroke-width="3"/>' + text(x, y + 8, str(k), "big"))
    f.show("".join(edge(n, "blue", 5) for n in "ACE") + text(320, 318, "A→C→E = 7日", "big"), 1, 2)
    f.show("".join(edge(n, "mark", 5) for n in "BDE") + text(320, 318, "B→D→E = 11日", "big"), 2)


def bubble():
    f = fig("0036", "バブルソートの1周目", [
        "隣どうしを比べる：5 と 3",
        "左が大きいので入れ替える → 3, 5",
        "8 と 1 も入れ替える → 1 が左へ",
        "1周目で、いちばん大きい 8 が右端に決まる",
        "これをくり返すと、小さい順に並ぶ",
    ])
    x = lambda i: 150 + i * 95
    # 値ごとの、各ステップでの位置（番号）
    where = {5: [0, 1, 1, 1, 2], 3: [1, 0, 0, 0, 1], 8: [2, 2, 3, 3, 3], 1: [3, 3, 2, 2, 0]}
    for v, idx in where.items():
        f.el(box(0, 140, 80, 80, str(v), "bluesoft", "blue", 34, "mono"), *[(k, x(i), 0, 1) for k, i in enumerate(idx)])
    f.show('<rect x="142" y="128" width="191" height="104" rx="12" fill="none" class="s-warn" stroke-width="4"/>', 0, 2)
    f.show('<rect x="332" y="128" width="191" height="104" rx="12" fill="none" class="s-warn" stroke-width="4"/>', 2, 3)
    f.show('<rect x="427" y="128" width="96" height="104" rx="12" fill="none" class="s-ok" stroke-width="5"/>' + text(475, 270, "確定", "lbl"), 3, 4)
    f.show('<rect x="142" y="128" width="381" height="104" rx="12" fill="none" class="s-ok" stroke-width="5"/>' + text(332, 270, "小さい順", "lbl"), 4)
    f.fixed(text(320, 80, "隣どうしを比べて、入れ替えていく", "lbl"))


def bst():
    f = fig("0030", "二分探索木で 6 を探す様子", [
        "小さい値は左、大きい値は右に並ぶ二分木",
        "6 は 8 より小さい → 左へ",
        "6 は 3 より大きい → 右へ",
        "6 が見つかった（3回の比較）",
    ])
    nodes = {8: (320, 70), 3: (190, 160), 10: (450, 160), 1: (120, 250), 6: (260, 250), 14: (520, 250)}
    for a, b in ((8, 3), (8, 10), (3, 1), (3, 6), (10, 14)):
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        f.fixed(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="s-line" stroke-width="3"/>')
    for v, (x, y) in nodes.items():
        f.fixed(f'<circle cx="{x}" cy="{y}" r="28" class="f-bluesoft s-blue" stroke-width="3"/>' + text(x, y + 9, str(v), "big"))
    for step, v in ((1, 8), (2, 3), (3, 6)):
        x, y = nodes[v]
        col = "ok" if v == 6 else "warn"
        f.show(f'<circle cx="{x}" cy="{y}" r="36" fill="none" class="s-{col}" stroke-width="5"/>', step)
    f.show(text(380, 110, "6 < 8", "lbl", "start"), 1, 2)
    f.show(text(120, 205, "6 > 3", "lbl", "start"), 2, 3)
    f.show(text(320, 310, "見つかった！", "big"), 3)


def hashing():
    f = fig("0035", "ハッシュ法でしまう場所を決める様子", [
        "ハッシュ関数：しまう場所 = キー ÷ 7 の余り",
        "15 ÷ 7 の余りは 1 → 1番にしまう",
        "22 ÷ 7 の余りも 1 → 同じ場所になる",
        "この重なりを衝突（シノニム）という",
    ])
    for i in range(7):
        f.fixed(box(380, 30 + i * 40, 60, 34, str(i), "bg", "line", 18, "mono"))
    f.fixed(text(410, 22, "表", "lbl"))
    f.show(box(70, 100, 110, 50, "15", "warnsoft", "warn", 26, "mono"), 1)
    f.show(arrow(185, 125, 372, 87, "warn") + text(250, 95, "15 % 7 = 1", "lbl"), 1)
    f.show(box(450, 72, 90, 34, "15", "oksoft", "ok", 18, "mono"), 1)
    f.show(box(70, 200, 110, 50, "22", "warnsoft", "warn", 26, "mono"), 2)
    f.show(arrow(185, 225, 372, 92, "mark") + text(250, 262, "22 % 7 = 1", "lbl"), 2)
    f.show(box(550, 72, 80, 34, "22", "soft", "mark", 18, "mono"), 3)
    f.show(text(510, 160, "衝突！", "big") + text(510, 190, "（シノニム）", "lbl"), 3)


def cache():
    f = fig("0053", "キャッシュメモリの働き", [
        "CPU と主記憶のあいだに、速いキャッシュ",
        "初めてのデータは、遅い主記憶から読む",
        "読んだデータを、キャッシュにも置いておく",
        "2回目からはキャッシュから速く読める（ヒット）",
    ])
    f.fixed(box(40, 120, 120, 80, "CPU", "warnsoft", "warn", 26))
    f.fixed(box(250, 120, 140, 80, "キャッシュ", "oksoft", "ok", 22) + text(320, 225, "速い・小さい", "lbl"))
    f.fixed(box(480, 120, 130, 80, "主記憶", "bluesoft", "blue", 22) + text(545, 225, "遅い・大きい", "lbl"))
    f.show(arrow(545, 115, 100, 115, "blue", dash=True) + text(320, 102, "遅い道", "lbl"), 1, 3)
    f.el(box(0, 0, 50, 34, "A", "bg", "ink", 18), (0, 520, 255, 0), (1, 520, 255, 1), (2, 295, 255, 1))
    f.show(arrow(245, 175, 166, 175, "ok", width=5) + text(205, 285, "ヒット！", "big"), 3)


def raid1():
    f = fig("0066", "RAID1（ミラーリング）の様子", [
        "2台のディスクに、同じデータを書き込む",
        "データ A・B・C が、両方に入っている",
        "1台が壊れても、もう1台にデータが残る",
    ])
    for k, x in enumerate((170, 390)):
        f.fixed(f'<rect x="{x}" y="60" width="120" height="200" rx="14" class="f-bluesoft s-blue" stroke-width="3"/>' + text(x + 60, 285, f"ディスク{k + 1}", "lbl"))
        for j, c in enumerate("ABC"):
            f.show(box(x + 20, 80 + j * 55, 80, 40, c, "oksoft", "ok", 20), 1 if j else 0)
    f.show('<path d="M398 68L502 252M502 68L398 252" class="s-mark" stroke-width="8"/>' + text(450, 315, "故障", "big"), 2)
    f.show(text(230, 315, "データは無事", "big"), 2)


def raid5():
    f = fig("0067", "RAID5（パリティで復元）の様子", [
        "データとパリティ（復元用の情報）を、3台以上に分けて書く",
        "パリティは、ディスクごとに場所をずらす",
        "1台が壊れても、残りのデータとパリティから復元できる",
    ])
    lay = [["A1", "A2", "P"], ["B1", "P", "B2"], ["P", "C1", "C2"]]
    for k in range(3):
        x = 130 + k * 140
        f.fixed(f'<rect x="{x}" y="50" width="110" height="200" rx="14" class="f-bluesoft s-blue" stroke-width="3"/>' + text(x + 55, 275, f"ディスク{k + 1}", "lbl"))
        for j in range(3):
            s = lay[j][k]
            fill, st = ("soft", "mark") if s == "P" else ("oksoft", "ok")
            f.show(box(x + 15, 68 + j * 60, 80, 44, s, fill, st, 20, "mono"), 0 if s != "P" else 1)
    f.show('<path d="M278 58L382 242M382 58L278 242" class="s-mark" stroke-width="8"/>', 2)
    f.show(text(330, 315, "A2・C1 は、ほかのディスクから計算して復元", "lbl"), 2)


def availability():
    f = fig("0068", "稼働率の求め方", [
        "動いている時間（MTBF）と、修理の時間（MTTR）がくり返す",
        "稼働率 ＝ MTBF ÷（MTBF ＋ MTTR）",
        "例：MTBF 90時間、MTTR 10時間 → 90 ÷ 100 ＝ 0.9",
    ])
    segs = [(60, 230, "ok", "MTBF"), (230, 280, "mark", "MTTR"), (280, 450, "ok", "MTBF"), (450, 500, "mark", "MTTR"), (500, 580, "ok", "")]
    for a, b, c, n in segs:
        f.fixed(f'<rect x="{a}" y="70" width="{b - a - 3}" height="44" rx="6" class="f-{c}"/>' + (text((a + b) / 2, 140, n, "lbl") if n else ""))
    f.fixed(text(320, 45, "時間 →", "lbl"))
    f.show(text(320, 210, "稼働率 ＝ MTBF ÷（MTBF ＋ MTTR）", "big"), 1)
    f.show(text(320, 265, "90 ÷（90 ＋ 10）＝ 0.9（90%）", "big"), 2)


def lru():
    f = fig("0090", "LRU でページを置き換える様子", [
        "主記憶の枠は3つ。A・B・C の順に読み込む",
        "A をもう一度使う（A が最近使ったものになる）",
        "D が必要。空きがないので、置き換える",
        "いちばん長く使われていない B を追い出して D を入れる",
    ])
    for k in range(3):
        f.fixed(f'<rect x="{180 + k * 110}" y="110" width="90" height="90" rx="12" class="f-bg s-line" stroke-width="3"/>')
    f.fixed(text(110, 160, "枠", "lbl"))
    f.el(box(0, 0, 70, 70, "A", "oksoft", "ok", 28), (0, 190, 120, 1))
    f.el(box(0, 0, 70, 70, "B", "oksoft", "ok", 28), (0, 300, 120, 1), (3, 300, 260, 0))
    f.el(box(0, 0, 70, 70, "C", "oksoft", "ok", 28), (0, 410, 120, 1))
    f.el(box(0, 0, 70, 70, "D", "warnsoft", "warn", 28), (0, 530, 30, 0), (2, 530, 30, 1), (3, 300, 120, 1))
    f.show(text(225, 225, "使った！", "lbl"), 1, 2)
    f.show(text(335, 235, "いちばん古い", "lbl"), 2, 3)
    f.show(text(320, 300, "最近使われていないものから追い出す", "big"), 3)


def normalize():
    f = fig("0104", "正規化で表を分ける様子", [
        "注文の表に、顧客名が何度も出てくる（重複）",
        "重複を、別の表（顧客の表）に分ける",
        "顧客名を変えるときも、1か所直すだけでよい",
    ])
    rows = [("1", "C1", "田中"), ("2", "C2", "佐藤"), ("3", "C1", "田中")]
    for k, (a, b, c) in enumerate(rows):
        y = 70 + k * 46
        f.el(box(0, 0, 60, 40, a, "bg", "line", 18) + box(64, 0, 70, 40, b, "bg", "line", 18), (0, 60, y, 1))
        f.el(box(0, 0, 80, 40, c, "warnsoft" if c == "田中" else "bg", "warn" if c == "田中" else "line", 18), (0, 198, y, 1), (1, 198, y, 0))
    f.fixed(text(160, 52, "注文の表", "lbl"))
    f.show(text(470, 52, "顧客の表", "lbl") + box(400, 70, 70, 40, "C1", "bg", "line", 18) + box(474, 70, 80, 40, "田中", "oksoft", "ok", 18)
           + box(400, 116, 70, 40, "C2", "bg", "line", 18) + box(474, 116, 80, 40, "佐藤", "oksoft", "ok", 18), 1)
    f.show(arrow(300, 150, 392, 110, "ok"), 1)
    f.show(text(320, 290, "重複をなくして、矛盾を防ぐ", "big"), 2)


def dns():
    f = fig("0138", "DNS で名前から IP アドレスを調べる様子", [
        "ブラウザに www.example.com と入力する",
        "DNS サーバに「この名前の IP アドレスは？」と聞く",
        "DNS サーバが IP アドレスを答える",
        "その IP アドレスの Web サーバにつなぐ",
    ])
    f.fixed(box(40, 120, 120, 70, "PC", "bluesoft", "blue", 24))
    f.fixed(box(250, 20, 150, 70, "DNS サーバ", "oksoft", "ok", 20))
    f.fixed(box(480, 200, 130, 70, "Web サーバ", "warnsoft", "warn", 20))
    f.fixed(text(545, 295, "203.0.113.10", "lbl"))
    f.show(text(100, 220, "www.example.com", "lbl"), 0)
    f.show(arrow(160, 135, 245, 75, "blue") + text(150, 85, "IP は？", "lbl", "end"), 1)
    f.show(arrow(300, 95, 165, 160, "ok") + text(300, 140, "203.0.113.10", "lbl", "start"), 2)
    f.show(arrow(165, 175, 475, 230, "warn", width=5), 3)


def common_key():
    f = fig("0157", "共通鍵暗号方式で送る様子", [
        "送る人と受け取る人が、同じ鍵を持つ",
        "その鍵で暗号化して送る",
        "受け取った人は、同じ鍵で復号する",
        "鍵を安全に渡すのがむずかしい（鍵配送問題）",
    ])
    f.fixed(person(90, 70, "送る A さん", "blue"))
    f.fixed(person(550, 70, "受け取る B さん", "ok"))
    f.el(key("warn", "共通鍵"), (0, 70, 190, 1))
    f.el(key("warn", "共通鍵"), (0, 520, 190, 1))
    f.el(doc(False), (0, 150, 180, 1), (1, 150, 180, 0))
    f.el(doc(True), (0, 150, 180, 0), (1, 150, 180, 1), (2, 440, 180, 1), (3, 440, 180, 0))
    f.el(doc(False), (0, 440, 180, 0), (2, 440, 180, 0), (3, 440, 180, 1))
    f.show(arrow(215, 236, 425, 236, "ink", dash=True), 1, 3)
    f.show(text(320, 310, "同じ鍵を、どうやって安全に渡す？", "big"), 3)


def signature():
    f = fig("0160", "デジタル署名のしくみ", [
        "送る人は、文書のハッシュ値を自分の秘密鍵で暗号化（署名）",
        "文書と署名を一緒に送る",
        "受け取った人は、送る人の公開鍵で署名を復号する",
        "文書のハッシュ値と一致すれば、本人で改ざんなし",
    ])
    f.fixed(person(80, 60, "送る人", "blue"))
    f.fixed(person(560, 60, "受け取る人", "ok"))
    f.el(doc(False), (0, 140, 170, 1), (1, 420, 170, 1))
    f.el('<circle cx="22" cy="22" r="22" class="f-mark"/>' + text(22, 29, "署", "lbl", size=18).replace('class="lbl"', 'class="lbl" style="fill:#fff"'),
         (0, 210, 160, 1), (1, 490, 160, 1))
    f.show(key("mark", "秘密鍵"), 0, 1, 60, 250)
    f.show(arrow(215, 260, 410, 260, "ink", dash=True), 1, 2)
    f.show(key("ok", "公開鍵"), 2, None, 500, 250)
    f.show(text(300, 300, "ハッシュ値が一致", "big") + text(300, 330, "→ 本人が送った・改ざんなし", "lbl"), 3)


def dmz():
    f = fig("0184", "DMZ の置き場所", [
        "インターネットと社内の間に、ファイアウォールを置く",
        "公開する Web サーバは、間の区域（DMZ）に置く",
        "外から DMZ の Web サーバには入れる",
        "外から社内のネットワークには入れない",
    ])
    f.fixed(box(15, 120, 135, 70, "インターネット", "bluesoft", "blue", 16))
    f.fixed('<rect x="170" y="70" width="18" height="180" class="f-mark"/><rect x="420" y="70" width="18" height="180" class="f-mark"/>')
    f.fixed(text(179, 280, "FW", "lbl") + text(429, 280, "FW", "lbl"))
    f.show('<rect x="205" y="60" width="200" height="200" rx="16" class="f-warnsoft s-warn" stroke-width="3"/>' + text(305, 90, "DMZ", "big")
           + box(245, 130, 120, 60, "Web サーバ", "bg", "warn", 18), 1)
    f.fixed('<rect x="455" y="60" width="170" height="200" rx="16" class="f-oksoft s-ok" stroke-width="3"/>' + text(540, 90, "社内", "big")
            + box(480, 130, 120, 60, "社内の PC", "bg", "ok", 18))
    f.show(arrow(150, 150, 240, 160, "ok", width=5) + text(305, 225, "入れる", "big"), 2)
    f.show(arrow(150, 178, 412, 176, "mark", dash=True) + '<text x="429" y="188" text-anchor="middle" class="big t-mark" font-size="40">×</text>' + text(540, 225, "入れない", "big"), 3)


def sqli():
    f = fig("0167", "SQLインジェクションのしくみ", [
        "ログインの入力欄に、ふつうは名前を入れる",
        "攻撃者は「' OR '1'='1」のような文字を入れる",
        "SQL 文の条件がいつも正しくなり、全員のデータが出てしまう",
        "対策：プレースホルダで、入力を文字として扱う",
    ])
    f.fixed(text(40, 50, "名前：", "lbl", "start"))
    f.fixed('<rect x="110" y="25" width="300" height="40" rx="6" class="f-bg s-line" stroke-width="2"/>')
    f.show(text(122, 52, "tanaka", "lbl", "start"), 0, 1)
    f.show(text(122, 52, "' OR '1'='1", "big", "start").replace('class="big"', 'class="big mono"'), 1)
    f.fixed(text(40, 120, "SQL 文：", "lbl", "start"))
    f.show(text(40, 160, "SELECT * FROM 会員 WHERE 名前 = 'tanaka'", "lbl", "start").replace('class="lbl"', 'class="lbl mono"'), 0, 1)
    f.show(text(40, 160, "SELECT * FROM 会員 WHERE 名前 = '' OR '1'='1'", "lbl", "start").replace('class="lbl"', 'class="lbl mono"'), 1)
    f.show(text(320, 220, "条件がいつも正しい → 全員のデータが出る", "big"), 2, 3)
    f.show(text(320, 220, "プレースホルダ：入力はただの文字として扱う", "big") + text(320, 260, "→ SQL 文として動かない", "lbl"), 3)


for make in (stack, queue, complement, public_key, deadlock, critical_path,
             bubble, bst, hashing, cache, raid1, raid5, availability, lru, normalize, dns, common_key, signature, dmz, sqli):
    make()

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    for f in FIGS:
        (OUT / f"{f.id}.svg").write_text(f.svg(), encoding="utf-8")
        meta[f.id] = {"title": f.title, "steps": f.steps}
    (ROOT / "data" / "figs.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"図を {len(FIGS)} 個作りました: {OUT}")
