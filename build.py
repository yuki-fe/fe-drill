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


def page(path, title, desc, body, rel, body_class="", jsonld=None, scripts=""):
    """path は docs/ からの相対パス。rel はそのページからサイトのルートへの相対パス（"" か "../"）。"""
    url = BASE + "/" + ("" if path == "index.html" else path)
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&family=JetBrains+Mono:wght@500&display=swap">
<link rel="stylesheet" href="{rel}assets/style.css">
{head_extras()}
{ld}
</head>
<body class="{body_class}">
<header class="site-head">
  <a class="brand" href="{rel}index.html">{escape(SITE)}</a>
  <nav class="site-nav" aria-label="サイト内">
    <a href="{rel}index.html">学習する</a>
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
  <h2>4つの学び方</h2>
  <dl class="howto">
    <dt>カード</dt><dd>用語を見て意味を思い出し、裏返して確かめます。「意味 → 用語」の向きにも切り替えられます。</dd>
    <dt>4択クイズ</dt><dd>本試験と同じア〜エの選択肢から答えを選びます。同じ分野の用語がひっかけとして並びます。</dd>
    <dt>書いて答える</dt><dd>説明を読んで、用語を自分で入力します。ひらがなや英字の略語でも正解になります。</dd>
    <dt>一覧</dt><dd>用語を検索し、覚えた用語に印を付けられます。</dd>
  </dl>
  <h2>収録している分野</h2>
  <ul class="field-list">{field_links}</ul>
  <p>すべての用語は<a href="terms/index.html">用語一覧</a>から、1語ずつ解説ページで読めます。</p>
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
    page("404.html", f"ページが見つかりません｜{SITE}", "お探しのページは見つかりませんでした。", body, "")


def build_meta_files():
    urls = [BASE + "/", f"{BASE}/terms/index.html", f"{BASE}/about.html", f"{BASE}/privacy.html"]
    urls += [f"{BASE}/terms/{t['id']}.html" for t in terms]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{escape(u)}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls)
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
    build_home()
    build_index()
    for i, t in enumerate(terms):
        build_term(t, terms[i - 1] if i > 0 else None, terms[i + 1] if i + 1 < len(terms) else None)
    build_about()
    build_privacy()
    build_404()
    build_meta_files()
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"docs/ に {n} ページを書き出しました（用語 {len(terms)} 語）")
    for w in warnings:
        print("注意:", w)


if __name__ == "__main__":
    main()
