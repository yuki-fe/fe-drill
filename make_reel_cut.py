"""長い MV から、3分以内のリール版を切り抜く（用語サイトの宣伝つき）。

- 曲の小節の区切りで切った部分をつなぐ（つなぎ目は映像も音も少し重ねる）
- 画面のいちばん上に、用語サイトの小さな案内を出しておく
- 最後に、用語サイトの宣伝の画面（PROMO_SEC 秒）を入れ、終わりは映像も音もフェードアウトする
曲を作り直さず、できあがった MV のファイルから切り抜く。

    python make_reel_cut.py
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import imageio_ffmpeg
from mv_common import BG1, CELL, CREAM, GOLD, GREEN, BLUE, MUTED, font, mix

ROOT = Path(__file__).parent
SONGS_DIR = ROOT / "notes" / "曲の動画"
WORK = SONGS_DIR / "作業用"                 # 背景の動画・宣伝の画像など
FOLDER = {"ストラテジ・アイランド": "ストラテジ・アイランド（商用不可）"}   # 曲名とフォルダ名がちがうもの


def song_dir(name):
    return SONGS_DIR / FOLDER.get(name, name)
W, H, FPS = 1080, 1920, 60

# 名前: (切る部分 [(開始秒, 終了秒), ...], 宣伝の画面の背景にする MV の秒, 宣伝の画面のあいだに流す曲の部分の開始秒)
# ストラテジ・アイランド: 小節の区切り（136BPM・1小節 1.765秒）で切る。① SWOT〜サビ2 ② ラストサビ
CUTS = {
    "ストラテジ・アイランド": ([(38.97, 167.79), (206.62, 229.56)], 262.0, 229.56),
    # 新しい音源（72.75BPM・1小節 3.299秒）。① SWOT〜サビ2 ② ラストサビ
    "ワン・ラブ・ストラテジ": ([(26.62, 158.58), (191.57, 217.96)], 225.0, 217.96),
    # クリティカルパス（136BPM・1小節 1.765秒）。① 冬の駅前〜1回目のサビ ② ブリッジ（EVM）〜最後のサビ〜アウトロ
    "クリティカルパス": ([(12.57, 104.34), (178.45, 254.33)], 262.0, 254.33),
    # コミットしないで（68BPM・1小節 3.529秒）。① 2進数〜1回目のサビ ② ブリッジ〜最後のサビ〜アウトロ（曲の終わりまで）
    # 曲がアウトロのすぐあとで終わるので、宣伝の画面のあいだは音なし（None）
    "コミットしないで": ([(11.41, 99.64), (184.35, 254.0)], 250.0, None),
}
# --shorts のときは YouTube ショート用（案内の文を「チャンネルのリンクから」に、ファイル名を _ショート に）
LINK_TEXT = "プロフィールのリンクから"
OUT_SUFFIX = "_リール"
XFADE = 0.4      # つなぎ目で重ねる秒数
PROMO_SEC = 6.0  # 宣伝の画面の長さ
FADE_OUT = 2.0   # 最後のフェードアウトの秒数
SITES = [("ITパスポート用語ドリル", "ip.yogo-drill.com", GREEN), ("FE用語ドリル", "fe.yogo-drill.com", BLUE)]


def grab(src, t):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return Image.frombytes("RGB", (W, H), raw[: W * H * 3])


def promo_card(bg, path):
    """宣伝の画面: MV の最後の映像をぼかして暗くし、サイトの名前とアドレスを出す。"""
    img = bg.filter(ImageFilter.GaussianBlur(14))
    img = Image.blend(img, Image.new("RGB", (W, H), BG1), 0.62)
    d = ImageDraw.Draw(img)

    def text(y, s, size, col, bold=True):
        d.text((W / 2, y), s, font=font(size, bold), fill=col, anchor="mm")

    text(430, "用語の意味は、サイトで確認", 60, CREAM)
    text(510, "この曲に出てきた用語も、まとめて覚えられる", 36, MUTED, False)
    for k, (name, url, col) in enumerate(SITES):
        y = 680 + k * 250
        d.rounded_rectangle((110, y - 90, W - 110, y + 110), radius=30, fill=mix(BG1, CELL, 0.9), outline=col, width=5)
        text(y - 20, name, 56, CREAM)
        text(y + 55, url, 46, GOLD)
    for k, s in enumerate(["カード・4択・書いて答える", "無料・登録なし・スマホで使える"]):
        text(1260 + k * 70, s, 40, CREAM, False)
    d.rounded_rectangle((200, 1430, W - 200, 1530), radius=50, fill=GOLD)
    text(1480, LINK_TEXT, 44, BG1)
    img.save(path)


def banner(path):
    """画面のいちばん上に出す、小さな案内（透明な PNG）。"""
    img = Image.new("RGBA", (W, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = f"ITパスポート・FE用語ドリル（無料）｜{LINK_TEXT}"
    f = font(30, True)
    tw = f.getlength(s)
    d.rounded_rectangle(((W - tw) / 2 - 26, 30, (W + tw) / 2 + 26, 86), radius=28, fill=(10, 20, 18, 170))
    d.text((W / 2, 58), s, font=f, fill=(244, 234, 213, 255), anchor="mm")
    img.save(path)


def cut(name, segs, promo_at, promo_audio):
    src = song_dir(name) / f"{name}_MV.mp4"
    out = song_dir(name) / f"{name}{OUT_SUFFIX}.mp4"
    tmp = WORK
    tmp.mkdir(exist_ok=True)
    card, ban = tmp / f"{name}_宣伝{OUT_SUFFIX}.png", tmp / f"上の案内{OUT_SUFFIX}.png"
    # 宣伝の画面の背景は、文字の入っていない背景の映像から取る（なければ MV から）
    bgv = tmp / f"{name}_MV_背景.mp4"
    promo_card(grab(bgv if bgv.exists() else src, promo_at), card)
    banner(ban)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    L = [b - a for a, b in segs] + [PROMO_SEC]
    fc = []
    for k, (a, b) in enumerate(segs):
        fc.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={FPS}[v{k}]")
        fc.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{k}]")
    n = len(segs)
    # 宣伝の画面（静止画）と、そのあいだに流す曲の続き
    fc.append(f"[1:v]scale={W}:{H},setsar=1,format=yuv420p,trim=duration={PROMO_SEC},setpts=PTS-STARTPTS,fps={FPS}[v{n}]")
    if promo_audio is None:
        fc.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={PROMO_SEC}[a{n}]")
    else:
        fc.append(f"[0:a]atrim={promo_audio}:{promo_audio + PROMO_SEC},asetpts=PTS-STARTPTS[a{n}]")
    vlast, alast, total = "v0", "a0", L[0]
    for k in range(1, n + 1):
        off = total - XFADE
        fc.append(f"[{vlast}]format=yuv420p[p{k}];[v{k}]format=yuv420p[q{k}];[p{k}][q{k}]xfade=transition=fade:duration={XFADE}:offset={off:.3f}[x{k}]")
        fc.append(f"[{alast}][a{k}]acrossfade=d={XFADE}[y{k}]")
        vlast, alast = f"x{k}", f"y{k}"
        total = off + L[k]
    fc.append(f"[{vlast}][2:v]overlay=0:0:format=auto[ov]")
    fc.append(f"[ov]fade=t=out:st={total - FADE_OUT:.3f}:d={FADE_OUT}[vout]")
    fc.append(f"[{alast}]afade=t=out:st={total - FADE_OUT:.3f}:d={FADE_OUT}[aout]")
    work = out.with_name(out.stem + "_作成中.mp4")
    cmd = [ff, "-y", "-loglevel", "error", "-i", str(src), "-loop", "1", "-i", str(card), "-loop", "1", "-i", str(ban),
           "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(work)]
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"切り抜きに失敗しました: {name}")
    if out.exists():
        out.replace(out.with_name(out.stem + "_前の版.mp4"))
    work.replace(out)
    print(f"{out}  {total:.1f} 秒")


if __name__ == "__main__":
    # 名前を指定すると、その曲だけ作る（例: python make_reel_cut.py ワン・ラブ・ストラテジ）
    args = sys.argv[1:]
    if "--shorts" in args:
        args.remove("--shorts")
        LINK_TEXT, OUT_SUFFIX = "チャンネルのリンクから", "_ショート"
    for name in args or list(CUTS):
        segs, promo_at, promo_audio = CUTS[name]
        cut(name, segs, promo_at, promo_audio)
