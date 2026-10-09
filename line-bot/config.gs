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
 *
 * ファイルの分け方（Apps Script のエディタでも同じ名前で作る）:
 *   config.gs     サイトの設定・投稿の種類・ニュースのジャンル・共通の小さな関数・setup
 *   talk.gs       話し方の設定（先輩エンジニア）
 *   report.gs     毎朝のレポート・アクセス解析・Search Console・サイトの状態
 *   news.gs       ITニュース
 *   instagram.gs  Instagram の下書き・投稿・コメント・反応
 *   inquiry.gs    お問い合わせ（フォームの回答シート）
 *   line.gs       LINE から届いたメッセージ（Webhook）と、LINE へ送る処理
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
  // 曜日ごとの投稿の種類（日・月・火・水・木・金・土）。term=用語クイズ、trace=トレースクイズ、reel=リール動画、news=今週のITニュース
  rotation: ["reel", "term", "term", "trace", "term", "reel", "news"],
  newsCandidates: 8,                                      // 今週のITニュース: LINE に出す候補の数
  newsPostCount: 3,                                       // 今週のITニュース: 1回の投稿に載せるニュースの数（3まで）
  scheduleHour: 20,                                       // 「〇時に投稿」ボタンで投稿する時刻
};

/* ========== Instagram の投稿の種類 ==========
 * file はサイトに置いた投稿のストック。make_ig_images.py / make_b_media.py が作る */
const IG_KINDS = {
  term: { file: "ig/posts.json", next: "IG_NEXT", label: "用語クイズ", maker: "make_ig_images.py" },
  trace: { file: "ig/trace-posts.json", next: "IG_NEXT_TRACE", label: "トレースクイズ", maker: "make_b_media.py" },
  reel: { file: "ig/reels.json", next: "IG_NEXT_REEL", label: "リール動画", maker: "make_b_media.py" },
  // ストックではなく、その週に運営者が LINE で選ぶ（news.gs）。画像は GitHub の自動実行が作る
  news: { file: null, next: "IG_NEWS_DONE", label: "今週のITニュース", maker: "" },
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
PIN_COMMENTS.news = [
  "📌 ニュースに出てきた用語の意味は、無料の学習サイト「FE用語ドリル」で確かめられます",
  "・基本情報の用語345語を、カード・4択・書いて答えるで",
  "・用語ごとの解説ページつき",
  "登録なし・スマホでそのまま使えます",
  "▶ プロフィールのリンクから",
].join("\n");
// 最初の紹介リール（LINE の「紹介リール」）用
PIN_COMMENTS.intro = [
  "📌 サイトはプロフィールのリンクから開けます",
  "・科目A：用語345語（カード・4択・書いて答える・意味から答える）",
  "・科目B：プログラムを1行ずつ再生するトレース練習",
  "無料・登録なし・スマホでそのまま使えます",
  "「この用語を取り上げてほしい」などのリクエストも、コメントでどうぞ",
].join("\n");

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

/* 今週のITニュースの投稿文で、試験の用語が見つからなかったニュースに付けるひとこと（ジャンルごと） */
const NEWS_NOTES = {
  "AI": "機械学習など、AI の用語を思い出しながら読んでみよう。",
  "セキュリティ": "攻撃の手口と対策は、試験のセキュリティの知識で読み解ける。",
  "クラウド": "クラウドの仕組み（IaaS・PaaS・SaaS）とあわせて押さえよう。",
  "プログラミング": "開発の進め方や手法の話は、マネジメント系の用語にもつながる。",
  "IT資格": "資格や試験の動きは、受験の計画を立てるときの参考に。",
  "": "IT の今の動きとして押さえておきたいニュース。",
};

/* ========== ここから下は、ふだん変えなくてよい部分 ========== */

const PROPS = PropertiesService.getScriptProperties();
const prop = (k) => PROPS.getProperty(k) || "";
const pick = (a) => (Array.isArray(a) ? a[Math.floor(Math.random() * a.length)] : a);
const fmt = (d, f) => Utilities.formatDate(d, "Asia/Tokyo", f);
const jsonProp = (k, d) => { try { return JSON.parse(prop(k)) || d; } catch (e) { return d; } };

/* いくつかの URL を、まとめて同時に取りに行く（1つずつ順番より速い）。reqs は { url, method, ... } の配列 */
function fetchAll(reqs) {
  return reqs.length ? UrlFetchApp.fetchAll(reqs.map((r) => Object.assign({ muteHttpExceptions: true }, r))) : [];
}

/* fetchAll の名前付き版: { 名前: リクエスト } → { 名前: 返事 }。うまくいかなければ空（それぞれが自分で取り直す） */
function fetchNamed(reqs) {
  const keys = Object.keys(reqs);
  const out = {};
  try { fetchAll(keys.map((k) => reqs[k])).forEach((res, i) => { out[keys[i]] = res; }); } catch (e) { console.warn(e); }
  return out;
}

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
