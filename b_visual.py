"""科目Bのリール動画の「動きの図」。コードの下に、プログラムの動きを図で見せる。

  ・配列: 値の入った箱を横に並べる（下に番号）
  ・番号に使う変数（i・j・low・mid など。コードの [ ] の中に出てくる変数）: 箱の下の色つきの矢印。次の箱へすべって動く
  ・代入（tmp ← data[j] など）: 値が、元の箱やカードから、行き先へ飛んでいく
  ・比べる行（if・while の中の data[j] など）: 比べている箱をオレンジで囲む
  ・ふつうの変数: カード。変わった値は緑
  ・再帰: 呼び出しの深さを、積み重なる箱で見せる

make_b_media.py の make_reel から使う（VISUAL が True のとき）。
"""
import math
import re

from PIL import Image, ImageDraw

import make_b_media as mb
from make_b_media import BG, HL, INK, LINE, MARK, MARK_SOFT, MUTED, OK, OK_SOFT, PAPER, W, H, font, fmt, pill, wrap

PTR_COLORS = ["#2d68a8", "#c0435a", "#2b7a68", "#9a4a1c", "#5a3fb0"]
CMP = "#e0782b"          # 比べている箱のふち
FLY = 0.75               # 1行の時間のうち、値が飛んでいく割合
IDENT = r"[A-Za-z_]\w*"


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def is_undef(v):
    return isinstance(v, dict) and v.get("undef")


GLOBALS = set()   # 図に入れる大域変数の名前（コードに「大域:」と書いてあるもの。Layout が決める）


def allvars(step):
    """その時点の変数（コードで「大域:」と宣言した変数も入れる。同じ名前なら関数の中の変数を優先）。"""
    if not step:
        return {}
    g = {k: v for k, v in (step.get("globals") or {}).items() if k in GLOBALS}
    return {**g, **(step.get("vars") or {})}


def ev(expr, vars_):
    """配列の [ ] の中の式（j + 1、(low + high) ÷ 2 など）を、変数の値で計算する。できなければ None。"""
    e = expr.replace("÷", "//").replace("×", "*").replace("mod", "%")
    ok = True

    def sub(m):
        nonlocal ok
        v = vars_.get(m.group(0))
        if isinstance(v, bool) or not isinstance(v, int):
            ok = False
            return "0"
        return str(v)
    e = re.sub(IDENT, sub, e)
    if not ok or not re.fullmatch(r"[\d\s+\-*/%()]+", e):
        return None
    try:
        return int(eval(e, {"__builtins__": {}}, {}))
    except Exception:
        return None


def refs(text, vars_):
    """行の中の 配列[式] を、(配列の名前, 番号) にして返す。"""
    out = []
    for m in re.finditer(rf"({IDENT})\[([^\[\]]+)\]", text):
        name = m.group(1)
        if isinstance(vars_.get(name), list):
            k = ev(m.group(2), vars_)
            if k is not None and 1 <= k <= len(vars_[name]):
                out.append((name, k))
    return out


def assignment(text, vars_):
    """代入の行なら (行き先, [元]) を返す。行き先・元は ("arr", 名前, 番号) か ("var", 名前)。"""
    m = re.match(rf"\s*(?:[^:：←]+[:：]\s*)?({IDENT})(?:\[([^\]]+)\])?\s*←\s*(.+)$", text)
    if not m:
        return None
    name, idx, rhs = m.group(1), m.group(2), m.group(3)
    if idx is not None:
        k = ev(idx, vars_)
        if k is None:
            return None
        dest = ("arr", name, k)
    else:
        dest = ("var", name)
    srcs = [("arr", a, k) for a, k in refs(rhs, vars_)]
    rest = re.sub(rf"{IDENT}\[[^\]]+\]", " ", rhs)
    for v in re.findall(IDENT, rest):
        if v in vars_ and not isinstance(vars_[v], list) and ("var", v) not in srcs:
            srcs.append(("var", v))
    return dest, srcs


class Layout:
    """1本の動画の中で変わらない、図の置き場所。"""

    def __init__(self, it, steps):
        self.it = it
        code = it["code"]
        GLOBALS.clear()
        for line in code:
            m = re.match(r"\s*大域\s*[:：]\s*[^:：]*[:：]\s*(.+)$", line)
            if m:
                GLOBALS.update(re.findall(rf"({IDENT})\s*(?:←[^,]*)?(?:,|$)", m.group(1)))
        self.code_y = 268
        self.code_size = mb.code_size(code, W - 120 - 96, 470)
        lh = int(self.code_size * 1.62)
        self.code_end = self.code_y + lh * len(code) + 36
        # 出てくる変数を集める（配列と、ふつうの変数）
        arrays, scalars = [], []
        for s in steps:
            for k, v in allvars(s).items():
                if isinstance(v, list) and all(not isinstance(e, list) for e in v):
                    if k not in arrays:
                        arrays.append(k)
                elif not isinstance(v, list) and k not in scalars:
                    scalars.append(k)
        self.arrays = arrays[:2]
        self.max_len = {a: max(len(allvars(s).get(a) or []) for s in steps) for a in self.arrays}
        # 番号に使う変数（コードの [ ] の中に出てくる変数）
        text = "\n".join(code)
        ptr = []
        for m in re.finditer(rf"({IDENT})\[([^\[\]]+)\]", text):
            for v in re.findall(IDENT, m.group(2)):
                if v in scalars and v not in ptr:
                    ptr.append(v)
        # 番号に使う変数に代入する式に出てくる変数も、番号として扱う（mid ← (low + high) ÷ 2 の low・high）
        for line in code:
            m = re.match(rf"\s*(?:[^:：←]+[:：]\s*)?({IDENT})\s*←\s*(.+)$", line)
            if m and m.group(1) in ptr:
                for v in re.findall(IDENT, re.sub(rf"{IDENT}\[[^\]]+\]", " ", m.group(2))):
                    if v in scalars and v not in ptr:
                        ptr.append(v)
        self.ptrs = ptr[:4]
        self.scalars = scalars[:9]
        self.depth = max(s.get("depth", 1) for s in steps)
        # 縦の位置（図の部品を大きめにして、余った高さは部品の間に分ける）
        n = len(self.scalars)
        self.cols = n if 0 < n <= 4 else 3
        rows = math.ceil(n / self.cols) if n else 0
        top, bottom = self.code_end + 40, 1465
        # 入りきらないときは、箱・カード・矢印の間を小さくしていく
        for self.box_h, self.card_h, self.ptr_row in ((150, 132, 58), (130, 112, 50), (110, 96, 44), (96, 84, 40)):
            arr_h = [44 + self.box_h + 40 + self.ptr_row * max(1, len(self.ptrs)) for _ in self.arrays]
            need = 60 + sum(arr_h) + rows * (self.card_h + 18)
            if top + need <= bottom:
                break
        gap = max(16, min(70, (bottom - top - need) / (len(self.arrays) + 2)))
        y = top
        self.panel_y = y
        y += 60 + gap
        self.arr_y = {}
        for a, h in zip(self.arrays, arr_h):
            self.arr_y[a] = y + 44
            y += h + gap
        self.card_y = y
        self.panel_end = y + rows * (self.card_h + 18)

    def box(self, a, k):
        """配列 a の k 番目（1から）の箱の (x, y, w, h)。"""
        n = max(1, self.max_len[a])
        bw = min(160, (W - 160) // n)
        x0 = 80 + ((W - 160) - bw * n) / 2
        return x0 + (k - 1) * bw, self.arr_y[a], bw, self.box_h

    def card(self, name):
        i = self.scalars.index(name)
        gap = 16
        cw = (W - 120 - gap * (self.cols - 1)) / self.cols
        r, c = divmod(i, self.cols)
        return 60 + c * (cw + gap), self.card_y + r * (self.card_h + gap), cw, self.card_h

    def center(self, ref):
        if ref[0] == "arr" and ref[1] in self.arr_y:
            x, y, w, h = self.box(ref[1], ref[2])
            return x + w / 2, y + h / 2
        if ref[0] == "var" and ref[1] in self.scalars:
            x, y, w, h = self.card(ref[1])
            return x + w / 2, y + h * 0.62
        return None


def draw_frame(L, it, no, step, prev, idx, total, fn, args, u=1.0, cur_pos=None):
    """1コマ。u は、この行の動きの進み具合（0〜1）。"""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    label = f"科目B トレース No.{no}" if it["kind"] == "trace" else "科目B アルゴリズム図鑑"
    pill(d, 60, 90, label, MARK, 32)
    tf = font(52, True)
    d.text((60, 172), wrap(it["title"], tf, W - 160)[0], font=tf, fill=INK)
    cur = step["line"] if step else None
    mb.draw_code(d, it["code"], 60, L.code_y, W - 120, cur=cur, mark=it.get("line"), size=L.code_size, cur_pos=cur_pos)

    vars_ = allvars(step)
    pv = allvars(prev)
    same = prev is not None and step is not None and prev["fn"] == step["fn"] and prev["depth"] == step["depth"]
    if not same:
        pv = {}
    # 前の行の動き（代入なら、値が飛んでいく）
    fly = None
    if same and prev.get("line"):
        a = assignment(it["code"][prev["line"] - 1], pv)
        if a:
            fly = a
    hold = {}   # 値が届くまで、行き先は前の値を見せる
    if fly and u < FLY:
        dest = fly[0]
        if dest[0] == "arr" and isinstance(pv.get(dest[1]), list) and dest[2] <= len(pv[dest[1]]):
            hold[dest] = pv[dest[1]][dest[2] - 1]
        elif dest[0] == "var" and dest[1] in pv:
            hold[dest] = pv[dest[1]]
    # 比べている箱（今の行が if・while のとき）
    cmp = set()
    if cur and re.search(r"\b(if|while|elseif)\b", it["code"][cur - 1]):
        cmp = {("arr", a, k) for a, k in refs(it["code"][cur - 1], vars_)}

    # 図の見出し
    d.text((60, L.panel_y), "動きの図", font=font(34, True), fill=MUTED)
    d.line((60 + font(34, True).getlength("動きの図") + 16, L.panel_y + 22, W - 60, L.panel_y + 22), fill=LINE, width=2)

    vf = font(int(L.box_h * 0.43), True, mono=True)
    for a in L.arrays:
        arr = vars_.get(a) if isinstance(vars_.get(a), list) else []
        parr = pv.get(a) if isinstance(pv.get(a), list) else None
        d.text((60, L.arr_y[a] - 44), a, font=font(36, True, mono=True), fill=MUTED)
        for k in range(1, L.max_len[a] + 1):
            x, y, w, h = L.box(a, k)
            if k > len(arr):
                d.rounded_rectangle((x + 4, y, x + w - 4, y + h), radius=12, outline=LINE, width=2)
                continue
            val = hold.get(("arr", a, k), arr[k - 1])
            changed = parr is not None and k <= len(parr) and fmt(parr[k - 1]) != fmt(arr[k - 1]) and ("arr", a, k) not in hold
            fill = OK_SOFT if changed else PAPER
            outline, wd = (OK, 4) if changed else (LINE, 3)
            if ("arr", a, k) in cmp:
                outline, wd = CMP, 6
            d.rounded_rectangle((x + 4, y, x + w - 4, y + h), radius=12, fill=fill, outline=outline, width=wd)
            t = fmt(val)
            f = vf if vf.getlength(t) < w - 24 else font(40, True, mono=True)
            d.text((x + (w - f.getlength(t)) / 2, y + (h - f.size) / 2 - 4), t, font=f, fill=OK if changed else INK)
            fi = font(28, mono=True)
            d.text((x + (w - fi.getlength(str(k))) / 2, y + h + 6), str(k), font=fi, fill=MUTED)
        # 番号の矢印（前の値から今の値へ、すべって動く）
        for r, p in enumerate(L.ptrs):
            v = vars_.get(p)
            if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= L.max_len[a]):
                continue
            ov = pv.get(p) if isinstance(pv.get(p), int) and 1 <= pv.get(p) <= L.max_len[a] else v
            pos = ov + (v - ov) * ease(u / 0.8)
            x, y, w, h = L.box(a, 1)
            cx = x + w / 2 + (pos - 1) * w
            ty = y + h + 44 + r * L.ptr_row
            col = PTR_COLORS[r % len(PTR_COLORS)]
            d.polygon([(cx, ty), (cx - 20, ty + 30), (cx + 20, ty + 30)], fill=col)
            lab = f"{p}={v}"
            lf = font(34, True, mono=True)
            d.text((cx + 26, ty - 4), lab, font=lf, fill=col)

    # ふつうの変数のカード
    for name in L.scalars:
        x, y, w, h = L.card(name)
        v = vars_.get(name, {"undef": True})
        shown = hold.get(("var", name), v)
        changed = same and name in pv and not is_undef(v) and fmt(pv[name]) != fmt(v) and ("var", name) not in hold
        is_ptr = name in L.ptrs and L.arrays
        d.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=OK_SOFT if changed else PAPER, outline=OK if changed else LINE, width=3)
        nf = font(32, True, mono=True)
        col = PTR_COLORS[L.ptrs.index(name) % len(PTR_COLORS)] if is_ptr else MUTED
        d.text((x + 16, y + 10), name, font=nf, fill=col)
        t = "未定" if is_undef(shown) or name not in vars_ else fmt(shown)
        f = font(int(L.card_h * 0.44), True, mono=True)
        while f.getlength(t) > w - 30 and len(t) > 3:
            t = t[:-2] + "…"
        d.text((x + w - 18 - f.getlength(t), y + h - f.size - 14), t, font=f, fill=OK if changed else (MUTED if t == "未定" else INK))

    # 再帰: 呼び出しの深さ
    if L.depth > 1 and step:
        dep = step.get("depth", 1)
        bx = W - 60 - 230
        by = L.panel_y - 4
        d.text((bx - 10 - font(26, True).getlength("呼び出し"), by + 2), "呼び出し", font=font(26, True), fill=MUTED)
        for k in range(dep):
            d.rounded_rectangle((bx + k * 30, by, bx + k * 30 + 24, by + 34), radius=6, fill=MARK if k == dep - 1 else MARK_SOFT)

    # 飛んでいく値
    if fly and u < FLY:
        dest, srcs = fly
        dc = L.center(dest)
        q = ease(u / FLY)
        # 計算の式（s ← 0 + 3 など）を、行き先の上に出す
        line = it["code"][prev["line"] - 1]
        m = re.match(rf"\s*(?:[^:：←]+[:：]\s*)?({IDENT}(?:\[[^\]]+\])?)\s*←\s*(.+)$", line)
        if m and dc:
            def val(mm):
                v = pv.get(mm.group(1))
                if mm.group(2) is not None:
                    k = ev(mm.group(2), pv)
                    v = v[k - 1] if isinstance(v, list) and k and 1 <= k <= len(v) else None
                return fmt(v) if v is not None and not is_undef(v) and not isinstance(v, list) else mm.group(0)
            rhs = re.sub(rf"({IDENT})(?:\[([^\]]+)\])?", val, m.group(2))
            if rhs.strip() != m.group(2).strip() and len(rhs) <= 22:
                lab = f"{m.group(1)} ← {rhs}"
                ff = font(38, True, mono=True)
                lw = ff.getlength(lab) + 40
                lx = min(max(dc[0] - lw / 2, 40), W - 40 - lw)
                ly = dc[1] - 150
                d.rounded_rectangle((lx, ly, lx + lw, ly + 62), radius=31, fill=INK)
                d.text((lx + 20, ly + 10), lab, font=ff, fill=PAPER)
        for s in srcs:
            if s == dest:
                continue   # 自分自身から自分へは飛ばさない（s ← s + data[i] の s）
            sc = L.center(s)
            if not sc or not dc:
                continue
            sv = pv.get(s[1])
            if s[0] == "arr":
                sv = sv[s[2] - 1] if isinstance(sv, list) and s[2] <= len(sv) else None
            if sv is None or is_undef(sv):
                continue
            x = sc[0] + (dc[0] - sc[0]) * q
            y = sc[1] + (dc[1] - sc[1]) * q - 120 * math.sin(math.pi * q)
            t = fmt(sv)
            f = font(40, True, mono=True)
            cw = max(80, f.getlength(t) + 36)
            d.rounded_rectangle((x - cw / 2, y - 34, x + cw / 2, y + 34), radius=17, fill=OK, outline=PAPER, width=3)
            d.text((x - f.getlength(t) / 2, y - 26), t, font=f, fill=PAPER)

    # 進み具合と案内（今までと同じ）
    d.rounded_rectangle((60, 1490, W - 60, 1504), radius=7, fill=LINE)
    d.rounded_rectangle((60, 1490, 60 + int((W - 120) * (idx + 1) / max(1, total)), 1504), radius=7, fill=MARK)
    d.text((60, 1520), f"手順 {idx + 1} / {total}" + (f"    {cur}行目" if cur else ""), font=font(30, mono=True), fill=MUTED)
    where = f"▶ サイトで自分で動かせる｜トレース練習 No.{no}" if it["kind"] == "trace" else f"▶ サイトで自分で動かせる｜図鑑「{it['title']}」"
    d.rounded_rectangle((60, 1576, W - 160, 1640), radius=32, fill=PAPER, outline=MARK, width=3)
    d.text((88, 1590), wrap(where, font(30, True), W - 280)[0], font=font(30, True), fill=MARK)
    return img


def step_shots(it, no, fn, args, steps, per):
    """1行ずつの画面（動きの図つき）。返り値は make_b_media.step_shots と同じ形。"""
    L = Layout(it, steps)
    total = len(steps)
    slide = min(0.25, per * 0.5)
    shots, cover, prev = [], None, None
    for i, s in enumerate(steps):
        final = draw_frame(L, it, no, s, prev, i, total, fn, args)
        if cover is None and i >= total * 0.4:
            cover = final
        start = prev["line"] if prev and prev.get("line") else None

        def shot(t, s=s, prev=prev, i=i, final=final, start=start):
            u = t / per
            if u >= 1:
                return final
            pos = None
            if start is not None and start != s["line"] and t < slide:
                pos = start + (s["line"] - start) * ease(t / slide)
            return draw_frame(L, it, no, s, prev, i, total, fn, args, u=min(1.0, u * 1.25), cur_pos=pos)
        if i:
            shot.no_fade = True   # 1行目の前（最初の画面から）だけ、ふわっと切り替える
        shots.append((shot, per))
        prev = s
    return shots, cover, prev
