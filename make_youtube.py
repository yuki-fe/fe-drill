"""縦長の MV から、YouTube 用の横長の動画（1920×1080）・サムネイル・説明文を作る。

- まん中に縦長の MV（図と歌詞）を置き、左右は文字のない背景の映像をぼかして広げる
- 左に曲名と説明、右に用語サイトの宣伝を出す
- サムネイル（1280×720）と、チャプター（場面ごとの時間）つきの説明文も作る

    python make_youtube.py
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import imageio_ffmpeg
from mv_common import BG1, BLUE, CELL, CREAM, GOLD, GREEN, MUTED, font, mix

ROOT = Path(__file__).parent
SONGS_DIR = ROOT / "notes" / "曲の動画"
WORK = SONGS_DIR / "作業用"                 # 背景の動画・宣伝の画像など
FOLDER = {"ストラテジ・アイランド": "ストラテジ・アイランド（商用不可）"}   # 曲名とフォルダ名がちがうもの


def song_dir(name):
    return SONGS_DIR / FOLDER.get(name, name)
YW, YH = 1920, 1080
MVW = 608            # まん中の縦長の MV の幅（高さ 1080）
SIDE = (YW - MVW) // 2

SONGS = {
    "ストラテジ・アイランド": {
        "title": "Strategy Riddim", "sub": "〜ストラテジ・アイランド〜",
        "lead": ["ITパスポート・基本情報の", "ストラテジ系の用語を、", "歌と図で覚える"],
        "terms": ["SWOT分析・3C分析", "4P・4C・PPM", "損益分岐点・ROE", "KGI・KPI・BSC", "ERP・SCM・CRM・BPR", "パレート図・ABC分析", "著作権・特許・PL法", "CSR・コンプライアンス"],
        "thumb_at": 97.0,
        "thumb_big": ["ストラテジ系", "用語を歌で覚える"],
        "thumb_small": "SWOT・PPM・損益分岐点・ROE…",
        "chapters": [(0, "タイトル・イントロ"), (39, "SWOT分析"), (53, "3C分析"), (66, "4Pと4C"), (81, "PPM"),
                     (108, "損益分岐点"), (122, "ROEと流動比率"), (130, "KGI・KPI・バランススコアカード"),
                     (144, "ERP・SCM・CRM・BPR"), (171, "パレート図・ABC分析・特性要因図"),
                     (186, "著作権・特許・PL法・不正アクセス禁止法"), (207, "CSR・コンプライアンス"), (236, "アウトロ")],
        "yt_title": "【勉強ソング】ストラテジ系の用語を歌で覚える｜Strategy Riddim 〜ストラテジ・アイランド〜（ITパスポート・基本情報）",
        "tags": "#ITパスポート #基本情報技術者試験 #ストラテジ系 #勉強ソング #資格勉強",
        "desc": "ITパスポート試験・基本情報技術者試験のストラテジ系に出てくる用語を、歌にしました。",
    },
    "クリティカルパス": {
        "title": "クリティカルパス", "sub": "〜完了しなかったプロジェクト〜",
        "lead": ["プロジェクトマネジメントの", "用語で歌う、", "冬の歌"],
        "terms": ["ガントチャート・WBS", "スラック・クリティカルパス", "クラッシング・ファストトラッキング", "リスク対応の4つ",
                  "SLA・インシデント・問題管理", "EVM（PV・EV・AC）", "BCP・変更管理", "ベースライン・監査証跡"],
        "thumb_at": 100.0,
        "thumb_big": ["クリティカルパス", "PM用語で歌う冬の歌"],
        "thumb_small": "WBS・EVM・リスク対応・変更管理…",
        "chapters": [(0, "イントロ"), (13, "ガントチャート"), (42, "WBS"), (62, "スラック"), (72, "クリティカルパス（サビ）"),
                     (108, "リスク対応（回避・転嫁・軽減・受容）"), (122, "SLA・インシデント"), (138, "問題管理"),
                     (149, "クリティカルパス（サビ2）"), (178, "EVM・BCP"), (208, "変更管理・ベースライン"),
                     (240, "監査証跡"), (254, "エンディング")],
        "yt_title": "【勉強ソング】プロジェクトマネジメントの用語で歌う冬の歌｜クリティカルパス 〜完了しなかったプロジェクト〜（ITパスポート・基本情報）",
        "tags": "#ITパスポート #基本情報技術者試験 #プロジェクトマネジメント #勉強ソング #資格勉強",
        "desc": "ITパスポート試験・基本情報技術者試験のマネジメント系に出てくる、プロジェクトマネジメントやサービスマネジメントの用語を、冬の歌にしました。",
    },
}
# 新しい音源（ワン・ラブ・ストラテジ）: 用語は同じで、曲名・時間・チャプターがちがう
# （2026-10-22: 前の曲名のまま写していたので、曲名・タイトル・用語を分けた）
SONGS["ワン・ラブ・ストラテジ"] = dict(
    SONGS["ストラテジ・アイランド"], thumb_at=84.0,
    title="ワン・ラブ・ストラテジ", sub="〜One Love Strategy〜",
    yt_title="【勉強ソング】ストラテジ系の用語を歌で覚える｜ワン・ラブ・ストラテジ（ITパスポート・基本情報）",
    desc="ITパスポート試験・基本情報技術者試験のストラテジ系に出てくる用語を、レゲエの歌にしました。",
    terms=["SWOT分析・3C分析", "4P・4C・PPM", "損益分岐点・ROE・流動比率", "KGI・KPI・BSC",
           "ERP・SCM・CRM・コアコンピタンス・BPR", "パレート図・ABC分析・特性要因図",
           "著作権・特許・PL法・不正アクセス禁止法", "CSR・コンプライアンス"],
    chapters=[
    (0, "イントロ"), (29, "SWOT分析"), (44, "3C分析"), (55, "4Pと4C"), (69, "PPM"), (94, "損益分岐点"),
    (108, "ROEと流動比率"), (121, "KGI・KPI・バランススコアカード"), (136, "ERP・SCM・CRM・BPR"),
    (160, "パレート図・ABC分析・特性要因図"), (178, "著作権・特許・PL法・不正アクセス禁止法"),
    (192, "CSR・コンプライアンス"), (217, "エンディング")])
SONGS["コミットしないで"] = {
    "title": "コミットしないで", "sub": "〜夏の恋とコンピュータ〜",
    "lead": ["コンピュータの", "用語で歌う、", "夏の恋の歌"],
    "terms": ["2進数", "割り込み・優先度", "3ウェイハンドシェイク", "コミット・ロールバック・ACID",
              "キャッシュ・デッドロック", "排他制御", "二分探索・ping・バックアップ", "暗号化・秘密鍵"],
    "thumb_at": 80.0,
    "thumb_big": ["コミットしないで", "IT用語で歌う夏の恋"],
    "thumb_small": "ACID・デッドロック・暗号化…",
    "chapters": [(0, "イントロ"), (14, "2進数"), (41, "割り込みと優先度"), (57, "3ウェイハンドシェイク"),
                 (69, "コミットとロールバック（サビ）"), (102, "キャッシュ"), (130, "デッドロック"), (145, "排他制御"),
                 (158, "コミットとロールバック（サビ2）"), (186, "二分探索・ping・フルバックアップ"),
                 (216, "暗号化と秘密鍵"), (245, "アウトロ")],
    "yt_title": "【勉強ソング】コンピュータの用語で歌う夏の恋の歌｜コミットしないで（ITパスポート・基本情報）",
    "tags": "#ITパスポート #基本情報技術者試験 #テクノロジ系 #勉強ソング #資格勉強",
    "desc": "ITパスポート試験・基本情報技術者試験のテクノロジ系に出てくる、2進数・ネットワーク・データベース・セキュリティの用語を、夏の恋の歌にしました。",
}
SITES = [("ITパスポート用語ドリル", "https://ip.yogo-drill.com/", GREEN), ("FE用語ドリル", "https://fe.yogo-drill.com/", BLUE)]


def grab(src, t, w, h):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), raw[: w * h * 3])


def panels(info, path):
    """左右の文字（まん中は透明）。"""
    img = Image.new("RGBA", (YW, YH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = SIDE / 2

    def text(x, y, s, size, col, bold=True):
        d.text((x, y), s, font=font(size, bold), fill=col + (255,), anchor="mm")

    # 左: 曲名と説明
    text(cx, 170, info["title"], 64, GOLD)
    text(cx, 240, info["sub"], 38, CREAM)
    for k, s in enumerate(info["lead"]):
        text(cx, 340 + k * 50, s, 34, CREAM, False)
    for k, s in enumerate(info["terms"]):
        y = 540 + k * 58
        d.rounded_rectangle((cx - 240, y - 24, cx + 240, y + 24), radius=24, fill=mix(BG1, CELL, 0.9) + (215,))
        text(cx, y, s, 28, CREAM)
    # 右: 用語サイトの宣伝
    rx = SIDE + MVW + SIDE / 2
    text(rx, 230, "用語の復習は", 44, CREAM)
    for k, (name, url, col) in enumerate(SITES):
        y = 380 + k * 190
        d.rounded_rectangle((rx - 270, y - 70, rx + 270, y + 70), radius=26, fill=mix(BG1, CELL, 0.9) + (225,), outline=col + (255,), width=4)
        text(rx, y - 20, name, 40, CREAM)
        text(rx, y + 32, url.replace("https://", "").rstrip("/"), 32, GOLD)
    text(rx, 720, "カード・4択・書いて答える", 32, CREAM, False)
    text(rx, 770, "無料・登録なし・スマホで使える", 32, CREAM, False)
    d.rounded_rectangle((rx - 200, 850, rx + 200, 920), radius=35, fill=GOLD + (255,))
    text(rx, 885, "概要欄のリンクから", 34, BG1)
    img.save(path)


FONTS = SONGS_DIR / "フォント"   # Google Fonts（OFL。商用でも無料）。公開しないフォルダに置く
# 曲ごとのサムネイル: 曲名の字体・景色（背景素材の映像の番号と秒）・色
THUMBS = {
    "クリティカルパス": {"font": "ShipporiMincho-ExtraBold.ttf", "clip": 4240, "at": 6.0, "size": 128,
                       "tint": (60, 90, 150), "dark": 0.42, "snow": True, "title_col": (240, 244, 250), "glow": (120, 170, 255),
                       "sub": "〜完了しなかったプロジェクト〜", "line": "プロジェクトマネジメントの用語で歌う、冬の歌"},
    "ワン・ラブ・ストラテジ": {"font": "ReggaeOne-Regular.ttf", "clip": 44499, "at": 6.0, "size": 88,
                          "tint": None, "dark": 0.25, "snow": False, "rasta": True, "glow": (0, 0, 0),
                          "sub": "One Love Strategy", "line": "ストラテジ系の用語を、レゲエで覚える"},
    "コミットしないで": {"font": "KleeOne-SemiBold.ttf", "clip": 4151, "at": 6.0, "size": 124,
                       "tint": None, "dark": 0.2, "snow": False, "title_col": (255, 244, 248), "glow": (255, 120, 170),
                       "sub": "", "line": "コンピュータの用語で歌う、夏の恋の歌"},
}


def thumbnail(name, info, path):
    """曲名に合った字体と、曲に合った景色のサムネイル（1280×720）。"""
    from PIL import ImageFont
    import random
    cfg = THUMBS[name]
    bg = grab(SONGS_DIR / "背景素材" / f"{cfg['clip']}.mp4", cfg["at"], 1920, 1080).resize((1280, 720), Image.LANCZOS)
    if cfg.get("tint"):
        bg = Image.blend(bg, Image.new("RGB", bg.size, cfg["tint"]), 0.25)
    # 左側を暗くして、曲名を読みやすく
    shade = Image.new("L", (1280, 720))
    sd = ImageDraw.Draw(shade)
    for x in range(1280):
        sd.line((x, 0, x, 720), fill=int(255 * (0.75 * max(0.0, 1 - x / 900)) + 255 * cfg["dark"] * 0.5))
    bg = Image.composite(Image.new("RGB", bg.size, (6, 10, 16)), bg, shade.point(lambda v: min(v, 235)))
    d = ImageDraw.Draw(bg)
    if cfg.get("snow"):
        rnd = random.Random(3)
        for _ in range(140):
            x, y, r = rnd.uniform(0, 1280), rnd.uniform(0, 720), rnd.uniform(1.2, 3.6)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(236, 242, 250))
    f = ImageFont.truetype(str(FONTS / cfg["font"]), cfg["size"])
    title = name
    x0, y0 = 70, 300
    # 光（ぼかした曲名）
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((x0, y0), title, font=f, fill=cfg["glow"] + (230,), anchor="ls")
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    bg.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(bg)
    if cfg.get("rasta"):
        # レゲエの3色（赤・金・緑）を1文字ずつ、黒いふちどり
        cols = [(228, 60, 50), (250, 200, 40), (40, 160, 80)]
        x = x0
        for k, ch in enumerate(title):
            d.text((x, y0), ch, font=f, fill=cols[k % 3], anchor="ls", stroke_width=7, stroke_fill=(10, 10, 10))
            x += f.getlength(ch)
    else:
        d.text((x0, y0), title, font=f, fill=cfg["title_col"], anchor="ls", stroke_width=2, stroke_fill=cfg["glow"])
    sub_font = ImageFont.truetype(str(FONTS / cfg["font"]), 46)
    y = y0 + 70
    if cfg["sub"]:
        d.text((x0 + 4, y), cfg["sub"], font=sub_font, fill=(240, 236, 228), anchor="ls", stroke_width=2, stroke_fill=(10, 10, 10))
        y += 70
    d.text((x0 + 4, y + 10), cfg["line"], font=font(36), fill=(240, 236, 228), anchor="ls", stroke_width=2, stroke_fill=(10, 10, 10))
    d.rounded_rectangle((x0, 600, x0 + 430, 666), radius=33, fill=GOLD)
    d.text((x0 + 215, 633), "ITパスポート・基本情報", font=font(32), fill=BG1, anchor="mm")
    bg.save(path, quality=93)


def description(info, path):
    ch = "\n".join(f"{t // 60}:{t % 60:02d} {s}" for t, s in info["chapters"])
    sites = "\n".join(f"・{n}：{u}" for n, u, _ in SITES)
    text = f"""{info['yt_title']}

{info['desc']}
歌詞に合わせて、用語の意味を図で解説しています。

▼ 用語の復習は、無料の単語帳サイトで（登録なし・スマホで使えます）
{sites}

▼ チャプター
{ch}

▼ この動画で出てくる用語
{"・".join(info["terms"])}

曲：Suno で作成
映像素材：Mixkit

{info['tags']}
"""
    path.write_text(text, encoding="utf-8")


def make(name, info):
    mv = song_dir(name) / f"{name}_MV.mp4"
    bgv = WORK / f"{name}_MV_背景.mp4"
    out = song_dir(name) / f"{name}_YouTube.mp4"
    tmp = WORK
    pan = tmp / f"{name}_YouTube_左右.png"
    panels(info, pan)
    thumbnail(name, info, song_dir(name) / f"{name}_YouTube_サムネイル.jpg")
    description(info, song_dir(name) / f"{name}_YouTube_説明文.txt")
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    fc = (f"[1:v]scale={YW}:-2,crop={YW}:{YH},boxblur=18:2,colorchannelmixer=rr=0.45:gg=0.45:bb=0.45[bg];"
          f"[0:v]scale={MVW}:{YH}[mv];[bg][mv]overlay={SIDE}:0[a];[a][2:v]overlay=0:0:format=auto,format=yuv420p[v]")
    work = out.with_name(out.stem + "_作成中.mp4")
    cmd = [ff, "-y", "-loglevel", "error", "-i", str(mv), "-i", str(bgv), "-loop", "1", "-i", str(pan),
           "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-shortest",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "60", "-c:a", "copy", "-movflags", "+faststart", str(work)]
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"YouTube の動画を作れませんでした: {name}")
    if out.exists():
        out.replace(out.with_name(out.stem + "_前の版.mp4"))
    work.replace(out)
    print(out)


def meta_only(name, info):
    """横長の動画は make_mv_*.py --youtube で作ったものを使い、サムネイルと説明文だけ作る。"""
    mv = song_dir(name) / f"{name}_MV.mp4"
    bgv = WORK / f"{name}_MV_背景.mp4"
    thumbnail(name, info, song_dir(name) / f"{name}_YouTube_サムネイル.jpg")
    description(info, song_dir(name) / f"{name}_YouTube_説明文.txt")
    print(song_dir(name) / f"{name}_YouTube_サムネイル.jpg")


if __name__ == "__main__":
    args = sys.argv[1:]
    meta = "--meta" in args
    names = [a for a in args if a != "--meta"] or list(SONGS)
    for n in names:
        (meta_only if meta else make)(n, SONGS[n])
