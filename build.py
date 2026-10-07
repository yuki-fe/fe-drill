"""FE用語ドリルの静的サイトを docs/ に書き出す。

使い方:  python build.py
入力:    config.json（サイトの設定）、data/terms.json（用語）、static/（CSS・JS）
出力:    docs/（GitHub Pages でそのまま公開できる）
"""
import json
import random
import re
import shutil
import sys
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
FIELDS = {"T": "テクノロジ系", "M": "マネジメント系", "S": "ストラテジ系"}
KANA = ["ア", "イ", "ウ", "エ"]

config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
terms = json.loads((ROOT / "data" / "terms.json").read_text(encoding="utf-8"))
by_id = {t["id"]: t for t in terms}
BASE = config["base_url"].rstrip("/")
SITE = config["site_name"]
TODAY = date.today().isoformat()
TERM_ID = {t["term"]: t["id"] for t in terms}


def load_b(name):
    p = ROOT / "data" / "b" / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


# 科目B: algorithms（図鑑）・trace（トレース）・fill（穴埋め）・security（事例）・notation（記法クイズ）・kakomon（過去問解説）
B = {k: load_b(k) for k in ["algorithms", "trace", "fill", "security", "notation", "kakomon"]}


# ---------- 用語の文字列処理 ----------

def aliases(term):
    """「排他的論理和（XOR）」→ 全体・「排他的論理和」・「XOR」のように別名を返す。"""
    out = [term]
    m = re.match(r"^(.*?)[（(](.*?)[)）](.*)$", term)
    if m:
        out.append((m.group(1) + m.group(3)).strip())
        out += [s.strip() for s in re.split(r"[、,]", m.group(2))]
    for a in list(out):
        out += [s.strip() for s in re.split(r"\s*/\s*", a)]
    return [a for a in dict.fromkeys(out) if a]


def masked(t):
    """説明文の中に出てくる答えの用語を「〇〇」で隠す。"""
    d = t["desc"]
    for a in sorted((a for a in aliases(t["term"]) if len(a) >= 2), key=len, reverse=True):
        d = d.replace(a, "〇〇")
    return d


# ---------- 共通レイアウト ----------

def head_extras():
    tags = []
    ga = config.get("google_analytics_id")
    if ga:
        tags.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={escape(ga)}"></script>'
                    f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
                    f"gtag('js',new Date());gtag('config','{escape(ga)}');</script>")
    ad = config.get("adsense_client")
    if ad:
        tags.append(f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={escape(ad)}" crossorigin="anonymous"></script>')
    return "\n".join(tags)


SITEMAP = []  # page() で書き出したページの URL（sitemap.xml に載せる）


def page(path, title, desc, body, rel, body_class="", jsonld=None, scripts="", index=True):
    """path は docs/ からの相対パス。rel はそのページからサイトのルートへの相対パス（"" / "../" / "../../"）。"""
    url = BASE + "/" + ("" if path == "index.html" else path)
    if index:
        SITEMAP.append(url)
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{escape(url)}">
<meta property="og:type" content="{'website' if path == 'index.html' else 'article'}">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:url" content="{escape(url)}">
<meta property="og:site_name" content="{escape(SITE)}">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&family=JetBrains+Mono:wght@500&family=M+PLUS+1+Code:wght@400;500&display=swap">
<link rel="stylesheet" href="{rel}assets/style.css">
{'' if index else '<meta name="robots" content="noindex">'}
{head_extras()}
{ld}
</head>
<body class="{body_class}" data-root="{rel}">
<header class="site-head">
  <a class="brand" href="{rel}index.html">{escape(SITE)}</a>
  <nav class="site-nav" aria-label="サイト内">
    <a href="{rel}index.html">科目A 用語</a>
    <a href="{rel}b/index.html">科目B</a>
    <a href="{rel}terms/index.html">用語一覧</a>
    <a href="{rel}about.html">このサイトについて</a>
  </nav>
</header>
{body}
<footer class="site-foot">
  <nav aria-label="フッター">
    <a href="{rel}terms/index.html">用語一覧</a>
    <a href="{rel}about.html">運営者情報</a>
    <a href="{rel}privacy.html">プライバシーポリシー・免責事項</a>
  </nav>
  <p>基本情報技術者試験は、独立行政法人 情報処理推進機構（IPA）が実施する国家試験です。当サイトはIPAとは関係のない個人の学習サイトです。</p>
  <p>© {date.today().year} {escape(config.get("operator") or SITE)}</p>
</footer>
{scripts}
</body>
</html>
"""
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")


def pr_box():
    """アフィリエイトの枠。景品表示法（ステマ規制）に従い「PR」と表示する。"""
    snippet = config.get("affiliate_html", "").strip()
    if not snippet:
        return ""
    return f'<aside class="pr-box"><span class="pr-label">PR</span><p class="pr-title">試験対策におすすめの教材</p>{snippet}</aside>'


def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


# ---------- 各ページ ----------

def build_home():
    counts = {k: sum(t["field"] == k for t in terms) for k in FIELDS}
    field_links = "".join(f'<li><a href="terms/index.html#{k}">{v}</a><span class="mono">{counts[k]}語</span></li>' for k, v in FIELDS.items())
    body = f"""
<a class="home-feature" href="b/trace.html"><span class="tag">科目B</span><b>プログラムの動きを1行ずつ再生できる「トレース練習」{len(B["trace"])}問</b><span class="go">試してみる →</span></a>
<div class="app">
  <aside class="side">
    <div>
      <p class="label">学び方</p>
      <nav class="modes" role="tablist" id="modes" aria-label="学び方"></nav>
    </div>
    <div>
      <p class="label">分野と覚えた数</p>
      <div class="fields" id="fields"></div>
    </div>
  </aside>
  <main class="main">
    <div class="toolbar" id="toolbar"></div>
    <section class="panel" id="panel"><noscript><p class="empty">この学習機能を使うには JavaScript を有効にしてください。<a href="terms/index.html">用語一覧</a>はそのまま読めます。</p></noscript></section>
    <p class="save-note">進み具合はこのブラウザに保存されます。<button id="reset" type="button">進み具合をリセット</button></p>
  </main>
</div>

<section class="prose home-intro">
  <h1>{escape(SITE)}<small>{escape(config["tagline"])}</small></h1>
  <p>基本情報技術者試験（FE）の科目A・科目Bで出てくる用語を、{len(terms)}語収録しています。登録は不要で、スマホでもパソコンでも無料で使えます。</p>
  <h2>5つの学び方</h2>
  <dl class="howto">
    <dt>カード</dt><dd>用語を見て意味を思い出し、裏返して確かめます。「意味 → 用語」の向きにも切り替えられます。</dd>
    <dt>4択クイズ</dt><dd>本試験と同じア〜エの選択肢から答えを選びます。同じ分野の用語がひっかけとして並びます。</dd>
    <dt>書いて答える</dt><dd>説明を読んで、用語を自分で入力します。ひらがなや英字の略語でも正解になります。</dd>
    <dt>復習</dt><dd>「まだ」を押した用語や、クイズで間違えた用語だけを集めて、カード・4択・書いて答えるで学習し直せます。</dd>
    <dt>一覧</dt><dd>用語を検索し、覚えた用語に印を付けられます。</dd>
  </dl>
  <h2>収録している分野</h2>
  <ul class="field-list">{field_links}</ul>
  <p>すべての用語は<a href="terms/index.html">用語一覧</a>から、1語ずつ解説ページで読めます。</p>
  <h2>科目Bの対策</h2>
  <p>科目Bでは、プログラムの動きを追う「トレース」が鍵になります。このサイトでは、擬似言語のプログラムを<b>1行ずつ再生</b>して、どの行で変数がどう変わるかを目で見て確かめられます。<a href="b/trace.html">トレース練習</a>（{len(B["trace"])}問）のほか、アルゴリズム図鑑、穴埋め問題、情報セキュリティの事例問題、自分で書いたプログラムを動かせるシミュレータも用意しています。<a href="b/index.html">科目Bのページへ</a></p>
</section>
"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": BASE + "/", "description": config["description"]}]
    page("index.html", f"{SITE}｜{config['tagline']}", config["description"], body, "", "home", ld,
         '<script src="assets/terms.js"></script>\n<script src="assets/app.js"></script>')


def related_terms(t, n=6):
    same = [x for x in terms if x["sub"] == t["sub"] and x["id"] != t["id"]]
    if len(same) < 3:
        same += [x for x in terms if x["field"] == t["field"] and x["sub"] != t["sub"]][: 3 - len(same) + 3]
    i = int(t["id"])
    same.sort(key=lambda x: abs(int(x["id"]) - i))
    return same[:n]


def mini_quiz(t, related):
    rng = random.Random(t["id"])
    target = rng.choice(related)
    pool = [x for x in terms if x["sub"] == target["sub"] and x["id"] != target["id"]]
    if len(pool) < 3:
        pool += [x for x in terms if x["field"] == target["field"] and x["sub"] != target["sub"]]
    choices = rng.sample(pool, 3) + [target]
    rng.shuffle(choices)
    answer = choices.index(target)
    buttons = "".join(
        f'<button class="choice" type="button" data-k="{k}"><span class="oval">{KANA[k]}</span><span>{escape(c["term"])}</span></button>'
        for k, c in enumerate(choices))
    return f"""
  <section class="mini-quiz" data-answer="{answer}" data-term="{escape(target['term'])}" data-href="{target['id']}.html">
    <h2>確認問題</h2>
    <p>次の説明に当てはまる用語はどれか。</p>
    <p class="qd">{escape(masked(target))}</p>
    <div class="choices">{buttons}</div>
    <p class="quiz-result" hidden></p>
  </section>"""


def build_term(t, prev, nxt):
    field = FIELDS[t["field"]]
    rel = related_terms(t)
    related_html = "".join(f'<li><a href="{x["id"]}.html">{escape(x["term"])}</a><p>{escape(x["desc"])}</p></li>' for x in rel)
    pager = '<nav class="pager" aria-label="前後の用語">'
    pager += f'<a href="{prev["id"]}.html" rel="prev"><small>前の用語</small>{escape(prev["term"])}</a>' if prev else "<span></span>"
    pager += f'<a href="{nxt["id"]}.html" rel="next" class="next"><small>次の用語</small>{escape(nxt["term"])}</a>' if nxt else "<span></span>"
    pager += "</nav>"
    blinks = B_LINKS.get(t["id"], [])
    b_html = ('<section><h2>科目Bで練習する</h2><ul class="b-links">'
              + "".join(f'<li><a href="../{escape(h)}">{escape(label)}</a></li>' for label, h in blinks)
              + "</ul></section>") if blinks else ""
    body = f"""
<main class="prose term-page">
  <nav class="crumbs" aria-label="パンくずリスト"><a href="../index.html">ホーム</a><span>›</span><a href="index.html#{t['field']}">{field}</a><span>›</span><a href="index.html#sub-{t['field']}-{escape(t['sub'])}">{escape(t['sub'])}</a></nav>
  <p class="eyebrow">{field}・{escape(t['sub'])}</p>
  <h1>{escape(t['term'])}</h1>
  <p class="lead">{escape(t['desc'])}</p>
  <div class="cta-row">
    <a class="btn primary" href="../index.html#card">カードで練習する</a>
    <a class="btn" href="../index.html#type">書いて答える問題に挑戦</a>
  </div>
  <section>
    <h2>同じ分野の用語</h2>
    <ul class="related">{related_html}</ul>
  </section>
  {b_html}
  {mini_quiz(t, rel)}
  {pr_box()}
  {pager}
</main>
"""
    url = f"{BASE}/terms/{t['id']}.html"
    ld = [
        {"@context": "https://schema.org", "@type": "DefinedTerm", "name": t["term"], "description": t["desc"], "url": url,
         "inDefinedTermSet": {"@type": "DefinedTermSet", "name": f"{SITE} 基本情報技術者試験 用語集", "url": f"{BASE}/terms/index.html"}},
        breadcrumb_ld([("ホーム", BASE + "/"), (field, f"{BASE}/terms/index.html#{t['field']}"), (t["term"], url)]),
    ]
    short = t["desc"] if len(t["desc"]) <= 100 else t["desc"][:99] + "…"
    page(f"terms/{t['id']}.html", f"{t['term']}とは？意味と覚え方｜基本情報技術者試験の用語｜{SITE}",
         f"{t['term']}（{field}・{t['sub']}）: {short}", body, "../", "", ld, '<script src="../assets/term.js"></script>')


def build_index():
    sections, toc = [], []
    for k, v in FIELDS.items():
        group = [t for t in terms if t["field"] == k]
        subs = list(dict.fromkeys(t["sub"] for t in group))
        toc.append(f'<li><a href="#{k}">{v}</a><span class="mono">{len(group)}語</span></li>')
        blocks = []
        for s in subs:
            items = "".join(f'<li><a href="{t["id"]}.html">{escape(t["term"])}</a><p>{escape(t["desc"])}</p></li>' for t in group if t["sub"] == s)
            blocks.append(f'<h3 id="sub-{k}-{escape(s)}">{escape(s)}</h3><ul class="term-list">{items}</ul>')
        sections.append(f'<section><h2 id="{k}">{v}</h2>{"".join(blocks)}</section>')
    body = f"""
<main class="prose wide">
  <nav class="crumbs" aria-label="パンくずリスト"><a href="../index.html">ホーム</a><span>›</span><span>用語一覧</span></nav>
  <h1>基本情報技術者試験の用語一覧<small>{len(terms)}語</small></h1>
  <p>基本情報技術者試験の出題範囲を、テクノロジ系・マネジメント系・ストラテジ系の分野ごとに並べています。用語名から解説ページに進めます。</p>
  <ul class="field-list">{''.join(toc)}</ul>
  {pr_box()}
  {''.join(sections)}
</main>
"""
    page("terms/index.html", f"基本情報技術者試験の用語一覧（{len(terms)}語）｜{SITE}",
         f"基本情報技術者試験の頻出用語{len(terms)}語を、分野ごとに一覧にしました。各用語の意味と、同じ分野の用語をまとめて確認できます。",
         body, "../", "", [breadcrumb_ld([("ホーム", BASE + "/"), ("用語一覧", f"{BASE}/terms/index.html")])])


# ---------- 科目B ----------

B_SECTIONS = [
    ("index.html", "トップ"),
    ("notation.html", "擬似言語の書き方"),
    ("algorithms/index.html", "アルゴリズム図鑑"),
    ("trace.html", "トレース練習"),
    ("fill.html", "穴埋め問題"),
    ("security.html", "セキュリティ事例"),
    ("simulator.html", "シミュレータ"),
]
B_LINKS = {}  # 用語 id → [(リンクの文言, docs/ からのパス)]


def collect_b_links():
    links = {}

    def add(names, label, href):
        for n in names:
            links.setdefault(TERM_ID[n], []).append((label, href))

    for a in B["algorithms"]:
        add(a["terms"], f"{a['title']}（アルゴリズム図鑑）", f"b/algorithms/{a['slug']}.html")
    for x in B["trace"]:
        add(x["terms"], f"トレース練習: {x['title']}", f"b/trace.html#{x['id']}")
    for x in B["fill"]:
        add(x["terms"], f"穴埋め問題: {x['title']}", f"b/fill.html#{x['id']}")
    for x in B["security"]:
        add(x["terms"], f"セキュリティ事例: {x['title']}", f"b/security.html#{x['id']}")
    for x in B["kakomon"]:
        add(x.get("terms", []), f"過去問解説: {x['title']}", f"b/kakomon/{x['slug']}.html")
    return links


def b_scripts(rel):
    return (f'<script src="{rel}assets/pseudo.js"></script>\n<script src="{rel}assets/b-data.js"></script>\n'
            f'<script src="{rel}assets/b.js"></script>')


def b_nav(rb, current):
    """rb はそのページから b/ への相対パス。"""
    sections = B_SECTIONS + ([("kakomon/index.html", "過去問解説")] if B["kakomon"] else [])
    cur = ' aria-current="page"'
    items = "".join(f'<a href="{rb}{href}"{cur if href == current else ""}>{label}</a>' for href, label in sections)
    return f'<nav class="b-nav" aria-label="科目Bのメニュー">{items}</nav>'


def b_crumbs(rel, *items):
    parts = [f'<a href="{rel}index.html">ホーム</a>', f'<a href="{rel}b/index.html">科目B</a>']
    for label, href in items:
        parts.append(f'<a href="{href}">{escape(label)}</a>' if href else f"<span>{escape(label)}</span>")
    return '<nav class="crumbs" aria-label="パンくずリスト">' + "<span>›</span>".join(parts) + "</nav>"


def term_chips(names, rel):
    chips = "".join(f'<a class="term-chip" href="{rel}terms/{TERM_ID[n]}.html">{escape(n)}</a>' for n in names)
    return f'<p class="b-related"><span>関連する用語</span>{chips}</p>' if names else ""


def code_pre(lines):
    return f'<pre class="code-plain">{escape(chr(10).join(lines))}</pre>'


def b_page(path, title, desc, body, rel):
    page(path, f"{title}｜基本情報技術者試験 科目B｜{SITE}", desc, body, rel, "b-page", scripts=b_scripts(rel))


def build_b_hub():
    counts = {"trace": len(B["trace"]), "fill": len(B["fill"]), "security": len(B["security"]),
              "notation": len(B["notation"]), "algorithms": len(B["algorithms"])}
    cards = [
        ("notation.html", "擬似言語の書き方", f"記号と書き方の早見表と、確認クイズ {counts['notation']}問。まずはここから。"),
        ("algorithms/index.html", "アルゴリズム図鑑", f"探索・整列・再帰など {counts['algorithms']}種類。プログラムの動きを1行ずつ見られます。"),
        ("trace.html", "トレース練習", f"変数の値を表に書き込んで、プログラムの動きを追う練習 {counts['trace']}問。答え合わせの後、1行ずつ再生して確かめられます。"),
        ("fill.html", "穴埋め問題", f"本番と同じ形の、空欄に入るものを選ぶ問題 {counts['fill']}問。間違えた答えで動かして確かめられます。"),
        ("security.html", "セキュリティ事例", f"場面を読んで正しい対応を選ぶ問題 {counts['security']}問。"),
        ("simulator.html", "シミュレータ", "自分で書いた擬似言語のプログラムを、ブラウザで動かせます。"),
    ]
    if B["kakomon"]:
        cards.append(("kakomon/index.html", "過去問解説", f"IPA の公開問題の解説 {len(B['kakomon'])}問。"))
    cards_html = "".join(f'<a class="b-card" href="{h}"><b>{t}</b><span>{d}</span></a>' for h, t, d in cards)
    body = f"""
<main class="b-wrap">
  {b_crumbs("../")}
  {b_nav("", "index.html")}
  <h1 class="b-title">科目B対策<small>擬似言語のトレースと情報セキュリティ</small></h1>
  <p class="b-intro">科目Bは100分で20問。そのうち16問がアルゴリズムとプログラミング（擬似言語）、4問が情報セキュリティです。用語を覚えるより、<b>プログラムを読んで動きを追う力</b>が問われます。</p>
  <section class="b-feature">
    <p class="b-feature-tag">このサイトだけの機能</p>
    <h2>トレースを、1行ずつ再生して確かめる</h2>
    <p>紙の上で追うしかなかったプログラムの動きを、「再生」「進む」で1行ずつ見られます。いま実行している行と、値が変わった変数に色が付くので、自分のトレースがどこでずれたかをその場で見つけられます。下は二分探索の例です。「再生」を押してみてください。</p>
    <div data-b="trace-demo" data-id="t4"><noscript><p>動きを見るには JavaScript を有効にしてください。</p></noscript></div>
    <div class="cta-row"><a class="btn primary" href="trace.html#t4">この問題を自分で解く</a><a class="btn" href="trace.html">トレース練習 {counts['trace']}問へ</a></div>
  </section>
  <div class="b-cards">{cards_html}</div>
  <section class="b-sec">
    <h2>学習状況</h2>
    <div data-b="dashboard"><noscript><p>学習状況を表示するには JavaScript を有効にしてください。</p></noscript></div>
  </section>
  <section class="b-sec">
    <h2>おすすめの進め方</h2>
    <ol class="b-steps">
      <li><a href="notation.html">擬似言語の書き方</a>で、記号と配列の番号の数え方に慣れる</li>
      <li><a href="algorithms/index.html">アルゴリズム図鑑</a>で、よく出るアルゴリズムの動きを1行ずつ見る</li>
      <li><a href="trace.html">トレース練習</a>で、変数の値を自分で追えるようにする</li>
      <li><a href="fill.html">穴埋め問題</a>と<a href="security.html">セキュリティ事例</a>で、本番の形式に慣れる</li>
      <li>間違えた問題は、上の「復習する問題」から解き直す</li>
    </ol>
  </section>
  <p class="muted">試験の仕組みは、2023年4月からの制度に基づいています。最新の出題範囲と擬似言語の仕様は、IPA の公式サイトで確認してください。</p>
</main>
"""
    b_page("b/index.html", "科目B対策", "基本情報技術者試験の科目B対策。擬似言語の書き方、アルゴリズムの動きが見られる図鑑、トレース練習、穴埋め問題、情報セキュリティの事例問題、擬似言語のシミュレータを無料で使えます。", body, "../")


def build_b_notation():
    body = f"""
<main class="b-wrap">
  {b_crumbs("../", ("擬似言語の書き方", None))}
  {b_nav("", "notation.html")}
  <h1 class="b-title">擬似言語の書き方<small>記号の早見表と確認クイズ</small></h1>
  <p class="b-intro">科目Bのプログラムは、IPA が決めた「擬似言語」で書かれます。よく出る書き方をまとめました。正式な仕様は、試験の問題冊子に載っている説明で必ず確認してください。</p>
  <div class="b-cols notation">
    <section>
      <h2>変数の宣言と代入</h2>
      {code_pre(["整数型: x ← 5", "整数型: i, j", "文字列型: name ← \"FE\"", "x ← x + 1"])}
      <p>「型名: 変数名」で宣言し、← で値を入れます（代入）。型には 整数型・実数型・文字型・文字列型・論理型 があります。</p>
    </section>
    <section>
      <h2>演算子と優先順位</h2>
      <table class="b-table">
        <tr><th>種類</th><th>演算子</th></tr>
        <tr><td>単項</td><td><code>not</code> <code>+</code> <code>−</code></td></tr>
        <tr><td>乗除</td><td><code>×</code> <code>÷</code> <code>mod</code>（余り）</td></tr>
        <tr><td>加減</td><td><code>+</code> <code>−</code></td></tr>
        <tr><td>比較</td><td><code>=</code> <code>≠</code> <code>&lt;</code> <code>&gt;</code> <code>≦</code> <code>≧</code></td></tr>
        <tr><td>論理積</td><td><code>and</code></td></tr>
        <tr><td>論理和</td><td><code>or</code></td></tr>
      </table>
      <p>上ほど先に計算します。and と or は、左側だけで結果が決まると右側を計算しません。</p>
    </section>
    <section>
      <h2>配列</h2>
      {code_pre(["整数型の配列: a ← {4, 8, 15, 16}", "a[1]          /* 4（番号は 1 から） */", "aの要素数      /* 4 */", "aの末尾に 23 の値を追加する", "整数型の配列: b ← {5個の 0}"])}
      <p>番号は <b>1 から</b>始まります。最後の要素は <code>a[aの要素数]</code> です。</p>
    </section>
    <section>
      <h2>条件分岐</h2>
      {code_pre(["if (x > 0)", "  /* x が正のとき */", "elseif (x = 0)", "  /* x が 0 のとき */", "else", "  /* それ以外 */", "endif"])}
    </section>
    <section>
      <h2>繰り返し</h2>
      {code_pre(["while (条件)", "  /* 条件が true の間、繰り返す */", "endwhile", "", "do", "  /* 先に1回実行してから条件を調べる */", "while (条件)", "", "for (i を 1 から n まで 1 ずつ増やす)", "  /* i = 1, 2, …, n */", "endfor"])}
      <p>for は「減らす」もあります（例: <code>i を n から 1 まで 1 ずつ減らす</code>）。</p>
    </section>
    <section>
      <h2>関数と手続</h2>
      {code_pre(["○整数型: add(整数型: a, 整数型: b)", "  return a + b", "", "○show(整数型: x)", "  /* 値を返さない手続 */", "", "大域: 整数型: count ← 0", "/* どの関数からも使える大域変数 */"])}
      <p>「○戻り値の型: 名前(引数)」で関数を、戻り値の型を書かずに手続を宣言します。</p>
    </section>
  </div>
  <section class="b-sec">
    <h2>このサイトでの約束</h2>
    <ul>
      <li>整数どうしの <code>÷</code> は、<b>商（小数点以下を切り捨てた値）</b>として計算します。本番では問題文の説明に従ってください。</li>
      <li><code>print(値)</code> は、値を表示するための<b>このサイト独自の命令</b>です。本番の擬似言語にはありません。</li>
      <li>関数の中身は、○の行より字下げして書きます。</li>
    </ul>
  </section>
  <section class="b-sec">
    <h2>確認クイズ</h2>
    <p>プログラムを実行したときに、print で表示される値を答えてください。</p>
    <div data-b="notation"><noscript><p>クイズを使うには JavaScript を有効にしてください。</p></noscript></div>
  </section>
</main>
"""
    b_page("b/notation.html", "擬似言語の書き方 早見表", "基本情報技術者試験 科目Bの擬似言語の書き方を一覧にしました。変数の宣言、演算子の優先順位、配列（番号は1から）、if・while・for、関数の書き方と、確認クイズ13問。", body, "../")


def build_b_algorithms():
    algos = B["algorithms"]
    items = "".join(f'<a class="b-card" href="{a["slug"]}.html"><b>{escape(a["title"])}</b><span>{escape(a["summary"])}</span><em class="mono">{escape(a["complexity"])}</em></a>' for a in algos)
    body = f"""
<main class="b-wrap">
  {b_crumbs("../../", ("アルゴリズム図鑑", None))}
  {b_nav("../", "algorithms/index.html")}
  <h1 class="b-title">アルゴリズム図鑑<small>擬似言語のコードと、動きの見える化</small></h1>
  <p class="b-intro">科目Bによく出るアルゴリズムを、擬似言語のコードで紹介します。各ページの「進む」「再生」で、どの行が実行され、変数がどう変わるかを1行ずつ確かめられます。</p>
  <div class="b-cards">{items}</div>
</main>
"""
    b_page("b/algorithms/index.html", "アルゴリズム図鑑", f"基本情報技術者試験 科目Bによく出るアルゴリズム{len(algos)}種類（線形探索・二分探索・バブルソート・選択ソート・挿入ソート・再帰など）を、擬似言語のコードと動きのアニメーションで解説します。", body, "../../")
    for a in algos:
        probs = [(f"トレース練習: {x['title']}", f"../trace.html#{x['id']}") for x in B["trace"] if x.get("algo") == a["slug"]]
        probs += [(f"穴埋め問題: {x['title']}", f"../fill.html#{x['id']}") for x in B["fill"] if x.get("algo") == a["slug"]]
        practice = ("<section class=\"b-sec\"><h2>この図鑑の問題を解く</h2><ul class=\"b-links\">"
                    + "".join(f'<li><a href="{h}">{escape(lbl)}</a></li>' for lbl, h in probs) + "</ul></section>") if probs else ""
        others = "".join(f'<li><a href="{x["slug"]}.html">{escape(x["title"])}</a></li>' for x in algos if x is not a)
        body = f"""
<main class="b-wrap">
  {b_crumbs("../../", ("アルゴリズム図鑑", "index.html"), (a["title"], None))}
  {b_nav("../", "algorithms/index.html")}
  <p class="eyebrow">アルゴリズム図鑑</p>
  <h1 class="b-title">{escape(a["title"])}</h1>
  <p class="lead">{escape(a["summary"])}</p>
  <div data-b="viewer" data-algo="{a["slug"]}"><noscript>{code_pre(a["code"])}</noscript></div>
  <div class="b-cols">
    <section><h2>考え方</h2><ul>{"".join(f"<li>{escape(p)}</li>" for p in a["points"])}</ul></section>
    <section><h2>計算量</h2><p class="b-big mono">{escape(a["complexity"])}</p></section>
    <section><h2>試験でのポイント</h2><ul>{"".join(f"<li>{escape(p)}</li>" for p in a["tips"])}</ul></section>
  </div>
  {practice}
  {term_chips(a["terms"], "../../")}
  <section class="b-sec"><h2>ほかのアルゴリズム</h2><ul class="b-links inline">{others}</ul></section>
</main>
"""
        b_page(f"b/algorithms/{a['slug']}.html", f"{a['title']}の擬似言語と動き",
               f"{a['title']}を基本情報技術者試験 科目Bの擬似言語で解説。{a['summary']}", body, "../../")


def build_b_practice(path, key, title, sub, intro, desc, items):
    lst = "".join(f'<li><a href="#{x["id"]}">{escape(x["title"])}</a></li>' for x in items)
    body = f"""
<main class="b-wrap">
  {b_crumbs("../", (title, None))}
  {b_nav("", path.split("/", 1)[1])}
  <h1 class="b-title">{title}<small>{sub}</small></h1>
  <p class="b-intro">{intro}</p>
  <div data-b="{key}" class="b-app"><noscript><p>問題を解くには JavaScript を有効にしてください。</p></noscript></div>
  <details class="b-list"><summary>問題の一覧（{len(items)}問）</summary><ol>{lst}</ol></details>
</main>
"""
    b_page(path, title, desc, body, "../")


def build_b_simulator():
    body = f"""
<main class="b-wrap">
  {b_crumbs("../", ("シミュレータ", None))}
  {b_nav("", "simulator.html")}
  <h1 class="b-title">擬似言語シミュレータ<small>書いたプログラムをブラウザで動かす</small></h1>
  <p class="b-intro">擬似言語でプログラムを書いて「実行する」を押すと、1行ずつの動きと変数の変化を確かめられます。書いた内容はこのブラウザに保存されます。</p>
  <div data-b="simulator"><noscript><p>シミュレータを使うには JavaScript を有効にしてください。</p></noscript></div>
  <section class="b-sec">
    <h2>書き方のメモ</h2>
    <ul>
      <li>関数・手続は <code>○整数型: f(整数型: x)</code> のように宣言し、中身は字下げして書きます。</li>
      <li>字下げしない行は、上から順に実行されます。ここで関数を呼び出してください。</li>
      <li>結果を見るには <code>print(値)</code> を使います（このサイト独自の命令です）。</li>
      <li>記号はボタンで入力できます。<code>&lt;=</code> は ≦、<code>*</code> は ×、<code>/</code> は ÷ としても書けます。</li>
      <li>くわしい書き方は<a href="notation.html">擬似言語の書き方</a>を見てください。</li>
    </ul>
  </section>
</main>
"""
    b_page("b/simulator.html", "擬似言語シミュレータ", "基本情報技術者試験 科目Bの擬似言語で書いたプログラムを、ブラウザでそのまま動かせる無料のシミュレータ。1行ずつの動きと変数の変化を確認できます。", body, "../")


def build_b_kakomon():
    """IPA 公開問題の解説。data/b/kakomon.json に解説があるときだけページを作る。"""
    ks = B["kakomon"]
    if not ks:
        return
    items = "".join(f'<a class="b-card" href="{k["slug"]}.html"><b>{escape(k["title"])}</b><span>{escape(k["summary"])}</span></a>' for k in ks)
    body = f"""
<main class="b-wrap">
  {b_crumbs("../../", ("過去問解説", None))}
  {b_nav("../", "kakomon/index.html")}
  <h1 class="b-title">過去問解説<small>IPA の公開問題</small></h1>
  <div class="b-cards">{items}</div>
</main>
"""
    b_page("b/kakomon/index.html", "過去問解説", "基本情報技術者試験 科目Bの公開問題の解説です。", body, "../../")
    for k in ks:
        sections = "".join(f'<section class="b-sec"><h2>{escape(s["h"])}</h2>' + "".join(f"<p>{escape(p)}</p>" for p in s["p"]) + "</section>" for s in k["sections"])
        viewer = f'<div data-b="code" class="b-sec">{code_pre(k["code"])}</div>' if k.get("code") else ""
        body = f"""
<main class="b-wrap">
  {b_crumbs("../../", ("過去問解説", "index.html"), (k["title"], None))}
  {b_nav("../", "kakomon/index.html")}
  <h1 class="b-title">{escape(k["title"])}</h1>
  <p class="lead">{escape(k["summary"])}</p>
  <p class="muted">出典: <a href="{escape(k["source"]["url"])}">{escape(k["source"]["name"])}</a></p>
  {viewer}
  {sections}
  {term_chips(k.get("terms", []), "../../")}
</main>
"""
        b_page(f"b/kakomon/{k['slug']}.html", k["title"], k["summary"], body, "../../")


def build_b():
    build_b_hub()
    build_b_notation()
    build_b_algorithms()
    build_b_practice("b/trace.html", "trace", "トレース練習", "変数の値を表に書き込んで追う",
                     "プログラムを1行ずつ追い、指定された行を実行した直後の変数の値を表に書き込みます。答え合わせの後は<b>「▶ 動きを見る」でプログラムを1行ずつ再生</b>して、どの行で変数がどう変わるかを確かめられます。自分のトレースがどこでずれたかが、その場でわかります。",
                     f"基本情報技術者試験 科目Bのトレース練習{len(B['trace'])}問。擬似言語のプログラムを1行ずつ再生して、変数の動きを目で見て確かめられます。表に書き込んで答え合わせもできる無料の練習問題です。", B["trace"])
    build_b_practice("b/fill.html", "fill", "穴埋め問題", "空欄に入るものを選ぶ",
                     "本番と同じく、プログラムの空欄に入るものをア〜エから選びます。間違えたときは、選んだ答えでプログラムを動かして、どこがおかしくなるかを確かめられます。",
                     f"基本情報技術者試験 科目Bの擬似言語の穴埋め問題{len(B['fill'])}問。解説付きで、正しい答えと選んだ答えのそれぞれでプログラムの動きを確認できます。", B["fill"])
    build_b_practice("b/security.html", "security", "セキュリティ事例", "場面を読んで正しい対応を選ぶ",
                     "科目Bの情報セキュリティの問題では、会社で起きた出来事を読んで、適切な対応を選ぶ力が問われます。",
                     f"基本情報技術者試験 科目Bの情報セキュリティ事例問題{len(B['security'])}問。フィッシング、ランサムウェア、SQLインジェクションなどの場面で、正しい対応を解説付きで学べます。", B["security"])
    build_b_simulator()
    build_b_kakomon()
    data = {k: B[k] for k in ["algorithms", "trace", "fill", "security", "notation"]}
    data["terms"] = TERM_ID
    (OUT / "assets" / "b-data.js").write_text("window.FE_B = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")


def write_b_check():
    """科目Bの全問を実際に動かして確かめるページ（checks/b-check.html。公開しない）。"""
    d = ROOT / "checks"
    d.mkdir(exist_ok=True)
    (d / "b-check.html").write_text("""<!doctype html><meta charset="utf-8"><title>科目B データ確認</title>
<body><pre id="out">確認中…</pre>
<script src="../docs/assets/pseudo.js"></script><script src="../docs/assets/b-data.js"></script>
<script>
const B = FE_B, P = Pseudo, lines = []; let ng = 0;
const out = (r) => r.error ? "エラー: " + r.error.message : r.output.join(" / ");
function ok(name, cond, detail) { lines.push((cond ? "OK " : "NG ") + name + (cond ? "" : " … " + detail)); if (!cond) ng++; }
B.algorithms.forEach((a) => { const r = P.run(a.code.concat(a.main).join("\\n"), { record: false }); ok("図鑑 " + a.slug, !r.error && r.output.join("\\n") === a.expect, out(r)); });
B.trace.forEach((t) => {
  const r = P.run(t.code.concat(t.main).join("\\n"));
  const rows = r.events.filter((e) => e.phase === "after" && e.line === t.line);
  ok("トレース " + t.id + "（" + rows.length + "行）", !r.error && rows.length >= 1 && rows.length <= 10, out(r));
  rows.forEach((e, i) => lines.push("    " + (i + 1) + ": " + t.vars.map((v) => v + "=" + P.format(v in e.vars ? e.vars[v] : (e.globals || {})[v])).join(", ")));
});
B.fill.forEach((f) => f.choices.forEach((c, k) => {
  const code = f.code.map((l) => l.replace("{{a}}", c));
  const pass = f.tests.every((t) => { const r = P.run(code.concat(t.main).join("\\n"), { record: false }); return !r.error && r.output.join("\\n") === t.expect; });
  ok("穴埋め " + f.id + " 選択肢" + "アイウエ"[k], k === f.answer ? pass : !pass, k === f.answer ? "正解なのにテストが通らない" : "不正解なのにテストが通ってしまう");
}));
B.notation.forEach((n) => { const r = P.run(n.code.join("\\n"), { record: false }); ok("記法 " + n.id, !r.error && r.output.join("\\n") === n.answer, out(r)); });
document.getElementById("out").textContent = (ng ? "NG " + ng + "件" : "ALL OK") + "\\n" + lines.join("\\n");
</script>
""", encoding="utf-8")


def contact_html():
    c = config.get("contact", "").strip()
    if not c:
        return "（お問い合わせ先を config.json の contact に設定してください）"
    if c.startswith("http"):
        return f'<a href="{escape(c)}">お問い合わせフォーム</a>'
    return escape(c)


def build_about():
    op = escape(config.get("operator") or "（運営者名を config.json の operator に設定してください）")
    body = f"""
<main class="prose">
  <h1>このサイトについて</h1>
  <h2>サイトの目的</h2>
  <p>{escape(SITE)}は、基本情報技術者試験を受ける人が、すきま時間に用語を覚えられるように作った無料の学習サイトです。</p>
  <h2>用語の説明について</h2>
  <p>用語の説明は、運営者がAIの支援を受けて作成し、内容を確認したうえで掲載しています。試験の公式な定義や最新の出題範囲は、IPAの公式サイトで確認してください。誤りに気づいた場合は、下記のお問い合わせ先から教えていただけると助かります。</p>
  <h2>運営者情報</h2>
  <table class="info">
    <tr><th>サイト名</th><td>{escape(SITE)}</td></tr>
    <tr><th>運営者</th><td>{op}</td></tr>
    <tr><th>開設日</th><td>{escape(config.get("established", ""))}</td></tr>
    <tr><th>お問い合わせ</th><td>{contact_html()}</td></tr>
  </table>
  <p>当サイトは、独立行政法人 情報処理推進機構（IPA）とは関係ありません。</p>
</main>
"""
    page("about.html", f"このサイトについて｜{SITE}", f"{SITE}の目的と運営者情報です。", body, "")


def build_privacy():
    parts = []
    if config.get("google_analytics_id"):
        parts.append("""<h2>アクセス解析ツールについて</h2>
  <p>当サイトでは、Googleによるアクセス解析ツール「Googleアナリティクス」を使っています。Googleアナリティクスはデータの収集のためにCookieを使用します。このデータは匿名で収集されており、個人を特定するものではありません。この機能はブラウザの設定でCookieを無効にすることで拒否できます。詳しくは<a href="https://marketingplatform.google.com/about/analytics/terms/jp/">Googleアナリティクス利用規約</a>をご覧ください。</p>""")
    if config.get("adsense_client"):
        parts.append("""<h2>広告の配信について</h2>
  <p>当サイトでは、第三者配信の広告サービス「Google AdSense」を利用しています。Googleなどの第三者配信事業者は、Cookieを使用して、利用者が当サイトや他のサイトに過去にアクセスした際の情報に基づいて広告を配信します。利用者は<a href="https://adssettings.google.com/">広告設定</a>でパーソナライズ広告を無効にできます。詳しくは<a href="https://policies.google.com/technologies/ads?hl=ja">Googleの広告に関するポリシー</a>をご覧ください。</p>""")
    if config.get("affiliate_html") or config.get("amazon_associate"):
        amazon = "<p>当サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。</p>" if config.get("amazon_associate") else ""
        parts.append(f"""<h2>アフィリエイトプログラムについて</h2>
  <p>当サイトには、商品やサービスを紹介するアフィリエイトリンクが含まれます。該当する箇所には「PR」と表示しています。</p>
  {amazon}""")
    body = f"""
<main class="prose">
  <h1>プライバシーポリシー・免責事項</h1>
  <h2>学習の記録について</h2>
  <p>学習機能の進み具合（覚えた用語など）は、利用者のブラウザの中（localStorage）にだけ保存されます。運営者のサーバに送られることはありません。ブラウザのデータを消去すると、進み具合も消えます。</p>
  <h2>個人情報の利用目的</h2>
  <p>お問い合わせの際に、お名前やメールアドレスなどの個人情報をご提供いただく場合があります。これらの情報は、お問い合わせへの回答や必要な連絡のためにだけ利用し、法令に基づく場合を除き、本人の同意なく第三者に提供しません。</p>
  {''.join(parts)}
  <h2>免責事項</h2>
  <p>当サイトの内容は、できる限り正確な情報を掲載するよう努めていますが、正確性や最新性を保証するものではありません。当サイトの情報を利用したことで生じた損害について、運営者は責任を負いません。</p>
  <p>当サイトからリンクしている外部サイトの内容について、運営者は責任を負いません。</p>
  <h2>著作権</h2>
  <p>当サイトに掲載している文章の著作権は運営者に帰属します。無断での転載はご遠慮ください。</p>
  <h2>お問い合わせ</h2>
  <p>{contact_html()}</p>
  <h2>改定</h2>
  <p>このページの内容は、必要に応じて予告なく変更することがあります。</p>
  <p class="muted">制定日: {escape(config.get("established", ""))} / 最終更新日: {TODAY}</p>
</main>
"""
    page("privacy.html", f"プライバシーポリシー・免責事項｜{SITE}", f"{SITE}のプライバシーポリシーと免責事項です。", body, "")


def build_404():
    body = """
<main class="prose">
  <h1>ページが見つかりません</h1>
  <p>お探しのページは、移動したか削除された可能性があります。</p>
  <p><a href="index.html">ホームに戻る</a> / <a href="terms/index.html">用語一覧を見る</a></p>
</main>
"""
    page("404.html", f"ページが見つかりません｜{SITE}", "お探しのページは見つかりませんでした。", body, "", index=False)


def build_meta_files():
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{escape(u)}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in SITEMAP)
    sitemap += "</urlset>\n"
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    ad = config.get("adsense_client", "")
    if ad:
        pub = ad.replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    # 独自ドメインのときは GitHub Pages 用の CNAME を書く（docs/ を作り直しても設定が消えないように）
    host = urlparse(BASE).hostname or ""
    if host and not host.endswith("github.io"):
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")
    data =[{"id": t["id"], "f": t["field"], "sub": t["sub"], "term": t["term"], "desc": t["desc"]} for t in terms]
    (OUT / "assets" / "terms.js").write_text("window.FE_TERMS = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")


def check():
    """データと設定の問題を探す。致命的なものがあれば中断する。"""
    errors, warnings = [], []
    ids = [t["id"] for t in terms]
    names = [t["term"] for t in terms]
    for x in set(ids):
        if ids.count(x) > 1:
            errors.append(f"id が重複しています: {x}")
    for x in set(names):
        if names.count(x) > 1:
            errors.append(f"用語が重複しています: {x}")
    for t in terms:
        if t["field"] not in FIELDS:
            errors.append(f"{t['id']} の field が不正です: {t['field']}")
        if not re.fullmatch(r"\d{4}", t["id"]):
            errors.append(f"id は4桁の数字にしてください: {t['id']}")
    # 科目B
    slugs = {a["slug"] for a in B["algorithms"]}
    for kind in ["algorithms", "trace", "fill", "security", "notation", "kakomon"]:
        keys = [x.get("id") or x.get("slug") for x in B[kind]]
        for x in set(keys):
            if keys.count(x) > 1:
                errors.append(f"科目B {kind} の id が重複しています: {x}")
        for x in B[kind]:
            name = f"科目B {kind} {x.get('id') or x.get('slug')}"
            for n in x.get("terms", []):
                if n not in TERM_ID:
                    errors.append(f"{name}: 用語「{n}」が data/terms.json にありません")
            if x.get("algo") and x["algo"] not in slugs:
                errors.append(f"{name}: 図鑑「{x['algo']}」がありません")
            if kind in ("fill", "security") and not (0 <= x["answer"] < len(x["choices"]) == 4):
                errors.append(f"{name}: 選択肢は4つ、answer は 0〜3 にしてください")
            if kind == "fill" and sum(line.count("{{a}}") for line in x["code"]) != 1:
                errors.append(f"{name}: 空欄 {{{{a}}}} はコードに1つだけ入れてください")
            if kind == "trace" and not (1 <= x["line"] <= len(x["code"])):
                errors.append(f"{name}: line がコードの行数の範囲外です")
    if "YOUR-NAME" in BASE:
        warnings.append("config.json の base_url が仮の値のままです（公開するURLに変えてください）")
    if not config.get("operator"):
        warnings.append("config.json の operator（運営者名）が空です")
    if not config.get("contact"):
        warnings.append("config.json の contact（お問い合わせ先）が空です。AdSense の審査ではほぼ必須です")
    return errors, warnings


def main():
    errors, warnings = check()
    for e in errors:
        print("エラー:", e)
    if errors:
        sys.exit(1)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    B_LINKS.update(collect_b_links())
    build_home()
    build_index()
    for i, t in enumerate(terms):
        build_term(t, terms[i - 1] if i > 0 else None, terms[i + 1] if i + 1 < len(terms) else None)
    build_about()
    build_privacy()
    build_404()
    build_b()
    build_meta_files()
    write_b_check()
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"docs/ に {n} ページを書き出しました（用語 {len(terms)} 語、科目B {len(B['algorithms'])} 図鑑・{len(B['trace']) + len(B['fill']) + len(B['security']) + len(B['notation'])} 問）")
    print("科目Bの答えの確認: checks/b-check.html をブラウザで開いてください")
    for w in warnings:
        print("注意:", w)


if __name__ == "__main__":
    main()
