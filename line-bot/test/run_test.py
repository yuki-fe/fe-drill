"""LINE ボットの動作テスト。Google や LINE には接続せず、まねした相手（モック）で動かす。

使い方:  python line-bot/test/run_test.py
         Microsoft Edge でテストのページを開き、結果を表示する。最後に「ALL OK」と出れば成功。
         line-bot/ の .gs ファイルを全部読み込む（config.gs・talk.gs があれば先に読む）。
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
BOT = HERE.parent
SITE = BOT.parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
FIRST = ["config.gs", "talk.gs"]

gs = sorted(BOT.glob("*.gs"), key=lambda p: (FIRST.index(p.name) if p.name in FIRST else len(FIRST), p.name))
code = "\n".join(p.read_text(encoding="utf-8") for p in gs)
stock = {name: json.loads((SITE / "static" / "ig" / name).read_text(encoding="utf-8")) for name in ["posts.json", "trace-posts.json", "reels.json", "intro/intro.json"]}

MOCKS = r"""
const sent = [], igCalls = [];
const store = { LINE_TOKEN: "t", WEBHOOK_KEY: "key", OWNER_USER_ID: "U1", IG_TOKEN: "ig", IG_USER_ID: "1789" };
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
const XmlService = { getNamespace: () => ({}), parse: () => { throw new Error("skip"); } };
const t_resp = (code, body) => ({ getResponseCode: () => code, getContentText: () => body });
let status = "IN_PROGRESS", mediaN = 500;
const UrlFetchApp = { fetch: (url, o) => {
  if (url.includes("api.line.me")) { sent.push(JSON.parse(o.payload)); return t_resp(200, "{}"); }
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
    if (path.includes("/insights")) return t_resp(200, JSON.stringify({ data: [{ name: "reach", values: [{ value: 340 }] }, { name: "saved", values: [{ value: 28 }] }] }));
    if (path.includes("/media?fields")) return t_resp(200, JSON.stringify({ data: [{ id: "m1", caption: "【科目B トレース No.4】二分探索", timestamp: new RealDate(NOW - 86400e3).toISOString(), like_count: 30, comments_count: 1 }] }));
    return t_resp(200, JSON.stringify({ id: String(mediaN++) }));
  }
  return t_resp(200, "ok");
} };
"""

SCENARIO = r"""
const t_post = (ev) => doPost({ parameter: { key: "key" }, postData: { contents: JSON.stringify({ events: [Object.assign({ replyToken: "r", source: { userId: "U1" } }, ev)] }) } });
const t_say = (text) => t_post({ type: "message", message: { type: "text", text } });
const t_tap = (data) => t_post({ type: "postback", postback: { data } });
const t_show = (m) => m.messages.map((x, i) => `[${i + 1}] ` + (x.type === "video" ? `（動画）${x.originalContentUrl.split("/").pop()}` : x.type === "image" ? "（画像）" : x.text.split("\n").slice(0, 4).join(" / ")) + (x.quickReply ? "\n    ボタン: " + x.quickReply.items.map((q) => q.action.label).join(" / ") : "")).join("\n");
const lastMsg = () => sent[sent.length - 1];
const t_last = () => (sent.length ? (lastMsg().to ? "PUSH " : "REPLY ") + t_show(lastMsg()) : "(なし)");
const t_text = () => lastMsg().messages.map((x) => x.text || "").join("\n");
const out = [], fails = [];
const check = (name, cond) => { out.push((cond ? "  OK  " : "  NG  ") + name); if (!cond) fails.push(name); };
try {
  setup();
  check("トリガーを作る", triggers.length >= 3);
  check("金曜はリールの日", kindToday() === "reel");
  const mm = toMessages(morningMessages());
  out.push("--- 毎朝のレポート（吹き出し " + mm.length + " 個）", t_show({ messages: mm }));
  check("毎朝の吹き出しは5個まで", mm.length <= 5);
  check("自分の紹介コメントは新しいコメントに数えない", !JSON.stringify(mm).includes("📌 紹介コメント"));

  igCalls.length = 0;
  const reel = STOCK["reels.json"][0];
  t_tap("ig=post&k=reel&id=" + reel.key); out.push("--- リールを今すぐ投稿", t_last());
  check("リールは処理待ちになる", !!store.IG_PENDING);
  t_tap("ig=post&k=reel&id=" + reel.key);
  check("処理中は二重に投稿しない", t_text().includes("処理中"));
  const before = sent.length; igWorker();
  check("処理中の見回りでは何も送らない", sent.length === before);
  status = "FINISHED"; igCalls.length = 0; igWorker(); out.push("--- 見回り（処理が完了）", t_last(), ...igCalls);
  check("リールを公開して知らせる", t_text().includes("投稿したよ"));
  check("リールに紹介コメントを付ける", igCalls.some((c) => c.includes("/comments [📌 科目B")));
  check("YouTube のセットも届く", lastMsg().messages.length >= 3);
  check("リールのストックが進む", store.IG_NEXT_REEL === "1");

  // 紹介リール: 下書き → 投稿 → 処理完了。リールのストックは進めない
  igCalls.length = 0; status = "IN_PROGRESS";
  t_say("紹介リール"); out.push("--- 紹介リール", t_last());
  check("紹介リールの下書きに動画とボタン", lastMsg().messages[0].type === "video" && t_text().includes("今すぐ投稿"));
  t_tap("ig=intro"); out.push("--- 紹介リールを投稿", t_last());
  check("紹介リールは処理待ちになる", !!store.IG_PENDING && JSON.parse(store.IG_PENDING).kind === "intro");
  status = "FINISHED"; igCalls.length = 0; igWorker(); out.push("--- 見回り（紹介リール完了）", t_last(), ...igCalls);
  check("紹介リールを公開して知らせる", t_text().includes("投稿したよ") && lastMsg().messages.length >= 3);
  check("紹介リールに紹介用のコメント", igCalls.some((c) => c.includes("/comments [📌 サイトはプロフィール")));
  check("紹介リールではリールのストックを進めない", store.IG_NEXT_REEL === "1" && !!store.IG_INTRO_DONE);
  t_say("紹介リール");
  check("紹介リールは二重に投稿しない", t_text().includes("もう投稿してある"));
  t_tap("ig=intro");
  check("古いボタンでも二重に投稿しない", t_text().includes("もう投稿してある") && !store.IG_PENDING);

  t_say("インスタ トレース");
  check("「インスタ トレース」でトレースの下書き", t_text().includes("トレースクイズ"));
  const tr = STOCK["trace-posts.json"][0];
  t_tap("ig=sched&k=trace&id=" + tr.no);
  check("20時の予約", !!store.IG_SCHEDULE);
  NOW = new Date("2026-10-09T20:05:00+09:00").getTime(); igCalls.length = 0;
  igWorker(); out.push("--- 見回り（20:05）", t_last(), ...igCalls);
  check("予約した時刻に投稿する", t_text().includes("投稿したよ") && store.IG_NEXT_TRACE === "1");
  check("トレースに紹介コメントを付ける", igCalls.some((c) => c.includes("/comments [📌 科目B")));

  igCalls.length = 0;
  const term = STOCK["posts.json"][0];
  t_tap("ig=post&k=term&id=" + term.no);
  check("用語クイズに用語向けの紹介コメント", igCalls.some((c) => c.includes("/comments [📌 この問題は")));
  t_tap("ig=post&k=term&id=" + term.no);
  check("古い下書きのボタンでは投稿しない", !t_text().includes("投稿したよ"));

  t_say("紹介コメント"); out.push("--- 紹介コメント", t_last());
  check("「紹介コメント」で最新の投稿に付ける", t_text().includes("紹介コメントを付けたよ"));
  t_say("コメント"); out.push("--- コメント", t_last());
  check("コメント一覧に自分のコメントを出さない", t_text().includes("it_student") && !t_text().includes("📌"));
  t_say("反応");
  check("反応", t_text().includes("リーチ"));
  t_say("使い方");
  check("使い方に「紹介コメント」がある", t_text().includes("紹介コメント"));
  NOW = new Date("2026-10-12T08:00:00+09:00").getTime();
  check("月曜は用語クイズの日", kindToday() === "term");
} catch (e) { out.push("ERROR " + e.stack); fails.push("例外"); }
out.push("", fails.length ? "FAILED: " + fails.join("、") : "ALL OK");
document.getElementById("out").textContent = out.join("\n");
"""

html = ("<!doctype html><meta charset='utf-8'><body><pre id='out'>running</pre>\n<script>const STOCK = "
        + json.dumps(stock, ensure_ascii=False) + ";\n" + MOCKS + "</script>\n<script>\n" + code
        + "\n</script>\n<script>\n" + SCENARIO + "</script>")
page = HERE / "test.html"
page.write_text(html, encoding="utf-8")

dom = subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--virtual-time-budget=5000",
                      "--dump-dom", page.as_uri()], capture_output=True, encoding="utf-8", errors="replace").stdout
start, end = dom.find("<pre id=\"out\">"), dom.find("</pre>")
result = dom[start + len("<pre id=\"out\">"):end] if start >= 0 else "結果を読めませんでした: " + dom[:300]
result = result.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
print(result)
sys.exit(0 if result.rstrip().endswith("ALL OK") else 1)
