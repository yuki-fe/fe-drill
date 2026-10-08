/**
 * FE用語ドリル 運用LINE（キャラクター: 先輩エンジニア）
 *
 * お問い合わせフォームの回答スプレッドシートに付ける Google Apps Script。
 * - フォームに投稿があったら LINE に知らせる
 * - 毎朝、閲覧者の数・検索の数字・サイトの状態・最後の更新・未対応のお問い合わせ・ITニュース・
 *   Instagram の投稿の下書きを、1通にまとめて送る（月曜は先週の閲覧者のグラフも付ける）
 * - LINE で「状況」「グラフ」「人気」「問い合わせ」「済 3」「ニュース」「ジャンル」「インスタ」「使い方」と送ると返事をする
 * - Instagram は、LINE の「今すぐ投稿」「20時に投稿」ボタンを押したときだけ投稿する。
 *   曜日ごとに「用語クイズ」「トレースクイズ」「リール動画」の下書きを切り替え、
 *   リール動画は YouTube ショート用のタイトルと説明も届ける
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
  // Instagram API（バージョンは Meta の案内に合わせて変える）
  //   Facebook ログインで作った合言葉（Facebook ページのトークン）: https://graph.facebook.com/v23.0
  //   Instagram ログインで作った合言葉:                           https://graph.instagram.com/v23.0
  instagramApi: "https://graph.facebook.com/v23.0",
  // 曜日ごとの投稿の種類（日・月・火・水・木・金・土）。term=用語クイズ、trace=トレースクイズ、reel=リール動画
  rotation: ["reel", "term", "term", "trace", "term", "reel", "term"],
  scheduleHour: 20,                                       // 「〇時に投稿」ボタンで投稿する時刻
};

/* ========== Instagram の投稿の種類 ==========
 * file はサイトに置いた投稿のストック。make_ig_images.py / make_b_media.py が作る */
const IG_KINDS = {
  term: { file: "ig/posts.json", next: "IG_NEXT", label: "用語クイズ", maker: "make_ig_images.py" },
  trace: { file: "ig/trace-posts.json", next: "IG_NEXT_TRACE", label: "トレースクイズ", maker: "make_b_media.py" },
  reel: { file: "ig/reels.json", next: "IG_NEXT_REEL", label: "リール動画", maker: "make_b_media.py" },
};

/* ========== 投稿に付ける、サイトの紹介コメント ==========
 * 投稿した直後に、自分のアカウントからコメントする（固定はアプリで手作業）。
 * コメントのリンクは押せないので、プロフィールのリンクへ案内する。空にすると付けない。 */
const PIN_COMMENTS = {
  term: [
    "📌 この問題は、無料の学習サイト「FE用語ドリル」から出しています",
    "・基本情報の用語345語を、4択・書いて答える・意味から答えるの3通りで",
    "・間違えた用語だけ集めて、まとめて復習",
    "・科目Bは、プログラムが1行ずつ動いて変数の変化が見える「トレース練習」つき",
    "登録なし・スマホでそのまま使えます",
    "▶ プロフィールのリンクから",
  ].join("\n"),
  trace: [
    "📌 科目Bのトレースは、無料の学習サイト「FE用語ドリル」で練習できます",
    "・プログラムが1行ずつ動いて、変数がどう変わるかを目で追える",
    "・穴埋め問題は、選んだ答えでプログラムを動かして「なぜ違うか」まで確かめられる",
    "・自分で書いた擬似言語をそのまま動かせるシミュレータつき",
    "・基本情報の用語345語の単語帳も",
    "登録なし・スマホでそのまま使えます",
    "▶ プロフィールのリンクから",
  ].join("\n"),
};
PIN_COMMENTS.reel = PIN_COMMENTS.trace;

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

  igHead: (label, title) => `今日のインスタの下書きだよ（${label}「${title}」）。中身を確認してね。`,
  igPosted: (url, commented) => `インスタに投稿したよ！\n${url}\n` +
    (commented ? "サイトの紹介コメントも付けといた。アプリでそのコメントを長押し→「固定」してね（固定はアプリでしかできないんだ）。" : "コメントが来てたら返してあげてね。"),
  igPinDone: (url) => `いちばん新しい投稿に、サイトの紹介コメントを付けたよ。\n${url}\nアプリでそのコメントを長押し→「固定」してね。`,
  igPinError: (why) => `紹介コメントを付けられなかった…（${why}）。`,
  igPostError: (why) => `投稿できなかった…（${why}）。「ニュースとInstagramの設定」の「困ったとき」を見てみて。`,
  igImageMissing: "画像がまだ公開されてないみたい。make_ig_images.py を実行して、GitHub に Push した？",
  igSkipped: "了解、今日はお休みね。",
  igNext: "別のにしたよ。",
  igEmpty: (label, maker) => `${label}のストックがなくなったよ。${maker} の数を増やして実行して、GitHub に Push してね。`,
  igKindChanged: (label) => `${label}に変えたよ。`,
  igScheduled: (when, title) => `了解、${when}に「${title}」を投稿するね。終わったら知らせるよ。`,
  igReelProcessing: "動画をインスタに送ったよ。処理に数分かかるから、終わったら知らせるね。",
  igBusy: "前の動画をまだ処理中だよ。終わったら知らせるから、そのあとでもう一度押してね。",
  ytKitHead: (url) => `YouTube ショートにも出そう。\n\n① 動画を保存する: ${url}\n（パソコンなら、サイトのフォルダの static/ig/reels/ に同じ名前のファイルがあるよ）\n② YouTube アプリの「＋」→「ショート」→ 保存した動画を選ぶ\n③ 次の2つの吹き出し（タイトルと説明）を、それぞれ長押しでコピーして貼ってね`,
  ytNone: "YouTube に出せるリール動画がまだないよ。",
  igCommentsNew: (n) => `新しいコメント ${n} 件:`,
  igCommentLine: (user, label, text) => `・@${user}（${label}）「${text}」`,
  igCommentsHead: "最近のコメントだよ（新しい順）。返してあげてね。",
  igCommentsNone: "この1週間、コメントはないみたい。",
  igCommentsError: "コメントは取れなかった。トークンにコメントの権限があるか確かめてみて。",
  igOff: "インスタはまだつながってないよ。設定の手順書を見てね。",
  igStale: "それは前の下書きのボタンだよ。今の下書きは「インスタ」って送ると出せるよ。",

  visitorsIg: (y, w, d) => `うちインスタから: 昨日 ${y} 人／直近7日 ${w} 人（その前の7日より ${d >= 0 ? "+" : ""}${d} 人）`,
  igStatsPost: (date, label, s) => `最新の投稿（${date}「${label}」）: リーチ ${s.reach}、いいね ${s.likes}、保存 ${s.saved}、コメント ${s.comments}`,
  igFollowers: (n, d) => `フォロワー ${n} 人` + (d === null ? "" : `（前の記録より ${d >= 0 ? "+" : ""}${d}）`),
  igSavedHigh: "保存がいつもの1.5倍以上。この形式、刺さってるね。",
  igSavedLow: "保存はいつもより少なめ。テーマや画像の見せ方を変えてみてもいいかも。",
  igNoPost: "まだ投稿がないみたい。",
  igStatsError: "インスタの数字は取れなかった。トークンに「インサイト」の権限があるか確かめてみて（「リール動画とYouTube・反応の設定」参照）。",
  igRecentHead: "最近の投稿の反応だよ（新しい順）。",
  igLink: (url) => `プロフィールのリンクには、これを入れてね。インスタから来た人を数えられるよ。\n${url}`,

  help: [
    "使えることばはこれだよ。",
    "・状況 … 閲覧者・検索の数字やサイトの様子",
    "・グラフ … 直近7日の閲覧者のグラフ",
    "・人気 … 直近7日でよく見られたページ",
    "・問い合わせ … 未対応のお問い合わせの一覧",
    "・済 3 … 3番のお問い合わせを対応済みにする",
    "・ニュース … 今のジャンルの最新ITニュース（「ニュース AI」で1ジャンルだけ）",
    "・ジャンル … ニュースのジャンルを見る・変える",
    "・インスタ … 今日の Instagram の下書き（「インスタ リール」「インスタ トレース」「インスタ 用語」で種類を選べる）",
    "・コメント … 最近の Instagram のコメント",
    "・紹介コメント … いちばん新しい投稿に、サイトの紹介コメントを付ける",
    "・ユーチューブ … 最近のリール動画を YouTube ショートに出すためのタイトルと説明",
    "・反応 … 最近の Instagram の投稿のリーチ・保存",
    "・リンク … プロフィールに入れる目印付きのURL",
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
  ScriptApp.newTrigger("igWorker").timeBased().everyMinutes(10).create();
  doneColumn(responseSheet());
  Logger.log("準備ができました。");
  Logger.log("Webhook の URL の最後に付ける文字: ?key=" + prop("WEBHOOK_KEY"));
  Logger.log("LINE で送る登録の言葉: 登録 " + prop("SETUP_CODE"));
  Logger.log("Instagram: " + (igReady() ? "つながっています" : "まだ設定されていません（IG_TOKEN と IG_USER_ID）"));
  Logger.log("Instagram のプロフィールに入れるリンク: " + igProfileLink());
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
    if (st) { msgs[0].text += "\n\n" + TALK.chartWeekly; msgs.push(chartMessage(st)); }
  }
  msgs.push({ type: "text", text: newsText(selectedGenres(), CONFIG.newsPerGenre, TALK.newsHead) });
  if (igReady()) [].concat(igDraftMessage()).forEach((m) => msgs.push(m));
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
      const ig = igVisitorStats();
      if (ig) lines.push(TALK.visitorsIg(ig.yesterday, ig.week, ig.week - ig.prevWeek));
      lines.push(st.week > st.prevWeek ? TALK.visitorsUp : st.week < st.prevWeek ? TALK.visitorsDown : TALK.visitorsSame);
    }
    lines.push("");
  }
  if (igReady()) {
    lines.push("【インスタ】", igStatsText());
    const c = igNewCommentsText(morning);
    if (c) lines.push(c);
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

/* 今日の投稿の種類（「インスタ リール」などで変えたら、その日はそれを使う） */
function kindToday() {
  const o = jsonProp("IG_KIND_TODAY", null);
  if (o && o.date === fmt(new Date(), "yyyy-MM-dd") && IG_KINDS[o.kind]) return o.kind;
  return CONFIG.rotation[new Date(fmt(new Date(), "yyyy/MM/dd")).getDay()] || "term";
}

function setKindToday(kind) {
  PROPS.setProperty("IG_KIND_TODAY", JSON.stringify({ date: fmt(new Date(), "yyyy-MM-dd"), kind }));
}

function kindFromWord(w) {
  if (/用語/.test(w)) return "term";
  if (/トレース|とれーす/.test(w)) return "trace";
  if (/リール|動画|りーる/i.test(w)) return "reel";
  return null;
}

/* サイトに置いた投稿のストック */
function igPosts(kind) {
  const res = UrlFetchApp.fetch(CONFIG.siteUrl + IG_KINDS[kind].file, { muteHttpExceptions: true });
  return res.getResponseCode() === 200 ? JSON.parse(res.getContentText()) : [];
}

function igCurrent(kind) {
  return igPosts(kind)[Number(prop(IG_KINDS[kind].next) || 0)] || null;
}

function igAdvance(kind) {
  const k = IG_KINDS[kind].next;
  PROPS.setProperty(k, String(Number(prop(k) || 0) + 1));
}

const postId = (p, kind) => (kind === "reel" ? p.key : String(p.no));
const postTitle = (p) => p.term || p.title;

function igDraftMessage(prefix, kind) {
  kind = kind || kindToday();
  const K = IG_KINDS[kind];
  const p = igCurrent(kind);
  if (!p) return { type: "text", text: TALK.igEmpty(K.label, K.maker) };
  const preview = p.caption.length > 600 ? p.caption.slice(0, 600) + "…" : p.caption;
  const media = kind === "reel" ? ["動画: " + p.video, `長さ: ${Math.round(p.seconds)} 秒`] : ["1枚目: " + p.images[0], "2枚目: " + p.images[1]];
  const d = `k=${kind}&id=${postId(p, kind)}`;
  const text = {
    type: "text",
    text: [prefix, TALK.igHead(K.label, postTitle(p)), ""].concat(media, ["", "―― 投稿文 ――", preview]).filter((x) => x !== undefined).join("\n"),
    quickReply: { items: [
      qr("今すぐ投稿", "ig=post&" + d),
      qr(`${CONFIG.scheduleHour}時に投稿`, "ig=sched&" + d),
      qr("別のにする", "ig=next&" + d),
      qr("種類を変える", "ig=kind&" + d),
      qr("今日はやめる", "ig=skip&" + d),
    ] },
  };
  // クイックリプライは最後の吹き出しに付ける必要があるので、動画は先に置く
  return kind === "reel" ? [{ type: "video", originalContentUrl: p.video, previewImageUrl: p.cover }, text] : text;
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
function igPublish(p, kind) {
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
  rememberPost(media, p.term);
  const commented = igPinComment(media, kind);
  let url = "https://www.instagram.com/";
  try { url = igCall(`/${media}?fields=permalink`, null, "get").permalink; } catch (e) { /* URL が取れなくても投稿はできている */ }
  return { url, commented };
}

/* サイトの紹介コメントを付ける。付けられたら true */
function igPinComment(mediaId, kind) {
  const text = PIN_COMMENTS[kind];
  if (!text) return false;
  try {
    igCall(`/${mediaId}/comments`, { message: text });
    return true;
  } catch (e) {
    console.warn("紹介コメント: " + e.message);
    return false;
  }
}

/* LINE で「紹介コメント」: いちばん新しい投稿に付ける（前に投稿したものや、アプリで投稿したもの用） */
function igPinLatest() {
  try {
    const m = (igCall(`/${prop("IG_USER_ID")}/media?fields=id,media_type,permalink&limit=1`, null, "get").data || [])[0];
    if (!m) return TALK.igNoPost;
    const kind = m.media_type === "VIDEO" ? "reel" : "term";
    igCall(`/${m.id}/comments`, { message: PIN_COMMENTS[kind] });
    return TALK.igPinDone(m.permalink || "https://www.instagram.com/");
  } catch (e) {
    return TALK.igPinError(e.message);
  }
}

/* 「〇時に投稿」の時刻。もう過ぎていたら次の日 */
function scheduledTime() {
  const t = new Date(fmt(new Date(), "yyyy/MM/dd") + " " + CONFIG.scheduleHour + ":00:00");
  if (t.getTime() <= Date.now()) t.setDate(t.getDate() + 1);
  return t;
}

function igAction(action, kind, id) {
  if (!igReady()) return TALK.igOff;
  kind = IG_KINDS[kind] ? kind : "term";
  const K = IG_KINDS[kind];
  const cur = igCurrent(kind);
  if (!cur) return TALK.igEmpty(K.label, K.maker);
  if (id && id !== postId(cur, kind)) return TALK.igStale;
  if (action === "skip") return TALK.igSkipped;
  if (action === "next") { igAdvance(kind); return igDraftMessage(TALK.igNext, kind); }
  if (action === "kind") {
    const order = Object.keys(IG_KINDS);
    const nk = order[(order.indexOf(kind) + 1) % order.length];
    setKindToday(nk);
    return igDraftMessage(TALK.igKindChanged(IG_KINDS[nk].label), nk);
  }
  if (prop("IG_PENDING")) return TALK.igBusy;
  if (action === "sched") {
    const t = scheduledTime();
    PROPS.setProperty("IG_SCHEDULE", JSON.stringify({ kind, id: postId(cur, kind), at: t.getTime() }));
    const when = (fmt(t, "yyyy-MM-dd") === fmt(new Date(), "yyyy-MM-dd") ? "今日の" : "明日の") + CONFIG.scheduleHour + "時";
    return TALK.igScheduled(when, postTitle(cur));
  }
  return igPublishNow(kind, cur);
}

/* すぐ投稿する。画像はその場で投稿し、動画は Instagram に送って、処理が終わるのを igWorker で待つ */
function igPublishNow(kind, p) {
  try {
    if (kind === "reel") { igStartReel(p); return TALK.igReelProcessing; }
    const r = igPublish(p, kind);
    igAdvance(kind);
    return TALK.igPosted(r.url, r.commented);
  } catch (e) {
    return e.message === "IMAGE_MISSING" ? TALK.igImageMissing : TALK.igPostError(e.message);
  }
}

function igStartReel(p) {
  if (UrlFetchApp.fetch(p.cover, { muteHttpExceptions: true }).getResponseCode() !== 200) throw new Error("IMAGE_MISSING");
  const c = igCall(`/${prop("IG_USER_ID")}/media`, { media_type: "REELS", video_url: p.video, cover_url: p.cover, caption: p.caption, share_to_feed: "true" }).id;
  PROPS.setProperty("IG_PENDING", JSON.stringify({ container: c, kind: "reel", id: p.key, label: p.title, at: Date.now() }));
}

/* 10分ごとにトリガーから呼ばれる: 処理中の動画の投稿と、予約した投稿 */
function igWorker() {
  if (!igReady() || !prop("OWNER_USER_ID")) return;
  const pend = jsonProp("IG_PENDING", null);
  if (pend) {
    let st;
    try { st = igCall(`/${pend.container}?fields=status_code`, null, "get").status_code; } catch (e) { st = "ERROR"; }
    if (st === "FINISHED") {
      PROPS.deleteProperty("IG_PENDING");
      try {
        const media = igCall(`/${prop("IG_USER_ID")}/media_publish`, { creation_id: pend.container }).id;
        rememberPost(media, pend.label);
        const commented = igPinComment(media, pend.kind);
        let url = "https://www.instagram.com/";
        try { url = igCall(`/${media}?fields=permalink`, null, "get").permalink; } catch (e) { /* URL が取れなくても投稿はできている */ }
        igAdvance(pend.kind);
        PROPS.setProperty("IG_LAST_REEL", pend.id);
        const p = igPosts("reel").find((x) => x.key === pend.id);
        push([TALK.igPosted(url, commented)].concat(p ? ytKitMessages(p) : []));
      } catch (e) {
        push(TALK.igPostError(e.message));
      }
    } else if (st === "ERROR" || st === "EXPIRED" || Date.now() - pend.at > 60 * 60 * 1000) {
      PROPS.deleteProperty("IG_PENDING");
      push(TALK.igPostError("動画の処理がうまくいかなかった（" + st + "）"));
    }
    return;
  }
  const sch = jsonProp("IG_SCHEDULE", null);
  if (sch && Date.now() >= sch.at) {
    PROPS.deleteProperty("IG_SCHEDULE");
    const cur = igCurrent(sch.kind);
    if (!cur || postId(cur, sch.kind) !== sch.id) return;
    const r = igPublishNow(sch.kind, cur);
    if (r !== TALK.igReelProcessing) push(r);  // 動画は、処理が終わったときに知らせる
  }
}

/* YouTube ショート用: 説明・タイトル・本文を別々の吹き出しにして、長押しでコピーしやすくする */
function ytKitMessages(p) {
  return [TALK.ytKitHead(p.video), p.youtube.title, p.youtube.description];
}

function ytKitReply() {
  const posts = igPosts("reel");
  const p = posts.find((x) => x.key === prop("IG_LAST_REEL")) || igCurrent("reel") || posts[0];
  return p ? ytKitMessages(p) : TALK.ytNone;
}

/* ---------- Instagram のコメント ---------- */
function igComments(sinceMs) {
  const list = igCall(`/${prop("IG_USER_ID")}/media?fields=id,caption,timestamp&limit=5`, null, "get").data || [];
  const out = [];
  list.forEach((m) => {
    (igCall(`/${m.id}/comments?fields=id,text,username,timestamp&limit=20`, null, "get").data || []).forEach((c) => {
      const t = new Date(c.timestamp).getTime();
      if (t > sinceMs && c.username !== igUsername()) out.push({ user: c.username || "?", text: String(c.text || ""), label: postLabel(m), t });
    });
  });
  return out.sort((a, b) => b.t - a.t);
}

/* 自分のアカウント名（一度取ったら覚えておく）。自分の紹介コメントを「新しいコメント」に数えないため */
function igUsername() {
  let u = prop("IG_USERNAME");
  if (!u) {
    u = igCall(`/${prop("IG_USER_ID")}?fields=username`, null, "get").username || "";
    if (u) PROPS.setProperty("IG_USERNAME", u);
  }
  return u;
}

const clip = (t, n) => (t.length > n ? t.slice(0, n) + "…" : t);

/* 毎朝のレポート用: 前回のレポート以降の新しいコメント（毎朝だけ「見た」記録を進める） */
function igNewCommentsText(update) {
  try {
    const since = Number(prop("IG_COMMENTS_SEEN")) || Date.now() - 86400000;
    const list = igComments(since);
    if (update) PROPS.setProperty("IG_COMMENTS_SEEN", String(Date.now()));
    if (!list.length) return "";
    return [TALK.igCommentsNew(list.length)].concat(list.slice(0, 3).map((c) => TALK.igCommentLine(c.user, c.label, clip(c.text, 40)))).join("\n");
  } catch (e) {
    console.warn("Instagram comments: " + e.message);
    return "";
  }
}

/* LINE で「コメント」: この1週間のコメント */
function igCommentsList() {
  try {
    const list = igComments(Date.now() - 7 * 86400000);
    if (!list.length) return TALK.igCommentsNone;
    return [TALK.igCommentsHead, ""].concat(list.slice(0, 10).map((c) => `${fmt(new Date(c.t), "M/d")} ` + TALK.igCommentLine(c.user, c.label, clip(c.text, 80)).slice(1))).join("\n");
  } catch (e) {
    console.warn(e);
    return TALK.igCommentsError;
  }
}

/* Instagram ログインの長期トークン（60日で切れる）を毎週のばす。トリガーから呼ばれる。
 * Facebook ログインで作った「Facebook ページのトークン」は期限がないので、何もしない */
function refreshInstagramToken() {
  if (!prop("IG_TOKEN") || CONFIG.instagramApi.indexOf("graph.facebook.com") >= 0) return;
  const res = UrlFetchApp.fetch("https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=" + encodeURIComponent(prop("IG_TOKEN")), { muteHttpExceptions: true });
  const json = JSON.parse(res.getContentText() || "{}");
  if (json.access_token) PROPS.setProperty("IG_TOKEN", json.access_token);
  else console.warn("Instagram のトークンを更新できませんでした: " + res.getContentText());
}

/* ---------- Instagram の反応と、Instagram から来た閲覧者 ---------- */

/* プロフィールに入れるリンク。目印（utm）が付いていると、アナリティクスで「instagram から来た」と数えられる */
function igProfileLink() {
  return CONFIG.siteUrl + "?utm_source=instagram&utm_medium=social&utm_campaign=profile";
}

/* Instagram から来た閲覧者（参照元に instagram を含むもの。目印付きリンクと、アプリ内ブラウザの l.instagram.com の両方） */
function igVisitorStats() {
  if (!gaReady()) return null;
  const r = gaReport({
    dateRanges: [{ startDate: "14daysAgo", endDate: "yesterday" }],
    dimensions: [{ name: "date" }],
    metrics: [{ name: "activeUsers" }],
    dimensionFilter: { filter: { fieldName: "sessionSource", stringFilter: { matchType: "CONTAINS", value: "instagram", caseSensitive: false } } },
  });
  if (!r) return null;
  const byDate = {};
  (r.rows || []).forEach((row) => { byDate[row.dimensionValues[0].value] = Number(row.metricValues[0].value); });
  const days = [];
  for (let n = 14; n >= 1; n--) days.push(byDate[fmt(new Date(Date.now() - n * 86400000), "yyyyMMdd")] || 0);
  const sum = (a) => a.reduce((t, x) => t + x, 0);
  return { yesterday: days[13], week: sum(days.slice(7)), prevWeek: sum(days.slice(0, 7)) };
}

/* 投稿した日の記録: { メディアID: 用語 }。投稿の名前を「No.60…」ではなく用語で見せるため */
function rememberPost(mediaId, label) {
  const log = jsonProp("IG_POST_LOG", {});
  log[mediaId] = label;
  const keys = Object.keys(log);
  keys.slice(0, Math.max(0, keys.length - 60)).forEach((k) => delete log[k]);
  PROPS.setProperty("IG_POST_LOG", JSON.stringify(log));
}

function postLabel(m) {
  const known = jsonProp("IG_POST_LOG", {})[m.id];
  if (known) return known;
  const first = String(m.caption || "").split("\n")[0].replace(/[【】]/g, "");
  return first.length > 18 ? first.slice(0, 18) + "…" : first || "（投稿文なし）";
}

/* 1投稿の数字。API のバージョンによって使える指標が違うので、だめなら少ない指標で取り直す */
function igMediaStats(m) {
  const tryMetrics = ["reach,saved,likes,comments,shares", "reach,saved"];
  for (const metrics of tryMetrics) {
    try {
      const data = igCall(`/${m.id}/insights?metric=${metrics}`, null, "get").data || [];
      const v = {};
      data.forEach((x) => { v[x.name] = x.values && x.values[0] ? Number(x.values[0].value) : Number(x.total_value && x.total_value.value) || 0; });
      return {
        reach: v.reach || 0, saved: v.saved || 0,
        likes: v.likes !== undefined ? v.likes : m.like_count || 0,
        comments: v.comments !== undefined ? v.comments : m.comments_count || 0,
      };
    } catch (e) {
      console.warn("Instagram insights: " + e.message);
    }
  }
  return null;
}

/* 最近の投稿（新しい順）と、それぞれの数字 */
function igRecent(count) {
  const list = igCall(`/${prop("IG_USER_ID")}/media?fields=id,caption,timestamp,like_count,comments_count&limit=${count}`, null, "get").data || [];
  return list.map((m) => ({ m, stats: igMediaStats(m) }));
}

/* フォロワー数を1日1回記録して、前の記録との差を出す */
function igFollowers() {
  const n = Number(igCall(`/${prop("IG_USER_ID")}?fields=followers_count`, null, "get").followers_count || 0);
  const log = jsonProp("IG_FOLLOWERS", {});
  const today = fmt(new Date(), "yyyy-MM-dd");
  const before = Object.keys(log).filter((d) => d < today).sort();
  const diff = before.length ? n - log[before[before.length - 1]] : null;
  log[today] = n;
  Object.keys(log).sort().slice(0, -30).forEach((d) => delete log[d]);
  PROPS.setProperty("IG_FOLLOWERS", JSON.stringify(log));
  return { n, diff };
}

/* 毎朝のレポートの【インスタ】の欄 */
function igStatsText() {
  try {
    const lines = [];
    const recent = igRecent(6);
    if (!recent.length) lines.push(TALK.igNoPost);
    else {
      const latest = recent[0];
      if (!latest.stats) return TALK.igStatsError;
      lines.push(TALK.igStatsPost(fmt(new Date(latest.m.timestamp), "M/d"), postLabel(latest.m), latest.stats));
      const others = recent.slice(1).filter((x) => x.stats);
      if (others.length >= 3) {
        const avg = others.reduce((t, x) => t + x.stats.saved, 0) / others.length;
        if (avg > 0 && latest.stats.saved >= avg * 1.5) lines.push(TALK.igSavedHigh);
        else if (avg >= 4 && latest.stats.saved <= avg * 0.5) lines.push(TALK.igSavedLow);
      }
    }
    const f = igFollowers();
    lines.push(TALK.igFollowers(f.n, f.diff));
    return lines.join("\n");
  } catch (e) {
    console.warn(e);
    return TALK.igStatsError;
  }
}

/* LINE で「反応」と送ったとき: 最近5投稿の数字 */
function igRecentText() {
  try {
    const recent = igRecent(5);
    if (!recent.length) return TALK.igNoPost;
    return [TALK.igRecentHead, ""].concat(recent.map((x) => {
      const s = x.stats;
      return `■ ${fmt(new Date(x.m.timestamp), "M/d")}「${postLabel(x.m)}」\n` +
        (s ? `リーチ ${s.reach}／いいね ${s.likes}／保存 ${s.saved}／コメント ${s.comments}` : "数字を取れなかった");
    })).join("\n");
  } catch (e) {
    console.warn(e);
    return TALK.igStatsError;
  }
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
    if (data.ig) return reply(ev.replyToken, igAction(data.ig, data.k || "term", data.id || data.no));
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
  if ((m = text.match(/^(インスタ|instagram|下書き)\s*(.*)$/i))) {
    if (!igReady()) return TALK.igOff;
    const k = kindFromWord(m[2]);
    if (k) setKindToday(k);
    return igDraftMessage(undefined, k || kindToday());
  }
  if (/^投稿(する)?$/.test(text)) return igAction("post", kindToday());
  if (/^紹介コメント/.test(text)) return igReady() ? igPinLatest() : TALK.igOff;
  if (/^(コメント|こめんと)/.test(text)) return igReady() ? igCommentsList() : TALK.igOff;
  if (/^(ユーチューブ|ゆーちゅーぶ|youtube)/i.test(text)) return ytKitReply();
  if (/^(反応|はんのう|インサイト)/.test(text)) return igReady() ? igRecentText() : TALK.igOff;
  if (/^(リンク|りんく)/.test(text)) return TALK.igLink(igProfileLink());
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
