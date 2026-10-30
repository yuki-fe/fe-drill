/**
 * FE用語ドリル 運用LINE（キャラクター: 先輩エンジニア）
 *
 * お問い合わせフォームの回答スプレッドシートに付ける Google Apps Script。
 * - フォームに投稿があったら LINE に知らせる
 * - 毎朝、公開中の用語サイトごとの閲覧者・検索の数字・サイトの状態・最後の更新と、未対応のお問い合わせ・ITニュース・
 *   Instagram の投稿の下書きを、1通にまとめて送る（月曜は先週の閲覧者のグラフも付ける）
 * - 試験の主催者などのページが変わったら朝のレポートで知らせ、Google カレンダーに「見直す」予定と試験の予定・月に1回の用語の確認を入れる
 * - LINE で「グラフ」「人気」「問い合わせ」「済 3」「コメント」「反応」「点検」「試験」「使い方」などと送ると返事をする
 * - Instagram には投稿しない。曜日ごとに「用語クイズ」「トレースクイズ」「リール動画」の下書きを送り、
 *   「素材を受け取る」でもらった画像・動画を運営者がアプリから投稿する。
 *   リール動画は「投稿した」を押すと YouTube ショート用のタイトルと説明も届ける
 *
 * 合言葉（LINE や Instagram のトークンなど）はコードに書かず、「スクリプト プロパティ」に保存する。
 * 手順は「LINE運用ボットの作り方.pdf」「ニュースとInstagramの設定.pdf」「アクセス解析とグラフの設定.pdf」を参照。
 *
 * ファイルの分け方（Apps Script のエディタでも同じ名前で作る）:
 *   config.gs     サイトの設定・投稿の種類・ニュースのジャンル・共通の小さな関数・setup
 *   talk.gs       話し方の設定（先輩エンジニア）
 *   report.gs     毎朝のレポート・アクセス解析・Search Console・サイトの状態
 *   news.gs       ITニュース（毎朝のレポートに載せる）
 *   instagram.gs  Instagram の下書き・素材・コメント・反応
 *   youtube.gs    YouTube の数字とコメント（読むだけ）
 *   watch.gs      試験の変更の見張りの結果・試験の予定・Google カレンダー
 *   inquiry.gs    お問い合わせ（フォームの回答シート）
 *   line.gs       LINE から届いたメッセージ（Webhook）と、LINE へ送る処理
 */

/* ========== サイトの設定（公開されても困らない値） ========== */
const CONFIG = {
  siteName: "FE用語ドリル",
  siteUrl: "https://fe.yogo-drill.com/",        // サイトのURL（Instagram の投稿のストックを置いている）
  reportHour: 8,                                          // 毎朝のレポートを送る時刻（0〜23時）
  chartWeekday: 1,                                        // 先週のグラフを送る曜日（0=日曜, 1=月曜, … 6=土曜）
  newsPerGenre: 2,                                        // 毎朝のレポートに載せる、ジャンルごとのニュースの数
  // Instagram API（バージョンは Meta の案内に合わせて変える）
  //   Facebook ログインで作った合言葉（Facebook ページのトークン）: https://graph.facebook.com/v23.0
  //   Instagram ログインで作った合言葉:                           https://graph.instagram.com/v23.0
  instagramApi: "https://graph.facebook.com/v23.0",
  // 曜日ごとの投稿の種類（日・月・火・水・木・金・土）。term=用語クイズ、trace=トレースクイズ、reel=リール動画
  rotation: ["reel", "term", "term", "trace", "term", "reel", "term"],
  // サイトの点検（全サイト・毎週月曜の朝に GitHub の自動実行が点検する）の結果。空にすると出さない
  checkUrl: "https://raw.githubusercontent.com/yuki-fe/yogo-drill/check-results/result.json",
  checkStaleDays: 9,                                      // これより古い結果しかないときは「点検が止まっている」と知らせる
  // 試験の変更の見張り（GitHub の自動実行が毎朝、試験の主催者などのページを見る。yogo-drill の check/watch.json）の結果。空にすると出さない
  watchUrl: "https://raw.githubusercontent.com/yuki-fe/yogo-drill/watch-results/watch.json",
  watchStaleDays: 3,                                      // これより古い結果しかないときは、月曜に「見張りが止まっている」と知らせる
  // Google カレンダー: スクリプトの持ち主のアカウントに、この名前のカレンダーを作って予定を入れる。空にすると入れない
  calendarName: "用語ドリルの運用",
  calendarRemindDays: [7, 1],                             // 試験の予定を、何日前の朝9時に知らせるか（カレンダーの通知）
  examNoticeDays: [7, 1, 0],                              // 毎朝のレポートで「あと何日」と知らせる日
  examListDays: 60,                                       // LINE の「試験」で出す、これからの予定の日数
  termReviewDay: 1,                                       // 毎月この日に「用語の確認」の予定（カレンダーと朝のレポート）
};

/* ========== 試験の予定（カレンダーに入れる・朝のレポートで「あと何日」と知らせる） ==========
 * 試験の主催者のページで確かめた日付だけを書く（推測で書かない）。過ぎた予定は残しておいてよい（入れ直さない）。
 *   key: 予定ごとにちがう名前（一度入れたらカレンダーに入れ直さない目印）
 *   site: SITES の key / date・end: "yyyy-MM-dd"（end は何日か続くとき） / note: カレンダーの説明に書くこと */
const EXAM_DATES = [
  { key: "dl-2026-6", site: "dl", date: "2026-11-06", end: "2026-11-07", title: "G検定 2026年 第6回", note: "日程は https://www.jdla.org/certificate/general/ で確かめた（2026-10-30）" },
  { key: "boki-174", site: "boki", date: "2026-11-15", title: "簿記 第174回 統一試験（1〜3級）", note: "日程は https://www.kentei.ne.jp/calendar_2026 で確かめた（2026-10-30）" },
  { key: "dl-2027-onsite-1", site: "dl", date: "2027-01-15", end: "2027-01-17", title: "G検定 会場試験", note: "日程は https://www.jdla.org/certificate/general/ で確かめた（2026-10-30）" },
  { key: "genai-2027-02-apply", site: "genai", date: "2027-01-31", title: "生成AIパスポート 2月試験の申込の締め切り", note: "https://guga.or.jp/generativeaiexam/ の年間スケジュール（2026-10-30）" },
  { key: "genai-2027-02", site: "genai", date: "2027-02-01", end: "2027-02-28", title: "生成AIパスポート 2月試験（2027年試験のシラバス）", note: "新しいシラバスの最初の試験。サイトの用語が新しいシラバスに合っているか、前に見直す" },
  { key: "boki-175", site: "boki", date: "2027-02-28", title: "簿記 第175回 統一試験（2級・3級）", note: "日程は https://www.kentei.ne.jp/calendar_2026 で確かめた（2026-10-30）" },
  { key: "boki-kubun-2027", site: "boki", date: "2027-04-01", title: "簿記 2027年度の出題区分表の試験が始まる", note: "2027年度適用の出題区分表（https://www.kentei.ne.jp/51147）。サイトの用語が合っているか、前に見直す" },
];

/* ========== 毎朝のレポートに出す、公開中の用語サイト ==========
 * サイトを公開したら、ここに足す（入り口の yogo-drill の sites.json で "public" が true のもの。旅行は入れない）。
 *   short: LINE で「グラフ 簿記」のように送るときの名前（ボタンにも出る）
 *   repo:  最後の更新を調べるリポジトリ
 *   ga:    GA4 のプロパティ ID（数字）。空ならアナリティクスの欄は「まだ」と出す。
 *          main のサイト（FE）は、スクリプト プロパティの GA_PROPERTY_ID を使う
 *   search: Search Console に URL プレフィックスで登録してあれば true（検索の数字を出す）
 *   color:  グラフの線の色（sites.json の color） */
const SITES = [
  { key: "fe", name: "FE用語ドリル", short: "FE", url: "https://fe.yogo-drill.com/", repo: "yuki-fe/fe-drill", ga: "", main: true, search: true, color: "#c0435a" },
  { key: "ip", name: "ITパスポート用語ドリル", short: "ITパスポート", url: "https://ip.yogo-drill.com/", repo: "yuki-fe/ip-drill", ga: "558662911", search: true, color: "#2d68a8" },
  { key: "cloud", name: "クラウド用語ドリル", short: "クラウド", url: "https://cloud.yogo-drill.com/", repo: "yuki-fe/cloud-drill", ga: "560673744", search: false, color: "#1a6f7a" },
  { key: "genai", name: "生成AI用語ドリル", short: "生成AI", url: "https://genai.yogo-drill.com/", repo: "yuki-fe/genai-drill", ga: "560644762", search: false, color: "#5a3fb0" },
  { key: "dl", name: "ディープラーニング用語ドリル", short: "ディープラーニング", url: "https://dl.yogo-drill.com/", repo: "yuki-fe/dl-drill", ga: "560689908", search: false, color: "#9b2f7a" },
  { key: "boki", name: "簿記用語ドリル", short: "簿記", url: "https://boki.yogo-drill.com/", repo: "yuki-fe/boki-drill", ga: "560565665", search: false, color: "#7a6a12" },
  { key: "iryo", name: "医療事務用語ドリル", short: "医療事務", url: "https://iryo.yogo-drill.com/", repo: "yuki-fe/iryo-drill", ga: "560599396", search: false, color: "#0b6e99" },
];

/* ========== Instagram の投稿の種類 ==========
 * file はサイトに置いた投稿のストック。make_ig_images.py / make_b_media.py が作る */
const IG_KINDS = {
  term: { file: "ig/posts.json", next: "IG_NEXT", label: "用語クイズ", maker: "make_ig_images.py" },
  trace: { file: "ig/trace-posts.json", next: "IG_NEXT_TRACE", label: "トレースクイズ", maker: "make_b_media.py" },
  reel: { file: "ig/reels.json", next: "IG_NEXT_REEL", label: "リール動画", maker: "make_b_media.py" },
};

/* ========== 投稿に付ける、サイトの紹介コメント ==========
 * 「素材を受け取る」の最後の吹き出しで送る。LINE の「紹介コメント」では、いちばん新しい投稿に自動で付ける（固定はアプリで手作業）。
 * コメントのリンクは押せないので、プロフィールのリンクへ案内する。 */
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
 * 毎朝のレポートに載せるジャンルは、スクリプト プロパティ NEWS_GENRES（["AI", "セキュリティ"] の形）。
 * ここにない言葉も、そのまま検索の言葉として入れられる。 */
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
  doneColumn(responseSheet());
  Logger.log("準備ができました。");
  Logger.log("Webhook の URL の最後に付ける文字: ?key=" + prop("WEBHOOK_KEY"));
  Logger.log("LINE で送る登録の言葉: 登録 " + prop("SETUP_CODE"));
  Logger.log("Instagram: " + (igReady() ? "つながっています" : "まだ設定されていません（IG_TOKEN と IG_USER_ID）"));
  Logger.log("Instagram のプロフィールに入れるリンク: " + igProfileLink());
  Logger.log("アナリティクス: " + (gaReady() ? "プロパティ " + prop("GA_PROPERTY_ID") : "まだ設定されていません（GA_PROPERTY_ID）"));
  if (!ytReady()) {
    try { Logger.log("YouTube: チャンネル「" + ytFindChannel() + "」を見つけました"); }
    catch (e) { Logger.log("YouTube: まだ設定されていません（" + e.message + "）。チャンネルが別のアカウントなら YT_CHANNEL_ID を入れてください"); }
  } else Logger.log("YouTube: チャンネル " + prop("YT_CHANNEL_ID"));
  if (calendarReady()) {
    try { Logger.log("カレンダー: 「" + CONFIG.calendarName + "」に " + calendarSync(null) + " 件入れました"); }
    catch (e) { Logger.log("カレンダー: 入れられませんでした（" + e.message + "）"); }
  }
}
