/**
 * FE用語ドリル 運用LINE（キャラクター: 先輩エンジニア）
 *
 * お問い合わせフォームの回答スプレッドシートに付ける Google Apps Script。
 * - フォームに投稿があったら LINE に知らせる
 * - 毎朝、閲覧者の数・検索の数字・サイトの状態・最後の更新・未対応のお問い合わせ・ITニュース・
 *   Instagram の投稿の下書きを、1通にまとめて送る（月曜は先週の閲覧者のグラフも付ける）
 * - LINE で「状況」「グラフ」「人気」「問い合わせ」「済 3」「ニュース」「ジャンル」「インスタ」「使い方」と送ると返事をする
 * - Instagram は、LINE の「投稿する」ボタンを押したときだけ投稿する
 *
 * 合言葉（LINE や Instagram のトークンなど）はコードに書かず、「スクリプト プロパティ」に保存する。
 * 手順は「LINE運用ボットの作り方.pdf」「ニュースとInstagramの設定.pdf」「アクセス解析とグラフの設定.pdf」を参照。
 */

/* ========== サイトの設定（公開されても困らない値） ========== */
const CONFIG = {
  siteName: "FE用語ドリル",
  siteUrl: "https://yuki-fe.github.io/fe-drill/",        // サイトのURL（Search Console に登録したものと同じ）
  githubRepo: "yuki-fe/fe-drill",                         // 最後の更新を調べるリポジトリ
  reportHour: 8,                                          // 毎朝のレポートを送る時刻（0〜23時）
  chartWeekday: 1,                                        // 先週のグラフを送る曜日（0=日曜, 1=月曜, … 6=土曜）
  newsPerGenre: 2,                                        // 毎朝のレポートに載せる、ジャンルごとのニュースの数
  instagramApi: "https://graph.instagram.com/v23.0",      // Instagram API（バージョンは Meta の案内に合わせて変える）
};

/* ========== ニュースのジャンル ==========
 * 「ジャンル 追加 〇〇」で、ここにない言葉もそのまま検索の言葉として追加できる。 */
const NEWS_GENRES = {
  "AI": "生成AI OR 人工知能 OR ChatGPT OR LLM",
  "セキュリティ": "サイバー攻撃 OR 脆弱性 OR 情報漏えい OR ランサムウェア",
  "クラウド": "クラウド AWS OR Azure OR \"Google Cloud\"",
  "プログラミング": "プログラミング OR ソフトウェア開発 OR エンジニア",
  "IT資格": "情報処理技術者試験 OR 基本情報技術者 OR IT資格",
  "スマホ・ガジェット": "iPhone OR Android OR ガジェット",
  "IT業界": "IT企業 OR テック企業 OR DX",
  "半導体": "半導体",
  "ゲーム": "ゲーム業界 OR ゲーム開発",
};
const DEFAULT_GENRES = ["AI", "セキュリティ", "IT資格"];

/* ========== 話し方の設定（先輩エンジニア） ==========
 * 文の中身を変えれば、キャラクターの話し方を変えられる。
 * 配列になっているものは、毎回その中から1つが選ばれる。 */
const TALK = {
  morning: [
    "おはよう！昨日までのドリルの様子をまとめといたよ。",
    "おはよ。今朝のレポートだよ。",
    "おはよう。コーヒー片手にどうぞ。今日の様子ね。",
  ],
  now: ["今の様子をまとめたよ。", "はい、最新の状況ね。"],
  visitorsDay: (u, v) => `昨日: ${u} 人（ページ ${v} 回）`,
  visitorsWeek: (u, d) => `直近7日: ${u} 人（その前の7日より ${d >= 0 ? "+" : ""}${d} 人）`,
  visitorsUp: "先週より増えてる。この調子！",
  visitorsDown: "先週より少し減ったね。週によって波があるから、気長にいこう。",
  visitorsSame: "先週と同じくらいだね。",
  gaError: "閲覧者の数は取れなかった。アナリティクスの設定を見直してみて（「アクセス解析とグラフの設定」参照）。",
  gaOff: "アナリティクスはまだつながってないよ。「アクセス解析とグラフの設定」を見てね。",
  chartText: (u, d) => `直近7日の閲覧者のグラフだよ。合計 ${u} 人（その前の7日より ${d >= 0 ? "+" : ""}${d} 人）。\n赤い線が直近7日、灰色の点線がその前の7日。`,
  chartWeekly: "今週もおつかれ。先週1週間の閲覧者をグラフにしといたよ。",
  rankHead: "直近7日でよく見られたページはこれ。",
  rankNone: "まだランキングを出せるほどデータがないみたい。",
  searchUp: (n) => `前の日より ${n} 回増えたね、いい感じ。`,
  searchDown: (n) => `前の日より ${n} 回減ったけど、日によって波があるから気にしなくていいよ。`,
  searchSame: "前の日と同じくらいだね。",
  searchNone: "まだ検索のデータがないみたい。載り始めるまで、のんびり待とう。",
  searchError: "検索の数字は取れなかった。Search Console の設定を見直してみて（手順書の「困ったとき」参照）。",
  siteOk: (sec) => `ちゃんと動いてる（${sec}秒で表示）。`,
  siteNg: (why) => `あれ、サイトが開けないみたい（${why}）。GitHub の Pages の設定を見てみて。`,
  updated: (date, msg) => `${date}「${msg}」`,
  updatedUnknown: "取れなかった（GitHub が混んでるのかも）。",
  inquiryNone: "お問い合わせは今のところないよ。",
  inquirySome: (n) => `未対応が ${n} 件あるから、時間あるときに見といて。「問い合わせ」で一覧を出せるよ。`,
  newInquiry: (no) => `お問い合わせが来たよ！（${no}番）`,
  newInquiryFoot: (no) => `対応したら「済 ${no}」って送ってね。対応済みにしとくから。`,
  listHead: (n) => `未対応のお問い合わせは ${n} 件。`,
  listFoot: "対応したら「済 番号」って送ってね。",
  done: (no) => `${no}番、対応済みにしといた。おつかれ！`,
  doneAlready: (no) => `${no}番はもう対応済みになってるよ。`,
  doneMissing: (no) => `${no}番のお問い合わせは見つからなかった。「問い合わせ」で番号を確かめてみて。`,

  newsHead: "ITニュースもまとめといたよ。気になるのがあったら読んでみて。",
  newsGenreHead: (g) => `「${g}」の最新ニュースね。`,
  newsNone: "この24時間は目立ったニュースがなかったみたい。",
  newsError: "ニュースが取れなかった。少し時間をおいて「ニュース」って送ってみて。",
  genreList: (sel, all) => `今見てるジャンルはこれ。\n${sel.map((g) => "・" + g).join("\n")}\n\n選べるジャンル: ${all.join("、")}\n\n変えたいときは、こう送ってね。\n・ジャンル 追加 クラウド\n・ジャンル 外す ゲーム\n・ジャンル AI、セキュリティ（まとめて入れ替え）\n一覧にない言葉（例: 量子コンピュータ）も追加できるよ。`,
  genreAdded: (g) => `「${g}」を追加したよ。明日の朝から届くね。今すぐ見たいなら「ニュース ${g}」って送って。`,
  genreRemoved: (g) => `「${g}」を外したよ。`,
  genreMissing: (g) => `「${g}」は今のジャンルに入ってないみたい。「ジャンル」で一覧を見てみて。`,
  genreSet: (list) => `ジャンルを入れ替えたよ: ${list.join("、")}`,
  genreTooMany: "ジャンルは5つまでにしとこう。多すぎると朝のレポートが長くなるからね。",

  igHead: (no, term) => `今日のインスタの下書きだよ（No.${no}「${term}」）。画像はリンクから確認してね。`,
  igPosted: (url) => `インスタに投稿したよ！\n${url}\nコメントが来てたら返してあげてね。`,
  igPostError: (why) => `投稿できなかった…（${why}）。「ニュースとInstagramの設定」の「困ったとき」を見てみて。`,
  igImageMissing: "画像がまだ公開されてないみたい。make_ig_images.py を実行して、GitHub に Push した？",
  igSkipped: "了解、今日はお休みね。",
  igNext: "別の用語にしたよ。",
  igEmpty: "投稿のストックがなくなったよ。make_ig_images.py の数を増やして実行して、GitHub に Push してね。",
  igOff: "インスタはまだつながってないよ。設定の手順書を見てね。",
  igStale: "それは前の下書きのボタンだよ。今の下書きは「インスタ」って送ると出せるよ。",

  help: [
    "使えることばはこれだよ。",
    "・状況 … 閲覧者・検索の数字やサイトの様子",
    "・グラフ … 直近7日の閲覧者のグラフ",
    "・人気 … 直近7日でよく見られたページ",
    "・問い合わせ … 未対応のお問い合わせの一覧",
    "・済 3 … 3番のお問い合わせを対応済みにする",
    "・ニュース … 今のジャンルの最新ITニュース（「ニュース AI」で1ジャンルだけ）",
    "・ジャンル … ニュースのジャンルを見る・変える",
    "・インスタ … 今日の Instagram の下書き",
    "・使い方 … この説明",
    "毎朝のレポートも送るね。",
  ].join("\n"),
  unknown: [
    "ごめん、それはまだわからないんだ。「使い方」って送ると、できることを出すよ。",
    "うーん、その言葉は知らないなあ。「使い方」で一覧を出せるよ。",
  ],
  registered: "登録できた！これからドリルの様子を知らせるね。よろしく。\n\n",
  needRegister: "はじめまして。運営者の人は「登録 合言葉」って送ってね。",
  notOwner: "ごめんね、このアカウントは運営者専用なんだ。",
  greeting: "友だち追加ありがとう。FE用語ドリルの運用を手伝う先輩だよ。運営者の人は「登録 合言葉」って送ってね。",
};

/* ========== ここから下は、ふだん変えなくてよい部分 ========== */

const PROPS = PropertiesService.getScriptProperties();
const prop = (k) => PROPS.getProperty(k) || "";
const pick = (a) => (Array.isArray(a) ? a[Math.floor(Math.random() * a.length)] : a);
const fmt = (d, f) => Utilities.formatDate(d, "Asia/Tokyo", f);
const jsonProp = (k, d) => { try { return JSON.parse(prop(k)) || d; } catch (e) { return d; } };

/* ---------- 最初に1回だけ実行する（設定を変えたときも、もう一度実行してよい） ---------- */
function setup() {
  if (!prop("LINE_TOKEN")) throw new Error("スクリプト プロパティに LINE_TOKEN を入れてから、もう一度実行してください。");
  if (!prop("WEBHOOK_KEY")) PROPS.setProperty("WEBHOOK_KEY", Utilities.getUuid().replace(/-/g, ""));
  if (!prop("SETUP_CODE")) PROPS.setProperty("SETUP_CODE", String(Math.floor(100000 + Math.random() * 900000)));
  if (!prop("NEWS_GENRES")) PROPS.setProperty("NEWS_GENRES", JSON.stringify(DEFAULT_GENRES));
  ScriptApp.getProjectTriggers().forEach((t) => ScriptApp.deleteTrigger(t));
  const ss = SpreadsheetApp.getActive();
  ScriptApp.newTrigger("onFormSubmit").forSpreadsheet(ss).onFormSubmit().create();
  ScriptApp.newTrigger("dailyReport").timeBased().atHour(CONFIG.reportHour).everyDays(1).inTimezone("Asia/Tokyo").create();
  ScriptApp.newTrigger("refreshInstagramToken").timeBased().everyWeeks(1).onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(4).create();
  doneColumn(responseSheet());
  Logger.log("準備ができました。");
  Logger.log("Webhook の URL の最後に付ける文字: ?key=" + prop("WEBHOOK_KEY"));
  Logger.log("LINE で送る登録の言葉: 登録 " + prop("SETUP_CODE"));
  Logger.log("Instagram: " + (igReady() ? "つながっています" : "まだ設定されていません（IG_TOKEN と IG_USER_ID）"));
  Logger.log("アナリティクス: " + (gaReady() ? "プロパティ " + prop("GA_PROPERTY_ID") : "まだ設定されていません（GA_PROPERTY_ID）"));
}

/* LINE を使わずに、毎朝のレポートの中身だけを確かめる */
function testReport() {
  morningMessages().forEach((m) => Logger.log(m.text));
}

/* 登録した LINE に、試しに毎朝のレポートを送る */
function testPush() {
  push(morningMessages());
}

/* ---------- 毎朝のレポート（1回の送信にまとめて、送信数を1通に抑える） ---------- */
function dailyReport() {
  if (prop("OWNER_USER_ID")) push(morningMessages());
}

function morningMessages() {
  const msgs = [{ type: "text", text: buildReport(true) }];
  if (gaReady() && new Date(fmt(new Date(), "yyyy/MM/dd")).getDay() === CONFIG.chartWeekday) {
    const st = visitorStats();
    if (st) msgs.push({ type: "text", text: TALK.chartWeekly }, chartMessage(st));
  }
  msgs.push({ type: "text", text: newsText(selectedGenres(), CONFIG.newsPerGenre, TALK.newsHead) });
  if (igReady()) msgs.push(igDraftMessage());
  return msgs.slice(0, 5);
}

function buildReport(morning) {
  const lines = [pick(morning ? TALK.morning : TALK.now), ""];
  if (gaReady()) {
    const st = visitorStats();
    lines.push("【閲覧者】");
    if (!st) lines.push(TALK.gaError);
    else {
      const y = st.days[st.days.length - 1];
      lines.push(TALK.visitorsDay(y.users, y.views), TALK.visitorsWeek(st.week, st.week - st.prevWeek));
      lines.push(st.week > st.prevWeek ? TALK.visitorsUp : st.week < st.prevWeek ? TALK.visitorsDown : TALK.visitorsSame);
    }
    lines.push("");
  }
  const s = searchStats();
  lines.push("【検索】");
  if (s.error) lines.push(TALK.searchError);
  else if (!s.latest) lines.push(TALK.searchNone);
  else {
    lines.push(`${s.latest.date} の分: 表示 ${s.latest.impressions} 回、クリック ${s.latest.clicks} 回`);
    lines.push(`直近7日: 表示 ${s.week.impressions} 回、クリック ${s.week.clicks} 回`);
    if (s.prev) {
      const diff = s.latest.impressions - s.prev.impressions;
      lines.push(diff > 0 ? TALK.searchUp(diff) : diff < 0 ? TALK.searchDown(-diff) : TALK.searchSame);
    }
  }
  const h = siteHealth();
  lines.push("", "【サイト】", h.ok ? TALK.siteOk(h.sec) : TALK.siteNg(h.why));
  const u = lastUpdate();
  lines.push("", "【最後の更新】", u ? TALK.updated(u.date, u.message) : TALK.updatedUnknown);
  const n = openInquiries().length;
  lines.push("", "【お問い合わせ】", n ? TALK.inquirySome(n) : TALK.inquiryNone);
  return lines.join("\n");
}

/* ---------- 閲覧者（Google アナリティクス 4） ---------- */
function gaReady() {
  return !!prop("GA_PROPERTY_ID");
}

function gaReport(body) {
  try {
    const res = UrlFetchApp.fetch("https://analyticsdata.googleapis.com/v1beta/properties/" + prop("GA_PROPERTY_ID") + ":runReport", {
      method: "post", contentType: "application/json", muteHttpExceptions: true,
      headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(body),
    });
    if (res.getResponseCode() !== 200) {
      console.warn("Analytics: " + res.getResponseCode() + " " + res.getContentText().slice(0, 300));
      return null;
    }
    return JSON.parse(res.getContentText());
  } catch (e) {
    console.warn(e);
    return null;
  }
}

/* 直近14日（昨日まで）の日ごとの閲覧者数。データのない日は 0 で埋める */
function visitorStats() {
  const r = gaReport({
    dateRanges: [{ startDate: "14daysAgo", endDate: "yesterday" }],
    dimensions: [{ name: "date" }],
    metrics: [{ name: "activeUsers" }, { name: "screenPageViews" }],
  });
  if (!r) return null;
  const byDate = {};
  (r.rows || []).forEach((row) => {
    byDate[row.dimensionValues[0].value] = { users: Number(row.metricValues[0].value), views: Number(row.metricValues[1].value) };
  });
  const days = [];
  for (let n = 14; n >= 1; n--) {
    const d = new Date(Date.now() - n * 86400000);
    const v = byDate[fmt(d, "yyyyMMdd")] || { users: 0, views: 0 };
    days.push({ label: fmt(d, "M/d"), users: v.users, views: v.views });
  }
  const sum = (a) => a.reduce((t, x) => t + x.users, 0);
  return { days: days.slice(7), prevDays: days.slice(0, 7), week: sum(days.slice(7)), prevWeek: sum(days.slice(0, 7)) };
}

/* グラフの画像（QuickChart）。日本語の文字化けを避けるため、グラフの中は数字と日付だけにする */
function chartUrl(st) {
  const cfg = {
    type: "line",
    data: {
      labels: st.days.map((d) => d.label),
      datasets: [
        { data: st.days.map((d) => d.users), borderColor: "#c0435a", backgroundColor: "rgba(192,67,90,0.12)", fill: true, cubicInterpolationMode: "monotone", pointRadius: 6, pointBackgroundColor: "#c0435a", borderWidth: 4 },
        { data: st.prevDays.map((d) => d.users), borderColor: "#9aa5a6", borderDash: [8, 6], fill: false, cubicInterpolationMode: "monotone", pointRadius: 0, borderWidth: 3 },
      ],
    },
    options: {
      legend: { display: false },
      layout: { padding: { left: 12, right: 36, top: 16, bottom: 8 } },
      scales: {
        yAxes: [{ ticks: { beginAtZero: true, precision: 0, fontSize: 18 }, gridLines: { color: "#e3e8e5" } }],
        xAxes: [{ ticks: { fontSize: 18 }, gridLines: { display: false } }],
      },
    },
  };
  return "https://quickchart.io/chart?w=900&h=500&bkg=white&f=png&c=" + encodeURIComponent(JSON.stringify(cfg));
}

function chartMessage(st) {
  const url = chartUrl(st);
  return { type: "image", originalContentUrl: url, previewImageUrl: url };
}

function chartReply() {
  if (!gaReady()) return TALK.gaOff;
  const st = visitorStats();
  if (!st) return TALK.gaError;
  return [TALK.chartText(st.week, st.week - st.prevWeek), chartMessage(st)];
}

/* 直近7日でよく見られたページ（タイトルの「｜」より前だけを見せる） */
function rankingText() {
  if (!gaReady()) return TALK.gaOff;
  const r = gaReport({
    dateRanges: [{ startDate: "7daysAgo", endDate: "yesterday" }],
    dimensions: [{ name: "pageTitle" }],
    metrics: [{ name: "screenPageViews" }],
    orderBys: [{ metric: { metricName: "screenPageViews" }, desc: true }],
    limit: 5,
  });
  if (!r) return TALK.gaError;
  const rows = r.rows || [];
  if (!rows.length) return TALK.rankNone;
  return [TALK.rankHead, ""].concat(rows.map((row, i) =>
    `${i + 1}. ${row.dimensionValues[0].value.split("｜")[0]}（${row.metricValues[0].value} 回）`)).join("\n");
}

/* Search Console: 直近10日分を日ごとに取り、データがある最新の日と前の日を比べる */
function searchStats() {
  try {
    const url = "https://searchconsole.googleapis.com/webmasters/v3/sites/" + encodeURIComponent(CONFIG.siteUrl) + "/searchAnalytics/query";
    const day = (n) => fmt(new Date(Date.now() - n * 86400000), "yyyy-MM-dd");
    const res = UrlFetchApp.fetch(url, {
      method: "post", contentType: "application/json", muteHttpExceptions: true,
      headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
      payload: JSON.stringify({ startDate: day(10), endDate: day(1), dimensions: ["date"] }),
    });
    if (res.getResponseCode() !== 200) {
      console.warn("Search Console: " + res.getResponseCode() + " " + res.getContentText().slice(0, 300));
      return { error: true };
    }
    const rows = (JSON.parse(res.getContentText()).rows || [])
      .map((r) => ({ date: Number(r.keys[0].slice(5, 7)) + "/" + Number(r.keys[0].slice(8, 10)), key: r.keys[0], clicks: r.clicks, impressions: r.impressions }))
      .sort((a, b) => (a.key < b.key ? -1 : 1));
    if (!rows.length) return {};
    const week = rows.slice(-7).reduce((t, r) => ({ clicks: t.clicks + r.clicks, impressions: t.impressions + r.impressions }), { clicks: 0, impressions: 0 });
    return { latest: rows[rows.length - 1], prev: rows[rows.length - 2], week };
  } catch (e) {
    console.warn(e);
    return { error: true };
  }
}

function siteHealth() {
  try {
    const t = Date.now();
    const res = UrlFetchApp.fetch(CONFIG.siteUrl, { muteHttpExceptions: true, followRedirects: true });
    const code = res.getResponseCode();
    return code === 200 ? { ok: true, sec: ((Date.now() - t) / 1000).toFixed(1) } : { ok: false, why: "エラー " + code };
  } catch (e) {
    return { ok: false, why: "つながらない" };
  }
}

/* 最後の更新: GitHub の更新フィード（Atom）を読む。API は Apps Script からだと回数制限にかかりやすいため */
function lastUpdate() {
  try {
    const res = UrlFetchApp.fetch("https://github.com/" + CONFIG.githubRepo + "/commits/main.atom", { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return null;
    const ns = XmlService.getNamespace("http://www.w3.org/2005/Atom");
    const entry = XmlService.parse(res.getContentText()).getRootElement().getChild("entry", ns);
    if (!entry) return null;
    return { date: fmt(new Date(entry.getChildText("updated", ns)), "M/d"), message: entry.getChildText("title", ns).trim().split("\n")[0] };
  } catch (e) {
    console.warn(e);
    return null;
  }
}

/* ---------- ITニュース（Google ニュースの検索結果の RSS を読む） ---------- */
function selectedGenres() {
  return jsonProp("NEWS_GENRES", DEFAULT_GENRES);
}

function genreQuery(name) {
  return NEWS_GENRES[name] || name;
}

/* 1ジャンル分のニュース: [{ title, source, link }]。取れなかったときは null */
function fetchNews(name, count) {
  try {
    const q = encodeURIComponent(genreQuery(name) + " when:1d");
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

/* ---------- Instagram（下書き → LINE のボタンで投稿） ---------- */
function igReady() {
  return !!(prop("IG_TOKEN") && prop("IG_USER_ID"));
}

/* サイトに置いた投稿のストック（make_ig_images.py が作る ig/posts.json） */
function igPosts() {
  const res = UrlFetchApp.fetch(CONFIG.siteUrl + "ig/posts.json", { muteHttpExceptions: true });
  return res.getResponseCode() === 200 ? JSON.parse(res.getContentText()) : [];
}

function igCurrent() {
  const posts = igPosts();
  return posts[Number(prop("IG_NEXT") || 0)] || null;
}

function igDraftMessage(prefix) {
  const p = igCurrent();
  if (!p) return { type: "text", text: TALK.igEmpty };
  const preview = p.caption.length > 600 ? p.caption.slice(0, 600) + "…" : p.caption;
  return {
    type: "text",
    text: [prefix, TALK.igHead(p.no, p.term), "", "1枚目: " + p.images[0], "2枚目: " + p.images[1], "", "―― 投稿文 ――", preview].filter((x) => x !== undefined).join("\n"),
    quickReply: { items: [
      qr("投稿する", "ig=post&no=" + p.no),
      qr("別の用語にする", "ig=next&no=" + p.no),
      qr("今日はやめる", "ig=skip&no=" + p.no),
    ] },
  };
}

function qr(label, data) {
  return { type: "action", action: { type: "postback", label, data, displayText: label } };
}

function igCall(path, params, method) {
  const opts = { method: method || "post", muteHttpExceptions: true };
  if (params) opts.payload = Object.assign({ access_token: prop("IG_TOKEN") }, params);
  const sep = path.indexOf("?") >= 0 ? "&" : "?";
  const url = CONFIG.instagramApi + path + (params ? "" : sep + "access_token=" + encodeURIComponent(prop("IG_TOKEN")));
  const json = JSON.parse(UrlFetchApp.fetch(url, opts).getContentText() || "{}");
  if (json.error) throw new Error(json.error.message || "Instagram API エラー");
  return json;
}

/* 2枚組（カルーセル）で投稿し、投稿の URL を返す */
function igPublish(p) {
  for (const url of p.images) {
    if (UrlFetchApp.fetch(url, { muteHttpExceptions: true }).getResponseCode() !== 200) throw new Error("IMAGE_MISSING");
  }
  const user = prop("IG_USER_ID");
  const children = p.images.map((url) => igCall(`/${user}/media`, { image_url: url, is_carousel_item: "true" }).id);
  const container = igCall(`/${user}/media`, { media_type: "CAROUSEL", children: children.join(","), caption: p.caption }).id;
  for (let i = 0; i < 5; i++) {
    const st = igCall(`/${container}?fields=status_code`, null, "get").status_code;
    if (st === "FINISHED") break;
    if (st === "ERROR") throw new Error("画像の読み込みに失敗しました");
    Utilities.sleep(2000);
  }
  const media = igCall(`/${user}/media_publish`, { creation_id: container }).id;
  try { return igCall(`/${media}?fields=permalink`, null, "get").permalink; } catch (e) { return "https://www.instagram.com/"; }
}

function igAction(action, no) {
  if (!igReady()) return TALK.igOff;
  const cur = igCurrent();
  if (!cur) return TALK.igEmpty;
  if (no && Number(no) !== cur.no) return TALK.igStale;
  if (action === "skip") return TALK.igSkipped;
  if (action === "next") {
    PROPS.setProperty("IG_NEXT", String(Number(prop("IG_NEXT") || 0) + 1));
    return igDraftMessage(TALK.igNext);
  }
  try {
    const url = igPublish(cur);
    PROPS.setProperty("IG_NEXT", String(Number(prop("IG_NEXT") || 0) + 1));
    return TALK.igPosted(url);
  } catch (e) {
    return e.message === "IMAGE_MISSING" ? TALK.igImageMissing : TALK.igPostError(e.message);
  }
}

/* Instagram の長期トークン（60日で切れる）を毎週のばす。トリガーから呼ばれる */
function refreshInstagramToken() {
  if (!prop("IG_TOKEN")) return;
  const res = UrlFetchApp.fetch("https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=" + encodeURIComponent(prop("IG_TOKEN")), { muteHttpExceptions: true });
  const json = JSON.parse(res.getContentText() || "{}");
  if (json.access_token) PROPS.setProperty("IG_TOKEN", json.access_token);
  else console.warn("Instagram のトークンを更新できませんでした: " + res.getContentText());
}

/* ---------- お問い合わせ（フォームの回答シート） ---------- */
function responseSheet() {
  const sheets = SpreadsheetApp.getActive().getSheets();
  return sheets.find((s) => s.getRange(1, 1).getValue() === "タイムスタンプ") || sheets[0];
}

/* 「対応済み」の列がなければ、いちばん右に作る */
function doneColumn(sheet) {
  const head = sheet.getRange(1, 1, 1, Math.max(1, sheet.getLastColumn())).getValues()[0];
  let col = head.indexOf("対応済み") + 1;
  if (!col) {
    col = head.length + 1;
    sheet.getRange(1, col).setValue("対応済み");
  }
  return col;
}

/* 見出しの一部の文字から列を探す（例: 「種類」→「お問い合わせの種類」） */
function fieldOf(head, row, word) {
  const i = head.findIndex((h) => String(h).indexOf(word) >= 0);
  return i >= 0 ? String(row[i] || "").trim() : "";
}

function inquiryText(head, row) {
  const body = fieldOf(head, row, "内容");
  return [
    "種類: " + (fieldOf(head, row, "種類") || "（なし）"),
    "対象: " + (fieldOf(head, row, "対象") || "（なし）"),
    "内容: " + (body.length > 300 ? body.slice(0, 300) + "…" : body),
    "返信先: " + (fieldOf(head, row, "メール") ? "メールアドレスあり（スプレッドシートで確認）" : "なし"),
  ].join("\n");
}

/* 未対応のお問い合わせ: [{ no: 番号, head, row }] 番号はシートの行番号 − 1 */
function openInquiries() {
  const sheet = responseSheet();
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const col = doneColumn(sheet);
  const values = sheet.getRange(1, 1, last, Math.max(col, sheet.getLastColumn())).getValues();
  const head = values[0];
  const out = [];
  for (let r = 1; r < values.length; r++) {
    if (values[r][0] && !values[r][col - 1]) out.push({ no: r, head, row: values[r] });
  }
  return out;
}

/* フォームに投稿があったとき（トリガーから呼ばれる） */
function onFormSubmit(e) {
  if (!prop("OWNER_USER_ID")) return;
  const sheet = responseSheet();
  const head = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const rowNo = e && e.range ? e.range.getRow() : sheet.getLastRow();
  const row = sheet.getRange(rowNo, 1, 1, head.length).getValues()[0];
  const no = rowNo - 1;
  push([TALK.newInquiry(no), "", inquiryText(head, row), "", TALK.newInquiryFoot(no)].join("\n"));
}

function listText() {
  const items = openInquiries();
  if (!items.length) return TALK.inquiryNone;
  const shown = items.slice(-10);
  return [TALK.listHead(items.length), ""]
    .concat(shown.map((it) => `■ ${it.no}番（${fmt(new Date(it.row[0]), "M/d")}）\n${inquiryText(it.head, it.row)}`).join("\n\n"))
    .concat(["", TALK.listFoot]).join("\n");
}

function markDone(no) {
  const sheet = responseSheet();
  const rowNo = no + 1;
  if (no < 1 || rowNo > sheet.getLastRow() || !sheet.getRange(rowNo, 1).getValue()) return TALK.doneMissing(no);
  const cell = sheet.getRange(rowNo, doneColumn(sheet));
  if (cell.getValue()) return TALK.doneAlready(no);
  cell.setValue(fmt(new Date(), "yyyy/MM/dd HH:mm"));
  return TALK.done(no);
}

/* ---------- LINE から届いたメッセージ（Webhook） ---------- */
function doPost(e) {
  if (!e || !e.parameter || e.parameter.key !== prop("WEBHOOK_KEY")) return ok();
  const body = JSON.parse((e.postData && e.postData.contents) || "{}");
  (body.events || []).forEach((ev) => {
    try { handleEvent(ev); } catch (err) { console.error(err); }
  });
  return ok();
}

function ok() {
  return ContentService.createTextOutput("OK");
}

function handleEvent(ev) {
  const user = ev.source && ev.source.userId;
  const owner = prop("OWNER_USER_ID");
  if (ev.type === "follow") return reply(ev.replyToken, owner && owner !== user ? TALK.notOwner : TALK.greeting);
  if (ev.type === "postback") {
    if (!owner || user !== owner) return reply(ev.replyToken, TALK.notOwner);
    const data = {};
    ev.postback.data.split("&").forEach((kv) => { const [k, v] = kv.split("="); data[k] = v; });
    if (data.ig) return reply(ev.replyToken, igAction(data.ig, data.no));
    return;
  }
  if (ev.type !== "message" || ev.message.type !== "text") return;
  const text = ev.message.text.normalize("NFKC").trim();
  if (!owner) {
    const m = text.match(/^登録\s*(\d+)$/);
    if (m && m[1] === prop("SETUP_CODE")) {
      PROPS.setProperty("OWNER_USER_ID", user);
      return reply(ev.replyToken, TALK.registered + TALK.help);
    }
    return reply(ev.replyToken, TALK.needRegister);
  }
  if (user !== owner) return reply(ev.replyToken, TALK.notOwner);
  reply(ev.replyToken, answer(text));
}

/* 文字列か、LINE のメッセージの形（クイックリプライ付きなど）を返す */
function answer(text) {
  let m;
  if (/^(状況|じょうきょう|レポート|様子)/.test(text)) return buildReport(false);
  if (/^(グラフ|ぐらふ|アクセス|閲覧者)/.test(text)) return chartReply();
  if (/^(人気|ランキング|にんき)/.test(text)) return rankingText();
  if (/^(問い合わせ|問合せ|といあわせ|お問い合わせ)/.test(text)) return listText();
  if ((m = text.match(/^(済|対応済み?|done)\s*(\d+)/i))) return markDone(Number(m[2]));
  if ((m = text.match(/^ニュース\s*(.*)$/))) {
    const g = m[1].trim();
    return g ? newsText([g], 5, TALK.newsGenreHead(g)) : newsText(selectedGenres(), 3, TALK.newsHead);
  }
  if ((m = text.match(/^ジャンル\s*(.*)$/))) {
    return m[1].trim() ? changeGenres(m[1].trim()) : TALK.genreList(selectedGenres(), Object.keys(NEWS_GENRES));
  }
  if (/^(インスタ|instagram|下書き)/i.test(text)) return igReady() ? igDraftMessage() : TALK.igOff;
  if (/^投稿(する)?$/.test(text)) return igAction("post");
  if (/^(使い方|つかいかた|ヘルプ|help|\?)/i.test(text)) return TALK.help;
  return pick(TALK.unknown);
}

/* ---------- LINE へ送る ---------- */
function lineApi(path, payload) {
  const res = UrlFetchApp.fetch("https://api.line.me/v2/bot/message/" + path, {
    method: "post", contentType: "application/json", muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + prop("LINE_TOKEN") },
    payload: JSON.stringify(payload),
  });
  if (res.getResponseCode() !== 200) console.error("LINE " + path + ": " + res.getResponseCode() + " " + res.getContentText());
}

/* 文字列・メッセージ・その配列を、LINE のメッセージの配列（最大5つ）にそろえる */
function toMessages(x) {
  return [].concat(x).slice(0, 5).map((m) => {
    const msg = typeof m === "string" ? { type: "text", text: m } : m;
    if (msg.text && msg.text.length > 4900) msg.text = msg.text.slice(0, 4900) + "…";
    return msg;
  });
}

/* 返信（無料・送信数に数えられない） */
function reply(token, x) {
  if (token) lineApi("reply", { replyToken: token, messages: toMessages(x) });
}

/* こちらから送る（無料プランでは月200通まで。1回の送信で吹き出し5つまでを1通として数える） */
function push(x) {
  const to = prop("OWNER_USER_ID");
  if (to) lineApi("push", { to, messages: toMessages(x) });
}
