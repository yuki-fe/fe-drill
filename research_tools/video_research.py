r"""YouTube・Instagram の動画を、Claude が読める形（情報・字幕・文字起こし・静止画の一覧）にする。

  .venv\Scripts\python research_tools/video_research.py URL          # 1本の動画を調べる
  .venv\Scripts\python research_tools/video_research.py 動画.mp4     # 手元の動画ファイル（Instagram で保存したものなど）
  .venv\Scripts\python research_tools/video_research.py --search "基本情報 勉強" -n 15
  .venv\Scripts\python research_tools/video_research.py --list チャンネルや再生リストのURL -n 30

できたものは notes/動画の調査/ に置く（公開しない）。動画・音声のファイルは使ったら消す。
くわしい手順はスキル /video-research（.claude/skills/video-research/SKILL.md）。
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notes" / "動画の調査"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ASR_PY = ROOT / ".venv-asr" / "Scripts" / "python.exe"
FONT = "C:/Windows/Fonts/meiryo.ttc"
TILES = 36          # 静止画の数の上限（3×3 の一覧で4枚まで）
SUB_LANGS = ["ja", "ja-orig"]  # 英語までたのむと 429（取りすぎ）になりやすい


def ydl(**opts):
    base = {"quiet": True, "no_warnings": True, "noprogress": True, "ffmpeg_location": FFMPEG}
    base.update(opts)
    return yt_dlp.YoutubeDL(base)


def safe(s, n=40):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")[:n] or "video"


def hms(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def num(v):
    return "-" if v is None else f"{v:,}"


# ---- 検索・一覧 ----------------------------------------------------------

def list_videos(source, n, label):
    with ydl(extract_flat="in_playlist", playlistend=n) as y:
        info = y.extract_info(source, download=False)
    rows = []
    for e in (info.get("entries") or [])[:n]:
        url = e.get("url") or e.get("webpage_url") or ""
        if url and not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={e.get('id')}"
        rows.append({"title": e.get("title"), "channel": e.get("channel") or e.get("uploader"),
                     "views": e.get("view_count"), "duration": e.get("duration"), "url": url})
    lines = [f"# {label}", "", f"調べた日: {datetime.date.today()}", "",
             "| # | タイトル | チャンネル | 再生回数 | 長さ | URL |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        title = (r["title"] or "").replace("|", "／")
        dur = hms(r["duration"]) if r["duration"] else "-"
        lines.append(f"| {i} | {title} | {r['channel'] or '-'} | {num(r['views'])} | {dur} | {r['url']} |")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{datetime.date.today()}_{safe(label)}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n→ {path}")


# ---- 字幕 ----------------------------------------------------------------

def vtt_to_text(vtt):
    """VTT を「[mm:ss] 文」の行にする。自動字幕のくり返しは除く。"""
    out, last, t = [], None, 0
    for line in vtt.splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)[.,]\d+ -->", line) or re.match(r"(\d+):(\d+)[.,]\d+ -->", line)
        if m:
            g = [int(x) for x in m.groups()]
            t = g[0] * 3600 + g[1] * 60 + g[2] if len(g) == 3 else g[0] * 60 + g[1]
            continue
        if not line.strip() or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or line.strip().isdigit():
            continue
        text = re.sub(r"<[^>]+>", "", line).strip()
        if text and text != last:
            out.append(f"[{hms(t)}] {text}")
            last = text
    return "\n".join(out)


def get_subtitles(url, work):
    opts = {"skip_download": True, "writesubtitles": True, "writeautomaticsub": True,
            "subtitleslangs": SUB_LANGS, "subtitlesformat": "vtt", "outtmpl": str(work / "sub.%(ext)s")}
    try:
        with ydl(**opts) as y:
            y.download([url])
    except yt_dlp.utils.DownloadError as e:
        print("字幕を取れなかった:", e)
    subs = sorted(work.glob("sub*.vtt"), key=lambda p: (".ja" not in p.name, "orig" in p.name))
    if not subs:
        return None, None
    text = vtt_to_text(subs[0].read_text(encoding="utf-8", errors="replace"))
    lang = subs[0].name.split(".")[-2]
    for p in subs:
        p.unlink()
    return text, lang


# ---- 動画・音声 ----------------------------------------------------------

def download(url, work, fmt, name):
    with ydl(format=fmt, outtmpl=str(work / f"{name}.%(ext)s")) as y:
        y.download([url])
    files = [p for p in work.glob(f"{name}.*") if p.suffix not in (".part", ".ytdl")]
    return files[0] if files else None


def duration_of(path):
    r = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0


def contact_sheets(video, work, every):
    """数秒ごとの静止画を 3×3 の一覧にして、sheet_01.jpg… に書く。"""
    dur = duration_of(video)
    if dur <= 0:
        return []
    every = max(every, dur / TILES)
    times = [i * every + min(1, every / 2) for i in range(int(dur // every) + 1) if i * every < dur - 0.3][:TILES]
    frames = []
    for i, t in enumerate(times):
        f = work / f"f{i:03d}.jpg"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=480:-2", str(f)])
        if f.exists():
            frames.append((t, f))
    if not frames:
        return []
    w, h = Image.open(frames[0][1]).size
    font = ImageFont.truetype(FONT, max(18, w // 16))
    sheets = []
    for s in range(0, len(frames), 9):
        part = frames[s:s + 9]
        cols = 3
        rows = (len(part) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w + (cols + 1) * 8, rows * h + (rows + 1) * 8), "white")
        d = ImageDraw.Draw(sheet)
        for k, (t, f) in enumerate(part):
            x, y = 8 + (k % cols) * (w + 8), 8 + (k // cols) * (h + 8)
            sheet.paste(Image.open(f).convert("RGB").resize((w, h)), (x, y))
            label = hms(t)
            box = d.textbbox((x + 6, y + 6), label, font=font)
            d.rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3), fill="black")
            d.text((x + 6, y + 6), label, fill="white", font=font)
        p = work / f"sheet_{s // 9 + 1:02d}.jpg"
        sheet.save(p, quality=85)
        sheets.append(p)
    for _, f in frames:
        f.unlink()
    return sheets


def transcribe(media, work, model):
    if not ASR_PY.exists():
        print("文字起こしの .venv-asr がないので飛ばす")
        return None
    wav = work / "audio.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    if not wav.exists():
        return None
    out = work / "transcript.txt"
    print(f"文字起こし中（{model}）…", flush=True)
    subprocess.run([str(ASR_PY), str(ROOT / "research_tools" / "transcribe.py"), str(wav), str(out), "--model", model])
    wav.unlink()
    return out.read_text(encoding="utf-8") if out.exists() else None


# ---- 1本を調べる ---------------------------------------------------------

def research(src, args):
    local = Path(src).exists()
    if local:
        video = Path(src).resolve()
        info = {"title": video.stem, "webpage_url": str(video)}
        vid = safe(video.stem)
    else:
        opts = {"getcomments": args.comments > 0,
                "extractor_args": {"youtube": {"max_comments": [str(args.comments), "all", "0", "0"],
                                               "comment_sort": ["top"]}}}
        with ydl(**opts) as y:
            info = y.extract_info(src, download=False)
        vid = safe(f"{info.get('extractor_key', '')}_{info.get('id', 'video')}")
    work = OUT / f"{datetime.date.today()}_{vid}"
    work.mkdir(parents=True, exist_ok=True)

    meta = {k: info.get(k) for k in ("title", "channel", "uploader", "upload_date", "duration", "view_count",
                                     "like_count", "comment_count", "channel_follower_count", "tags",
                                     "categories", "webpage_url", "description")}
    (work / "info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    text, how = (None, None)
    if not local:
        text, lang = get_subtitles(src, work)
        how = f"字幕（{lang}）" if text else None
    video = video if local else None
    if not args.no_frames and not local:
        try:
            video = download(src, work, "bv*[height<=480]/b[height<=480]/wv*/w", "video")
        except yt_dlp.utils.DownloadError as e:
            print("動画を取れなかった:", e)
    sheets = contact_sheets(video, work, args.every) if video else []
    if not text and not args.no_asr:
        media = video
        if not local:
            try:
                media = download(src, work, "ba/b", "audio") if not video or not has_audio(video) else video
            except yt_dlp.utils.DownloadError as e:
                print("音声を取れなかった:", e)
        if media:
            text = transcribe(media, work, args.model)
            how = "音声の文字起こし（faster-whisper）" if text else None
    if not local:
        for p in work.glob("video.*"):
            p.unlink()
        for p in work.glob("audio.*"):
            p.unlink()
    if text:
        (work / "transcript.txt").write_text(text + "\n", encoding="utf-8")

    comments = sorted(info.get("comments") or [], key=lambda c: -(c.get("like_count") or 0))[:args.comments]
    lines = [f"# {meta['title']}", "",
             f"- URL: {meta['webpage_url']}",
             f"- チャンネル: {meta['channel'] or meta['uploader'] or '-'}（登録者 {num(meta['channel_follower_count'])}）",
             f"- 投稿日: {meta['upload_date'] or '-'}　長さ: {hms(meta['duration']) if meta['duration'] else '-'}",
             f"- 再生 {num(meta['view_count'])}　高評価 {num(meta['like_count'])}　コメント {num(meta['comment_count'])}",
             f"- タグ: {', '.join(meta['tags'] or []) or '-'}",
             f"- 中身の文字: {how or 'なし'}　静止画の一覧: {len(sheets)}枚",
             f"- 調べた日: {datetime.date.today()}", "",
             "## 説明文", "", (meta["description"] or "-").strip(), ""]
    if comments:
        lines += ["## コメント（高評価の多い順）", ""]
        lines += [f"- ({num(c.get('like_count'))}) {(c.get('text') or '').strip().replace(chr(10), ' ')}" for c in comments]
    (work / "info.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n→ {work}")
    for p in ["info.md", "transcript.txt"] + [s.name for s in sheets]:
        if (work / p).exists():
            print("  ", work / p)


def has_audio(video):
    r = subprocess.run([FFMPEG, "-i", str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return "Audio:" in r.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", help="動画の URL か、手元の動画ファイル")
    ap.add_argument("--search", help="YouTube をキーワードで検索して一覧にする")
    ap.add_argument("--new", action="store_true", help="--search を新しい順にする")
    ap.add_argument("--list", help="チャンネル・再生リストの動画を一覧にする")
    ap.add_argument("-n", type=int, default=15, help="一覧の数")
    ap.add_argument("--every", type=float, default=5, help="静止画の間隔（秒）。長い動画は自動で広げる")
    ap.add_argument("--comments", type=int, default=20, help="取るコメントの数（0 で取らない）")
    ap.add_argument("--no-frames", action="store_true", help="静止画を作らない（動画を取らない）")
    ap.add_argument("--no-asr", action="store_true", help="字幕がなくても文字起こしをしない")
    ap.add_argument("--model", default="large-v3-turbo", help="文字起こしのモデル（速くしたいときは small）")
    args = ap.parse_args()
    if args.search:
        prefix = "ytsearchdate" if args.new else "ytsearch"
        list_videos(f"{prefix}{args.n}:{args.search}", args.n, f"YouTube 検索「{args.search}」")
    elif args.list:
        list_videos(args.list, args.n, f"一覧 {args.list}")
    elif args.src:
        research(args.src, args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
