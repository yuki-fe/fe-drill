"""タイピングのランキング（ranking/ranking.gs）の動作テスト。Google には接続せず、まねした相手（モック）で動かす。

使い方:  python ranking/test/run_test.py
         Microsoft Edge（動かないときは Chrome）でテストのページを開き、結果を表示する。最後に「ALL OK」と出れば成功。
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
BROWSERS = [p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")) if p.exists()]
code = (HERE.parent / "ranking.gs").read_text(encoding="utf-8")

MOCKS = r"""
let NOW = new Date("2026-10-28T10:00:00+09:00").getTime();   // 水曜
const RealDate = Date;
Date = class extends RealDate { constructor(...a) { super(...(a.length ? a : [NOW])); } static now() { return NOW; } };
const store = {};
const PropertiesService = { getScriptProperties: () => ({ getProperty: (k) => store[k] ?? null }) };
let grid = [];
let sheetMade = false;
const sh = {
  appendRow: (r) => { grid.push(r.slice()); },
  setFrozenRows: () => {},
  getLastRow: () => grid.length,
  deleteRow: (n) => { grid.splice(n - 1, 1); },
  getRange: (r, c, nr, nc) => ({
    getValues: () => grid.slice(r - 1, r - 1 + nr).map((row) => row.slice(c - 1, c - 1 + nc)),
    setValues: (v) => { v.forEach((row, i) => { grid[r - 1 + i] = row.slice(); }); } }),
};
const SpreadsheetApp = { getActive: () => ({ getSheetByName: () => (sheetMade ? sh : null), insertSheet: () => { sheetMade = true; return sh; } }) };
let cacheMap = {};
const CacheService = { getScriptCache: () => ({ get: (k) => cacheMap[k] ?? null, put: (k, v) => { cacheMap[k] = v; }, remove: (k) => { delete cacheMap[k]; } }) };
const LockService = { getScriptLock: () => ({ waitLock: () => {}, releaseLock: () => {} }) };
const ContentService = { MimeType: { JSON: "json" }, createTextOutput: (s) => ({ setMimeType: () => s }) };
"""

SCENARIO = r"""
const out = [], fails = [];
function check(name, ok) { out.push((ok ? "OK   " : "NG   ") + name); if (!ok) fails.push(name); }
const P = (o) => JSON.parse(doPost({ postData: { contents: JSON.stringify(o) } }));
const G = (site, board) => JSON.parse(doGet({ parameter: { site, board } }));
const B = "practice-120-imi";
const pid = (n) => "p" + String(n).padStart(4, "0") + "-aaaaaaaaaaaaaaaa";
// chars 文字・ミスなし（打鍵は文字数の2倍）→ 点数は chars × 10
const ent = (n, chars, o) => Object.assign({ site: "fe", board: B, pid: pid(n), name: "名前" + n, chars, words: Math.floor(chars / 5), keys: chars * 2, miss: 0 }, o || {});
const send = (n, chars, o) => { cacheMap = {}; return P(ent(n, chars, o)); };
const COL = { points: 5, chars: 6, acc: 7, hidden: 10 };
try {
  check("今週は月曜から（水曜 → 10/26）", weekKey() === "2026-10-26");
  NOW = new Date("2026-11-01T23:59:00+09:00").getTime();
  check("日曜の夜も同じ週", weekKey() === "2026-10-26");
  NOW = new Date("2026-11-02T00:00:00+09:00").getTime();
  check("月曜0時（日本時間）から次の週", weekKey() === "2026-11-02");
  NOW = new Date("2026-10-28T10:00:00+09:00").getTime();

  // 点数の式（typing.js と同じ）
  check("点数 = 文字数 × 正確さ³ × 10（ミスなし）", points(300, 600, 0) === 3000);
  check("点数: 300文字・600打鍵・ミス60 → 2254点", points(300, 600, 60) === 2254);
  check("点数: 260文字・520打鍵・ミス5 → 2526点", points(260, 520, 5) === 2526);

  setup();
  check("setup でシート「記録」と見出しを作る", grid.length === 1 && grid[0][0] === "サイト" && grid[0][COL.points] === "点数");
  let r = send(1, 100);
  check("初めての記録は1位（今週・全期間）", r.ok && r.week.rank === 1 && r.all.rank === 1 && r.all.of === 1 && r.all.points === 1000);
  check("今週と全期間の2行を書く", grid.length === 3 && grid[1][COL.chars] === 100 && grid[1][COL.acc] === 100);
  r = send(2, 150);
  check("高い人は1位", r.all.rank === 1 && r.all.of === 2);
  r = send(1, 80, { name: "あたらしい名前" });
  check("ベストより低いと、記録はそのまま（順位はベストで）", r.all.rank === 2 && r.all.best === 1000 && r.all.points === 800);
  r = send(1, 110, { miss: 30, name: "あたらしい名前" });
  check("文字数が多くてもミスが多いと点数が低く、ベストは変わらない", r.all.best === 1000 && grid[1][COL.chars] === 100);
  let g = G("fe", B);
  check("表は点数の高い順", g.ok && g.all.map((x) => x.points).join() === "1500,1000" && g.week.length === 2);
  check("表に文字数と正確さ", g.all[0].chars === 150 && g.all[0].acc === 100);
  check("名前はいつも新しくする", g.all[1].name === "あたらしい名前");
  check("pid は先頭の6文字だけ出す", g.all[0].pid === pid(2).slice(0, 6));
  r = send(1, 200, { miss: 4 });
  check("ベストを超えたら書き換える（正確さは小数1桁）", r.all.rank === 1 && r.all.best === 1941 && grid.length === 5 && grid[1][COL.acc] === 99);
  check("送ったあとは表のキャッシュを消す", G("fe", B).all[0].points === 1941);
  grid.push(["fe", B, "all", pid(3), "手で足した人", 1200, 120, 100, 20, new Date(), ""]);
  check("キャッシュがあれば、それを返す（60秒）", G("fe", B).all.length === 2);
  cacheMap = {};
  check("キャッシュが切れたら新しい表", G("fe", B).all.length === 3);

  // はじくもの
  check("知らないサイト", send(9, 50, { site: "zz" }).error === "bad request");
  check("ランキングのない区分（60秒・180秒・腕だめし・意味なし）", ["practice-60-imi", "test-120-imi", "practice-180-imi", "practice-120-term"].every((b) => send(9, 50, { board: b }).error === "bad request") && G("fe", "practice-60-imi").ok === false);
  check("短い pid", send(9, 50, { pid: "abc" }).error === "pid");
  check("打鍵より文字数が多い", send(9, 50, { keys: 40 }).error === "score");
  check("速すぎる（120秒で2401打鍵）", send(9, 1000, { keys: 2401 }).error === "score");
  check("小数・負の数", send(9, 50.5).error === "score" && send(9, 50, { miss: -1 }).error === "score");
  check("文字数0", send(9, 0, { keys: 0, words: 0 }).error === "score");
  check("前の形（score）で送るとはじく", send(9, 50, { chars: undefined, score: 50 }).error === "score");
  check("名前が空・長すぎる", send(9, 50, { name: "  " }).error === "name" && send(9, 50, { name: "12345678901" }).error === "name");
  check("名前に URL", send(9, 50, { name: "abc.com" }).error === "name");
  check("名前に NG語（全角も）", send(9, 50, { name: "ＦＵＣＫ" }).error === "name");
  store.NG_WORDS = "ばか, あほ";
  check("NG語はスクリプト プロパティでも足せる", send(9, 50, { name: "ばかだね" }).error === "name");
  check("名前の記号は消す", send(9, 50, { name: "<b>太郎</b>" }).ok && grid.some((x) => x[4] === "b太郎/b"));
  check("10文字までは OK", send(10, 50, { name: "1234567890" }).ok);
  P(ent(11, 50));
  check("続けて送ると待ってもらう", P(ent(11, 60)).error === "wait");

  // 非表示
  const row = grid.findIndex((x) => x[3] === pid(2) && x[2] === "all");
  grid[row][COL.hidden] = "x";
  cacheMap = {};
  g = G("fe", B);
  check("非表示に印を付けると、今週・全期間とも出ない", !g.all.some((x) => x.points === 1500) && !g.week.some((x) => x.points === 1500));
  r = send(2, 300);
  check("非表示の人が送っても順位は出さず、印は消えない", r.ok && r.all === null && grid[row][COL.hidden] === "x" && grid[row][COL.points] === 3000);

  // 次の週
  NOW = new Date("2026-11-03T10:00:00+09:00").getTime();
  cacheMap = {};
  g = G("fe", B);
  check("週が変わると今週は空、全期間は残る", g.week.length === 0 && g.all.length >= 3);
  r = send(3, 90);
  check("新しい週の1位", r.week.rank === 1 && r.week.of === 1 && r.all.best === 1200);
  NOW = new Date("2026-12-29T10:00:00+09:00").getTime();
  const before = grid.filter((x) => String(x[2]) === "w2026-10-26").length;
  send(4, 70);
  check("8週より前の今週の記録は消す", before > 0 && !grid.some((x) => String(x[2]) === "w2026-10-26") && grid.some((x) => String(x[2]) === "w2026-11-02"));
  check("全期間の記録は消さない", grid.filter((x) => x[2] === "all").length >= 5);
  check("壊れた JSON", JSON.parse(doPost({ postData: { contents: "{" } })).error === "bad json");
} catch (e) { out.push("ERROR " + e.stack); fails.push("例外"); }
out.push("", fails.length ? "FAILED: " + fails.join("、") : "ALL OK");
document.getElementById("out").textContent = out.join("\n");
"""

html = ("<!doctype html><meta charset='utf-8'><body><pre id='out'>running</pre>\n<script>" + MOCKS
        + "</script>\n<script>\n" + code + "\n</script>\n<script>\n" + SCENARIO + "</script>")
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
