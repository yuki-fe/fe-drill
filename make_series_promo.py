"""用語ドリル全体（yogo-drill.com と7つのサイト）の宣伝リール動画を作る。

デザイン: スキル ui-ux-pro-max の「ミニマル・スイス」（サイトのレイアウトと同じ）。うすい灰緑の背景、太い見出し、
          はっきりした文字の強弱、グリッドにそろえた配置。色は各サイトの差し色（入り口の sites.json）。
          上のふちに7サイトの色を並べた帯を通して、「用語ドリル」全体の印にする。
動き:     部品は下から少し浮き上がって出る（0.35秒・減速・少しずつずらす）。はずむ動きは使わない。
音:       リール動画は音なし（2026-10-16 に決めた）。無音の音声トラックだけ入れる。

作るもの（static/ig/series-promo/ に書き出す）:
  ・reel.mp4 / reel-cover.jpg   リール動画（1080×1920、60fps、約34秒、音なし）と表紙
  ・captions.txt               リールの投稿文、YouTube ショートのタイトルと説明

使い方:  python make_series_promo.py            動画を作る
         python make_series_promo.py --stills   各場面の最後の画面だけを書き出す（確かめる用）
先に make_promo_shots.py でサイトの画面を撮っておく（notes/宣伝動画/画面/）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import make_b_media as mb
import media_fx as fx

ROOT = Path(__file__).parent
SITES_DIR = ROOT.parent
OUT = ROOT / "static" / "ig" / "series-promo"
SHOTS = ROOT / "notes" / "宣伝動画" / "画面"
PORTAL = json.loads((SITES_DIR / "yogo-drill" / "sites.json").read_text(encoding="utf-8"))
SITES = [s for s in PORTAL["sites"] if s.get("public")]
FOLDER = {"fe": "claude FE対策サイト"}

W, H, FPS = 1080, 1920, 60
X = 80                      # 左右の余白
ENTER, RISE = 0.35, 28      # 部品が出てくる秒数と、浮き上がる距離
FADE = 0.3                  # 場面の切り替え
BG, PAPER, INK, MUTED, LINE = "#F1F4F1", "#FBFCFA", "#1D2A2E", "#5D6C6E", "#D5DDD8"
OK = "#2B7A68"
MARKER = "#FFE9A8"
NOTO = "C:/Windows/Fonts/NotoSansJP-VF.ttf"
URL = PORTAL["base_url"].replace("https://", "")


# ---------- 文字 ----------

_fonts = {}


def font(size, weight=700):
    key = (size, weight)
    if key not in _fonts:
        try:
            f = ImageFont.truetype(NOTO, size)
            f.set_variation_by_axes([weight])
        except OSError:   # Noto Sans JP がないパソコンでは、今までの動画と同じ BIZ UDゴシック
            f = mb.font(size, weight >= 600)
        _fonts[key] = f
    return _fonts[key]


def fit(text, size, weight, width, minimum=22):
    """幅に収まるまで文字を小さくする。"""
    while size > minimum and font(size, weight).getlength(text) > width:
        size -= 2
    return font(size, weight)


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


# ---------- 部品と場面（make_promo_media.py と同じ仕組み。動きだけ控えめに） ----------

class Part:
    def __init__(self, draw_fn):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_fn(img, ImageDraw.Draw(img))
        box = img.getbbox() or (0, 0, 1, 1)
        self.img, self.x, self.y = img.crop(box), box[0], box[1]

    def put(self, frame, p, dy=0.0):
        if p <= 0:
            return
        im = self.img
        if p < 1:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * p)))
        frame.alpha_composite(im, (self.x, round(self.y + dy)))


def _background():
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)
    color_bar(d, 0, 0, W, 14)
    return img


class Scene:
    def __init__(self, sec):
        self.sec, self.items = sec, []

    def add(self, t0, draw_fn, rise=RISE, dur=ENTER):
        part = Part(draw_fn)

        def draw(f, t):
            p = (t - t0) / dur
            if p > 0:
                part.put(f, min(1.0, ease(p) * 1.15), dy=(1 - ease(p)) * rise)
        self.items.append(draw)

    def render(self, t):
        frame = BACKGROUND.copy()
        for fn in self.items:
            fn(frame, t)
        return frame


# ---------- 描く道具 ----------

def color_bar(d, x, y, w, h):
    """7サイトの色を並べた帯（用語ドリル全体の印）。"""
    seg = w / len(SITES)
    for i, s in enumerate(SITES):
        d.rectangle((round(x + i * seg), y, round(x + (i + 1) * seg), y + h), fill=s["color"])
    return y + h


def card(img, box, r=28, fill=PAPER, border=LINE):
    """平らなカード: 細いふちと、ごく薄い影。"""
    x1, y1, x2, y2 = box
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x1, y1 + 6, x2, y2 + 6), radius=r, fill=(29, 42, 46, 26))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).rounded_rectangle(box, radius=r, fill=fill, outline=border, width=2)


def site_icon(key, size):
    p = (SITES_DIR / FOLDER.get(key, f"{key}-drill") / "static" / "apple-touch-icon.png")
    if key == "top":
        p = SITES_DIR / "yogo-drill" / "static" / "apple-touch-icon.png"
    im = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 4, fill=255)
    im.putalpha(mask)
    return im


def chip(d, x, y, text, size=38, fg=INK, fill=None, border=INK, weight=700):
    f = font(size, weight)
    w, h = f.getlength(text), size + 30
    d.rounded_rectangle((x, y, x + w + 52, y + h), radius=h // 2, fill=fill, outline=border, width=3)
    d.text((x + 26, y + 12), text, font=f, fill=fg)
    return x + w + 52


def center(d, y, text, f, fill=INK):
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)


def check(d, cx, cy, r, color=OK):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    d.line((cx - r * .45, cy + r * .02, cx - r * .1, cy + r * .38, cx + r * .5, cy - r * .35), fill="#FFFFFF", width=max(4, r // 5), joint="curve")


def phone(img, shot, x, y, w, h):
    """スマホの枠に、サイトの画面（上から切り出し）を入れる。"""
    bez = 18
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x, y + 14, x + w, y + h + 14), radius=70, fill=(29, 42, 46, 60))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    ImageDraw.Draw(img).rounded_rectangle((x, y, x + w, y + h), radius=70, fill=INK)
    sw, shh = w - bez * 2, h - bez * 2
    src = Image.open(shot).convert("RGBA")
    src = src.resize((sw, round(src.height * sw / src.width)), Image.LANCZOS).crop((0, 0, sw, shh))
    mask = Image.new("L", (sw, shh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, shh - 1), radius=54, fill=255)
    src.putalpha(mask)
    img.alpha_composite(src, (x + bez, y + bez))


BACKGROUND = _background()


# ---------- 場面 ----------

def s_hook():
    sc = Scene(3.4)
    sc.add(0.15, lambda img, d: d.text((X, 560), "資格の勉強をしている人へ", font=font(42, 700), fill=MUTED))
    big = font(118, 900)
    sc.add(0.35, lambda img, d: d.text((X, 650), "資格の用語、", font=big, fill=INK))
    sc.add(0.55, lambda img, d: d.text((X, 800), "すきま時間に", font=big, fill=INK))

    def line3(img, d):
        w = big.getlength("覚えませんか？")
        d.rectangle((X - 6, 1010, X + w + 6, 1080), fill=MARKER)   # 蛍光ペンの線
        d.text((X, 950), "覚えませんか？", font=big, fill=INK)
    sc.add(0.75, line3)
    sc.add(1.25, lambda img, d: d.text((X, 1170), "スマホで、無料で、登録なしで。", font=font(48, 500), fill=MUTED))
    return sc


def s_title():
    sc = Scene(3.6)

    def logo(img, d):
        im = site_icon("top", 190)
        img.alpha_composite(im, ((W - 190) // 2, 470))
    sc.add(0.1, logo)
    sc.add(0.3, lambda img, d: center(d, 700, "用語ドリル", font(156, 900)))
    sc.add(0.5, lambda img, d: center(d, 905, f"{len(SITES)}つの資格の単語帳サイト", font(56, 700), MUTED))

    def chips(img, d):
        labels = ["無料", "登録なし", "スマホでOK"]
        f = font(40, 700)
        total = sum(f.getlength(s) + 52 for s in labels) + 24 * (len(labels) - 1)
        x = (W - total) / 2
        for s in labels:
            x = chip(d, x, 1040, s, size=40) + 24
    sc.add(0.8, chips)
    sc.add(1.0, lambda img, d: color_bar(d, (W - 620) // 2, 1200, 620, 18))
    return sc


def s_sites():
    sc = Scene(7.4)
    sc.add(0.0, lambda img, d: d.text((X, 300), f"{len(SITES)}つのサイト", font=font(92, 900), fill=INK))
    sc.add(0.15, lambda img, d: d.text((X, 420), "気になる資格から、どれでも無料", font=font(40, 500), fill=MUTED))
    y0, rh, gap = 510, 128, 12
    for i, s in enumerate(SITES):
        y = y0 + i * (rh + gap)

        def row(img, d, s=s, y=y):
            card(img, (X, y, W - X, y + rh), r=22)
            d.rounded_rectangle((X, y, X + 10, y + rh), radius=4, fill=s["color"])
            img.alpha_composite(site_icon(s["key"], 84), (X + 34, y + 22))
            right = f'{s["terms"]}語'
            rf = font(46, 900)
            rw = rf.getlength(right)
            d.text((W - X - 30 - rw, y + 36), right, font=rf, fill=s["color"])
            avail = W - X - 30 - rw - (X + 142) - 20
            d.text((X + 142, y + 18), s["name"], font=fit(s["name"], 44, 800, avail), fill=INK)
            d.text((X + 142, y + 76), s["exam"], font=fit(s["exam"], 28, 500, avail), fill=MUTED)
        sc.add(0.4 + i * 0.3, row, rise=22)
    return sc


def s_screen(name, site_key, lines):
    sc = Scene(3.4)
    site = next(s for s in SITES if s["key"] == site_key)

    def head(img, d):
        chip(d, X, 250, site["name"], size=34, fg="#FFFFFF", fill=site["color"], border=site["color"])
    sc.add(0.05, head)
    big = font(76, 900)
    for k, ln in enumerate(lines):
        sc.add(0.2 + k * 0.12, lambda img, d, ln=ln, k=k: d.text((X, 340 + k * 100), ln, font=big, fill=INK))
    sc.add(0.35, lambda img, d: phone(img, SHOTS / f"{name}.png", (W - 640) // 2, 600, 640, 1110), rise=120, dur=0.55)
    return sc


def s_features():
    sc = Scene(3.8)
    sc.add(0.0, lambda img, d: d.text((X, 330), "どのサイトでも", font=font(92, 900), fill=INK))
    sc.add(0.15, lambda img, d: d.text((X, 450), "同じ使い方で、すぐに慣れる", font=font(40, 500), fill=MUTED))
    items = ["カードで覚える", "4択クイズ", "書いて答える", "間違えた用語だけ復習", "分野別ミニテスト", "全部の用語を一覧で"]
    for i, t in enumerate(items):
        y = 570 + i * 132

        def row(img, d, t=t, y=y):
            card(img, (X, y, W - X, y + 108), r=20)
            check(d, X + 60, y + 54, 26)
            d.text((X + 112, y + 24), t, font=font(48, 700), fill=INK)
        sc.add(0.35 + i * 0.16, row, rise=20)
    return sc


def s_outro():
    sc = Scene(4.4)
    sc.add(0.05, lambda img, d: center(d, 470, "無料・登録なし", font(44, 700), MUTED))
    sc.add(0.2, lambda img, d: center(d, 560, URL, fit(URL, 112, 900, W - 2 * X)))
    sc.add(0.4, lambda img, d: center(d, 740, "プロフィールのリンクから", font(54, 700)))
    sc.add(0.55, lambda img, d: color_bar(d, (W - 620) // 2, 860, 620, 18))

    def icons(img, d):
        n, size, gap = len(SITES), 92, 22
        total = n * size + (n - 1) * gap
        x = (W - total) // 2
        for s in SITES:
            img.alpha_composite(site_icon(s["key"], size), (x, 960))
            x += size + gap
    sc.add(0.75, icons)
    note = font(30, 500)
    sc.add(1.1, lambda img, d: (center(d, 1130, "各試験の実施団体とは関係のない、", note, MUTED),
                                center(d, 1175, "個人の学習サイトです。", note, MUTED)))
    return sc


def scenes():
    return [s_hook(), s_title(), s_sites(),
            s_screen("fe-home", "fe", ["開いたら、", "すぐに学習できる"]),
            s_screen("ip-test", "ip", ["分野ごとの正答率が", "わかるミニテスト"]),
            s_screen("boki-term", "boki", ["1語ずつの解説と、", "確認問題"]),
            s_screen("iryo-abbr", "iryo", ["カルテの略語も、", "クイズで覚える"]),
            s_features(), s_outro()]


# ---------- 動画にする（make_promo_media.py と同じ） ----------

def encode(all_scenes, path, ffmpeg):
    total = sum(round(sc.sec * FPS) / FPS for sc in all_scenes)
    wav = path.with_suffix(".wav")
    fx.write_track(wav, total, [], music=False)   # 音なし（無音の音声トラックだけ）
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "16", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev_last, n = None, 0
    for sc in all_scenes:
        for i in range(round(sc.sec * FPS)):
            t = i / FPS
            img = sc.render(t).convert("RGB")
            if prev_last is not None and t < FADE:
                img = Image.blend(prev_last, img, ease(t / FADE))
            p.stdin.write(img.tobytes())
            n += 1
        prev_last = sc.render(sc.sec).convert("RGB")
        print(".", end="", flush=True)
    p.stdin.close()
    ok = p.wait() == 0
    wav.unlink(missing_ok=True)
    print()
    if not ok:
        sys.exit(f"動画の変換に失敗しました: {path.name}")
    return n / FPS


def exam_short(s):
    """投稿文の一覧用に、試験名のかっこ（シラバスや範囲の説明）を外す。医療事務は特定の試験に合わせていない"""
    if s["key"] == "iryo":
        return "医療事務の用語"
    return re.sub(r"[（(][^）)]*[）)]", "", s["exam"]).strip()


def caption():
    lines = "\n".join(f'・{exam_short(s)} → {s["name"]}（{s["terms"]}語）' for s in SITES)
    return ("【資格の用語、すきま時間に覚えよう】\n"
            "通学の電車や寝る前の5分で、試験に出る用語をカードとクイズで。\n"
            f"無料の単語帳サイト「用語ドリル」の{len(SITES)}つのサイトを、まとめて紹介します。\n\n"
            f"▶ {len(SITES)}つのサイト\n{lines}\n\n"
            "▶ どのサイトでも\n"
            "・カードで覚える／4択クイズ／書いて答える\n"
            "・分野別ミニテストで、苦手な分野がわかる\n"
            "・間違えた用語だけを集めて復習\n\n"
            "無料・登録なしで、スマホのブラウザでそのまま使えます。\n"
            f"サイトの一覧は、プロフィールのリンク（{URL}）から。\n\n"
            "いま勉強している資格を、コメントで教えてください。これからのサイトづくりの参考にします。\n\n"
            "※各試験の実施団体とは関係のない、個人の学習サイトです。\n\n"
            "#資格勉強 #資格 #スキマ時間 #勉強垢 #IT資格 #基本情報技術者試験 #ITパスポート #G検定 #生成AIパスポート #簿記 #医療事務 #単語帳")


def pin_comment():
    return (f"📌 サイトの一覧は、プロフィールのリンク（{URL}）から。どれも無料・登録なしで使えます。\n"
            "勉強中の資格や、ほしい機能があれば、気軽にコメントしてください。")


def youtube():
    title = f"【無料】資格の用語を覚える単語帳サイト{len(SITES)}つ #Shorts"
    desc = (f"無料の単語帳サイト「用語ドリル」。{len(SITES)}つの資格の用語を、カード・4択・ミニテストで覚えられます。\n\n"
            + "\n".join(f'・{s["name"]}: {s["url"]}' for s in SITES) +
            f"\n\n▶ サイトの一覧（無料・登録なし）: {PORTAL['base_url']}/?utm_source=youtube&utm_medium=video&utm_campaign=series-promo\n\n"
            "※各試験の実施団体とは関係のない、個人の学習サイトです。\n\n#資格勉強 #IT資格 #Shorts")
    return title, desc


def write_captions():
    yt_title, yt_desc = youtube()
    (OUT / "captions.txt").write_text(
        "■ リールの投稿文\n\n" + caption() +
        "\n\n\n■ 紹介コメント（投稿したらコメントに貼って、長押し→「固定」）\n\n" + pin_comment() +
        "\n\n\n■ YouTube ショートのタイトル\n\n" + yt_title +
        "\n\n\n■ YouTube ショートの説明\n\n" + yt_desc + "\n", encoding="utf-8")


def main():
    missing = [n for n in ("fe-home", "ip-test", "boki-term", "iryo-abbr") if not (SHOTS / f"{n}.png").exists()]
    if missing:
        sys.exit("サイトの画面がありません。先に make_promo_shots.py を動かしてください: " + ", ".join(missing))
    OUT.mkdir(parents=True, exist_ok=True)
    if "--captions" in sys.argv:   # 投稿文だけを作り直す
        write_captions()
        print("static/ig/series-promo/captions.txt を書き出しました")
        return
    all_scenes = scenes()
    if "--stills" in sys.argv:
        for k, sc in enumerate(all_scenes):
            sc.render(sc.sec).convert("RGB").save(OUT / f"still-{k + 1}.jpg", "JPEG", quality=85)
        print("static/ig/series-promo/ に still-*.jpg を書き出しました")
        return
    sec = encode(all_scenes, OUT / "reel.mp4", mb.find_ffmpeg())
    title = all_scenes[1]
    title.render(title.sec).convert("RGB").save(OUT / "reel-cover.jpg", "JPEG", quality=88)
    write_captions()
    print(f"static/ig/series-promo/ に書き出しました（リール {sec:.1f} 秒・{FPS}fps・音なし・表紙・投稿文）")


if __name__ == "__main__":
    main()
