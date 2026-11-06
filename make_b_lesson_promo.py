"""科目Bの解説動画シリーズ（23本）の宣伝リール・YouTube ショート（1080×1920・30fps・ナレーションつき）を作る。

- 見た目は本編と同じホワイトボード（紙の色・手書き風の Klee One）。派手な飾りは入れない（2026-11-05、運営者が「AI っぽい」と言ったため）
- 声は本編と同じ Nanami（速さ +10%・高さ +6Hz）。lemo-opuscar の tts_zh.py で作る（ネットが要る）
- 映像は本編（notes/科目B解説動画/<名前>/<名前>_本編_YouTube.mp4）の一部と、最後に各回のサムネイル
- できたものは notes/科目B解説動画/宣伝/（公開しない）
    .venv\\Scripts\\python make_b_lesson_promo.py            # 書き出す
    .venv\\Scripts\\python make_b_lesson_promo.py --stills   # 場面ごとの静止画だけ（確認用）
"""
import json, os, subprocess, sys, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
LES = ROOT / "notes" / "科目B解説動画"
OUT = LES / "宣伝"
WORK = OUT / "作業"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
LEMO = Path.home() / "lemo-opuscar"
W, H, FPS = 1080, 1920, 30
BGM = LES / "BGM" / "Focus Flow.mp3"
BGM_DB = -24
SFX_DB = -9      # 効果音（声より少し下）

# 本編と同じ色
PAPER, INK, ORANGE, BLUE = (247, 246, 242), (35, 38, 44), (226, 96, 40), (46, 96, 186)
FONT_HAND = str(ROOT / "notes" / "曲の動画" / "フォント" / "KleeOne-SemiBold.ttf")
FONT_SUB = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"

# 置き場所（Instagram の表示に隠れないよう、文字は y 300〜1480）
HEAD_Y = 290
PANEL = (0, 600, 1080, 1000)       # 映像の帯 x, y, w, h（幅:高さ = 1.08）
SUB_Y = 1350

V = lambda n: LES / n / f"{n}_本編_YouTube.mp4"
CROP = lambda x, y=0: (x, y, 1037, 960)      # 本編から切り出す所（下の字幕は入れない）
# 1場面 = 声1つ。head は上の手書きの見出し（[[...]] はオレンジ）。clips は (動画, 開始秒, 切り出し)
SCENES = [
    dict(id="p1", say="基本情報の科目ビー、解説動画が、にじゅうさんぼん、ぜんぶ無料って、知ってました？",
         sub="科目Bの解説動画が23本\nぜんぶ無料って知ってました？", head="科目Bの解説動画\n23本ぜんぶ[[無料]]ってマジ？",
         clips=[(V("二分探索"), 291, CROP(800))]),
    dict(id="p2", say="擬似言語って、最初は本当に読めないんですよね。",
         sub="擬似言語って\n最初は本当に読めないんですよね", head="擬似言語、\n[[読めない]]ところから",
         clips=[(V("二分探索"), 258, CROP(0, 10))], marks=[(860, 760, 0.9), (930, 1020, 1.15), (760, 1240, 1.4)]),
    dict(id="p3", say="なので、プログラムを1行ずつ動かして、変数がどう変わるかを、ホワイトボードで見せています。",
         sub="プログラムを1行ずつ動かして\n変数の変わり方を見せています", head="1行ずつ動かして\n[[トレース]]",
         clips=[(V("基礎回2_for・while・トレース表"), 150, CROP(760)), (V("バブルソート"), 172, CROP(300))]),
    dict(id="p4", say="二分探索、ソート、再帰など、試験によく出るアルゴリズムを、1本10分以内で。",
         sub="よく出るアルゴリズムを\n1本10分以内で", head="二分探索・ソート・再帰\n[[1本10分]]以内",
         clips=[(V("階乗（再帰）"), 137, CROP(600)), (V("クイックソート"), 167, CROP(0))]),
    dict(id="p5", say="最後に、本番と同じ形の穴埋め問題も入れました。",
         sub="最後に、本番と同じ形の\n穴埋め問題もあります", head="最後に\n[[穴埋め問題]]",
         clips=[(V("二分探索"), 362, CROP(840, 40))], magnet=0.3),
    dict(id="p6", say="ユーチューブで、科目ビー アルゴリズム解説、で探してみてください。",
         sub="YouTube で\n「科目B アルゴリズム解説」", head="基礎から全23本\nYouTube で[[見られます]]", wall=True),
]
LESSONS = ["基礎回1_変数・if・配列", "基礎回2_for・while・トレース表", "基礎回3_関数・大域変数", "最大値を求める", "線形探索",
           "二分探索", "10進数を2進数に変換する", "ユークリッドの互除法", "バブルソート", "選択ソート", "挿入ソート",
           "階乗（再帰）", "フィボナッチ数列", "スタック", "キュー", "リスト", "2分木", "ハッシュ", "クイックソート",
           "マージソート", "文字列探索", "素数", "2次元配列"]


# ── 声（本編と同じ Nanami） ──
def voices():
    vd = WORK / "voices"
    lines = [dict(id=s["id"], text=s["sub"].replace("\n", ""), say=s["say"]) for s in SCENES]
    lf = WORK / "lines.json"
    lf.write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run([str(LEMO / ".venv" / "Scripts" / "python"), str(LEMO / "core" / "tts" / "tts_zh.py"), str(lf), str(vd),
                    "--voice", "ja-JP-NanamiNeural", "--rate", "+10%", "--pitch", "+6Hz"], check=True, env=env, stdin=subprocess.DEVNULL)
    return [vd / f"{s['id']}.wav" for s in SCENES]


def wav_len(f):
    with wave.open(str(f)) as w:
        return w.getnframes() / w.getframerate()


# ── 絵の部品 ──
_fc = {}
def font(path, size):
    if (path, size) not in _fc:
        _fc[(path, size)] = ImageFont.truetype(path, size)
    return _fc[(path, size)]


def rich(text):
    out, hi = [], False
    for part in text.replace("]]", "[[").split("[["):
        if part:
            out.append((part, hi))
        hi = not hi
    return out


def draw_head(im, head, k, instant=False):
    """手書きの見出し。字が左から書かれていくように出る（最初の 0.45 秒）"""
    d = ImageDraw.Draw(im)
    rows = head.split("\n")
    total = sum(len(r.replace("[[", "").replace("]]", "")) for r in rows)
    shown = total if (instant or k > 0.45) else int(total * k / 0.45) + 1
    y, n, box = HEAD_Y, 0, None
    for i, row in enumerate(rows):
        parts = rich(row)
        size = 108 if i == len(rows) - 1 else 80
        while True:   # 幅に収まるまで小さく
            f = font(FONT_HAND, size)
            tw = sum(d.textlength(p, font=f) for p, _ in parts)
            if tw <= W - 100 or size <= 56:
                break
            size -= 4
        x = (W - tw) / 2
        for p, hi in parts:
            x0 = x
            for ch in p:
                if n < shown:
                    d.text((x, y), ch, font=f, fill=ORANGE if hi else INK)
                x += d.textlength(ch, font=f); n += 1
            if hi:
                box = (x0, y, x, y + f.size * 1.15)
        y += (f.size + 22)
    return box


def hand_path(pts, prog, d, width=9, color=ORANGE):
    """手書きの線を prog（0〜1）まで書く"""
    if prog <= 0:
        return
    m = max(2, int(len(pts) * min(1, prog)))
    d.line(pts[:m], fill=color, width=width, joint="curve")


def ellipse_pts(box, pad=26, seed=0):
    import math, random
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2 + 4, (x1 - x0) / 2 + pad, (y1 - y0) / 2 + pad * .55
    pts = []
    for i in range(70):   # 1周より少し多く（手で囲んだように、始まりと終わりがずれる）
        a = -2.6 + i / 69 * (2 * math.pi + .5)
        r = 1 + .04 * math.sin(i * .5 + rnd.random())
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a) + i * .25))
    return pts


def underline_pts(box):
    x0, y0, x1, y1 = box
    return [(x0 - 6 + (x1 - x0 + 16) * i / 30, y1 + 4 - 6 * (i / 30) + 3 * ((i * 7) % 3 - 1) / 3) for i in range(31)]


def draw_marks(im, marks, k):
    """「？」がポンと出る: marks = [(x, y, 出る秒)]"""
    d = ImageDraw.Draw(im)
    for x, y, t in marks:
        if k < t:
            continue
        s = 1 + .5 * max(0, 1 - (k - t) / .12)
        f = font(FONT_HAND, int(120 * s))
        d.text((x - 30 * s, y - 60 * s), "？", font=f, fill=ORANGE, stroke_width=6, stroke_fill=PAPER)


def ease(u):
    u = min(1, max(0, u)); return 1 - (1 - u) ** 3


def draw_panel(im, frame, k=9.0, enter="slide"):
    x, y, w, h = PANEL
    fr = frame.resize((w, h), Image.LANCZOS)
    if enter == "punch" and k < .25:      # 最初の場面: ぐっと寄ってから落ちつく
        z = 1 + .07 * (1 - ease(k / .25))
        fr = fr.resize((int(w * z), int(h * z)), Image.LANCZOS)
        fr = fr.crop(((fr.width - w) // 2, (fr.height - h) // 2, (fr.width - w) // 2 + w, (fr.height - h) // 2 + h))
    if enter == "slide" and k < .28:      # 右からすべりこむ
        x += int(W * (1 - ease(k / .28)))
    im.paste(fr, (x, y))
    # 上下のふちを紙の色になじませる
    fade = Image.new("RGBA", (w, 40), PAPER + (0,))
    for yy in range(40):
        ImageDraw.Draw(fade).line([(0, yy), (w, yy)], fill=PAPER + (int(255 * (1 - yy / 40)),))
    im.alpha_composite(fade, (x, y))
    im.alpha_composite(fade.transpose(Image.FLIP_TOP_BOTTOM), (x, y + h - 40))


def draw_sub(im, text, k=9.0):
    """字幕: 黒い箱に白い字。出るときに少し下からふわっと"""
    d = ImageDraw.Draw(im)
    f = font(FONT_SUB, 50)
    dy = int(18 * (1 - ease(k / .15)))
    rows = text.split("\n")
    for i, row in enumerate(rows):
        tw = d.textlength(row, font=f)
        bx, by = (W - tw) / 2 - 22, SUB_Y + i * 78 + dy
        d.rounded_rectangle([bx, by - 8, bx + tw + 44, by + 64], 12, fill=INK)
        d.text((bx + 22, by), row, font=f, fill=(255, 255, 255))


_thumbs = None
WALL_T = 2.0    # サムネイルが並び終わる秒
def wall(k):
    """最後: 23本のサムネイルが順に並ぶ"""
    global _thumbs
    if _thumbs is None:
        _thumbs = [Image.open(LES / n / f"{n}_サムネイル.jpg").convert("RGB").resize((240, 135), Image.LANCZOS) for n in LESSONS]
    x, y, w, h = PANEL
    img = Image.new("RGB", (w, h), PAPER)
    cols, tw, th, gap = 4, 240, 135, 20
    ox = (w - cols * tw - (cols - 1) * gap) / 2
    n = min(len(_thumbs), int(k / WALL_T * len(_thumbs)) + 1)
    for i in range(n):
        c, r = i % cols, i // cols
        t = _thumbs[i]
        sh = Image.new("RGBA", (tw + 16, th + 16), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([8, 10, tw + 8, th + 12], fill=(0, 0, 0, 60))
        img.paste(sh.filter(ImageFilter.GaussianBlur(4)), (int(ox + c * (tw + gap)) - 8, int(40 + r * (th + gap)) - 8), sh.filter(ImageFilter.GaussianBlur(4)))
        img.paste(t, (int(ox + c * (tw + gap)), int(40 + r * (th + gap))))
    if k >= WALL_T + .15:     # 「23本」のはんこ
        u = k - WALL_T - .15; sc = 1 + .6 * max(0, 1 - u / .14)
        d = ImageDraw.Draw(img); f = font(FONT_HAND, int(130 * sc))
        msg = "全23本"; tw2 = d.textlength(msg, font=f)
        bw, bh = tw2 + 70, f.size * 1.25 + 40; bx0, by0 = (w - bw) / 2, 330 - bh / 2; bx1, by1 = bx0 + bw, by0 + bh
        d.rounded_rectangle([bx0, by0, bx1, by1], 28, fill=PAPER, outline=ORANGE, width=9)
        d.text((bx0 + 35, by0 + 14), msg, font=f, fill=ORANGE)
    return img


def clip_frames(src, start, dur, rect):
    x, y, w, h = rect
    pw, ph = PANEL[2], PANEL[3]
    cmd = [FFMPEG, "-v", "error", "-ss", str(start), "-t", f"{dur + 0.2:.3f}", "-i", str(src),
           "-vf", f"crop={w}:{h}:{x}:{y},scale={pw}:{ph},fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
    sz = pw * ph * 3
    return [Image.frombytes("RGB", (pw, ph), raw[i:i + sz]) for i in range(0, len(raw) - sz + 1, sz)]


# ── 組み立て ──
def build(stills=False):
    WORK.mkdir(parents=True, exist_ok=True)
    GAP, TAIL = 0.25, 1.5
    vs = voices()
    durs = [wav_len(v) + GAP for v in vs]; durs[-1] += TAIL
    total = sum(durs)
    t0s = [sum(durs[:i]) for i in range(len(durs))]
    print(f"長さ {total:.1f} 秒", [round(d, 2) for d in durs])
    bg = Image.new("RGBA", (W, H), PAPER)

    if stills:
        sd = WORK / "stills"; sd.mkdir(exist_ok=True)
    else:
        video = WORK / "video.mp4"
        enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(video)], stdin=subprocess.PIPE)
    events = []      # 効果音: (秒, 種類, 長さ・高さ)
    for si, sc in enumerate(SCENES):
        T = t0s[si]
        n = int(round(durs[si] * FPS))
        clips = sc.get("clips", [])
        per = n / max(1, len(clips))
        first = si == 0
        HW = 0.0 if first else 0.1                     # 見出しを書き始める秒
        MK0, MK1 = (0.3, 0.75) if first else (0.65, 0.9)   # 丸・下線を書く秒
        events += [(T, "thump" if first else "whoosh", 0)]
        if not first:
            events.append((T + HW, "write", 0.45))
        events.append((T + MK0, "stroke", MK1 - MK0))
        for mx, my, mt in sc.get("marks", []):
            events.append((T + mt, "pop", 0))
        if sc.get("magnet"):
            events.append((T + sc["magnet"], "magnet", 0))
        if sc.get("wall"):
            events += [(T + i * WALL_T / len(LESSONS), "tick", 1 + i / len(LESSONS) * .6) for i in range(len(LESSONS))]
            events += [(T + WALL_T + .15, "magnet", 0), (T + WALL_T + .2, "ding", 0)]
        cache = {}
        pick = sorted({0, int(.4 * FPS), int(1.0 * FPS), n - 1}) if stills else range(n)
        for fi in pick:
            k = fi / FPS
            im = bg.copy()
            if sc.get("wall"):
                draw_panel(im, wall(k), k)
            else:
                ci = min(len(clips) - 1, int(fi / per))
                if ci not in cache:
                    cache[ci] = clip_frames(*clips[ci][:2], per / FPS, clips[ci][2])
                frs = cache[ci]; j = fi - ci * per
                draw_panel(im, frs[min(int(j), len(frs) - 1)], k if ci == 0 else 9.0, "punch" if first else "slide")
            box = draw_head(im, sc["head"], k - HW, instant=first)
            if box:
                pts = ellipse_pts(box, seed=si) if first else underline_pts(box)
                hand_path(pts, (k - MK0) / (MK1 - MK0), ImageDraw.Draw(im))
            draw_marks(im, sc.get("marks", []), k)
            draw_sub(im, sc["sub"], k)
            if stills:
                im.convert("RGB").save(sd / f"s{si}_{fi:04d}.jpg", quality=88)
            else:
                enc.stdin.write(im.convert("RGB").tobytes())
        print(f"場面 {si + 1}/{len(SCENES)}", flush=True)
    if stills:
        return
    enc.stdin.close(); enc.wait()

    # 効果音（本編と同じペン・磁石の音。lemo-opuscar の sfx を使うので、その .venv で動かす）
    ef = WORK / "sfx_events.json"
    ef.write_text(json.dumps(dict(dur=total, ev=events)), encoding="utf-8")
    sfx_wav = WORK / "sfx.wav"
    subprocess.run([str(LEMO / ".venv" / "Scripts" / "python"), str(ROOT / "b_promo_sfx.py"), str(ef), str(sfx_wav)],
                   check=True, stdin=subprocess.DEVNULL)

    # 音: 声を並べ、効果音と BGM を下に。-14 LUFS に
    inputs, filt = [], []
    for i, v in enumerate(vs):
        inputs += ["-i", str(v)]
        ms = int(t0s[i] * 1000)
        filt.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    nb = len(vs)
    inputs += ["-stream_loop", "-1", "-i", str(BGM), "-i", str(sfx_wav)]
    filt.append(f"[{nb}:a]aresample=48000,volume={BGM_DB}dB,atrim=0:{total:.3f},afade=t=out:st={total - 1.5:.3f}:d=1.5[b]")
    filt.append(f"[{nb + 1}:a]aresample=48000,volume={SFX_DB}dB[s]")
    filt.append("".join(f"[a{i}]" for i in range(nb)) + f"[b][s]amix=inputs={nb + 2}:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11[o]")
    mix = WORK / "mix.wav"
    subprocess.run([FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[o]", "-ar", "48000",
                    "-t", f"{total:.3f}", str(mix)], check=True, stdin=subprocess.DEVNULL)
    out = OUT / "科目B講座_宣伝_リール・ショート.mp4"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(video), "-i", str(mix), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True, stdin=subprocess.DEVNULL)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", "0.6", "-i", str(out), "-frames:v", "1", str(OUT / "科目B講座_宣伝_表紙.jpg")],
                   check=True, stdin=subprocess.DEVNULL)
    print("できた:", out)


if __name__ == "__main__":
    build(stills="--stills" in sys.argv)
