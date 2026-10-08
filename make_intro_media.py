"""Instagram の最初の投稿（サイトの紹介）の素材を作る。一度だけ使う。

作るもの（static/ig/intro/ に書き出す）:
  ・feed-1.jpg 〜 feed-5.jpg   フィード投稿（1080×1350 のカルーセル5枚）
  ・reel.mp4 / reel-cover.jpg   リール動画（1080×1920、約25秒、無音）
  ・story-1.jpg / story-2.jpg   ストーリー（1080×1920。2枚目にリンクのスタンプを置く）
  ・captions.txt               投稿文（フィード・リール）とストーリーのリンク
  ・intro.json                 LINE ボットの「紹介リール」が読むリールの情報（動画・表紙・投稿文・YouTube 用）

使い方:  python build.py            （先にビルドして、docs/assets に最新の問題データを入れる）
         python make_intro_media.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

import make_b_media as mb
from make_b_media import BASE, BG, HL, INK, LINE, MARK, MARK_SOFT, MUTED, OK, OK_SOFT, PAPER, font, pill, wrap

ROOT = Path(__file__).parent
OUT = ROOT / "static" / "ig" / "intro"
ICON = ROOT / "notes" / "brand" / "icon_instagram.png"
W = 1080
TAGS = "#基本情報技術者試験 #基本情報 #FE #IT資格 #情報系学生 #IT用語 #科目B #プログラミング学習 #資格勉強 #勉強垢"


def canvas(h):
    img = Image.new("RGB", (W, h), BG)
    return img, ImageDraw.Draw(img)


def icon(size):
    """アイコンを丸く切り抜く（notes/ にあるので、無ければ使わない）。"""
    if not ICON.exists():
        return None
    im = Image.open(ICON).convert("RGB").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return im, mask


def paste_icon(img, x, y, size):
    ic = icon(size)
    if ic:
        img.paste(ic[0], (x, y), ic[1])


def text_lines(d, x, y, lines, f, fill, gap=1.4):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def center(d, y, text, f, fill):
    d.text(((W - f.getlength(text)) / 2, y), text, font=f, fill=fill)


def bullet_rows(d, x, y, rows, w, size=38):
    """丸の付いた行。rows: [(見出し, 説明)]"""
    for head, sub in rows:
        d.ellipse((x, y + 12, x + 22, y + 34), fill=MARK)
        d.text((x + 44, y), head, font=font(size, True), fill=INK)
        y += int(size * 1.35)
        if sub:
            y = text_lines(d, x + 44, y, wrap(sub, font(30), w - 44), font(30), MUTED, 1.45)
        y += 26
    return y


def term_card(d, x, y, w, h, side, term, sub, desc, desc_size=40):
    """サイトの単語カード（表: 用語、裏: 意味）。"""
    d.rounded_rectangle((x, y, x + w, y + h), radius=28, fill=PAPER, outline=LINE, width=3)
    f = font(28)
    tag = f"テクノロジ系・{sub}"
    tw = f.getlength(tag)
    d.rounded_rectangle((x + (w - tw) / 2 - 22, y + 40, x + (w + tw) / 2 + 22, y + 92), radius=10, outline=MARK, width=2)
    d.text((x + (w - tw) / 2, y + 50), tag, font=f, fill=MARK)
    if side == "front":
        tf = font(96, True)
        d.text((x + (w - tf.getlength(term)) / 2, y + h / 2 - 60), term, font=tf, fill=INK)
        hint = "タップして意味を見る"
        d.text((x + (w - font(28).getlength(hint)) / 2, y + h - 90), hint, font=font(28), fill=MUTED)
    else:
        tf = font(56, True)
        df = font(desc_size, True)
        lines = wrap(desc, df, w - 120)
        if len(lines) > 1 and lines[-1] in "。、":
            lines[-2] += lines.pop()
        yy = y + 120 + (h - 120 - len(lines) * int(desc_size * 1.6) + 40) / 2
        d.text((x + (w - tf.getlength(term)) / 2, yy - 90), term, font=tf, fill=MARK)
        for ln in lines:
            d.text((x + (w - df.getlength(ln)) / 2, yy), ln, font=df, fill=INK)
            yy += int(desc_size * 1.6)


def choices_box(d, x, y, w, choices, answer=None, size=38):
    kana = "アイウエ"
    for k, c in enumerate(choices):
        ok = answer is not None and c == answer
        d.rounded_rectangle((x, y, x + w, y + 104), radius=18, fill=OK_SOFT if ok else PAPER, outline=OK if ok else LINE, width=3)
        d.ellipse((x + 28, y + 30, x + 100, y + 74), outline=OK if ok else MARK, width=4)
        d.text((x + 50, y + 33), kana[k], font=font(32, True), fill=OK if ok else MARK)
        d.text((x + 128, y + 52 - size // 2 - 4), c, font=font(size, True), fill=INK)
        if ok:
            d.text((x + w - 130, y + 30), "正解", font=font(36, True), fill=OK)
        y += 122
    return y


# ---------- フィード投稿（1080×1350 × 5枚） ----------

FH = 1350


def feed_frame(no, label, color=MARK):
    img, d = canvas(FH)
    d.rounded_rectangle((48, 48, W - 48, FH - 48), radius=36, fill=PAPER, outline=LINE, width=2)
    pill(d, 96, 100, label, color, 32)
    d.text((96, FH - 130), "FE用語ドリル", font=font(32, True), fill=INK)
    t = f"{no} / 5"
    d.text((W - 96 - font(30, mono=True).getlength(t), FH - 126), t, font=font(30, mono=True), fill=MUTED)
    return img, d


def feed1():
    img, d = feed_frame(1, "はじめまして")
    paste_icon(img, W - 96 - 220, 220, 220)
    y = 230
    y = text_lines(d, 96, y, ["基本情報の勉強を、", "スキマ時間で。"], font(76, True), INK, 1.35) + 30
    d.text((96, y), "無料の学習サイト", font=font(40), fill=MUTED)
    y += 70
    d.text((96, y), "FE用語ドリル", font=font(104, True), fill=MARK)
    y += 170
    d.line((96, y, W - 96, y), fill=LINE, width=3)
    y += 50
    y = bullet_rows(d, 96, y, [
        ("科目A：用語345語の単語帳", None),
        ("科目B：プログラムを1行ずつ再生", None),
        ("無料・登録なし・スマホでOK", None),
    ], W - 192, 42)
    t = "スワイプして中身を見てね →"
    d.text((W - 96 - font(32, True).getlength(t), FH - 200), t, font=font(32, True), fill=MARK)
    return img


def feed2():
    img, d = feed_frame(2, "科目A　用語")
    y = text_lines(d, 96, 200, ["よく出る用語345語を", "4つのやり方で覚える"], font(60, True), INK, 1.35) + 30
    term_card(d, 96, y, W - 192, 330, "back", "DNS", "ネットワーク", "ドメイン名とIPアドレスを対応づける仕組み。", 34)
    y += 370
    y = bullet_rows(d, 96, y, [
        ("カード", "タップで裏返して、覚えたかどうかを仕分け"),
        ("4択クイズ", "説明を読んで、当てはまる用語を選ぶ"),
        ("書いて答える・意味から答える", "思い出す練習で、記憶に残りやすく"),
        ("間違えた用語だけ復習", "苦手なものだけ、まとめてもう一度"),
    ], W - 192, 36)
    return img


def feed3(item):
    img, d = feed_frame(3, "科目B　トレース練習")
    y = text_lines(d, 96, 200, ["プログラムが", "1行ずつ動いて見える"], font(60, True), INK, 1.35) + 20
    y = text_lines(d, 96, y, ["実行した行と、変数の値の変化を並べて表示。", "自分のトレースがどこでずれたか、その場でわかる。"], font(32), MUTED, 1.5) + 24
    s = next(e for e in item["events"] if e["phase"] == "after" and e["line"] == 5 and e["vars"].get("i") == 2)
    y = mb.draw_code(d, item["code"], 96, y, W - 192, cur=s["line"], size=30)
    y += 30
    d.text((96, y), "変数", font=font(30, True), fill=MUTED)
    y += 54
    prev = {"i": 2, "s": 3}
    for k in ("i", "s"):
        d.line((96, y - 12, W - 96, y - 12), fill=LINE, width=2)
        d.text((96, y + 4), k, font=font(36, True, mono=True), fill=MUTED)
        y = mb.draw_value(d, 260, y, s["vars"][k], prev[k], 36, 600)
    d.line((96, y - 12, W - 96, y - 12), fill=LINE, width=2)
    lx, ly = 96, y + 16
    d.rectangle((lx, ly + 2, lx + 28, ly + 30), fill=HL)
    d.text((lx + 40, ly), "いま実行した行", font=font(26), fill=MUTED)
    d.rectangle((lx + 300, ly + 2, lx + 328, ly + 30), fill=OK_SOFT)
    d.text((lx + 340, ly), "変わった値", font=font(26), fill=MUTED)
    return img


def feed4():
    img, d = feed_frame(4, "科目B　ほかにも")
    y = text_lines(d, 96, 200, ["擬似言語に慣れる", "練習がそろっています"], font(60, True), INK, 1.35) + 30
    rows = [
        ("トレース練習", "20問", "変数の値を表に書いて、1行ずつ答え合わせ"),
        ("アルゴリズム図鑑", "10本", "整列・探索などの定番を、動きつきで"),
        ("穴埋め問題", "10問", "プログラムの空欄に入るものを考える"),
        ("セキュリティ事例", "10問", "よくある場面で、どう対策するか"),
        ("擬似言語の記法クイズ", "13問", "書き方のルールをクイズで確認"),
        ("シミュレータ", "", "自分で書いたプログラムを動かせる"),
    ]
    for head, n, sub in rows:
        d.rounded_rectangle((96, y, W - 96, y + 112), radius=20, fill=BG)
        d.text((128, y + 16), head, font=font(36, True), fill=INK)
        if n:
            d.text((W - 128 - font(34, True).getlength(n), y + 18), n, font=font(34, True), fill=MARK)
        d.text((128, y + 66), sub, font=font(28), fill=MUTED)
        y += 124
    return img


def feed5():
    img, d = feed_frame(5, "このアカウントでは")
    y = text_lines(d, 96, 200, ["スキマ時間に解ける", "問題を投稿します"], font(60, True), INK, 1.35) + 40
    y = bullet_rows(d, 96, y, [
        ("IT用語クイズ", "説明を読んで、当てはまる用語を4択で"),
        ("科目B トレースクイズ", "プログラムを追って、変数の値を書き出す"),
        ("リール動画", "プログラムが1行ずつ動く様子を再生"),
    ], W - 192, 42) + 20
    d.rounded_rectangle((96, y, W - 96, y + 300), radius=24, fill=MARK_SOFT)
    center(d, y + 46, "サイトは無料・登録なし", font(46, True), INK)
    center(d, y + 126, "プロフィールのリンクから", font(46, True), MARK)
    center(d, y + 210, "保存して、あとで見返してね", font(34), MUTED)
    return img


def feed_caption():
    return ("はじめまして。基本情報技術者試験（FE）の無料の学習サイト「FE用語ドリル」をつくりました。\n\n"
            "▶ 科目A\n"
            "よく出る用語345語を、カード・4択・書いて答える・意味から答えるの4つのやり方で。間違えた用語だけまとめて復習もできます。\n\n"
            "▶ 科目B\n"
            "擬似言語のプログラムを1行ずつ再生して、変数がどう変わるかを見ながらトレースの練習ができます。アルゴリズム図鑑・穴埋め・セキュリティ事例も。\n\n"
            "登録なし・スマホのブラウザでそのまま使えます。\n"
            "このアカウントでは、IT用語クイズや科目Bのトレースクイズを投稿していきます。\n\n"
            "サイトはプロフィールのリンクから。\n\n" + TAGS)


# ---------- リール動画（1080×1920） ----------

RH = 1920


def reel_head(d, label):
    pill(d, 60, 200, label, MARK, 34)


def r_hook():
    img, d = canvas(RH)
    d.rounded_rectangle((60, 360, W - 60, 1380), radius=40, fill=PAPER, outline=LINE, width=2)
    pill(d, 120, 430, "基本情報技術者試験（FE）", MARK, 34)
    y = text_lines(d, 120, 570, ["用語、覚えきれない", "科目Bのトレース、", "追いきれない"], font(80, True), INK, 1.4) + 40
    d.text((120, y), "…そんな人のためのサイトを", font=font(44), fill=MUTED)
    d.text((120, y + 70), "つくりました", font=font(44), fill=MUTED)
    return img


def r_title():
    img, d = canvas(RH)
    paste_icon(img, (W - 280) // 2, 360, 280)
    center(d, 720, "無料の学習サイト", font(48), MUTED)
    center(d, 810, "FE用語ドリル", font(120, True), MARK)
    center(d, 1010, "科目A・科目B どちらも", font(52, True), INK)
    center(d, 1090, "スマホでそのまま", font(52, True), INK)
    return img


def r_card(side):
    img, d = canvas(RH)
    reel_head(d, "科目A｜用語345語の単語帳")
    text_lines(d, 60, 310, ["カードをめくって", "覚える"], font(76, True), INK, 1.3)
    term_card(d, 60, 560, W - 120, 640, side, "DNS", "ネットワーク", "ドメイン名とIPアドレスを対応づける仕組み。", 50)
    if side == "back":
        for k, (t, c) in enumerate([("覚えた", OK), ("まだ", MARK)]):
            x = 60 + k * ((W - 120) // 2 + 10)
            w = (W - 120) // 2 - 10
            d.rounded_rectangle((x, 1240, x + w, 1340), radius=50, fill=c)
            center_x = x + (w - font(40, True).getlength(t)) / 2
            d.text((center_x, 1266), t, font=font(40, True), fill=PAPER)
    return img


def r_quiz(answer):
    img, d = canvas(RH)
    reel_head(d, "科目A｜4択クイズ")
    text_lines(d, 60, 310, ["この説明に当てはまる", "用語は？"], font(72, True), INK, 1.3)
    f = font(42)
    desc = wrap("ネットワークに接続した機器に、IPアドレスなどの設定を自動で割り当てるプロトコル。", f, W - 200)
    box_h = len(desc) * int(42 * 1.6) + 60
    d.rounded_rectangle((60, 540, W - 60, 540 + box_h), radius=20, fill=PAPER, outline=LINE, width=2)
    text_lines(d, 100, 570, desc, f, INK, 1.6)
    choices_box(d, 60, 540 + box_h + 50, W - 120, ["DNS", "NAT", "DHCP", "ARP"], "DHCP" if answer else None, 42)
    return img


def r_b_title():
    img, d = canvas(RH)
    reel_head(d, "科目B｜トレース練習")
    y = text_lines(d, 60, 420, ["プログラムが", "1行ずつ動く"], font(110, True), INK, 1.3) + 50
    text_lines(d, 60, y, ["いま実行している行と、", "変数の値の変化が見える"], font(52), MUTED, 1.5)
    return img


def r_outro():
    img, d = canvas(RH)
    d.rounded_rectangle((60, 300, W - 60, 1440), radius=40, fill=PAPER, outline=LINE, width=2)
    paste_icon(img, 120, 370, 160)
    d.text((310, 400), "FE用語ドリル", font=font(72, True), fill=MARK)
    d.text((310, 490), "基本情報技術者試験の学習サイト", font=font(32), fill=MUTED)
    y = bullet_rows(d, 120, 640, [
        ("科目A 用語345語・4つの覚え方", None),
        ("科目B トレース練習・図鑑・穴埋め", None),
        ("間違えたものだけ復習", None),
    ], W - 240, 44) + 20
    d.line((120, y, W - 120, y), fill=LINE, width=3)
    y += 60
    center(d, y, "無料・登録なし", font(76, True), INK)
    center(d, y + 120, "プロフィールのリンクから", font(54, True), MARK)
    return img


def make_reel(item, ffmpeg):
    frames = [(r_hook(), 3.0), (r_title(), 2.5),
              (r_card("front"), 1.5), (r_card("back"), 2.2),
              (r_quiz(False), 2.5), (r_quiz(True), 1.8),
              (r_b_title(), 2.0)]
    fn, args = mb.args_of(item)
    steps, last = mb.reel_frames(item)
    prev, cover = None, None
    for i, s in enumerate(steps):
        img = mb.draw_step(item, 1, s, prev, i, len(steps), fn, args)
        frames.append((img, 0.7))
        if cover is None and i >= len(steps) * 0.5:
            cover = img
        prev = s
    frames.append((r_outro(), 4.0))
    mb.encode(frames, OUT / "reel.mp4", ffmpeg)
    r_title().save(OUT / "reel-cover.jpg", "JPEG", quality=88)
    return sum(round(s * mb.FPS) for _, s in frames) / mb.FPS


def reel_caption():
    return ("【基本情報の勉強、スキマ時間に】\n"
            "無料の学習サイト「FE用語ドリル」をつくりました。\n\n"
            "・科目A：用語345語をカードと4択で\n"
            "・科目B：プログラムを1行ずつ再生して、変数の動きを見ながらトレース\n\n"
            "登録なし・スマホでそのまま使えます。プロフィールのリンクから。\n"
            "これから IT用語クイズや科目Bのトレースを投稿していくので、フォローしてもらえるとうれしいです。\n\n" + TAGS)


# ---------- ストーリー（1080×1920） ----------

def story1():
    img, d = canvas(RH)
    d.rounded_rectangle((60, 260, W - 60, 1560), radius=40, fill=PAPER, outline=LINE, width=2)
    paste_icon(img, (W - 260) // 2, 340, 260)
    center(d, 650, "Instagram はじめました", font(64, True), INK)
    center(d, 760, "基本情報技術者試験の学習サイト", font(40), MUTED)
    center(d, 830, "FE用語ドリル", font(110, True), MARK)
    y = 1020
    for t in ["IT用語クイズ", "科目B トレースクイズ", "1行ずつ動くリール動画"]:
        w = font(44, True).getlength(t) + 80
        d.rounded_rectangle(((W - w) / 2, y, (W + w) / 2, y + 90), radius=45, fill=BG)
        center(d, y + 20, t, font(44, True), INK)
        y += 120
    center(d, y + 20, "を投稿していきます", font(44), MUTED)
    return img


def story2():
    img, d = canvas(RH)
    center(d, 300, "サイトは無料・登録なし", font(64, True), INK)
    center(d, 400, "スマホでそのまま使えます", font(44), MUTED)
    y = 520
    for head, sub in [("科目A", "用語345語をカード・4択で"), ("科目B", "プログラムを1行ずつ再生")]:
        d.rounded_rectangle((120, y, W - 120, y + 170), radius=28, fill=PAPER, outline=LINE, width=2)
        pill(d, 160, y + 50, head, MARK, 34)
        d.text((360, y + 58), sub, font=font(40, True), fill=INK)
        y += 200
    y += 60
    center(d, y, "↓ ここをタップ ↓", font(56, True), MARK)
    y += 110
    # リンクのスタンプを置く場所
    x0, x1, y1 = 160, W - 160, y + 220
    for x in range(x0, x1, 38):
        d.line((x, y, min(x + 20, x1), y), fill=MARK, width=4)
        d.line((x, y1, min(x + 20, x1), y1), fill=MARK, width=4)
    for yy in range(y, y1, 38):
        d.line((x0, yy, x0, min(yy + 20, y1)), fill=MARK, width=4)
        d.line((x1, yy, x1, min(yy + 20, y1)), fill=MARK, width=4)
    return img


def intro_post(sec):
    yt_desc = ("基本情報技術者試験（FE）の無料の学習サイト「FE用語ドリル」の紹介です。\n\n"
               "・科目A：用語345語をカード・4択・書いて答える・意味から答えるの4つのやり方で\n"
               "・科目B：擬似言語のプログラムを1行ずつ再生して、変数の動きを見ながらトレース\n\n"
               f"▶ サイト（無料・登録なし）: {BASE}/?utm_source=youtube&utm_medium=video&utm_campaign=intro\n\n"
               "#基本情報技術者試験 #基本情報 #IT資格 #情報系学生 #科目B #Shorts")
    return {"key": "intro", "title": "FE用語ドリルの紹介", "seconds": sec,
            "video": f"{BASE}/ig/intro/reel.mp4", "cover": f"{BASE}/ig/intro/reel-cover.jpg",
            "caption": reel_caption(),
            "youtube": {"title": "【基本情報】用語と科目Bのトレースを無料で練習できるサイトをつくりました #Shorts", "description": yt_desc}}


STORY_LINK = BASE + "/?utm_source=instagram&utm_medium=story&utm_campaign=intro"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = mb.export_runs()
    item = next(it for it in items if it["kind"] == "trace" and it["id"] == "t1")
    for i, img in enumerate([feed1(), feed2(), feed3(item), feed4(), feed5()], 1):
        img.save(OUT / f"feed-{i}.jpg", "JPEG", quality=88, optimize=True, progressive=True)
    story1().save(OUT / "story-1.jpg", "JPEG", quality=88)
    story2().save(OUT / "story-2.jpg", "JPEG", quality=88)
    sec = make_reel(item, mb.find_ffmpeg())
    (OUT / "intro.json").write_text(json.dumps(intro_post(sec), ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "captions.txt").write_text(
        "■ フィード投稿の投稿文\n\n" + feed_caption() +
        "\n\n\n■ リール動画の投稿文\n\n" + reel_caption() +
        "\n\n\n■ ストーリー2枚目のリンク（スタンプ「リンク」に貼る）\n\n" + STORY_LINK +
        "\nスタンプの文字: FE用語ドリル（無料）\n", encoding="utf-8")
    print(f"static/ig/intro/ に書き出しました（フィード5枚・ストーリー2枚・リール {sec:.1f} 秒）")


if __name__ == "__main__":
    main()
