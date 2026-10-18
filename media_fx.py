"""動画の飾り: キャラクターのドット絵と、効果音。

キャラクター: notes/brand/ちびキャラ日常アクション絵文字シート.png からポーズを切り抜く（背景を透明にする）。
             シートは notes/（公開しない）にあるので、無いときはキャラクターなしで動画を作る。
効果音:     8ビットのゲーム風の音を、プログラムで作る（素材サイトの音を使わないので、利用規約を気にしなくてよい）。
"""
import array
import math
import random
import wave
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
SHEETS = {
    "a": ROOT / "notes" / "brand" / "ちびキャラ日常アクション絵文字シート.png",       # 大きめの絵（72ポーズ）
    "b": ROOT / "notes" / "brand" / "青年キャラクターの日本語ピクセル絵文字シート.png",  # 小さめの絵（150ポーズ以上）。3倍くらいで使う
}
SHEET = SHEETS["a"]

# ---------- キャラクター ----------

# 2枚目のシート（b）のポーズ。シートの中の位置（左, 上, 右, 下）。下のラベルの文字が入らないように切る
POSES_B = {
    # 基本表情
    "b_normal": (138, 33, 204, 114), "b_smile": (206, 33, 275, 114), "b_laugh": (275, 33, 346, 114),
    "b_surprise": (346, 33, 411, 114), "b_think": (606, 33, 670, 114), "b_trouble": (672, 33, 737, 114),
    "b_panic": (738, 33, 803, 114), "b_shock": (805, 33, 869, 114), "b_confident": (867, 33, 932, 114),
    "b_happy": (1062, 33, 1127, 114),
    # 勉強
    "b_note": (672, 302, 747, 381), "b_study": (750, 302, 820, 381), "b_focus": (831, 300, 902, 381),
    "b_idea": (898, 300, 980, 381), "b_worry": (1000, 300, 1076, 381), "b_stuck": (1083, 296, 1143, 381),
    # リアクション
    "b_glad": (18, 923, 74, 985), "b_best": (89, 923, 156, 985), "b_yay": (167, 917, 232, 985),
    "b_clap": (237, 917, 300, 985), "b_guts": (311, 917, 368, 985), "b_phew": (1076, 916, 1141, 985),
}

# 1枚目のシート（a）のポーズ
POSES = {
    "walk1": (196, 24, 277, 174), "walk2": (288, 24, 363, 174),
    "stand": (840, 14, 919, 174),
    "smile": (15, 228, 112, 359), "laugh": (144, 230, 237, 359), "surprise": (262, 228, 366, 360),
    "think": (617, 231, 712, 360), "trouble": (742, 239, 845, 360), "motivated": (869, 226, 981, 360),
    "worry": (251, 420, 346, 542), "idea": (368, 405, 485, 544),
    "jump": (16, 948, 120, 1062), "guts": (147, 958, 228, 1063), "wave": (380, 955, 466, 1063),
    "point": (495, 960, 596, 1062), "ok": (618, 961, 699, 1065), "wink": (738, 958, 819, 1063),
}
_cache = {}


def _is_bg(c):
    return c[0] > 225 and c[1] > 225 and c[2] > 215 and max(c[:3]) - min(c[:3]) < 22


def available():
    return all(p.exists() for p in SHEETS.values())


def sprite(name, scale=2):
    """ポーズを切り抜いて、ドットがぼけないように整数倍に拡大する。背景は透明。"""
    key = (name, scale)
    if key in _cache:
        return _cache[key]
    sheet, box = ("b", POSES_B[name]) if name in POSES_B else ("a", POSES[name])
    if not SHEETS[sheet].exists():
        return None
    if sheet not in _cache:
        _cache[sheet] = Image.open(SHEETS[sheet]).convert("RGBA")
    im = _cache[sheet].crop(box)
    w, h = im.size
    px = im.load()
    # ふちの背景色から塗りつぶすように、つながった背景だけを透明にする（服の白い線などは残る）
    q = deque((x, y) for x in range(w) for y in (0, h - 1)) + deque((x, y) for y in range(h) for x in (0, w - 1))
    seen = set()
    while q:
        x, y = q.popleft()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        if not _is_bg(px[x, y]):
            continue
        px[x, y] = (0, 0, 0, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    im = im.crop(im.getbbox())
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    _cache[key] = im
    return im


def hop(t, t0, height=80, dur=0.45):
    """t0 秒から跳ねたときの、上へのずれ（px）。"""
    if t0 <= t < t0 + dur:
        u = (t - t0) / dur
        return -height * 4 * u * (1 - u)
    return 0.0


# ---------- 効果音 ----------

SR = 44100


def _env(i, n, attack=0.004, release=None):
    t = i / SR
    a = min(1.0, t / attack) if attack else 1.0
    r = 1.0 - i / n if release is None else math.exp(-t / release)
    return a * r


def _square(phase, duty=0.5):
    return 1.0 if (phase % 1.0) < duty else -1.0


def _tone(freqs, dur, vol=0.3, wave_="square", release=None, duty=0.5, soften=0.35):
    """freqs: 周波数（数、または 0〜1 の進み具合を受けて周波数を返す関数）。"""
    n = int(dur * SR)
    out, phase, lp = [], 0.0, 0.0
    for i in range(n):
        f = freqs(i / n) if callable(freqs) else freqs
        phase += f / SR
        if wave_ == "square":
            s = _square(phase, duty)
        elif wave_ == "tri":
            s = 4 * abs((phase % 1.0) - 0.5) - 1
        else:
            s = math.sin(2 * math.pi * phase)
        lp += (s - lp) * soften   # 角を少し丸めて、耳に痛くない音にする
        out.append(lp * vol * _env(i, n, release=release))
    return out


def _noise(dur, vol=0.2, cutoff=lambda u: 0.2, shape=lambda u: math.sin(math.pi * u)):
    rnd = random.Random(1)
    n = int(dur * SR)
    out, lp = [], 0.0
    for i in range(n):
        u = i / n
        lp += (rnd.uniform(-1, 1) - lp) * cutoff(u)
        out.append(lp * vol * shape(u))
    return out


def _seq(parts, gap=0.0):
    out = []
    for p in parts:
        out += p + [0.0] * int(gap * SR)
    return out


def _sounds():
    note = lambda n: 440 * 2 ** ((n - 69) / 12)   # MIDI の音の番号 → 周波数
    return {
        # 部品が出るとき「ポッ」
        "pop": _tone(lambda u: 520 + 600 * u, 0.07, 0.22, duty=0.25),
        # トレースの1行ごと「カチッ」
        "tick": _tone(1800, 0.02, 0.10, release=0.006),
        # 数え上げの1つずつ（音が少しずつ上がる）
        "count": _tone(1400, 0.025, 0.08, release=0.01),
        # 場面の切り替え「シュッ」
        "whoosh": _noise(0.28, 0.16, cutoff=lambda u: 0.05 + 0.4 * u),
        # カードをめくる「パタッ」
        "flip": _seq([_noise(0.035, 0.32, cutoff=lambda u: 0.5, shape=lambda u: 1 - u),
                      _noise(0.045, 0.26, cutoff=lambda u: 0.3, shape=lambda u: 1 - u)], gap=0.06),
        # 跳ねる「ピョン」
        "jump": _tone(lambda u: 330 + 700 * u * u, 0.16, 0.2, duty=0.5),
        # ひらめく「ピコーン」
        "idea": _seq([_tone(note(84), 0.06, 0.18, duty=0.25), _tone(note(91), 0.22, 0.18, duty=0.25, release=0.08)]),
        # 正解「ピンポン」
        "correct": _seq([_tone(note(88), 0.13, 0.22, duty=0.25, release=0.09), _tone(note(84), 0.35, 0.22, duty=0.25, release=0.15)]),
        # ふきだしの文字が出るとき「ピッ」（昔のゲームの会話のように）
        "talk": _tone(lambda u: 880 - 120 * u, 0.03, 0.12, duty=0.5, release=0.012),
        # 足音「トッ」
        "step": _tone(lambda u: 180 - 80 * u, 0.05, 0.16, wave_="tri", release=0.02),
        # 最後のしめくくり「タラララン」
        "fanfare": _seq([_tone(note(n), d, 0.17, duty=0.25, release=r)
                         for n, d, r in [(72, 0.09, None), (76, 0.09, None), (79, 0.09, None), (84, 0.45, 0.2)]]),
    }


_SOUNDS = None


# ---------- BGM（8ビットのゲーム風。プログラムで作曲する） ----------
# 曲の形: 前奏（2小節）→ A → B → A'（メロディに2つ目の声を重ねる）→ B' →（くり返し）。1つの部分は4小節
#         （短いリールでも、途中で曲の感じが変わるように）
# 部分ごとにコード進行・メロディ・ベース・和音・ドラムのリズムを変えて、くり返しに聞こえにくくする。
# 4小節ごとにドラムのおかず（フィル）、新しい部分の始まりにシンバルを入れる。

def _note_freq(n):
    return 440 * 2 ** ((n - 69) / 12)


# コード（根音の音の番号, 和音の音）
CH = {
    "C": (36, (60, 64, 67, 72)), "G": (43, (59, 62, 67, 71)), "Am": (45, (57, 60, 64, 69)), "F": (41, (57, 60, 65, 69)),
    "Em": (40, (59, 64, 67, 71)), "Dm": (38, (57, 62, 65, 69)),
}
PROG_A = ["C", "G", "Am", "F", "C", "G", "F", "G"]
PROG_B = ["F", "G", "Em", "Am", "Dm", "Em", "F", "G"]
# メロディ（1小節 = 8分音符8つ）。(音の番号, 8分音符いくつ分)。None は休み
MELODY_A = [
    [(76, 2), (79, 2), (84, 3), (83, 1)],
    [(79, 2), (74, 2), (79, 3), (None, 1)],
    [(76, 2), (81, 2), (84, 2), (81, 2)],
    [(77, 3), (76, 1), (74, 4)],
    [(76, 1), (76, 1), (79, 2), (84, 2), (86, 2)],
    [(83, 2), (79, 2), (74, 3), (None, 1)],
    [(77, 2), (81, 2), (84, 2), (81, 2)],
    [(79, 6), (None, 2)],
]
MELODY_B = [
    [(81, 4), (79, 2), (77, 2)],
    [(79, 3), (74, 1), (79, 4)],
    [(76, 2), (79, 2), (83, 4)],
    [(81, 6), (None, 2)],
    [(77, 2), (81, 2), (84, 2), (81, 2)],
    [(79, 2), (83, 2), (79, 2), (76, 2)],
    [(77, 2), (76, 2), (74, 2), (72, 2)],
    [(74, 4), (79, 2), (83, 2)],
]
SCALE = [0, 2, 4, 5, 7, 9, 11]   # ハ長調の音


def _third_below(n):
    """ハ長調の中で、3度下の音（2つ目の声に使う）。"""
    pc, octv = n % 12, n // 12
    idx = min(range(7), key=lambda i: abs(SCALE[i] - pc))
    j = idx - 2
    return (octv - (1 if j < 0 else 0)) * 12 + SCALE[j % 7]


def _add(buf, start, samples, vol):
    n = len(buf)
    for i, s in enumerate(samples):
        if start + i >= n:
            break
        buf[start + i] += s * vol


def _sections(n_bars, intro_bars=2):
    """小節ごとの (部分の名前, メロディ・コードの何小節目, 部分の中の何小節目)。1つの部分は4小節。"""
    out = [("intro", i, i) for i in range(intro_bars)]
    order = [("A", 0), ("B", 0), ("A2", 4), ("B", 4)]   # A の前半 → B の前半 → A の後半（2声）→ B の後半
    k = 0
    while len(out) < n_bars:
        name, off = order[k % len(order)]
        out += [(name, off + j, j) for j in range(4)]
        k += 1
    return out[:n_bars]


def bgm(seconds, bpm=120):
    """seconds 秒の BGM。最後の1.5秒でフェードアウトする。"""
    n = int(seconds * SR) + SR
    buf = [0.0] * n
    e8 = 60 / bpm / 2          # 8分音符の長さ
    bar = e8 * 8
    cache = {}

    def snd(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    kick = snd("kick", lambda: _tone(lambda u: 150 - 110 * u, 0.12, 1.0, wave_="sine", release=0.05, soften=1))
    snare = snd("snare", lambda: _noise(0.11, 1.0, cutoff=lambda u: 0.7, shape=lambda u: (1 - u) ** 2))
    hat = snd("hat", lambda: _noise(0.03, 1.0, cutoff=lambda u: 0.95, shape=lambda u: 1 - u))
    crash = snd("crash", lambda: _noise(0.9, 1.0, cutoff=lambda u: 0.9, shape=lambda u: (1 - u) ** 3))
    tom = lambda f: snd(("tom", f), lambda: _tone(lambda u: f - f * 0.4 * u, 0.12, 1.0, wave_="tri", release=0.06, soften=0.8))

    def note(key, n_, dur, wave_, duty=0.5, release=None):
        return snd((key, n_, round(dur, 3)), lambda: _tone(_note_freq(n_), dur, 1.0, wave_=wave_, duty=duty, release=release))

    secs = _sections(int(seconds / bar) + 2)
    for b, (sec, i, j) in enumerate(secs):
        t_bar = b * bar
        if t_bar >= seconds:
            break
        name = (PROG_B if sec == "B" else PROG_A)[i % 8]
        root, chord = CH[name]
        at = lambda k: int((t_bar + k * e8) * SR)
        fill = sec != "intro" and j == 3
        # 新しい部分の始まりにシンバル
        if j == 0 and sec != "intro":
            _add(buf, at(0), crash, 0.10)
        # ドラム
        for k in range(8):
            if fill and k >= 6:
                continue
            if sec == "intro":
                if k == 0:
                    _add(buf, at(k), kick, 0.30)
                if k % 2 == 1:
                    _add(buf, at(k), hat, 0.05)
                continue
            if k in (0, 4) or (sec in ("B", "A2") and k == 3):
                _add(buf, at(k), kick, 0.36)
            if k in (2, 6):
                _add(buf, at(k), snare, 0.15)
            if k % 2 == 1 or sec in ("B", "A2"):
                _add(buf, at(k), hat, 0.05 if k % 2 else 0.03)
        if fill:   # 小節の終わりのおかず: スネアの連打と、下がっていく音
            for h in range(4):
                _add(buf, at(6) + int(h * e8 / 2 * SR), snare, 0.08 + 0.03 * h)
                _add(buf, at(6) + int(h * e8 / 2 * SR), tom(220 - 30 * h), 0.25)
        # ベース
        for k in range(8):
            if sec == "B":
                bn = root + (0, 7, 12, 7)[k % 4]          # 根音・5度・オクターブと歩く
            elif sec == "intro":
                if k % 2:
                    continue
                bn = root
            else:
                bn = root + (12 if k % 2 else 0)          # 根音とオクターブを交互に
            _add(buf, at(k), note("bass", bn, e8 * 0.85, "tri", release=0.15), 0.30)
        # 和音
        if sec == "B":   # 裏拍に和音をまとめて「チャッ」と鳴らす
            for k in (1, 3, 5, 7):
                for cn in chord[:3]:
                    _add(buf, at(k), note("stab", cn, e8 * 0.5, "square", duty=0.25, release=0.05), 0.022)
        else:            # 16分音符で和音の音を順に（前奏は小さく）
            v = 0.03 if sec == "intro" else 0.042
            for k in range(8):
                for h in range(2):
                    an = chord[(k * 2 + h) % len(chord)]
                    _add(buf, at(k) + int(h * e8 / 2 * SR), note("arp", an, e8 / 2 * 0.8, "square", duty=0.125, release=0.05), v)
        # メロディ（A' は3度下の2つ目の声も重ねる）
        if sec != "intro":
            pos = 0
            for mn, ln in (MELODY_B if sec == "B" else MELODY_A)[i % 8]:
                if mn is not None:
                    _add(buf, at(pos), note("mel", mn, e8 * ln * 0.92, "square", duty=0.25, release=0.35), 0.11)
                    if sec == "A2":
                        _add(buf, at(pos), note("har", _third_below(mn), e8 * ln * 0.92, "square", duty=0.5, release=0.35), 0.05)
                pos += ln
    # 最後の1.5秒で小さくしていく
    end, fade = int(seconds * SR), int(1.5 * SR)
    for i in range(max(0, end - fade), n):
        buf[i] *= max(0.0, (end - i) / fade)
    return buf


# ---------- 楽器の音の BGM（ピアノ・アコースティックギター・ベース・ドラム） ----------
# 電子音ではなく、楽器に近い音をプログラムで作る。
#   ギター・ベース: 弦をはじく音をまねる計算（カープラス・ストロング法）
#   ピアノ: 倍音を重ね、高い倍音ほど早く消えるようにする（ハンマーの「コツ」という音も少し）
#   ドラム: バスドラム・スネア・ハイハットを、電子音っぽさを抑えて作る
# 曲の形とコード進行・メロディは、上の 8ビットの BGM と同じ（A・B・A'）。

def _pluck(freq, dur, damp=0.996, bright=0.55, seed=1):
    """弦をはじいた音。damp が 1 に近いほど長く響き、bright が大きいほど明るい音。"""
    rnd = random.Random(seed)
    period = max(2, int(round(SR / freq)))
    buf, lp = [], 0.0
    for _ in range(period):   # はじいた瞬間のざらざらした音（明るさは、なめらかにする強さで変える）
        lp += (rnd.uniform(-1, 1) - lp) * bright
        buf.append(lp)
    n = int(dur * SR)
    out = [0.0] * n
    rel = int(0.03 * SR)
    for i in range(n):
        j = i % period
        v = buf[j]
        buf[j] = damp * 0.5 * (v + buf[(j + 1) % period])
        g = 1.0 if i < n - rel else (n - i) / rel
        out[i] = v * g
    return out


def _piano(freq, dur, vel=1.0):
    """ピアノに近い音。倍音を重ねて、高い倍音ほど早く消えるようにする。"""
    n = int(dur * SR)
    out = [0.0] * n
    rel = int(0.05 * SR)
    for k in range(1, 9):
        f = freq * k * math.sqrt(1 + 0.0004 * k * k)   # 弦の太さで、高い倍音が少しずれる
        if f > SR / 2.2:
            break
        amp = vel / k ** 1.15
        decay = 1.6 + 0.9 * k
        w = 2 * math.pi * f / SR
        c = 2 * math.cos(w)
        s1, s2 = 0.0, -math.sin(w)   # sin の値を、かけ算だけで次々に出す
        for i in range(n):
            s = c * s1 - s2
            s2, s1 = s1, s
            out[i] += s * amp * math.exp(-decay * i / SR)
    rnd = random.Random(int(freq))
    lp = 0.0
    for i in range(min(n, int(0.012 * SR))):   # ハンマーが当たる「コツ」
        lp += (rnd.uniform(-1, 1) - lp) * 0.3
        out[i] += lp * 0.15 * vel * (1 - i / (0.012 * SR))
    att = int(0.003 * SR)
    for i in range(n):
        g = min(1.0, i / att) if att else 1.0
        if i > n - rel:
            g *= (n - i) / rel
        out[i] *= g * 0.35
    return out


def _kick():
    n = int(0.25 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += (45 + 75 * math.exp(-t * 30)) / SR
        out.append(math.sin(2 * math.pi * ph) * math.exp(-t * 14))
    rnd = random.Random(3)
    for i in range(int(0.004 * SR)):   # 打った瞬間の「コッ」
        out[i] += rnd.uniform(-1, 1) * 0.3 * (1 - i / (0.004 * SR))
    return out


def _snare():
    n = int(0.2 * SR)
    rnd = random.Random(5)
    out, lp1, lp2 = [], 0.0, 0.0
    for i in range(n):
        t = i / SR
        x = rnd.uniform(-1, 1)
        lp1 += (x - lp1) * 0.6
        lp2 += (x - lp2) * 0.08
        noise = (lp1 - lp2) * math.exp(-t * 22)              # 響き線の「シャッ」
        body = math.sin(2 * math.pi * 185 * t) * math.exp(-t * 40)   # 胴の「タン」
        out.append(noise * 0.9 + body * 0.5)
    return out


def _hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    rnd = random.Random(7)
    out, lp = [], 0.0
    for i in range(n):
        x = rnd.uniform(-1, 1)
        lp += (x - lp) * 0.35
        out.append((x - lp) * math.exp(-i / SR * (14 if open_ else 70)))   # 高い音だけを残す
    return out


def _guitar_voicing(name):
    """ギターで押さえる和音（低い方から）。"""
    root, chord = CH[name]
    tones = sorted({root + 12} | {c - 12 for c in chord[:3]} | {chord[0], chord[1]})
    return [t for t in tones if 40 <= t <= 67][:5]


def bgm_acoustic(seconds, bpm=112):
    """楽器の音の BGM。seconds 秒。最後の1.5秒でフェードアウトする。"""
    n = int(seconds * SR) + SR
    buf = [0.0] * n
    e8 = 60 / bpm / 2
    bar = e8 * 8
    cache = {}

    def snd(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    kick, snare = snd("kick", _kick), snd("snare", _snare)
    hat, ohat = snd("hat", _hat), snd("ohat", lambda: _hat(True))
    pl = lambda n_, dur, damp, bright, seed=1: snd(("pl", n_, round(dur, 3), damp, bright, seed),
                                                   lambda: _pluck(_note_freq(n_), dur, damp, bright, seed))
    pn = lambda n_, dur, vel=1.0: snd(("pn", n_, round(dur, 3), vel), lambda: _piano(_note_freq(n_), dur, vel))

    def strum(at_s, name, down=True, vol=0.12, ring=None):
        """ギターをじゃらんと弾く（弦を1本ずつ少しずらして鳴らす）。"""
        notes = _guitar_voicing(name)
        if not down:
            notes = notes[::-1][:3]
        for k, gn in enumerate(notes):
            _add(buf, at_s + int(k * 0.012 * SR), pl(gn, ring or e8 * 4, 0.997, 0.5, seed=gn), vol * (1.0 if down else 0.6))

    secs = _sections(int(seconds / bar) + 2)
    for b, (sec, i, j) in enumerate(secs):
        t_bar = b * bar
        if t_bar >= seconds:
            break
        name = (PROG_B if sec == "B" else PROG_A)[i % 8]
        root, chord = CH[name]
        at = lambda k: int((t_bar + k * e8) * SR)
        fill = sec != "intro" and j == 3
        # ドラム
        if sec == "intro":
            for k in (1, 3, 5, 7):
                _add(buf, at(k), hat, 0.10)
        else:
            if j == 0:
                _add(buf, at(0), ohat, 0.12)
            for k in range(8):
                if fill and k >= 6:
                    continue
                if k in (0, 4) or (sec in ("B", "A2") and k == 5):
                    _add(buf, at(k), kick, 0.55)
                if k in (2, 6):
                    _add(buf, at(k), snare, 0.28)
                _add(buf, at(k), hat, 0.10 if k % 2 == 0 else 0.06)
            if fill:   # おかず: スネアを細かく
                for h in range(4):
                    _add(buf, at(6) + int(h * e8 / 2 * SR), snare, 0.12 + 0.05 * h)
        # ベース（指で弾くエレキベースのような音）
        for k in (0, 3, 4, 6) if sec != "intro" else (0, 4):
            bn = root - 12 + (7 if (sec == "B" and k == 6) else 0)
            _add(buf, at(k), pl(bn, e8 * 2.5, 0.992, 0.25, seed=bn), 0.55)
        # ギター
        if sec == "B":     # 指で1音ずつ弾く（アルペジオ）
            gv = _guitar_voicing(name)
            for k in range(8):
                gn = gv[(0, 2, 3, 4, 3, 2, 1, 2)[k] % len(gv)]
                _add(buf, at(k), pl(gn, e8 * 3, 0.997, 0.45, seed=gn), 0.13)
        elif sec == "intro":
            strum(at(0), name, True, 0.10, ring=bar)
        else:              # じゃーん・じゃ・じゃかじゃん（下・下・上・上・下・上）
            for k, down in ((0, True), (2, True), (3, False), (5, False), (6, True), (7, False)):
                strum(at(k), name, down, 0.10)
        # ピアノのメロディ（A' は3度下の音も重ねて、少し厚くする）
        if sec != "intro":
            pos = 0
            for mn, ln in (MELODY_B if sec == "B" else MELODY_A)[i % 8]:
                if mn is not None:
                    dur = e8 * ln + 0.25   # ペダルを踏んだように、少し長めに響かせる
                    _add(buf, at(pos), pn(mn, dur, 1.0), 0.55)
                    if sec == "A2":
                        _add(buf, at(pos), pn(_third_below(mn), dur, 0.7), 0.35)
                pos += ln
    end, fade = int(seconds * SR), int(1.5 * SR)
    for i in range(max(0, end - fade), n):
        buf[i] *= max(0.0, (end - i) / fade)
    return buf


# ---------- ヒーリング風の BGM（ゆったりしたピアノ・ふわっとした音・オルゴール・響き） ----------
# テンポ 72、1小節に1つのコード。ドラムは入れない。最後に、ホールのような響き（リバーブ）をかける。

# 7th や 6th を足した、やわらかい響きのコード（根音, 和音の音）
CH_SOFT = {
    "Fmaj7": (41, (53, 57, 60, 64)), "G6": (43, (55, 59, 62, 64)), "Em7": (40, (52, 55, 59, 62)),
    "Am7": (45, (57, 60, 64, 67)), "Dm7": (38, (50, 53, 57, 60)), "Gsus4": (43, (55, 60, 62, 67)),
    "Cmaj7": (36, (48, 52, 55, 59)),
}
PROG_HEAL = ["Fmaj7", "G6", "Em7", "Am7", "Dm7", "Em7", "Fmaj7", "Gsus4"]
# メロディ（1小節 = 8分音符8つ）。少ない音を、長く鳴らす
MELODY_HEAL = [
    [(None, 2), (81, 3), (79, 3)],
    [(79, 4), (74, 4)],
    [(None, 2), (76, 2), (79, 4)],
    [(76, 8)],
    [(None, 2), (77, 3), (76, 3)],
    [(74, 4), (79, 4)],
    [(None, 2), (81, 2), (84, 4)],
    [(79, 8)],
]


def _pad(notes, dur, vol=1.0):
    """後ろに広がる、ふわっとした音（ストリングスのような）。少しずらした2つの音を重ねて、ゆれを出す。"""
    n = int(dur * SR)
    out = [0.0] * n
    att, rel = int(0.9 * SR), int(1.2 * SR)
    for nt in notes:
        f = _note_freq(nt)
        for det in (-0.6, 0.6):
            w1 = 2 * math.pi * (f + det) / SR
            w2 = 2 * w1
            for i in range(0, n):
                out[i] += math.sin(w1 * i) * 0.8 + math.sin(w2 * i) * 0.12
    for i in range(n):
        g = min(1.0, i / att)
        if i > n - rel:
            g *= max(0.0, (n - i) / rel)
        out[i] *= g * vol / (len(notes) * 2)
    return out


def _bell(freq, dur=2.5):
    """オルゴールのような「キラッ」。整数倍でない倍音を少し混ぜる。"""
    n = int(dur * SR)
    out = []
    for i in range(n):
        t = i / SR
        out.append((math.sin(2 * math.pi * freq * t) * math.exp(-t * 2.2)
                    + 0.4 * math.sin(2 * math.pi * freq * 2.76 * t) * math.exp(-t * 5)
                    + 0.2 * math.sin(2 * math.pi * freq * 5.4 * t) * math.exp(-t * 9)) * min(1.0, t / 0.002))
    return out


def _soft_bass(freq, dur):
    n = int(dur * SR)
    out = []
    rel = int(0.6 * SR)
    for i in range(n):
        t = i / SR
        g = min(1.0, t / 0.05) * (1.0 if i < n - rel else (n - i) / rel)
        out.append((math.sin(2 * math.pi * freq * t) + 0.2 * math.sin(4 * math.pi * freq * t)) * g * math.exp(-t * 0.4))
    return out


def _reverb(x, wet=0.32):
    """ホールのような響き（シュレーダー型のリバーブ）。"""
    n = len(x)
    out = [0.0] * n
    for d, fb in ((1557, 0.84), (1617, 0.83), (1491, 0.85), (1422, 0.84)):   # くし形フィルター4つ
        buf = [0.0] * d
        lp, j = 0.0, 0
        for i in range(n):
            y = buf[j]
            lp = y * 0.6 + lp * 0.4            # 高い音ほど早く消える
            buf[j] = x[i] + lp * fb
            out[i] += y * 0.25
            j = (j + 1) % d
    for d in (225, 556):                         # オールパスフィルター2つ（響きをなめらかに）
        buf = [0.0] * d
        j = 0
        for i in range(n):
            b = buf[j]
            y = -out[i] + b
            buf[j] = out[i] + b * 0.5
            out[i] = y
            j = (j + 1) % d
    return [a * (1 - wet) + b * wet for a, b in zip(x, out)]


def bgm_healing(seconds, bpm=72):
    """ヒーリング風の BGM。seconds 秒。最初はふわっと入り、最後の2.5秒でフェードアウトする。"""
    n = int(seconds * SR) + SR
    buf = [0.0] * n
    e8 = 60 / bpm / 2
    bar = e8 * 8
    cache = {}

    def snd(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    b = 0
    while b * bar < seconds:
        name = PROG_HEAL[b % len(PROG_HEAL)]
        root, chord = CH_SOFT[name]
        at = lambda k: int((b * bar + k * e8) * SR)
        # ふわっとした音（次の小節に少し重なるように長めに）
        _add(buf, at(0), snd(("pad", name), lambda: _pad([c + 12 for c in chord], bar + 1.2)), 0.22)
        # 低いベース
        _add(buf, at(0), snd(("bass", root), lambda: _soft_bass(_note_freq(root), bar + 0.5)), 0.30)
        # ピアノの分散和音（下から上へ、ゆっくり）
        arp = [root + 12, chord[0], chord[1], chord[2], chord[3], chord[2], chord[1], chord[0]]
        for k, an in enumerate(arp):
            _add(buf, at(k), snd(("pn", an), lambda an=an: _piano(_note_freq(an), 2.2, 0.55)), 0.30)
        # メロディ（1小節目は入れず、静かに始める）
        if b >= 1:
            pos = 0
            for mn, ln in MELODY_HEAL[(b - 1) % len(MELODY_HEAL)]:
                if mn is not None:
                    _add(buf, at(pos), snd(("mel", mn), lambda mn=mn: _piano(_note_freq(mn), 3.0, 0.8)), 0.42)
                pos += ln
        # 2小節に1回、オルゴールの「キラッ」
        if b % 2 == 1:
            bn = chord[3] + 24
            _add(buf, at(7), snd(("bell", bn), lambda: _bell(_note_freq(bn))), 0.06)
        b += 1
    buf = _reverb(buf)
    fin, fout = int(1.5 * SR), int(2.5 * SR)
    end = int(seconds * SR)
    for i in range(n):
        g = min(1.0, i / fin)
        if i > end - fout:
            g *= max(0.0, (end - i) / fout)
        buf[i] *= g
    return buf


BGM_STYLES = {"chip": lambda s: bgm(s), "band": lambda s: bgm_acoustic(s), "healing": lambda s: bgm_healing(s)}
# 動画に入れる BGM の種類: chip=8ビット / band=楽器（ピアノ・ギター・ベース・ドラム） / healing=ヒーリング風 / None=入れない
# 2026-10-16 に、リール動画は BGM なし（効果音だけ）に決めた。また入れるときは、ここを "chip" などにする
BGM_STYLE = None


# 動画に効果音を入れるか。2026-10-16 に、リール動画は音なし（BGM も効果音もなし）に決めた。また入れるときは True にする
SFX_ON = False


def write_track(path, seconds, events, music=True):
    """events: [(秒, 音の名前, 音量)] を1本の音（WAV、ステレオ）にまとめる。music=True で BGM も入れる。
    SFX_ON が False のときは効果音を入れない（BGM_STYLE も None なら、無音の音声トラックになる）。"""
    global _SOUNDS
    if _SOUNDS is None:
        _SOUNDS = _sounds()
    n = int(seconds * SR) + SR
    mix = [0.0] * n
    for t, name, vol in (events if SFX_ON else []):
        _add(mix, int(t * SR), _SOUNDS[name], vol)
    peak = max(1e-9, max(abs(v) for v in mix))
    mix = [v * 0.7 / peak for v in mix]   # 効果音のいちばん大きいところを -3dB くらいにそろえる
    if music and BGM_STYLE:
        m = BGM_STYLES[BGM_STYLE](seconds)
        rms = max(1e-9, math.sqrt(sum(w * w for w in m) / len(m)))
        g = 10 ** (-21 / 20) / rms   # BGM の平均の大きさを -21dB にそろえる（効果音が上に聞こえる大きさ）
        mix = [v + w * g for v, w in zip(mix, m)]
    # 重なって大きくなりすぎたところは、やわらかく抑える
    data = array.array("h", (int(math.tanh(v * 1.1) * 32767 * 0.95) for v in mix for _ in (0, 1)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
