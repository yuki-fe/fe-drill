"""LINE ボットの動作テスト。Google や LINE には接続せず、まねした相手（モック）で動かす。

使い方:  python line-bot/test/run_test.py
         Microsoft Edge（動かないときは Chrome）でテストのページを開き、結果を表示する。最後に「ALL OK」と出れば成功。
         line-bot/ の .gs ファイルを全部読み込む（config.gs・talk.gs があれば先に読む）。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
BOT = HERE.parent
SITE = BOT.parent
# PDF などを作るブラウザ。Edge が動かないとき（自動更新の途中など）は Chrome を使う
BROWSERS = [p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")) if p.exists()]
FIRST = ["config.gs", "talk.gs"]

gs = sorted(BOT.glob("*.gs"), key=lambda p: (FIRST.index(p.name) if p.name in FIRST else len(FIRST), p.name))
code = "\n".join(p.read_text(encoding="utf-8") for p in gs)
stock = {name: json.loads((SITE / "static" / "ig" / name).read_text(encoding="utf-8")) for name in ["posts.json", "trace-posts.json", "reels.json"]}

MOCKS = r"""
const sent = [], igCalls = [];
let insightsDenied = false;
let ytDenied = false, ytHidden = false, ytSubsN = 35;
const ytCalls = [];
let gaDeniedIp = false, downSite = "";   // downSite: 開けないことにするサイトの URL
let checkData = null, checkCode = 200;   // サイトの点検の結果（null のときは、まだ結果がない = 404）
const store = { LINE_TOKEN: "t", WEBHOOK_KEY: "key", OWNER_USER_ID: "U1", IG_TOKEN: "ig", IG_USER_ID: "1789", YT_API_KEY: "ytkey" };
const PropertiesService = { getScriptProperties: () => ({ getProperty: (k) => store[k] ?? null, setProperty: (k, v) => { store[k] = String(v); }, deleteProperty: (k) => { delete store[k]; } }) };
const grid = [["タイムスタンプ", "お問い合わせの種類"]];
const range = (r, c, nr, nc) => ({ getValue: () => (grid[r - 1] || [])[c - 1] ?? "", setValue: (v) => { grid[r - 1][c - 1] = v; }, getValues: () => Array.from({ length: nr || 1 }, (_, i) => Array.from({ length: nc || 1 }, (_, j) => (grid[r - 1 + i] || [])[c - 1 + j] ?? "")) });
const sheet = { getRange: range, getLastRow: () => grid.length, getLastColumn: () => 2 };
const SpreadsheetApp = { getActive: () => ({ getSheets: () => [sheet] }) };
const triggers = [];
const t_chain = new Proxy({}, { get: (t, k) => (k === "create" ? () => 1 : () => t_chain) });
const ScriptApp = { getProjectTriggers: () => [], deleteTrigger: () => {}, newTrigger: (n) => { triggers.push(n); return t_chain; }, getOAuthToken: () => "o", WeekDay: { MONDAY: 1 } };
const Logger = { log: () => {} };
const t_pad = (n) => String(n).padStart(2, "0");
let NOW = new Date("2026-10-09T10:00:00+09:00").getTime();  // 金曜（リールの日）
const RealDate = Date;
Date = class extends RealDate { constructor(...a) { super(...(a.length ? a : [NOW])); } static now() { return NOW; } };
const Utilities = { getUuid: () => "k", sleep: () => {}, formatDate: (d, tz, f) => {
  const y = d.getFullYear(), M = d.getMonth() + 1, D = d.getDate();
  return { "yyyy-MM-dd": `${y}-${t_pad(M)}-${t_pad(D)}`, "yyyy/MM/dd": `${y}/${t_pad(M)}/${t_pad(D)}`, "M/d": `${M}/${D}`, "yyyyMMdd": `${y}${t_pad(M)}${t_pad(D)}` }[f] || d.toISOString();
} };
const ContentService = { createTextOutput: (s) => s };
// Google ニュースの RSS は、テストでは JSON で返して、XmlService の形にくるむ
const XmlService = { getNamespace: () => ({}), parse: (text) => {
  const items = JSON.parse(text);
  return { getRootElement: () => ({ getChild: () => ({ getChildren: () => items.map((it) => ({ getChildText: (k) => it[k] })) }) }) };
} };
const t_resp = (code, body) => ({ getResponseCode: () => code, getContentText: () => body });
let status = "IN_PROGRESS", mediaN = 500;
const UrlFetchApp = { fetch: (url, o) => {
  if (url.includes("api.line.me")) { sent.push(JSON.parse(o.payload)); return t_resp(200, "{}"); }
  if (url.includes("analyticsdata.googleapis.com")) {
    // 閲覧者: 直近14日分。FE（111）は1日 10 人、ITパスポート（558662911）は1日 5 人、インスタから来た人は1日 2 人
    const ip = url.includes("/558662911:");
    if (ip && gaDeniedIp) return t_resp(403, '{"error":{"message":"User does not have sufficient permissions for this property."}}');
    const ig = String(o.payload || "").includes("instagram");
    const rows = [];
    for (let n = 14; n >= 1; n--) {
      const d = new RealDate(NOW - n * 86400e3), ymd = Utilities.formatDate(d, "", "yyyyMMdd");
      const u = ig ? 2 : ip ? 5 : 10;
      rows.push({ dimensionValues: [{ value: ymd }], metricValues: [{ value: String(u) }, { value: String(u * 2) }] });
    }
    return t_resp(200, JSON.stringify({ rows }));
  }
  if (url.includes("googleapis.com/youtube/")) {
    ytCalls.push(url);
    if (ytDenied) return t_resp(403, '{"error":{"code":403,"message":"YouTube Data API v3 has not been used in project 123 before or it is disabled."}}');
    if (url.includes("mine=true")) return t_resp(200, '{"items":[{"id":"UCtest","snippet":{"title":"FE用語ドリル"}}]}');
    if (url.includes("/channels?")) return t_resp(200, JSON.stringify({ items: [{ statistics: { subscriberCount: String(ytSubsN), hiddenSubscriberCount: ytHidden } }] }));
    if (url.includes("/playlistItems?")) return t_resp(200, url.includes("playlistId=UUtest") ? '{"items":[{"contentDetails":{"videoId":"v1"}},{"contentDetails":{"videoId":"v2"}}]}' : '{"items":[]}');
    const ago = (h) => new RealDate(NOW - h * 3600e3).toISOString();
    const c = (id, vid, name, text, h, ch) => ({ id, snippet: { videoId: vid, topLevelComment: { snippet: { videoId: vid, authorDisplayName: name, authorChannelId: { value: ch }, textOriginal: text, publishedAt: ago(h) } } } });
    // 本物と同じく、コメントは持ち主の権限（youtube.readonly）では読めず、API キーなら読める
    if (url.includes("/commentThreads?") && !url.includes("key=ytkey")) return t_resp(403, '{"error":{"code":403,"message":"Request had insufficient authentication scopes."}}');
    if (url.includes("/commentThreads?")) return t_resp(200, JSON.stringify({ items: [
      c("y1", "v1", "@fe_student", "変数の動きが見えてわかりやすい", 1, "UCviewer"),
      c("y2", "v1", "@fe_drill", "📌 サイトはプロフィールから", 0.5, "UCtest"),
      c("y3", "v3", "@old_viewer", "前の動画へのコメント", 240, "UCold") ] }));
    if (url.includes("/videos?")) {
      const v = { v1: ["二分探索を1行ずつ #shorts #基本情報", 24, 1234, 20, 2], v2: ["バブルソート", 96, 800, 11, 0], v3: ["線形探索", 400, 300, 3, 1] };
      const ids = decodeURIComponent(url.match(/id=([^&]*)/)[1]).split(",");
      return t_resp(200, JSON.stringify({ items: ids.filter((i) => v[i]).map((i) => ({ id: i, snippet: { title: v[i][0], publishedAt: ago(v[i][1]) },
        statistics: { viewCount: String(v[i][2]), likeCount: String(v[i][3]), commentCount: String(v[i][4]) } })) }));
    }
    return t_resp(404, '{"error":{"message":"not found"}}');
  }
  if (url.includes("news.google.com")) {
    const w = decodeURIComponent(url.match(/q=([^&]*)/)[1]).split(" ")[0];
    const titles = [`${w}の話題その1`, `${w}の話題その2`, `${w}の話題その3`];
    if (w.includes("サイバー")) titles.unshift("工場でランサムウェア被害、生産が一時停止");
    if (w.includes("AI")) titles.unshift("IPO を目指すAIスタートアップ");
    return t_resp(200, JSON.stringify(titles.map((t, i) => ({ title: t + " - 媒体" + i, source: "媒体" + i, link: "https://example.com/" + i }))));
  }
  if (url.includes("searchconsole.googleapis.com")) {
    // 検索: 直近の日ごとの数字（FE は表示 100・クリック 3、ITパスポートは表示 40・クリック 1）
    const ip = url.includes(encodeURIComponent("https://ip.yogo-drill.com/"));
    const rows = [3, 2].map((n) => ({ keys: [Utilities.formatDate(new RealDate(NOW - n * 86400e3), "", "yyyy-MM-dd")], impressions: ip ? 40 : 100, clicks: ip ? 1 : 3 }));
    return t_resp(200, JSON.stringify({ rows }));
  }
  if (downSite && url === downSite) return t_resp(404, "not found");
  if (url.includes("raw.githubusercontent.com/yuki-fe/yogo-drill/check-results/")) return checkData ? t_resp(checkCode, JSON.stringify(checkData)) : t_resp(404, "404: Not Found");
  for (const name in STOCK) if (url.endsWith("/ig/" + name)) return t_resp(200, JSON.stringify(STOCK[name]));
  if (url.includes("graph.facebook.com") || url.includes("graph.instagram.com")) {
    const path = url.replace(/^https:\/\/graph\.(facebook|instagram)\.com\/v[0-9.]+/, "").replace(/[?&]access_token=[^&]*/, "");
    igCalls.push((o.method || "get") + " " + path + (o.payload && o.payload.message ? " [" + o.payload.message.split("\n")[0] + "]" : ""));
    if (path.includes("status_code")) return t_resp(200, JSON.stringify({ status_code: status }));
    if (path.includes("fields=username")) return t_resp(200, '{"username":"it_senpai_lab"}');
    if (path.includes("fields=id,media_type")) return t_resp(200, '{"data":[{"id":"m9","media_type":"VIDEO","permalink":"https://www.instagram.com/reel/R/"}]}');
    if (path.includes("permalink")) return t_resp(200, '{"permalink":"https://www.instagram.com/reel/XYZ/"}');
    if (path.includes("/comments?")) return t_resp(200, JSON.stringify({ data: [
      { id: "c1", text: "トレースの動き、わかりやすい！", username: "it_student", timestamp: new RealDate(NOW - 3600e3).toISOString() },
      { id: "c2", text: "📌 紹介コメント", username: "it_senpai_lab", timestamp: new RealDate(NOW - 3000e3).toISOString() } ] }));
    if (path.includes("followers_count")) return t_resp(200, '{"followers_count": 152}');
    if (path.includes("/insights") && insightsDenied) return t_resp(400, '{"error":{"message":"(#10) Application does not have permission for this action"}}');
    if (path.includes("/insights")) return t_resp(200, JSON.stringify({ data: [{ name: "reach", values: [{ value: 340 }] }, { name: "saved", values: [{ value: 28 }] }] }));
    if (path.includes("/media?fields")) return t_resp(200, JSON.stringify({ data: [{ id: "m1", caption: "【科目B トレース No.4】二分探索", timestamp: new RealDate(NOW - 86400e3).toISOString(), like_count: 30, comments_count: 1 }] }));
    return t_resp(200, JSON.stringify({ id: String(mediaN++) }));
  }
  return t_resp(200, "ok");
} };
let fetchAllCalls = 0;
UrlFetchApp.fetchAll = (reqs) => { fetchAllCalls++; return reqs.map((r) => UrlFetchApp.fetch(r.url, r)); };
"""

SCENARIO = r"""
const t_post = (ev) => doPost({ parameter: { key: "key" }, postData: { contents: JSON.stringify({ events: [Object.assign({ replyToken: "r", source: { userId: "U1" } }, ev)] }) } });
const t_say = (text) => t_post({ type: "message", message: { type: "text", text } });
const t_tap = (data) => t_post({ type: "postback", postback: { data } });
const t_show = (m) => m.messages.map((x, i) => `[${i + 1}] ` + (x.type === "video" ? `（動画）${x.originalContentUrl.split("/").pop()}` : x.type === "image" ? "（画像）" : x.text.split("\n").slice(0, 4).join(" / ")) + (x.quickReply ? "\n    ボタン: " + x.quickReply.items.map((q) => q.action.label).join(" / ") : "")).join("\n");
const lastMsg = () => sent[sent.length - 1];
const t_last = () => (sent.length ? (lastMsg().to ? "PUSH " : "REPLY ") + t_show(lastMsg()) : "(なし)");
const t_text = () => lastMsg().messages.map((x) => x.text || "").join("\n");
const t_buttons = () => { const m = lastMsg().messages; const q = m[m.length - 1].quickReply; return q ? q.items.map((x) => x.action.label) : []; };
const out = [], fails = [];
const check = (name, cond) => { out.push((cond ? "  OK  " : "  NG  ") + name); if (!cond) fails.push(name); };
try {
  setup();
  check("トリガーを作る（お問い合わせ・毎朝・トークンの更新）", triggers.join(",") === "onFormSubmit,dailyReport,refreshInstagramToken");
  check("setup で YouTube のチャンネルを見つける", store.YT_CHANNEL_ID === "UCtest");
  check("金曜はリールの日", kindToday() === "reel");
  const mm = toMessages(morningMessages());
  out.push("--- 毎朝のレポート（吹き出し " + mm.length + " 個）", t_show({ messages: mm }));
  check("毎朝の吹き出しは5個まで", mm.length <= 5);
  check("自分の紹介コメントは新しいコメントに数えない", !JSON.stringify(mm).includes("📌 紹介コメント"));
  const mt = mm[0].text;
  out.push("--- 【YouTube】の欄", mt.slice(mt.indexOf("【YouTube】"), mt.indexOf("【お問い合わせ】")).trim());
  check("毎朝のレポートに【YouTube】の欄", mt.includes("【YouTube】") && mt.includes("最新の動画（10/8「二分探索を1行ずつ」）: 再生 1234、高く評価 20、コメント 2") && mt.includes("登録者 35 人"));
  check("YouTube の新しいコメント（自分のと古いのは出さない）", mt.includes("@fe_student（二分探索を1行ずつ）") && !mt.includes("📌 サイトはプロフィールから") && !mt.includes("old_viewer"));
  check("同じコメントを次の朝には出さない", !ytStatsText(true).includes("fe_student"));
  const draftButtons = mm[mm.length - 1].quickReply.items.map((q) => q.action.label);
  check("下書きのボタンは「素材を受け取る」から（自動投稿のボタンはない）", draftButtons[0] === "素材を受け取る" && !draftButtons.some((l) => l.includes("投稿")));

  // 公開中の用語サイトごとの欄
  out.push("--- サイトごとの欄", mt.slice(mt.indexOf("【FE用語ドリル】"), mt.indexOf("【インスタ】")).trim());
  check("公開中の7サイトの欄がある", SITES.length === 7 && SITES.every((s) => mt.includes("【" + s.name + "】")));
  check("ITパスポートの閲覧者と検索", mt.includes("【ITパスポート用語ドリル】\n閲覧者: 昨日 5 人（ページ 10 回）、直近7日 35 人（その前の7日より +0）\n検索: 10/7 表示 40・クリック 1、直近7日 表示 80・クリック 2\nサイト: 開ける／"));
  check("アナリティクスがないサイトは「まだ」、検索の欄は出さない", mt.includes("【簿記用語ドリル】\n閲覧者: アナリティクスはまだ付けてないよ\nサイト: 開ける／"));
  check("FE のアナリティクスがないときも、FE の検索とサイトの様子は出す", mt.includes("【FE用語ドリル】\n閲覧者: アナリティクスはまだ付けてないよ\n検索: 10/7 表示 100"));
  check("前の【検索】【サイト】【最後の更新】の欄はなくなった", !mt.includes("【検索】") && !mt.includes("【サイト】") && !mt.includes("【最後の更新】"));
  store.GA_PROPERTY_ID = "111";
  const both = buildReport();
  check("FE の閲覧者とインスタから来た人", both.includes("【FE用語ドリル】\n閲覧者: 昨日 10 人（ページ 20 回）、直近7日 70 人（その前の7日より +0）\nうちインスタから: 昨日 2 人") && both.includes("【ITパスポート用語ドリル】\n閲覧者: 昨日 5 人"));
  gaDeniedIp = true;
  const den = buildReport();
  check("ITパスポートの数字が取れなくても、ほかのサイトの数字は出す", den.includes("【ITパスポート用語ドリル】\n閲覧者: 取れなかった") && den.includes("閲覧者: 昨日 10 人"));
  gaDeniedIp = false;
  downSite = "https://boki.yogo-drill.com/";
  check("開けないサイトを知らせる", buildReport().includes("【簿記用語ドリル】\n閲覧者: アナリティクスはまだ付けてないよ\nサイト: 開けないみたい！（エラー 404）"));
  downSite = "";

  // グラフ（サイトごと）
  t_say("グラフ"); out.push("--- グラフ", t_last());
  check("「グラフ」でサイトを選ぶボタン（アナリティクスのあるサイトだけ）", t_buttons().join(",") === "FE,ITパスポート" && t_text().includes("簿記"));
  check("ボタンを押すと「グラフ サイト名」を送る", lastMsg().messages[0].quickReply.items[1].action.text === "グラフ ITパスポート");
  t_say("グラフ ITパスポート"); out.push("--- グラフ ITパスポート", t_last());
  check("「グラフ ITパスポート」でそのサイトのグラフ（サイトの色）", t_text().includes("ITパスポート用語ドリルの、直近7日の閲覧者のグラフ") && t_text().includes("合計 35 人") &&
    lastMsg().messages[1].type === "image" && lastMsg().messages[1].originalContentUrl.includes(encodeURIComponent("#2d68a8")));
  t_say("グラフ ip");
  check("「グラフ ip」のように短い名前でもよい", t_text().includes("ITパスポート用語ドリルの"));
  t_say("グラフ fe");
  check("「グラフ fe」で FE のグラフ", t_text().includes("FE用語ドリルの、直近7日") && t_text().includes("合計 70 人"));
  t_say("グラフ 簿記");
  check("アナリティクスがないサイトは、そう知らせる", t_text().includes("簿記用語ドリルは、まだアナリティクスを付けてない"));
  t_say("グラフ 宇宙");
  check("知らないサイトの名前", t_text().includes("「宇宙」のサイトは見つからなかった"));
  delete store.GA_PROPERTY_ID;
  t_say("グラフ");
  check("グラフを出せるサイトが1つだけなら、すぐそのグラフ", t_text().includes("ITパスポート用語ドリルの") && lastMsg().messages[1].type === "image");
  store.GA_PROPERTY_ID = "111";
  NOW = new Date("2026-10-12T08:00:00+09:00").getTime();
  const mon = toMessages(morningMessages());
  check("月曜は用語クイズの日", kindToday() === "term");
  check("月曜の朝は FE の先週のグラフ", mon[0].text.includes("先週1週間のFE用語ドリルの閲覧者") && mon[1].type === "image" && mon.length <= 5);
  NOW = new Date("2026-10-09T10:00:00+09:00").getTime();
  delete store.GA_PROPERTY_ID;

  // 素材を受け取って、自分でアプリから投稿する
  igCalls.length = 0;
  const term = STOCK["posts.json"][0];
  t_tap("ig=kit&k=term&id=" + term.no); out.push("--- 素材を受け取る（用語クイズ）", t_last());
  const km = lastMsg().messages;
  check("素材は画像2枚・手順・投稿文・紹介コメント", km.length === 5 && km[0].type === "image" && km[1].type === "image" && km[3].text === term.caption && km[4].text.startsWith("📌"));
  check("素材の最後に「投稿した」ボタン", km[4].quickReply.items[0].action.label === "投稿した");
  check("素材を送っても投稿しない・進めない", igCalls.length === 0 && !store.IG_NEXT);
  t_tap("ig=done&k=term&id=" + term.no); out.push("--- 投稿した", t_last());
  check("「投稿した」で次の下書きに進む", store.IG_NEXT === "1" && t_text().includes("おつかれ"));
  t_tap("ig=done&k=term&id=" + term.no);
  check("「投稿した」を2回押しても1つしか進まない", store.IG_NEXT === "1" && t_text().includes("前の下書きのボタン"));
  const reel = STOCK["reels.json"][0];
  t_tap("ig=kit&k=reel&id=" + reel.key); out.push("--- 素材（リール）", t_last());
  check("リールの素材は動画と表紙", lastMsg().messages[0].type === "video" && lastMsg().messages[1].type === "image" && lastMsg().messages.length === 5);
  t_tap("ig=done&k=reel&id=" + reel.key); out.push("--- 投稿した（リール）", t_last());
  check("リールを手で投稿したら次へ進んで YouTube のセット", store.IG_NEXT_REEL === "1" && t_text().includes("YouTube ショートにも出そう") && igCalls.length === 0);
  t_tap("ig=next&k=trace&id=" + STOCK["trace-posts.json"][0].no);
  check("「別のにする」で次の下書き", store.IG_NEXT_TRACE === "1" && t_text().includes("別のにしたよ"));
  t_tap("ig=kind&k=reel&id=" + STOCK["reels.json"][1].key);
  check("「種類を変える」で次の種類", kindToday() === "term" && t_text().includes("用語クイズに変えたよ"));
  igCalls.length = 0;
  t_tap("ig=post&k=term&id=" + STOCK["posts.json"][1].no);
  check("前にあった「今すぐ投稿」のボタンを押しても投稿しない", igCalls.length === 0 && store.IG_NEXT === "1");

  // 消したことば（「使い方」に案内する）
  ["状況", "インスタ", "インスタ リール", "素材", "投稿", "紹介リール", "ニュース", "ニュース AI", "ジャンル", "ニュース投稿 1 2"].forEach((w) => {
    t_say(w);
    check(`「${w}」はもう使わない`, t_text().includes("「使い方」"));
  });

  t_say("紹介コメント"); out.push("--- 紹介コメント", t_last());
  check("「紹介コメント」で最新の投稿に付ける", t_text().includes("紹介コメントを付けたよ"));
  t_say("コメント"); out.push("--- コメント", t_last());
  check("コメント一覧に自分のコメントを出さない", t_text().includes("it_student") && !t_text().includes("📌"));
  t_say("反応");
  check("反応", t_text().includes("リーチ"));
  t_say("ユーチューブ 反応"); out.push("--- ユーチューブ 反応", t_last());
  check("「ユーチューブ 反応」で最近の動画の数字", t_text().includes("■ 10/8「二分探索を1行ずつ」\n再生 1234／高く評価 20／コメント 2") && t_text().includes("バブルソート"));
  t_say("ユーチューブ");
  check("「ユーチューブ」だけでも最近の動画の数字", t_text().includes("再生 1234"));
  t_say("ユーチューブ コメント"); out.push("--- ユーチューブ コメント", t_last());
  check("「ユーチューブ コメント」で1週間のコメント", t_text().includes("fe_student") && !t_text().includes("📌") && !t_text().includes("old_viewer"));
  NOW += 86400e3; ytSubsN = 37;
  check("登録者の増減", ytStatsText(false).includes("登録者 37 人（前の記録より +2）"));
  ytHidden = true;
  check("登録者数が非公開のとき", ytStatsText(false).includes("非公開"));
  delete store.YT_API_KEY;
  const nk = ytStatsText(false);
  check("コメントが取れなくても、再生数と登録者は出す", nk.includes("再生 1234") && nk.includes("登録者") && nk.includes("コメントは取れなかった（コメント: Request had insufficient"));
  t_say("ユーチューブ 反応");
  check("コメントが取れなくても「ユーチューブ 反応」は出す", t_text().includes("再生 1234"));
  t_say("ユーチューブ コメント");
  check("「ユーチューブ コメント」は取れない理由を出す", t_text().includes("コメントを読むとき"));
  store.YT_API_KEY = "ytkey";
  ytHidden = false; ytDenied = true;
  const rd = buildReport();
  check("YouTube が取れなくても理由を出して、ほかの欄は出す", rd.includes("YouTube の数字は取れなかった（チャンネル: YouTube Data API v3 has not been used") && rd.includes("【ITパスポート用語ドリル】"));
  ytDenied = false;
  const ytId = store.YT_CHANNEL_ID; delete store.YT_CHANNEL_ID; const ytN = ytCalls.length;
  t_say("ユーチューブ 反応");
  check("YouTube の設定がないときは知らせるだけ", t_text().includes("まだつながってない") && !buildReport().includes("【YouTube】") && ytCalls.length === ytN);
  store.YT_CHANNEL_ID = ytId; NOW -= 86400e3;
  igMediaCache = null; fetchAllCalls = 0;
  const igBefore = igCalls.length;
  const all = buildReport();
  check("レポートはまとめて取りに行く（Instagram の一覧は1回だけ）", all.includes("【インスタ】") && fetchAllCalls <= 4 &&
    igCalls.slice(igBefore).filter((c) => c.includes("/media?fields")).length === 1);
  insightsDenied = true;
  check("数字が取れないときは理由も出す", igStatsText().includes("理由: (#10)") && igStatsText().includes("instagram_manage_insights"));
  check("リーチが取れなくても、いいねとフォロワーは出す", igStatsText().includes("いいね 30") && igStatsText().includes("フォロワー 152"));
  check("「反応」もリーチが取れなくても、いいねは出す", igRecentText().includes("いいね 30") && igRecentText().includes("理由: (#10)"));
  insightsDenied = false;
  NOW = new Date("2026-10-10T08:00:00+09:00").getTime();
  check("土曜は用語クイズの日（今週のITニュースはやめた）", kindToday() === "term");

  // サイトの点検（毎週月曜に GitHub の自動実行が点検した結果を読む）
  NOW = new Date("2026-10-23T08:00:00+09:00").getTime();
  check("点検の結果がまだなくても、月曜以外の朝は何も言わない", !buildReport().includes("【サイトの点検】"));
  const ckSite = (key, name, items) => ({ key, name, url: `https://${key}.yogo-drill.com/`, pages: 300, items, more: 0,
    problems: items.filter((i) => i.level === "問題").length, warnings: items.filter((i) => i.level === "注意").length });
  checkData = { checked_at: "2026-10-26T04:10:00+09:00", result_url: "https://github.com/yuki-fe/yogo-drill/blob/check-results/result.md",
    summary: { sites: 3, pages: 900, problems: 2, warnings: 1, infos: 1 },
    sites: [
      ckSite("fe", "FE用語ドリル", [{ level: "問題", kind: "リンク切れ", page: "https://fe.yogo-drill.com/about.html", detail: "https://fe.yogo-drill.com/x.html（エラー 404）" },
                                   { level: "注意", kind: "スマホで横にはみ出す", page: "https://fe.yogo-drill.com/b/trace.html", detail: "幅 390px に 420px" }]),
      ckSite("ip", "ITパスポート用語ドリル", [{ level: "問題", kind: "JavaScript のエラー", page: "https://ip.yogo-drill.com/", detail: "x is not defined" }]),
      ckSite("boki", "簿記用語ドリル", [{ level: "情報", kind: "アクセス解析なし", page: "https://boki.yogo-drill.com/", detail: "" }])] };
  NOW = new Date("2026-10-26T08:00:00+09:00").getTime();
  const ckm = buildReport();
  out.push("--- 【サイトの点検】の欄（月曜）", ckm.slice(ckm.indexOf("【サイトの点検】"), ckm.indexOf("【お問い合わせ】")).trim());
  check("新しい点検の結果を朝のレポートに出す", ckm.includes("【サイトの点検】\n10/26 の点検で、問題が 2 件・注意が 1 件 見つかったよ。") &&
    ckm.includes("・FE用語ドリル: リンク切れ（/about.html）") && ckm.includes("・ITパスポート用語ドリル: JavaScript のエラー（/）") && ckm.includes("「点検」"));
  check("同じ結果は次の朝には出さない", !buildReport().includes("【サイトの点検】"));
  t_say("点検"); out.push("--- 点検", t_last());
  check("「点検」でサイトごとの問題と注意", t_text().includes("■ FE用語ドリル（問題 1・注意 1）") && t_text().includes("・[問題] リンク切れ: /about.html") &&
    t_text().includes("問題なし: 簿記用語ドリル") && t_text().includes("check-results/result.md") && !t_text().includes("アクセス解析なし"));
  NOW = new Date("2026-11-09T08:00:00+09:00").getTime();
  check("点検が止まっていたら月曜に知らせる", buildReport().includes("点検が 14 日動いてない"));
  NOW = new Date("2026-11-10T08:00:00+09:00").getTime();
  check("月曜以外は、止まっていても毎朝は言わない", !buildReport().includes("【サイトの点検】"));
  checkData = Object.assign({}, checkData, { checked_at: "2026-11-09T04:00:00+09:00", summary: { sites: 8, pages: 2300, problems: 0, warnings: 0, infos: 6 }, sites: [] });
  check("問題がない週は「問題なし！」", buildReport().includes("11/9 に 8 サイト・2300 ページを点検したよ。問題なし！"));
  checkCode = 500; NOW = new Date("2026-11-16T08:00:00+09:00").getTime();
  check("結果が取れない月曜は知らせる", buildReport().includes("点検の結果が取れなかった"));
  checkCode = 200;
  t_say("使い方"); out.push("--- 使い方", t_last());
  check("使い方に「グラフ 簿記」「紹介コメント」「ユーチューブ」「点検」がある", ["グラフ 簿記", "・紹介コメント …", "・ユーチューブ …", "・点検 …"].every((w) => t_text().includes(w)));
  check("使い方に消したことばがない", !["・状況 …", "・インスタ …", "・素材 …", "・ニュース …", "・ジャンル …", "紹介リール"].some((w) => t_text().includes(w)));
} catch (e) { out.push("ERROR " + e.stack); fails.push("例外"); }
out.push("", fails.length ? "FAILED: " + fails.join("、") : "ALL OK");
document.getElementById("out").textContent = out.join("\n");
"""

html = ("<!doctype html><meta charset='utf-8'><body><pre id='out'>running</pre>\n<script>const STOCK = "
        + json.dumps(stock, ensure_ascii=False) + ";\n" + MOCKS + "</script>\n<script>\n" + code
        + "\n</script>\n<script>\n" + SCENARIO + "</script>")
page = HERE / "test.html"
page.write_text(html, encoding="utf-8")

dom = ""
for browser in BROWSERS:
    dom = subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--virtual-time-budget=5000",
                          "--dump-dom", page.as_uri()], capture_output=True, encoding="utf-8", errors="replace").stdout
    if '<pre id="out">' in dom:
        break
start, end = dom.find("<pre id=\"out\">"), dom.find("</pre>")
result = dom[start + len("<pre id=\"out\">"):end] if start >= 0 else "結果を読めませんでした: " + dom[:300]
result = result.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
print(result)
sys.exit(0 if result.rstrip().endswith("ALL OK") else 1)
