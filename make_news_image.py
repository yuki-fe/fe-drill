"""Instagram の「今週のITニュース」の画像（1080×1350）を作る。

ふだんは GitHub の自動実行（.github/workflows/news-image.yml）が動かす。
LINE ボットで運営者がニュースを選ぶと、ボットが GitHub に「画像を作って」と頼み、ここが呼ばれる。

  1枚目: 選んだニュースの見出し・媒体名・関係する試験の用語
  2枚目: ニュースに出てきた試験の用語の説明（用語が1つもないときは作らない）

使い方:  NEWS_PAYLOAD='{"no": "2026-10-10-1", "range": "10/3〜10/9", "items": [...]}' python make_news_image.py
         python make_news_image.py --cover     （ボットの合言葉がないとき用の、決まった表紙 cover.jpg を作る）
出力:    static/ig/news/〇〇-1.jpg・〇〇-2.jpg（docs/ への写しは自動実行がする）
         見出しは記事の本文や画像を使わず、ボットから受け取った見出しと媒体名だけを描く
"""
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from build import FIELDS, aliases, terms
from make_ig_images import BG, INK, LINE, MARK, MUTED, OK, OK_SOFT, PAPER, font

OUT = Path(__file__).parent / "static" / "ig" / "news"
W, H = 1080, 1350
KEEP_DAYS = 56  # これより古い画像は消す（投稿した後の画像は Instagram 側に残るので要らない）
NUMS = "①②③"


def frame(label, color, foot_right):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((48, 48, W - 48, H - 48), radius=36, fill=PAPER, outline=LINE, width=2)
    f = font(34, True)
    d.rounded_rectangle((96, 100, 96 + f.getlength(label) + 56, 164), radius=32, fill=color)
    d.text((124, 113), label, font=f, fill=PAPER)
    d.text((96, H - 130), "FE用語ドリル", font=font(32, True), fill=INK)
    fr = font(24)
    d.text((W - 96 - fr.getlength(foot_right), H - 122), foot_right, font=fr, fill=MUTED)
    return img, d


def wrap(text, f, width):
    """折り返す。英数字の単語（IaaS など）は途中で切らず、句読点や閉じ括弧は行頭に置かない。"""
    rows, cur = [], ""
    for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9.+#/-]*|.", text):
        if cur and f.getlength(cur + tok) > width:
            if tok in "、。，．）」』】・ー":
                cur += tok
                continue
            rows.append(cur.rstrip())
            cur = tok.lstrip()
        else:
            cur += tok
    return rows + ([cur] if cur else [])


def lines(d, x, y, rows, f, fill, gap=1.45):
    for r in rows:
        d.text((x, y), r, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def clip_lines(text, f, width, n):
    rows = wrap(text, f, width)
    if len(rows) > n:
        rows = rows[:n]
        rows[-1] = rows[-1][:-1] + "…"
    return rows


def headlines(p):
    img, d = frame("今週のITニュース", MARK, "見出しと媒体名を紹介しています")
    d.text((W - 96 - font(30).getlength(p["range"]), 120), p["range"], font=font(30), fill=MUTED)
    y = lines(d, 96, 200, ["この1週間の", "ITニュース"], font(64, True), INK, 1.3) + 30
    n = len(p["items"])
    block = (H - 190 - y) // max(n, 1)
    for k, it in enumerate(p["items"]):
        top = y + block * k
        d.line((96, top, W - 96, top), fill=LINE, width=2)
        d.text((96, top + 26), NUMS[k], font=font(52, True), fill=MARK)
        hf = font(38, True)
        yy = lines(d, 170, top + 28, clip_lines(it["title"], hf, W - 96 - 170, 3), hf, INK, 1.4)
        d.text((170, yy + 4), it.get("source") or "", font=font(26), fill=MUTED)
        yy += 52
        if it.get("term"):
            chip, color, back = f"試験の用語：{it['term']}", OK, OK_SOFT
        else:
            chip, color, back = f"ジャンル：{it.get('genre') or 'IT'}", MUTED, BG
        cf = font(26, True)
        d.rounded_rectangle((170, yy, 170 + cf.getlength(chip) + 40, yy + 48), radius=24, fill=back)
        d.text((190, yy + 9), chip, font=cf, fill=color)
    return img


def term_info(name):
    for t in terms:
        if name in aliases(t["term"]):
            return t
    return None


def glossary(p):
    found, seen = [], set()
    for it in p["items"]:
        t = term_info(it.get("term") or "")
        if t and t["id"] not in seen:
            seen.add(t["id"])
            found.append(t)
    if not found:
        return None
    img, d = frame("ニュースに出てきた試験の用語", OK, "用語の4択クイズはプロフィールのリンクから")
    top = 220
    for t in found:
        tf = font(56 if len(found) < 3 else 48, True)
        d.text((96, top), clip_lines(t["term"], tf, W - 192, 1)[0], font=tf, fill=INK)
        d.text((96, top + tf.size + 18), f"{FIELDS[t['field']]}・{t['sub']}", font=font(28), fill=OK)
        df = font(34)
        rows = clip_lines(t["desc"], df, W - 192 - 64, 4 if len(found) < 3 else 3)
        by = top + tf.size + 74
        bottom = by + len(rows) * int(34 * 1.55) + 44
        d.rounded_rectangle((96, by, W - 96, bottom), radius=20, fill=OK_SOFT)
        lines(d, 128, by + 22, rows, df, INK, 1.55)
        top = bottom + 64
    return img


def cover():
    img, d = frame("今週のITニュース", MARK, "見出しと媒体名を紹介しています")
    y = lines(d, 96, 260, ["この1週間の", "ITニュース"], font(110, True), INK, 1.3) + 60
    y = lines(d, 96, y, ["基本情報の用語とあわせて", "チェックしよう"], font(52, True), MARK, 1.45) + 60
    lines(d, 96, y, ["見出しは投稿文を見てね"], font(40), MUTED)
    return img


def clean_payload(raw):
    p = json.loads(raw)
    no = str(p.get("no", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{1,3}", no):  # ファイル名に使うので、形を確かめる
        sys.exit(f"no の形が違います: {no!r}")
    items = []
    for it in (p.get("items") or [])[:3]:
        items.append({k: str(it.get(k) or "")[:120] for k in ("title", "source", "genre", "term")})
    if not items:
        sys.exit("items が空です")
    return {"no": no, "range": str(p.get("range") or "")[:20], "items": items}


def remove_old():
    limit = date.today() - timedelta(days=KEEP_DAYS)
    for f in OUT.glob("*.jpg"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-", f.name)
        if m and date.fromisoformat(m.group(1)) < limit:
            f.unlink()


def save(img, name):
    img.save(OUT / name, "JPEG", quality=86, optimize=True, progressive=True)
    print("作りました:", OUT / name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if "--cover" in sys.argv:
        save(cover(), "cover.jpg")
        return
    p = clean_payload(os.environ.get("NEWS_PAYLOAD") or sys.stdin.read())
    save(headlines(p), f"{p['no']}-1.jpg")
    g = glossary(p)
    if g:
        save(g, f"{p['no']}-2.jpg")
    remove_old()


if __name__ == "__main__":
    main()
