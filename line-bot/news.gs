/* FE用語ドリル 運用LINE: ITニュース（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- ITニュース（Google ニュースの検索結果の RSS を読む） ---------- */
function selectedGenres() {
  return jsonProp("NEWS_GENRES", DEFAULT_GENRES);
}

function genreQuery(name) {
  return NEWS_GENRES[name] || name;
}

/* 1ジャンル分のニュース: [{ title, source, link }]。取れなかったときは null。when は "1d"（24時間）や "7d"（1週間） */
function fetchNews(name, count, when) {
  try {
    const q = encodeURIComponent(genreQuery(name) + " when:" + (when || "1d"));
    const res = UrlFetchApp.fetch("https://news.google.com/rss/search?q=" + q + "&hl=ja&gl=JP&ceid=JP:ja", { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return null;
    const items = XmlService.parse(res.getContentText()).getRootElement().getChild("channel").getChildren("item");
    return items.slice(0, count).map((it) => {
      const source = it.getChildText("source") || "";
      let title = it.getChildText("title") || "";
      if (source && title.endsWith(" - " + source)) title = title.slice(0, -(source.length + 3));
      return { title, source, link: it.getChildText("link") };
    });
  } catch (e) {
    console.warn(e);
    return null;
  }
}

function newsText(genres, perGenre, head) {
  const blocks = [head];
  genres.forEach((g) => {
    const items = fetchNews(g, perGenre);
    blocks.push("", "■ " + g);
    if (items === null) blocks.push(TALK.newsError);
    else if (!items.length) blocks.push(TALK.newsNone);
    else items.forEach((n) => blocks.push(`・${n.title}${n.source ? "（" + n.source + "）" : ""}\n${n.link}`));
  });
  return blocks.join("\n");
}

function changeGenres(arg) {
  const sel = selectedGenres();
  let m;
  if ((m = arg.match(/^追加\s*(.+)$/))) {
    const g = m[1].trim();
    if (sel.length >= 5) return TALK.genreTooMany;
    if (sel.indexOf(g) < 0) sel.push(g);
    PROPS.setProperty("NEWS_GENRES", JSON.stringify(sel));
    return TALK.genreAdded(g);
  }
  if ((m = arg.match(/^(外す|削除|消す)\s*(.+)$/))) {
    const g = m[2].trim();
    if (sel.indexOf(g) < 0) return TALK.genreMissing(g);
    PROPS.setProperty("NEWS_GENRES", JSON.stringify(sel.filter((x) => x !== g)));
    return TALK.genreRemoved(g);
  }
  const list = arg.split(/[、,\s]+/).map((s) => s.trim()).filter(Boolean);
  if (list.length > 5) return TALK.genreTooMany;
  PROPS.setProperty("NEWS_GENRES", JSON.stringify(list));
  return TALK.genreSet(list);
}

/* ---------- 今週のITニュース（土曜の Instagram 投稿） ----------
 * Google ニュースの RSS は「個人で読むため」のものなので、自動で選んでそのまま載せない。
 * 候補を LINE に出し（運営者が読む）、運営者が選んだものだけを、見出し・媒体名・ひとことで紹介する。
 *
 * 状態（スクリプト プロパティ IG_NEWS、その日のぶんだけ有効）:
 *   { date, cand: [候補], stage: "pick" }                      候補を出して、選ぶのを待っている
 *   { date, cand, stage: "image", no, term, items, images, caption, at, waiting }   画像を作っている／できた
 * 投稿したら IG_NEWS_DONE にその日の日付を入れる。
 * 画像は GitHub の自動実行（.github/workflows/news-image.yml）が作る。合言葉 GITHUB_TOKEN がないときは、決まった表紙を使う */

const todayStr = () => fmt(new Date(), "yyyy-MM-dd");

function newsState() {
  const st = jsonProp("IG_NEWS", null);
  return st && st.date === todayStr() ? st : null;
}

function saveNewsState(st) {
  PROPS.setProperty("IG_NEWS", JSON.stringify(st));
}

/* 投稿できる状態のニュース（igCurrent から使う）。投稿済み・まだ選んでいないときは null */
function newsCurrent() {
  if (prop("IG_NEWS_DONE") === todayStr()) return null;
  const st = newsState();
  return st && st.stage === "image" ? st : null;
}

/* サイトの用語（assets/terms.js）。ニュースの見出しに出てくる試験の用語を探すのに使う */
function siteTerms() {
  try {
    const res = UrlFetchApp.fetch(CONFIG.siteUrl + "assets/terms.js", { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return [];
    const s = res.getContentText();
    return JSON.parse(s.slice(s.indexOf("["), s.lastIndexOf("]") + 1));
  } catch (e) {
    console.warn("用語を読めませんでした: " + e.message);
    return [];
  }
}

/* 「排他的論理和（XOR）」→「排他的論理和（XOR）」「排他的論理和」「XOR」（build.py の aliases と同じ考え方） */
function termAliases(term) {
  const out = [term];
  const m = term.match(/^(.*?)[（(](.*?)[)）](.*)$/);
  if (m) out.push((m[1] + m[3]).trim(), ...m[2].split(/[、,]/).map((s) => s.trim()));
  return out.filter((a) => a && a.length >= 2);
}

/* 見出しに出てくる、いちばん長い試験の用語。英数字の用語は単語の途中では一致させない（IP と IPO など） */
function relatedTerm(title, terms) {
  const t = title.normalize("NFKC").toLowerCase();
  let best = null, bestLen = 0;
  terms.forEach((x) => termAliases(x.term).forEach((a) => {
    const name = a.normalize("NFKC").toLowerCase();
    if (name.length <= bestLen) return;
    for (let i = t.indexOf(name); i >= 0; i = t.indexOf(name, i + 1)) {
      const okBefore = !/^[a-z0-9]/.test(name) || !/[a-z0-9]/.test(t[i - 1] || "");
      const okAfter = !/[a-z0-9]$/.test(name) || !/[a-z0-9]/.test(t[i + name.length] || "");
      if (okBefore && okAfter) { best = x; bestLen = name.length; break; }
    }
  }));
  return best ? best.term : "";
}

/* この1週間の候補を集める。ジャンルを順番に回して、試験の用語が出てくるものを先にする */
function newsCandidates() {
  const terms = siteTerms();
  const seen = {};
  const pools = selectedGenres().map((g) => (fetchNews(g, 12, "7d") || [])
    .filter((n) => n.title && !seen[n.title] && (seen[n.title] = true))
    .map((n) => ({ t: n.title, s: n.source, g, term: relatedTerm(n.title, terms) }))
    .sort((a, b) => (b.term ? 1 : 0) - (a.term ? 1 : 0)));
  const cand = [];
  for (let round = 0; cand.length < CONFIG.newsCandidates && pools.some((p) => p.length > round); round++) {
    pools.forEach((p) => { if (p[round] && cand.length < CONFIG.newsCandidates) cand.push(p[round]); });
  }
  return cand;
}

/* 「10/3〜10/9」（今日の7日前から前日まで） */
function newsRange() {
  const d = (n) => fmt(new Date(Date.now() - n * 86400000), "M/d");
  return `${d(7)}〜${d(1)}`;
}

/* 土曜の下書き（毎朝のレポート・「インスタ ニュース」）。まだ選んでいなければ候補、選んだあとは投稿の下書き */
function newsDraftMessage(prefix) {
  if (prop("IG_NEWS_DONE") === todayStr()) return { type: "text", text: TALK.newsPosted };
  let st = newsState();
  if (!st) {
    const cand = newsCandidates();
    if (!cand.length) return { type: "text", text: TALK.newsNoCandidates };
    st = { date: todayStr(), cand, stage: "pick" };
    saveNewsState(st);
  }
  if (st.stage === "pick") return newsPickMessage(st, prefix);
  return newsReadyDraft(st, prefix);
}

function newsPickMessage(st, prefix) {
  const list = st.cand.map((c, i) => `${i + 1}. ${c.t}（${c.s || "?"}）` + (c.term ? `\n   → 試験の用語「${c.term}」` : ""));
  return {
    type: "text",
    text: [prefix, TALK.newsPickHead(CONFIG.newsPostCount), ""].concat(list, ["", TALK.newsPickFoot(CONFIG.newsPostCount)]).filter((x) => x !== undefined).join("\n"),
    quickReply: { items: [qr("おまかせで作る", "ig=newsauto&k=news"), qr("今日はやめる", "ig=skip&k=news")] },
  };
}

/* 番号で選ぶ（nums が null なら、おまかせ: 用語が出てくるものを、ジャンルが重ならないように先に選ぶ） */
function newsChoose(nums) {
  if (prop("IG_NEWS_DONE") === todayStr()) return TALK.newsPosted;
  const st = newsState();
  if (!st) return newsDraftMessage();
  if (st.stage === "image" && st.waiting) return TALK.newsMaking;
  let picks;
  if (nums) {
    const idx = [...new Set(nums)].map((n) => n - 1);
    if (!idx.length || idx.length > Math.min(3, CONFIG.newsPostCount) || idx.some((i) => !st.cand[i])) return TALK.newsBadNumbers(st.cand.length, CONFIG.newsPostCount);
    picks = idx.map((i) => st.cand[i]);
  } else {
    const order = st.cand.filter((c) => c.term).concat(st.cand.filter((c) => !c.term));
    picks = [];
    order.forEach((c) => { if (picks.length < CONFIG.newsPostCount && !picks.some((p) => p.g === c.g)) picks.push(c); });
    order.forEach((c) => { if (picks.length < CONFIG.newsPostCount && picks.indexOf(c) < 0) picks.push(c); });
  }
  const items = picks.map((c) => ({ title: c.t, source: c.s, genre: c.g, term: c.term }));
  const version = (st.version || 0) + 1;
  const no = `${st.date}-${version}`;
  const range = newsRange();
  Object.assign(st, { stage: "image", version, no, items, term: `今週のITニュース ${range}`, caption: newsCaption(items, range, !!prop("GITHUB_TOKEN") && items.some((it) => it.term)), at: Date.now() });
  if (!prop("GITHUB_TOKEN")) {
    st.images = [CONFIG.siteUrl + "ig/news/cover.jpg"];
    st.waiting = false;
    saveNewsState(st);
    return [TALK.newsNoToken].concat(newsReadyDraft(st));
  }
  const base = CONFIG.siteUrl + "ig/news/" + no;
  st.images = [base + "-1.jpg"].concat(items.some((it) => it.term) ? [base + "-2.jpg"] : []);
  try {
    githubDispatch("news-image", { no, range, items });
  } catch (e) {
    return TALK.newsDispatchError(e.message);
  }
  st.waiting = true;
  saveNewsState(st);
  return TALK.newsMaking;
}

/* glossary: 2枚目（用語の解説）の画像があるか */
function newsCaption(items, range, glossary) {
  const nums = "①②③";
  const body = items.map((it, i) => `${nums[i]} ${it.title}（${it.source || "?"}）\n→ ` +
    (it.term ? `試験に出る用語「${it.term}」が関係するニュース。意味を確かめておこう。` : NEWS_NOTES[it.genre] || NEWS_NOTES[""]));
  return [`【今週のITニュース】${range}`, `この1週間のITニュースから${items.length}つ。基本情報の用語とあわせてチェックしよう。`, ""]
    .concat(body.join("\n\n"), "")
    .concat(glossary ? ["2枚目では、ニュースに出てきた試験の用語を解説しています。", ""] : [])
    .concat(["※ 見出しと媒体名を紹介しています。くわしくは各媒体の記事で読んでください。",
      "用語の意味と4択クイズは、プロフィールのリンクの「FE用語ドリル」から（無料）。", "",
      "#ITニュース #テックニュース #基本情報技術者試験 #基本情報 #IT資格 #情報系学生 #IT用語"]).join("\n");
}

/* 画像ができたあとの下書き（いつもの下書きと同じボタン） */
function newsReadyDraft(st, prefix) {
  if (st.waiting) return { type: "text", text: TALK.newsMaking };
  const d = `k=news&id=${st.no}`;
  const preview = st.caption.length > 700 ? st.caption.slice(0, 700) + "…" : st.caption;
  const text = {
    type: "text",
    text: [prefix, TALK.igHead(IG_KINDS.news.label, st.term), "", "―― 投稿文 ――", preview].filter((x) => x !== undefined).join("\n"),
    quickReply: { items: [
      qr("今すぐ投稿", "ig=post&" + d),
      qr("素材を受け取る", "ig=kit&" + d),
      qr(`${CONFIG.scheduleHour}時に投稿`, "ig=sched&" + d),
      qr("選び直す", "ig=newsrepick&" + d),
      qr("今日はやめる", "ig=skip&" + d),
    ] },
  };
  return st.images.map((u) => ({ type: "image", originalContentUrl: u, previewImageUrl: u })).concat(text);
}

/* 「選び直す」: 候補の一覧に戻る */
function newsRepick() {
  const st = newsState();
  if (!st) return newsDraftMessage();
  if (st.waiting) return TALK.newsMaking;
  st.stage = "pick";
  saveNewsState(st);
  return newsPickMessage(st);
}

/* igWorker から: 画像ができたら（サイトに出たら）下書きを送る。30分たってもできなければ知らせる */
function newsWorker() {
  const st = newsState();
  if (!st || st.stage !== "image" || !st.waiting) return;
  const ready = st.images.every((u) => UrlFetchApp.fetch(u, { muteHttpExceptions: true }).getResponseCode() === 200);
  if (ready) {
    st.waiting = false;
    saveNewsState(st);
    push([TALK.newsImageReady].concat(newsReadyDraft(st)).slice(0, 5));
  } else if (Date.now() - st.at > 30 * 60 * 1000) {
    st.waiting = false;
    st.stage = "pick";
    saveNewsState(st);
    push(TALK.newsImageTimeout);
  }
}

/* GitHub の自動実行を動かす（合言葉 GITHUB_TOKEN: リポジトリの Contents の読み書きだけを許可したもの） */
function githubDispatch(type, payload) {
  const res = UrlFetchApp.fetch(`https://api.github.com/repos/${CONFIG.githubRepo}/dispatches`, {
    method: "post", contentType: "application/json", muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + prop("GITHUB_TOKEN"), Accept: "application/vnd.github+json" },
    payload: JSON.stringify({ event_type: type, client_payload: payload }),
  });
  if (res.getResponseCode() !== 204) throw new Error(`GitHub ${res.getResponseCode()}`);
}
