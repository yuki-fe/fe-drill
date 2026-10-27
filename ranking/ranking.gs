/* 用語タイピングのランキング（Google Apps Script のウェブアプリ）。
   LINE ボットとは別のプロジェクト。スプレッドシート「タイピングランキング」の Apps Script に貼る。
   サイトの typing.js が、上位を読む（doGet）・記録を送る（doPost）。
   ランキングは「練習・意味も打つ・180秒・分野すべて」（区分 practice-180-imi）の1つだけ。
   点数 = 文字数 × 正確さ³ × 10（正確さ = 打鍵 ÷（打鍵 + ミス））。typing.js の points と同じ式で、ここで計算する。
   シート「記録」は 1行 = サイト・区分・期間・利用者（pid）ごとのベスト（点数の高いもの）。
   運営者が「非表示」の列に何か書くと、その行は表に出ない（同じ pid の行は、ほかの期間も出さない）。 */

const RANK = {
  sites: ["fe"],                 // ランキングを使うサイト（config.json の site_key）
  boards: { "practice-180-imi": 180 },   // 区分 → 制限時間（秒）
  top: 20,                       // 表に出す人数
  nameMax: 10,
  maxKps: 20,                    // 1秒あたりの打鍵の上限（これより速いものは、はじく）
  keepWeeks: 8,                  // 今週の記録を残す週の数
  ngWords: ["死ね", "しね", "殺す", "ころす", "きもい", "うざい", "fuck", "shit", "sex", "ちんこ", "まんこ", "うんこ"],
};
const COLS = ["サイト", "区分", "期間", "pid", "名前", "点数", "文字数", "正確さ(%)", "語数", "日時", "非表示"];

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (!RANK.sites.includes(p.site) || !validBoard(p.board)) return json({ ok: false, error: "bad request" });
  const ckey = `top-${p.site}-${p.board}-${weekKey()}`;
  const cache = CacheService.getScriptCache();
  const hit = cache.get(ckey);
  if (hit) return json(JSON.parse(hit));
  const rows = readRows(), hidden = hiddenPids(rows), wk = weekKey();
  const res = { ok: true, week: topList(rows, p.site, p.board, "w" + wk, hidden), all: topList(rows, p.site, p.board, "all", hidden) };
  cache.put(ckey, JSON.stringify(res), 60);
  return json(res);
}

function doPost(e) {
  let d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json({ ok: false, error: "bad json" }); }
  const bad = checkEntry(d);
  if (bad) return json({ ok: false, error: bad });
  const name = cleanName(d.name);
  if (!name) return json({ ok: false, error: "name" });
  // 同じブラウザから続けて送るのを止める
  const cache = CacheService.getScriptCache();
  if (cache.get("pid-" + d.pid)) return json({ ok: false, error: "wait" });
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    cache.put("pid-" + d.pid, "1", 5);
    const sh = sheet(), rows = readRows(), wk = weekKey(), now = new Date();
    const rec = { points: points(d.chars, d.keys, d.miss), chars: d.chars, acc: Math.round(accuracy(d.keys, d.miss) * 1000) / 10, words: d.words };
    const res = { ok: true };
    [["all", "all"], ["w" + wk, "week"]].forEach(([period, k]) => {
      let r = rows.find((x) => x.site === d.site && x.board === d.board && x.period === period && x.pid === d.pid);
      if (!r) {
        r = Object.assign({ site: d.site, board: d.board, period, pid: d.pid, name, at: now, hidden: "" }, rec);
        sh.appendRow(toRow(r)); rows.push(r);
      } else {
        // 名前はいつも新しくする。記録は点数がベストを超えたときだけ
        r.name = name;
        if (rec.points > r.points) { Object.assign(r, rec); r.at = now; }
        sh.getRange(r.row, 1, 1, COLS.length).setValues([toRow(r)]);
      }
      const hidden = hiddenPids(rows);
      res[k] = hidden.has(d.pid) ? null : Object.assign(rankOf(rows, d.site, d.board, period, r.points, hidden), { best: r.points, points: rec.points });
    });
    pruneWeeks(sh, rows, wk);
    cache.remove(`top-${d.site}-${d.board}-${wk}`);
    return json(res);
  } finally { lock.releaseLock(); }
}

// ---------- 確かめる ----------
function validBoard(b) { return Object.prototype.hasOwnProperty.call(RANK.boards, String(b || "")); }
function accuracy(keys, miss) { return keys + miss ? keys / (keys + miss) : 0; }
function points(chars, keys, miss) { return Math.round(chars * Math.pow(accuracy(keys, miss), 3) * 10); }
function checkEntry(d) {
  if (!d || typeof d !== "object") return "bad request";
  if (!RANK.sites.includes(d.site) || !validBoard(d.board)) return "bad request";
  if (!/^[A-Za-z0-9-]{16,40}$/.test(String(d.pid || ""))) return "pid";
  const sec = RANK.boards[d.board];
  const ints = ["chars", "words", "keys", "miss"].every((k) => Number.isInteger(d[k]) && d[k] >= 0);
  // 文字数（読みの文字数）は打鍵の数より多くならない。用語の数は文字数より多くならない
  if (!ints || d.chars < 1 || d.keys < d.chars || d.words > d.chars || d.keys + d.miss > sec * RANK.maxKps) return "score";
  return "";
}
function cleanName(s) {
  // 見えない文字・制御文字・HTML の記号を除く
  const n = [...String(s || "").normalize("NFKC")].filter((c) => {
    const k = c.codePointAt(0);
    return k >= 0x20 && !(k >= 0x7f && k <= 0x9f) && !(k >= 0x200b && k <= 0x200f) && !(k >= 0x2028 && k <= 0x202e) && k !== 0xfeff && !"<>\"'`".includes(c);
  }).join("").trim();
  if (!n || [...n].length > RANK.nameMax) return "";
  if (/https?:|www\.|\.(com|net|jp|xyz)\b/i.test(n)) return "";
  const low = n.toLowerCase().replace(/\s/g, "");
  const extra = String(PropertiesService.getScriptProperties().getProperty("NG_WORDS") || "").split(",").map((w) => w.trim().toLowerCase()).filter(Boolean);
  if (RANK.ngWords.concat(extra).some((w) => low.includes(w))) return "";
  return n;
}

// ---------- 今週（月曜0時・日本時間で区切る） ----------
function weekKey() {
  const j = new Date(Date.now() + 9 * 3600e3);
  const back = (j.getUTCDay() + 6) % 7;
  const m = new Date(Date.UTC(j.getUTCFullYear(), j.getUTCMonth(), j.getUTCDate() - back));
  return m.toISOString().slice(0, 10);
}

// ---------- シート ----------
function sheet() {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName("記録");
  if (!sh) { sh = ss.insertSheet("記録"); sh.appendRow(COLS); sh.setFrozenRows(1); }
  return sh;
}
function readRows() {
  const sh = sheet(), n = sh.getLastRow() - 1;
  if (n < 1) return [];
  return sh.getRange(2, 1, n, COLS.length).getValues().map((v, i) => ({
    row: i + 2, site: String(v[0]), board: String(v[1]), period: String(v[2]), pid: String(v[3]), name: String(v[4]),
    points: Number(v[5]) || 0, chars: Number(v[6]) || 0, acc: Number(v[7]) || 0, words: Number(v[8]) || 0, at: v[9], hidden: String(v[10] || "").trim() }));
}
function toRow(r) { return [r.site, r.board, r.period, r.pid, r.name, r.points, r.chars, r.acc, r.words, r.at, r.hidden]; }
function hiddenPids(rows) { return new Set(rows.filter((r) => r.hidden).map((r) => r.pid)); }
function visible(rows, site, board, period, hidden) {
  return rows.filter((r) => r.site === site && r.board === board && r.period === period && !hidden.has(r.pid));
}
function topList(rows, site, board, period, hidden) {
  return visible(rows, site, board, period, hidden)
    .sort((a, b) => b.points - a.points || new Date(a.at) - new Date(b.at))
    .slice(0, RANK.top).map((r) => ({ name: r.name, points: r.points, chars: r.chars, acc: r.acc, words: r.words, pid: r.pid.slice(0, 6) }));
}
// 順位は、自分より高い点数の人数 + 1（同じ点数は同じ順位）
function rankOf(rows, site, board, period, pt, hidden) {
  const v = visible(rows, site, board, period, hidden);
  return { rank: v.filter((r) => r.points > pt).length + 1, of: v.length };
}
// 古い週の行を消す（下の行から消すと、行の番号がずれない）
function pruneWeeks(sh, rows, wk) {
  const limit = new Date(Date.parse(wk) - RANK.keepWeeks * 7 * 86400e3).toISOString().slice(0, 10);
  rows.filter((r) => r.period.startsWith("w") && r.period.slice(1) < limit).map((r) => r.row)
    .sort((a, b) => b - a).forEach((n) => sh.deleteRow(n));
}

function json(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

// エディタで1回実行すると、シート「記録」を作る
function setup() { sheet(); }
