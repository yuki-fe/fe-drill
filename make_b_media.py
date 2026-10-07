"""科目Bのトレースとアルゴリズム図鑑から、SNS 用の素材を作る。

作るもの:
  ・リール動画（1080×1920 の縦動画。Instagram リールと YouTube ショートで共用）
      static/ig/reels/〇〇.mp4、表紙の static/ig/reels/〇〇.jpg、一覧の static/ig/reels.json
  ・トレースクイズの画像（2枚組: 問題 → 答え）
      static/ig/trace/〇〇-q.jpg・-a.jpg、一覧の static/ig/trace-posts.json

使い方:  python build.py            （先にビルドして、最新の問題データを docs/assets に入れる）
         python make_b_media.py     （リール動画を8本と、トレースクイズを全問ぶん作る）
         python make_b_media.py 16  （リール動画を16本まで作る。動画は1本 1〜3MB なので、少しずつ増やす）

プログラムの動きは、サイトと同じインタプリタ（docs/assets/pseudo.js）を Edge で動かして取り出す。
動画の変換には ffmpeg を使う（猫動画プロジェクトの .venv にある imageio-ffmpeg、または環境変数 FFMPEG）。
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
OUT = ROOT / "static" / "ig"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
BASE = CONFIG["base_url"].rstrip("/")

W, H, FPS = 1080, 1920, 10
PAPER, BG, INK, MUTED, LINE = "#fbfcfa", "#f1f4f1", "#1d2a2e", "#5d6c6e", "#d5ddd8"
MARK, MARK_SOFT, OK, OK_SOFT, HL = "#c0435a", "#f6dfe3", "#2b7a68", "#d9eee8", "#fff1b8"
FONT_R = "C:/Windows/Fonts/BIZ-UDGothicR.ttc"
FONT_B = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"
REEL_TAGS = "#基本情報技術者試験 #科目B #擬似言語 #アルゴリズム #トレース #プログラミング学習 #情報系学生 #IT資格"


def font(size, bold=False, mono=False):
    # index=0 は等幅の BIZ UDゴシック（プログラム用）、index=1 は文字幅が変わる BIZ UDPゴシック
    return ImageFont.truetype(FONT_B if bold else FONT_R, size, index=0 if mono else 1)


# ---------- プログラムの動きを取り出す（Edge でサイトのインタプリタを動かす） ----------

def find_edge():
    for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]:
        if Path(p).exists():
            return p
    sys.exit("Microsoft Edge が見つかりません")


def find_ffmpeg():
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    found = sorted((ROOT.parent.parent / "cat-video" / ".venv").glob("Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg*.exe"))
    if found:
        return str(found[0])
    sys.exit("ffmpeg が見つかりません。環境変数 FFMPEG に ffmpeg.exe の場所を入れてください")


def export_runs():
    """trace と algorithms を全部動かし、1行ごとの状態を JSON で受け取る。"""
    page = ROOT / "checks" / "b-events.html"
    page.parent.mkdir(exist_ok=True)
    page.write_text("""<!doctype html><meta charset="utf-8"><pre id="out"></pre>
<script src="../docs/assets/pseudo.js"></script><script src="../docs/assets/b-data.js"></script>
<script>
const items = [].concat(
  FE_B.trace.map((t) => ({ kind: "trace", id: t.id, title: t.title, code: t.code, main: t.main, line: t.line, vars: t.vars })),
  FE_B.algorithms.map((a) => ({ kind: "algo", id: a.slug, title: a.title, code: a.code, main: a.main })));
items.forEach((it) => {
  const r = Pseudo.run(it.code.concat(it.main).join("\\n"));
  it.events = r.events.map((e) => ({ phase: e.phase, line: e.line, fn: e.fn, depth: e.depth, vars: e.vars, globals: e.globals, out: e.out }));
  it.output = r.output;
  it.error = r.error ? r.error.message : null;
});
document.getElementById("out").textContent = JSON.stringify(items);
</script>""", encoding="utf-8")
    with tempfile.TemporaryDirectory() as prof:
        res = subprocess.run([find_edge(), "--headless=new", "--disable-gpu", f"--user-data-dir={prof}",
                              "--allow-file-access-from-files", "--virtual-time-budget=20000", "--dump-dom", page.resolve().as_uri()],
                             capture_output=True, timeout=120)
    m = re.search(r'<pre id="out">(.*?)</pre>', res.stdout.decode("utf-8", "replace"), re.S)
    if not m or not m.group(1).strip():
        sys.exit("プログラムの動きを取り出せませんでした。先に python build.py を実行してください")
    items = json.loads(html.unescape(m.group(1)))
    for it in items:
        if it["error"]:
            sys.exit(f"{it['kind']} {it['id']} の実行でエラー: {it['error']}")
    return items


def fmt(v):
    if v is None or (isinstance(v, dict) and v.get("undef")):
        return "未定義"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "{" + ", ".join(fmt(x) for x in v) + "}"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def args_of(it):
    """最初に呼ばれた関数に渡された値（引数）。"""
    for e in it["events"]:
        if e["depth"] == 1 and e["phase"] == "line":
            return e["fn"], e["vars"]
    return "", {}


# ---------- 描画の部品 ----------

def pill(d, x, y, text, color, size=34):
    f = font(size, True)
    w = f.getlength(text)
    d.rounded_rectangle((x, y, x + w + 52, y + size + 30), radius=(size + 30) // 2, fill=color)
    d.text((x + 26, y + 13), text, font=f, fill=PAPER)
    return y + size + 30


def wrap(text, f, width):
    lines, cur = [], ""
    for ch in text:
        if f.getlength(cur + ch) > width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def draw_code(d, code, x, y, w, cur=None, mark=None, size=30):
    f, fn = font(size, mono=True), font(size - 8, mono=True)
    lh = int(size * 1.62)
    rows = [ln for ln in code]
    d.rounded_rectangle((x, y, x + w, y + lh * len(rows) + 36), radius=18, fill=PAPER, outline=LINE, width=2)
    yy = y + 18
    for i, ln in enumerate(rows, 1):
        if i == cur:
            d.rectangle((x + 2, yy, x + w - 2, yy + lh), fill=HL)
        elif i == mark:
            d.rectangle((x + 2, yy, x + w - 2, yy + lh), fill=MARK_SOFT)
        d.text((x + 58 - fn.getlength(str(i)), yy + (lh - fn.size) // 2), str(i), font=fn, fill=INK if i == cur else MUTED)
        text = ln
        while f.getlength(text) > w - 96 and len(text) > 4:
            text = text[:-2] + "…"
        d.text((x + 80, yy + (lh - size) // 2 - 2), text, font=f, fill=INK)
        yy += lh
    return yy + 18


def draw_value(d, x, y, v, prev, size=30, max_w=640):
    """配列はマス目（下に番号）、それ以外は文字。変わった値は緑にする。"""
    f = font(size, True, mono=True)
    if isinstance(v, list) and all(not isinstance(e, list) for e in v):
        cx, cw = x, max(64, int(f.getlength("00")) + 28)
        for i, e in enumerate(v):
            if cx + cw > x + max_w:
                d.text((cx, y + 8), "…", font=f, fill=MUTED)
                break
            changed = isinstance(prev, list) and (i >= len(prev) or fmt(prev[i]) != fmt(e))
            d.rounded_rectangle((cx, y, cx + cw - 6, y + size + 46), radius=8, fill=OK_SOFT if changed else PAPER, outline=OK if changed else LINE, width=2)
            t = fmt(e)
            d.text((cx + (cw - 6 - f.getlength(t)) / 2, y + 6), t, font=f, fill=OK if changed else INK)
            fi = font(18)
            d.text((cx + (cw - 6 - fi.getlength(str(i + 1))) / 2, y + size + 20), str(i + 1), font=fi, fill=MUTED)
            cx += cw
        return y + size + 56
    t = fmt(v)
    changed = prev is not None and fmt(prev) != t
    tw = f.getlength(t)
    if changed:
        d.rounded_rectangle((x - 8, y - 4, x + tw + 10, y + size + 12), radius=8, fill=OK_SOFT)
    d.text((x, y), t, font=f, fill=OK if changed else INK)
    return y + size + 22


# ---------- リール動画 ----------

def reel_frames(it):
    code_len = len(it["code"])
    steps = [e for e in it["events"] if e["phase"] == "line" and e["line"] <= code_len]
    return steps, it["events"][-1] if it["events"] else None


def code_size(code, width, height):
    """いちばん長い行が幅に収まり、全体が高さに収まる、いちばん大きい文字サイズ。"""
    for size in (38, 36, 34, 32, 30, 28, 26, 24, 22):
        f = font(size, mono=True)
        if max(f.getlength(ln) for ln in code) <= width and len(code) * int(size * 1.62) + 36 <= height:
            return size
    return 22


def draw_step(it, no, step, prev, idx, total, fn, args):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    label = f"科目B トレース No.{no}" if it["kind"] == "trace" else "科目B アルゴリズム図鑑"
    pill(d, 60, 90, label, MARK, 32)
    tf = font(56, True)
    d.text((60, 176), wrap(it["title"], tf, W - 160)[0], font=tf, fill=INK)
    # 渡す値
    y = 272
    d.text((60, y), f"{fn} に渡す値", font=font(30, True), fill=MUTED)
    y += 50
    for k, v in list(args.items())[:2]:
        d.text((60, y + 8), k, font=font(34, True, mono=True), fill=MUTED)
        y = draw_value(d, 240, y, v, None, 32, 760)
    y += 12
    size = code_size(it["code"], W - 120 - 96, 1440 - y - 300)
    cur = step["line"] if step else None
    y = draw_code(d, it["code"], 60, y, W - 120, cur=cur, mark=it.get("line"), size=size)
    legend_f = font(26)
    lx = 60
    d.rectangle((lx, y + 14, lx + 28, y + 42), fill=HL)
    d.text((lx + 40, y + 12), "いま実行する行", font=legend_f, fill=MUTED)
    if it.get("line"):
        lx += 270
        d.rectangle((lx, y + 14, lx + 28, y + 42), fill=MARK_SOFT)
        d.text((lx + 40, y + 12), "問題で聞かれる行", font=legend_f, fill=MUTED)
    lx += 300
    d.rectangle((lx, y + 14, lx + 28, y + 42), fill=OK_SOFT)
    d.text((lx + 40, y + 12), "変わった値", font=legend_f, fill=MUTED)
    # 変数
    y += 84
    d.text((60, y), "変数", font=font(30, True), fill=MUTED)
    y += 54
    vars_ = (step or {}).get("vars") or {}
    pvars = (prev or {}).get("vars") or {}
    same = prev is not None and step is not None and prev["fn"] == step["fn"] and prev["depth"] == step["depth"]
    shown = list(vars_.items()) + (list(step["globals"].items()) if step and step.get("globals") else [])
    for k, v in shown[:7]:
        if y > 1440:
            break
        d.line((60, y - 12, W - 60, y - 12), fill=LINE, width=2)
        d.text((60, y + 4), k, font=font(36, True, mono=True), fill=MUTED)
        pv = pvars.get(k) if same else None
        if pv is None and step and step.get("globals") and prev and prev.get("globals"):
            pv = prev["globals"].get(k)
        y = draw_value(d, 320, y, v, pv, 36, 680)
    if not shown:
        d.text((60, y), "（まだありません）", font=font(32), fill=MUTED)
    # 進み具合と案内（Instagram の画面下のボタンに隠れない高さに置く）
    d.rounded_rectangle((60, 1490, W - 60, 1504), radius=7, fill=LINE)
    d.rounded_rectangle((60, 1490, 60 + int((W - 120) * (idx + 1) / max(1, total)), 1504), radius=7, fill=MARK)
    d.text((60, 1520), f"手順 {idx + 1} / {total}" + (f"    {cur}行目" if cur else ""), font=font(30, mono=True), fill=MUTED)
    where = f"▶ サイトで自分で動かせる｜トレース練習 No.{no}" if it["kind"] == "trace" else f"▶ サイトで自分で動かせる｜図鑑「{it['title']}」"
    d.rounded_rectangle((60, 1576, W - 160, 1640), radius=32, fill=PAPER, outline=MARK, width=3)
    d.text((88, 1590), wrap(where, font(30, True), W - 280)[0], font=font(30, True), fill=MARK)
    return img


def draw_intro(it, no, fn, args):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 300, W - 60, 1400), radius=40, fill=PAPER, outline=LINE, width=2)
    pill(d, 120, 360, "基本情報技術者試験 科目B", MARK, 32)
    y = 480
    for ln in ["このプログラム、", "動きを追える？"]:
        d.text((120, y), ln, font=font(92, True), fill=INK)
        y += 130
    y += 40
    for ln in wrap(it["title"], font(54, True), W - 260):
        d.text((120, y), ln, font=font(54, True), fill=MARK)
        y += 76
    y += 30
    d.text((120, y), "1行ずつ再生して、変数の動きを見てみよう", font=font(36), fill=MUTED)
    return img


def draw_outro(it, no, output):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 260, W - 60, 1460), radius=40, fill=PAPER, outline=LINE, width=2)
    pill(d, 120, 320, "実行の結果", OK, 32)
    y = 430
    res = " / ".join(output) if output else "（表示なし）"
    for ln in wrap(res, font(64, True, mono=True), W - 260)[:3]:
        d.text((120, y), ln, font=font(64, True, mono=True), fill=INK)
        y += 86
    y += 60
    d.line((120, y, W - 120, y), fill=LINE, width=3)
    y += 60
    for ln in ["自分のペースで1行ずつ", "動かして確かめよう"]:
        d.text((120, y), ln, font=font(66, True), fill=INK)
        y += 92
    y += 40
    where = f"FE用語ドリル｜トレース練習 No.{no}" if it["kind"] == "trace" else f"FE用語ドリル｜アルゴリズム図鑑「{it['title']}」"
    for ln in wrap(where, font(40, True), W - 260):
        d.text((120, y), ln, font=font(40, True), fill=MARK)
        y += 58
    d.text((120, y + 20), "プロフィールのリンクから（無料）", font=font(36), fill=MUTED)
    return img


def encode(frames, path, ffmpeg):
    """frames: [(PIL.Image, 秒数)] を、無音の音声付き MP4（H.264 / yuv420p）にする。"""
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
           "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for img, sec in frames:
        data = img.tobytes()
        for _ in range(max(1, round(sec * FPS))):
            p.stdin.write(data)
    p.stdin.close()
    if p.wait() != 0:
        sys.exit(f"動画の変換に失敗しました: {path.name}")


def make_reel(it, no, ffmpeg):
    fn, args = args_of(it)
    steps, last = reel_frames(it)
    total = len(steps)
    per = min(0.9, max(0.2, 16 / max(1, total)))
    frames = [(draw_intro(it, no, fn, args), 2.5)]
    prev = None
    cover = None
    for i, s in enumerate(steps):
        img = draw_step(it, no, s, prev, i, total, fn, args)
        frames.append((img, per))
        if cover is None and i >= total * 0.4:
            cover = img
        prev = s
    frames.append((draw_step(it, no, None if not last else dict(last, line=0), prev, total - 1, total, fn, args), 1.0))
    frames.append((draw_outro(it, no, it["output"]), 3.5))
    key = f"{it['kind']}-{it['id']}"
    (OUT / "reels").mkdir(parents=True, exist_ok=True)
    mp4 = OUT / "reels" / f"{key}.mp4"
    encode(frames, mp4, ffmpeg)
    (cover or frames[0][0]).convert("RGB").save(OUT / "reels" / f"{key}.jpg", "JPEG", quality=85)
    seconds = sum(round(s * FPS) for _, s in frames) / FPS
    return key, seconds


def reel_post(it, no, key, seconds):
    if it["kind"] == "trace":
        page = f"b/trace.html?utm_source=youtube&utm_medium=video&utm_campaign=reel-{it['id']}#{it['id']}"
        where = f"「FE用語ドリル」のトレース練習 No.{no}"
        head = f"【科目B トレース No.{no}】{it['title']}"
    else:
        page = f"b/algorithms/{it['id']}.html?utm_source=youtube&utm_medium=video&utm_campaign=reel-{it['id']}"
        where = f"「FE用語ドリル」のアルゴリズム図鑑「{it['title']}」"
        head = f"【科目B アルゴリズム】{it['title']}"
    vars_note = "、".join(it.get("vars") or [])
    body = f"変数 {vars_note} がどう変わるか、1行ずつ再生しています。" if vars_note else "変数がどう変わるか、1行ずつ再生しています。"
    caption = (f"{head}\nこのプログラム、動きを追えた？\n{body}\n\n"
               f"▶ この問題は{where}で、自分のペースで1行ずつ動かしながら解けます（無料）。\n"
               "プロフィールのリンク →「科目B」から\n\n" + REEL_TAGS)
    yt_title = f"【基本情報 科目B】{it['title']}｜トレースを1行ずつ再生 #Shorts"
    yt_desc = (f"{head}\n{body}\n\n"
               f"▶ 1行ずつ自分で動かして解く（無料）: {BASE}/{page}\n\n"
               "基本情報技術者試験（FE）の科目B対策。擬似言語のプログラムの動きを、変数の変化とあわせて見せています。\n\n" + REEL_TAGS + " #Shorts")
    return {"key": key, "kind": it["kind"], "id": it["id"], "title": it["title"], "seconds": seconds,
            "video": f"{BASE}/ig/reels/{key}.mp4", "cover": f"{BASE}/ig/reels/{key}.jpg",
            "caption": caption, "youtube": {"title": yt_title[:100], "description": yt_desc}}


# ---------- トレースクイズの画像（2枚組） ----------

def trace_quiz(it, no):
    fn, args = args_of(it)
    rows = [e for e in it["events"] if e["phase"] == "after" and e["line"] == it["line"]]
    def val(e, v):
        if v in e["vars"]:
            return e["vars"][v]
        return (e.get("globals") or {}).get(v)
    for side in ("q", "a"):
        img = Image.new("RGB", (W, 1350), BG)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((40, 40, W - 40, 1310), radius=36, fill=PAPER, outline=LINE, width=2)
        pill(d, 84, 80, f"科目B トレースクイズ No.{no}" if side == "q" else f"答え No.{no}", MARK if side == "q" else OK, 30)
        d.text((84, 160), it["title"], font=font(44, True), fill=INK)
        y = 230
        argtext = "、".join(f"{k} = {fmt(v)}" for k, v in args.items())
        for ln in wrap(f"{fn}（{argtext}）を実行。{it['line']}行目を実行した直後の値を、順に書き出そう。", font(28), W - 170)[:3]:
            d.text((84, y), ln, font=font(28), fill=MUTED)
            y += 42
        y += 10
        size = 24 if len(it["code"]) > 13 else 26
        y = draw_code(d, it["code"], 84, y, W - 168, mark=it["line"], size=size)
        y += 20
        cols = ["回目"] + it["vars"]
        cw = (W - 168) // len(cols)
        rh = 50
        f = font(26, True, mono=True)
        for c, name in enumerate(cols):
            d.rectangle((84 + c * cw, y, 84 + (c + 1) * cw, y + rh), fill=BG, outline=LINE, width=2)
            d.text((84 + c * cw + (cw - f.getlength(name)) / 2, y + 12), name, font=f, fill=MUTED)
        for r, e in enumerate(rows[:6]):
            yy = y + rh * (r + 1)
            cells = [str(r + 1)] + [fmt(val(e, v)) if side == "a" else "" for v in it["vars"]]
            for c, t in enumerate(cells):
                d.rectangle((84 + c * cw, yy, 84 + (c + 1) * cw, yy + rh), fill=PAPER, outline=LINE, width=2)
                if t:
                    while f.getlength(t) > cw - 12 and len(t) > 3:
                        t = t[:-2] + "…"
                    d.text((84 + c * cw + (cw - f.getlength(t)) / 2, yy + 12), t, font=f, fill=OK if (side == "a" and c) else INK)
        foot = "答えは次の画像 →" if side == "q" else "1行ずつの動きは、プロフィールのリンクから"
        d.text((W - 84 - font(28, True).getlength(foot), 1250), foot, font=font(28, True), fill=MARK if side == "q" else OK)
        d.text((84, 1250), "FE用語ドリル", font=font(28, True), fill=INK)
        (OUT / "trace").mkdir(parents=True, exist_ok=True)
        img.save(OUT / "trace" / f"{it['id']}-{side}.jpg", "JPEG", quality=84, optimize=True, progressive=True)
    caption = (f"【科目B トレースクイズ No.{no}】{it['title']}\n"
               f"{fn}（{argtext}）を実行したとき、{it['line']}行目を実行した直後の {'・'.join(it['vars'])} の値を順に書き出してみよう。\n\n"
               "答えは2枚目の画像へ。\n"
               "▶ プログラムが1行ずつ動く様子は「FE用語ドリル」のトレース練習で見られます（無料）。プロフィールのリンクから。\n\n"
               + REEL_TAGS)
    return {"no": no, "id": it["id"], "term": it["title"],
            "images": [f"{BASE}/ig/trace/{it['id']}-q.jpg", f"{BASE}/ig/trace/{it['id']}-a.jpg"], "caption": caption}


def main():
    reels_count = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    items = export_runs()
    traces = [it for it in items if it["kind"] == "trace"]
    algos = [it for it in items if it["kind"] == "algo"]
    no_of = {it["id"]: i + 1 for i, it in enumerate(traces)}

    posts = [trace_quiz(it, no_of[it["id"]]) for it in traces]
    (OUT / "trace-posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"トレースクイズ: {len(posts)} 投稿分（画像 {len(posts) * 2} 枚）")

    # リールの順番: トレース2本ごとに図鑑を1本はさむ
    order, ti, ai = [], 0, 0
    while ti < len(traces) or ai < len(algos):
        for _ in range(2):
            if ti < len(traces):
                order.append(traces[ti]); ti += 1
        if ai < len(algos):
            order.append(algos[ai]); ai += 1
    ffmpeg = find_ffmpeg()
    reels = []
    for it in order[:reels_count]:
        no = no_of.get(it["id"], 0)
        key, sec = make_reel(it, no, ffmpeg)
        reels.append(reel_post(it, no, key, sec))
        print(f"  リール {key}: {sec:.1f} 秒")
    keep = {r["key"] for r in reels}
    for f in (OUT / "reels").glob("*"):
        if f.stem not in keep:
            f.unlink()
    (OUT / "reels.json").write_text(json.dumps(reels, ensure_ascii=False, indent=1), encoding="utf-8")
    size = sum(f.stat().st_size for f in (OUT / "reels").glob("*.mp4")) / 1024 / 1024
    print(f"リール動画: {len(reels)} 本（{size:.1f} MB）")
    print("このあと python build.py を実行して、GitHub に Push してください")


if __name__ == "__main__":
    main()
