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

def _note_freq(n):
    return 440 * 2 ** ((n - 69) / 12)


# コード進行（1小節ずつ）: C → G → Am → F → C → G → F → G。（根音の音の番号, 和音の音）
PROG = [(36, (60, 64, 67, 72)), (43, (59, 62, 67, 71)), (45, (60, 64, 69, 72)), (41, (60, 65, 69, 72)),
        (36, (60, 64, 67, 72)), (43, (59, 62, 67, 71)), (41, (60, 65, 69, 72)), (43, (59, 62, 67, 71))]
# メロディ（1小節 = 8分音符8つ）。(音の番号, 8分音符いくつ分)。None は休み
MELODY = [
    [(76, 2), (79, 2), (84, 3), (83, 1)],
    [(79, 2), (74, 2), (79, 4)],
    [(76, 2), (81, 2), (84, 2), (81, 2)],
    [(77, 3), (76, 1), (74, 4)],
    [(76, 1), (76, 1), (79, 2), (84, 2), (86, 2)],
    [(83, 2), (79, 2), (74, 4)],
    [(77, 2), (81, 2), (84, 2), (81, 2)],
    [(79, 6), (None, 2)],
]


def _add(buf, start, samples, vol):
    n = len(buf)
    for i, s in enumerate(samples):
        if start + i >= n:
            break
        buf[start + i] += s * vol


def bgm(seconds, bpm=120, intro_bars=2):
    """seconds 秒の BGM。前奏（ドラム・ベース・和音）のあとにメロディが入る。最後の1.5秒でフェードアウトする。"""
    n = int(seconds * SR) + SR
    buf = [0.0] * n
    eighth = 60 / bpm / 2
    bar = eighth * 8
    cache = {}

    def tone(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    kick = tone("kick", lambda: _tone(lambda u: 150 - 110 * u, 0.12, 1.0, wave_="sine", release=0.05, soften=1))
    snare = tone("snare", lambda: _noise(0.11, 1.0, cutoff=lambda u: 0.7, shape=lambda u: (1 - u) ** 2))
    hat = tone("hat", lambda: _noise(0.03, 1.0, cutoff=lambda u: 0.95, shape=lambda u: 1 - u))
    b = 0
    while b * bar < seconds:
        root, chord = PROG[b % len(PROG)]
        t_bar = b * bar
        for k in range(8):
            t = t_bar + k * eighth
            s = int(t * SR)
            # ドラム: 1・3拍目にバスドラム、2・4拍目にスネア、裏拍にハイハット
            if k in (0, 4):
                _add(buf, s, kick, 0.38)
            if k in (2, 6):
                _add(buf, s, snare, 0.16)
            if k % 2 == 1:
                _add(buf, s, hat, 0.07)
            # ベース: 根音とオクターブ上を交互に
            bn = root + (12 if k % 2 else 0)
            _add(buf, s, tone(("bass", bn), lambda bn=bn: _tone(_note_freq(bn), eighth * 0.9, 1.0, wave_="tri", release=0.15, soften=0.6)), 0.30)
            # 和音の粒（16分音符で和音の音を順に鳴らす）
            for h in range(2):
                an = chord[(k * 2 + h) % len(chord)]
                _add(buf, s + int(h * eighth / 2 * SR),
                     tone(("arp", an), lambda an=an: _tone(_note_freq(an), eighth / 2 * 0.8, 1.0, duty=0.125, release=0.05)), 0.045)
        # メロディ（前奏のあと）
        if b >= intro_bars:
            pos = 0
            for mn, ln in MELODY[(b - intro_bars) % len(MELODY)]:
                if mn is not None:
                    _add(buf, int((t_bar + pos * eighth) * SR),
                         tone(("mel", mn, ln), lambda mn=mn, ln=ln: _tone(_note_freq(mn), eighth * ln * 0.92, 1.0, duty=0.25, release=0.35)), 0.11)
                pos += ln
        b += 1
    # 最後の1.5秒で小さくしていく
    end, fade = int(seconds * SR), int(1.5 * SR)
    for i in range(max(0, end - fade), n):
        buf[i] *= max(0.0, (end - i) / fade)
    return buf


def write_track(path, seconds, events, music=True):
    """events: [(秒, 音の名前, 音量)] を1本の音（WAV、ステレオ）にまとめる。music=True で BGM も入れる。"""
    global _SOUNDS
    if _SOUNDS is None:
        _SOUNDS = _sounds()
    n = int(seconds * SR) + SR
    mix = [0.0] * n
    for t, name, vol in events:
        _add(mix, int(t * SR), _SOUNDS[name], vol)
    peak = max(1e-9, max(abs(v) for v in mix))
    mix = [v * 0.7 / peak for v in mix]   # 効果音のいちばん大きいところを -3dB くらいにそろえる
    if music:
        m = bgm(seconds)
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
