"""make_b_lesson_promo.py の効果音を作る（本編と同じペン・磁石の音）。lemo-opuscar の .venv で動かす。
    ~/lemo-opuscar/.venv/Scripts/python b_promo_sfx.py <events.json> <out.wav>
events.json = {"dur": 秒, "ev": [[秒, 種類, 長さ・高さ], ...]}
種類: thump（最初のドン）・whoosh（場面の切りかえ）・write（見出しを書く）・stroke（丸・下線）・pop（？）・tick（サムネイル）・magnet・ding
"""
import json, sys
from pathlib import Path
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path.home() / "lemo-opuscar" / "core" / "audio"))
import sfx
from sfx import SR, t_, env_exp, bp, hp, lp, noise, norm, add

rng = np.random.default_rng(5)


def pen(d, tone=1.0, squeak=False):
    """フェルトのペンがホワイトボードをこする音（本編の mix.py と同じ作り）"""
    d = max(d, .04); u = t_(d) / d
    speed = np.clip(1 - np.cos(2 * np.pi * u), 0, 2) / 2 + .15
    x = bp(noise(d), 2000 * tone, 7500) * .8 + bp(noise(d), 500 * tone, 1500) * .45
    grain = (rng.random(len(u)) < .004).astype(float); x += lp(grain, 3000) * .6
    x *= speed
    if squeak and d > .2:
        tt = t_(d); f = 1900 * tone + 120 * np.sin(2 * np.pi * 10 * tt)
        x += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) ** 2 * .25
    a = np.minimum(1, t_(d) / .006) * np.minimum(1, (d - t_(d)) / .01)
    return norm(x * a)


def writing(d):
    """字を書く: 短いこすれを何回か"""
    out = np.zeros(int(d * SR) + SR // 10)
    t = 0.0
    while t < d:
        L = .05 + rng.random() * .07
        s = pen(L, .95 + rng.random() * .1); i = int(t * SR); out[i:i + len(s)] += s[:len(out) - i] * (.6 + rng.random() * .4)
        t += L + .015 + rng.random() * .03
    return out


def magnet():
    d = .25; tt = t_(d)
    x = hp(noise(d), 2500) * env_exp(d, .002)
    x += sum(a * np.sin(2 * np.pi * f * tt) * env_exp(d, .03) for f, a in [(2300, .3), (3700, .2)])
    return norm(x) * .8 + sfx.thump(.5, 90)[:len(x)] * .5


ev = json.load(open(sys.argv[1], encoding="utf-8"))
out = np.zeros((int((ev["dur"] + 2) * SR), 2), np.float32)
for t, ty, a in ev["ev"]:
    if ty == "thump": add(out, sfx.thump(1, 75), t, .55); add(out, magnet(), t, .3)
    elif ty == "whoosh": add(out, sfx.whoosh(.32), t - .04, .35)
    elif ty == "write": add(out, writing(a), t, .30)
    elif ty == "stroke": add(out, pen(a, 1.08, squeak=True), t, .40, .1)
    elif ty == "pop": add(out, sfx.pop(), t, .30, rng.uniform(-.3, .3))
    elif ty == "tick": add(out, sfx.click(a, .7), t, .22, rng.uniform(-.25, .25))
    elif ty == "magnet": add(out, magnet(), t, .45)
    elif ty == "ding": add(out, sfx.ding(), t, .22)
for c in range(2):
    out[:, c] = sfx.limit(out[:, c], .95)
sf.write(sys.argv[2], out[:int(ev["dur"] * SR)], SR, subtype="PCM_16")
print("sfx", sys.argv[2])
