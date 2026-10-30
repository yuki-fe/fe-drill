"""用語の確認: 用語ドリルの各サイトの用語から、今回確かめるものを選んで一覧にする（スキル /term-review が使う）。

使い方:  python review_tools/term_review.py                次に確かめるサイトを選んで、一覧を作る
         python review_tools/term_review.py --site ip -n 30  サイトと数を決めて
         python review_tools/term_review.py --done 一覧.md     一覧の用語を「確かめた」と記録する
         python review_tools/term_review.py --status         サイトごとの確かめた数

選び方: 1年以内に確かめていない用語のうち、古くなりやすいもの（数字・年・法律・制度・版・料金などを含む説明）を先に。
サイトは、確かめた割合がいちばん少ないサイト（同じならサイトの順）。試験の変更の見張りで最近変わったサイトを --site で先にしてもよい。
一覧と記録は notes/用語の確認/（公開しない）。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
SITE = HERE.parent
DESK = SITE.parent
OUT = SITE / "notes" / "用語の確認"
STATE = OUT / "state.json"
AGAIN_DAYS = 365

# サイトの key → リポジトリのフォルダ（sites.json の順）
REPOS = {"fe": SITE, "ip": DESK / "ip-drill", "cloud": DESK / "cloud-drill", "genai": DESK / "genai-drill",
         "dl": DESK / "dl-drill", "boki": DESK / "boki-drill", "iryo": DESK / "iryo-drill"}

# 古くなりやすい説明の目印（重み）
RISKS = [
    (r"\d{4}年|令和|平成|年度", 3, "年"),
    (r"法律|法令|(保護|基本|防止|促進|規制|権|基準|取引|契約|署名|保存|表示|会社|医療|保険|税|派遣|下請|民|刑|商)法|条例|ガイドライン|指針|告示|省令|政令", 3, "法律・決まり"),
    (r"制度|改正|改定|新設|廃止|施行|義務", 3, "制度"),
    (r"版|バージョン|Ver\.?|v\d|第\d+版|C0\d", 2, "版"),
    (r"料金|価格|円|ドル|\$|無料|有料|課金", 2, "料金"),
    (r"\d+(%|％|割|倍|日|か月|ヶ月|年|時間|分|秒|GB|TB|MB|ビット|bit)", 2, "数字"),
    (r"最新|現行|主流|唯一|近年|最近", 2, "今の状態"),
    (r"ISO|JIS|IEEE|RFC|IEC|規格|標準", 1, "規格"),
    (r"AWS|Amazon|Azure|Google|Microsoft|OpenAI|サービス名", 1, "サービス"),
]


def site_names():
    p = DESK / "yogo-drill" / "sites.json"
    if p.exists():
        return {x["key"]: x["name"] for x in json.loads(p.read_text(encoding="utf-8"))["sites"]}
    return {k: k for k in REPOS}


def load_terms(key):
    return json.loads((REPOS[key] / "data" / "terms.json").read_text(encoding="utf-8"))


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"checked": {}}


def save_state(st):
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def risk(t):
    text = t.get("term", "") + " " + t.get("desc", "")
    score, why = 0, []
    for pat, w, name in RISKS:
        if re.search(pat, text):
            score += w
            why.append(name)
    return score, why


def fresh_ids(st, key):
    """1年以内に確かめた用語の id"""
    limit = (date.today() - timedelta(days=AGAIN_DAYS)).isoformat()
    return {i for i, d in st["checked"].get(key, {}).items() if d >= limit}


def status(st):
    names = site_names()
    rows = []
    for key in REPOS:
        if not (REPOS[key] / "data" / "terms.json").exists():
            continue
        terms = load_terms(key)
        done = fresh_ids(st, key) & {t["id"] for t in terms}
        rows.append((len(done) / max(1, len(terms)), key, names.get(key, key), len(done), len(terms)))
    return rows


def make_list(st, key, n):
    names = site_names()
    terms = load_terms(key)
    done = fresh_ids(st, key)
    cand = []
    for t in terms:
        if t["id"] in done:
            continue
        s, why = risk(t)
        cand.append((-s, t["id"], t, why))
    cand.sort(key=lambda x: (x[0], x[1]))
    pick = cand[:n]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{date.today().isoformat()}_{key}.md"
    lines = [f"# 用語の確認 {date.today().isoformat()} {names.get(key, key)}（{key}）", "",
             f"リポジトリ: `{REPOS[key]}`。{len(terms)} 語のうち、1年以内に確かめていない {len(cand)} 語から {len(pick)} 語。",
             "古くなりやすい目印が多い順。結果の欄に「OK」か「直す: 〇〇」（出典の URL つき）を書く。", "",
             "| id | 用語 | 説明 | 目印 | 結果 |", "|---|---|---|---|---|"]
    for _, i, t, why in pick:
        desc = t.get("desc", "").replace("|", "｜").replace("\n", " ")
        lines.append(f"| {i} | {t['term']} | {desc} | {'・'.join(why)} | |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, len(pick), len(cand)


def mark_done(st, path):
    p = Path(path)
    m = re.search(r"_([a-z]+)\.md$", p.name)
    if not m or m.group(1) not in REPOS:
        sys.exit(f"一覧のファイル名から、サイトがわかりません: {p.name}")
    key = m.group(1)
    ids = re.findall(r"^\| (\w+) \|", p.read_text(encoding="utf-8"), re.M)
    ids = [i for i in ids if i != "id"]
    day = date.today().isoformat()
    st["checked"].setdefault(key, {}).update({i: day for i in ids})
    save_state(st)
    return key, len(ids)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", choices=list(REPOS))
    ap.add_argument("-n", type=int, default=40)
    ap.add_argument("--done", help="確かめ終わった一覧の .md")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    st = load_state()
    if args.done:
        key, n = mark_done(st, args.done)
        print(f"{key} の {n} 語を「確かめた」と記録しました（{STATE}）")
        return
    rows = status(st)
    if args.status:
        for r, key, name, d, total in rows:
            print(f"{name}（{key}）: {d}/{total} 語（{r:.0%}）")
        return
    order = list(REPOS)
    key = args.site or min(rows, key=lambda r: (r[0], order.index(r[1])))[1]
    path, n, left = make_list(st, key, args.n)
    print(f"一覧: {path}")
    print(f"サイト: {key}・{n} 語（まだ確かめていない {left} 語のうち）")


if __name__ == "__main__":
    main()
