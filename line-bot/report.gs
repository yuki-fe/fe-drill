/* FE用語ドリル 運用LINE: 毎朝のレポート（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

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
  const msgs = [{ type: "text", text: buildReport() }];
  const main = mainSite();
  if (gaReady() && new Date(fmt(new Date(), "yyyy/MM/dd")).getDay() === CONFIG.chartWeekday) {
    const st = visitorStats(null, siteGa(main));
    if (st) { msgs[0].text += "\n\n" + TALK.chartWeekly(main.name); msgs.push(chartMessage(st, main)); }
  }
  msgs.push({ type: "text", text: newsText(selectedGenres(), CONFIG.newsPerGenre, TALK.newsHead) });
  if (igReady()) [].concat(igDraftMessage()).forEach((m) => msgs.push(m));
  return msgs.slice(0, 5);
}

function buildReport() {
  const lines = [pick(TALK.morning), ""];
  // 時間のかかる問い合わせは、先にまとめて同時に取りに行く（サイトごとに i 番目の名前を付ける）
  const reqs = {};
  SITES.forEach((site, i) => {
    reqs["open" + i] = healthRequest(site);
    reqs["update" + i] = updateRequest(site);
    if (siteGa(site)) reqs["visitors" + i] = gaRequest(VISITORS_QUERY, siteGa(site));
    if (site.search) reqs["search" + i] = searchRequest(site);
  });
  if (gaReady()) reqs.igVisitors = gaRequest(IG_VISITORS_QUERY, siteGa(mainSite()));
  if (ytReady()) Object.assign(reqs, ytRequests(5));
  if (CONFIG.checkUrl) reqs.check = checkRequest();
  const pre = fetchNamed(reqs);
  SITES.forEach((site, i) => lines.push(...siteLines(site, i, pre), ""));
  if (igReady()) {
    lines.push("【インスタ】", igStatsText());
    const c = igNewCommentsText(true);
    if (c) lines.push(c);
    lines.push("");
  }
  if (ytReady()) lines.push("【YouTube】", ytStatsText(true, pre), "");
  const ck = CONFIG.checkUrl ? checkSection(pre.check) : "";
  if (ck) lines.push("【サイトの点検】", ck, "");
  const n = openInquiries().length;
  lines.push("【お問い合わせ】", n ? TALK.inquirySome(n) : TALK.inquiryNone);
  return lines.join("\n");
}

/* 1サイトぶんの欄: 閲覧者・検索・開けるか・最後の更新。pre は buildReport が先に取った返事 */
function siteLines(site, i, pre) {
  const out = ["【" + site.name + "】"];
  if (!siteGa(site)) out.push(TALK.gaNone);
  else {
    const st = visitorStats(pre["visitors" + i], siteGa(site));
    if (!st) out.push(TALK.gaError);
    else {
      const y = st.days[st.days.length - 1];
      out.push(TALK.visitors(y.users, y.views, st.week, st.week - st.prevWeek));
      const ig = site.main ? igVisitorStats(pre.igVisitors) : null;
      if (ig) out.push(TALK.visitorsIg(ig.yesterday, ig.week, ig.week - ig.prevWeek));
    }
  }
  if (site.search) {
    const s = searchStats(site, pre["search" + i]);
    out.push(s.error ? TALK.searchError : !s.latest ? TALK.searchNone : TALK.search(s.latest, s.week));
  }
  const h = siteHealth(site, pre["open" + i]);
  const u = lastUpdate(site, pre["update" + i]);
  out.push((h.ok ? TALK.siteOk : TALK.siteNg(h.why)) + "／" + (u ? TALK.updated(u.date, u.message) : TALK.updatedUnknown));
  return out;
}

/* ---------- 用語サイト（config.gs の SITES） ---------- */
const mainSite = () => SITES.find((s) => s.main) || SITES[0];

/* GA4 のプロパティ ID。main のサイトはスクリプト プロパティの GA_PROPERTY_ID */
function siteGa(site) {
  return site.ga || (site.main ? prop("GA_PROPERTY_ID") : "");
}

/* 「簿記」「ip」「ITパスポート用語ドリル」などから、サイトを探す */
function findSite(word) {
  const w = word.normalize("NFKC").toLowerCase().trim();
  return SITES.find((s) => [s.key, s.short, s.name].some((x) => x.normalize("NFKC").toLowerCase() === w)) ||
    SITES.find((s) => s.name.normalize("NFKC").toLowerCase().indexOf(w) >= 0) || null;
}

/* ---------- 閲覧者（Google アナリティクス 4） ---------- */
/* main のサイト（FE）のアナリティクスがつながっているか（「人気」・Instagram から来た人・月曜のグラフ） */
function gaReady() {
  return !!siteGa(mainSite());
}

/* propertyId: そのサイトの GA4 のプロパティ ID。なければ main のサイト */
function gaRequest(body, propertyId) {
  return {
    url: "https://analyticsdata.googleapis.com/v1beta/properties/" + (propertyId || siteGa(mainSite())) + ":runReport",
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(body),
  };
}

function gaParse(res) {
  try {
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

function gaReport(body, propertyId) {
  try {
    return gaParse(fetchAll([gaRequest(body, propertyId)])[0]);
  } catch (e) {
    console.warn(e);
    return null;
  }
}

const VISITORS_QUERY = {
  dateRanges: [{ startDate: "14daysAgo", endDate: "yesterday" }],
  dimensions: [{ name: "date" }],
  metrics: [{ name: "activeUsers" }, { name: "screenPageViews" }],
};

/* 直近14日（昨日まで）の日ごとの閲覧者数。データのない日は 0 で埋める。
 * res: 先にまとめて取ってあれば、その返事（なければここで取りに行く）。propertyId: そのサイトの GA4 のプロパティ ID */
function visitorStats(res, propertyId) {
  const r = res ? gaParse(res) : gaReport(VISITORS_QUERY, propertyId);
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

/* グラフの画像（QuickChart）。日本語の文字化けを避けるため、グラフの中は数字と日付だけにする。線の色はサイトの色 */
function chartUrl(st, site) {
  const c = site.color;
  const fill = "rgba(" + [1, 3, 5].map((k) => parseInt(c.slice(k, k + 2), 16)).join(",") + ",0.12)";
  const cfg = {
    type: "line",
    data: {
      labels: st.days.map((d) => d.label),
      datasets: [
        { data: st.days.map((d) => d.users), borderColor: c, backgroundColor: fill, fill: true, cubicInterpolationMode: "monotone", pointRadius: 6, pointBackgroundColor: c, borderWidth: 4 },
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

function chartMessage(st, site) {
  const url = chartUrl(st, site);
  return { type: "image", originalContentUrl: url, previewImageUrl: url };
}

/* LINE の「グラフ」: サイトを選ぶボタンを出す（アナリティクスを付けたサイトが1つだけなら、すぐそのグラフ）。
 * 「グラフ 簿記」のようにサイトの名前を付けると、そのサイトのグラフ */
function chartReply(word) {
  const sites = SITES.filter(siteGa);
  if (!sites.length) return TALK.gaOff;
  let site = sites.length === 1 ? sites[0] : null;
  if (word) {
    site = findSite(word);
    if (!site) return TALK.siteUnknown(word, sites.map((s) => s.short));
    if (!siteGa(site)) return TALK.chartNoGa(site.name);
  }
  if (!site) {
    const items = sites.map((s) => ({ type: "action", action: { type: "message", label: s.short, text: "グラフ " + s.short } }));
    return { type: "text", text: TALK.chartPick(SITES.filter((s) => !siteGa(s)).map((s) => s.short)), quickReply: { items } };
  }
  const st = visitorStats(null, siteGa(site));
  if (!st) return TALK.gaError;
  return [TALK.chartText(site.name, st.week, st.week - st.prevWeek), chartMessage(st, site)];
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

/* Search Console: 直近10日分を日ごとに取り、データがある最新の日と直近7日を出す */
function searchRequest(site) {
  const day = (n) => fmt(new Date(Date.now() - n * 86400000), "yyyy-MM-dd");
  return {
    url: "https://searchconsole.googleapis.com/webmasters/v3/sites/" + encodeURIComponent(site.url) + "/searchAnalytics/query",
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
    payload: JSON.stringify({ startDate: day(10), endDate: day(1), dimensions: ["date"] }),
  };
}

function searchStats(site, res) {
  try {
    res = res || fetchAll([searchRequest(site)])[0];
    if (res.getResponseCode() !== 200) {
      console.warn("Search Console: " + res.getResponseCode() + " " + res.getContentText().slice(0, 300));
      return { error: true };
    }
    const rows = (JSON.parse(res.getContentText()).rows || [])
      .map((r) => ({ date: Number(r.keys[0].slice(5, 7)) + "/" + Number(r.keys[0].slice(8, 10)), key: r.keys[0], clicks: r.clicks, impressions: r.impressions }))
      .sort((a, b) => (a.key < b.key ? -1 : 1));
    if (!rows.length) return {};
    const week = rows.slice(-7).reduce((t, r) => ({ clicks: t.clicks + r.clicks, impressions: t.impressions + r.impressions }), { clicks: 0, impressions: 0 });
    return { latest: rows[rows.length - 1], week };
  } catch (e) {
    console.warn(e);
    return { error: true };
  }
}

/* サイトが開けるか（トップページ） */
function healthRequest(site) {
  return { url: site.url, followRedirects: true };
}

function siteHealth(site, res) {
  try {
    const code = (res || fetchAll([healthRequest(site)])[0]).getResponseCode();
    return code === 200 ? { ok: true } : { ok: false, why: "エラー " + code };
  } catch (e) {
    return { ok: false, why: "つながらない" };
  }
}

/* 最後の更新: GitHub の更新フィード（Atom）を読む。API は Apps Script からだと回数制限にかかりやすいため */
function updateRequest(site) {
  return { url: "https://github.com/" + site.repo + "/commits/main.atom" };
}

function lastUpdate(site, res) {
  try {
    res = res || fetchAll([updateRequest(site)])[0];
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

/* ---------- サイトの点検（全サイト。GitHub の自動実行が毎週月曜に点検して、結果を check-results のブランチに置く） ---------- */
function checkRequest() {
  return { url: CONFIG.checkUrl + "?t=" + Date.now() };
}

/* 結果を読む: { data } / { none: true }（まだ結果がない） / { error: true } */
function checkResult(res) {
  try {
    res = res || fetchAll([checkRequest()])[0];
    const code = res.getResponseCode();
    if (code === 404) return { none: true };
    if (code !== 200) return { error: true };
    return { data: JSON.parse(res.getContentText()) };
  } catch (e) {
    console.warn(e);
    return { error: true };
  }
}

const checkPage = (site, page) => (page || "").replace(site.url, "/");

/* 結果のまとめ（数行）。問題があれば、はじめの3件を出す */
function checkSummary(d) {
  const s = d.summary, date = fmt(new Date(d.checked_at), "M/d");
  if (!s.problems && !s.warnings) return TALK.checkOk(date, s.sites, s.pages);
  if (!s.problems) return TALK.checkWarnOnly(date, s.warnings);
  const items = [];
  d.sites.forEach((site) => site.items.filter((i) => i.level === "問題").forEach((i) => items.push(TALK.checkItem(site.name, i.kind, checkPage(site, i.page)))));
  return [TALK.checkNg(date, s.problems, s.warnings), ...items.slice(0, 3), TALK.checkMore].join("\n");
}

/* 毎朝のレポートの【サイトの点検】の欄。新しい結果が出た朝に1回だけ出す。
 * 点検の曜日（月曜）は、結果が取れない・古いときも知らせる */
function checkSection(res) {
  const r = checkResult(res);
  const monday = new Date(fmt(new Date(), "yyyy/MM/dd")).getDay() === CONFIG.chartWeekday;
  if (r.data) {
    const days = Math.floor((Date.now() - new Date(r.data.checked_at).getTime()) / 86400000);
    if (r.data.checked_at !== prop("CHECK_SEEN")) {
      PROPS.setProperty("CHECK_SEEN", r.data.checked_at);
      return checkSummary(r.data);
    }
    return monday && days >= CONFIG.checkStaleDays ? TALK.checkStale(days) : "";
  }
  if (!monday) return "";
  return r.none ? TALK.checkNone : TALK.checkError;
}

/* LINE の「点検」: サイトごとの問題・注意（1サイト5件まで） */
function checkDetailText() {
  if (!CONFIG.checkUrl) return TALK.checkOff;
  const r = checkResult();
  if (!r.data) return r.none ? TALK.checkNone : TALK.checkError;
  const d = r.data, lines = [TALK.checkDetailHead(fmt(new Date(d.checked_at), "M/d"), d.summary)];
  const ok = [];
  d.sites.forEach((site) => {
    const shown = site.items.filter((i) => i.level !== "情報");
    if (!shown.length) { ok.push(site.name); return; }
    lines.push("", `■ ${site.name}（問題 ${site.problems}・注意 ${site.warnings}）`);
    shown.slice(0, 5).forEach((i) => lines.push(`・[${i.level}] ${i.kind}` + (i.page ? `: ${checkPage(site, i.page)}` : "") + (i.detail ? `\n  ${String(i.detail).slice(0, 70)}` : "")));
    if (shown.length > 5) lines.push(`  ほか ${shown.length - 5} 件`);
  });
  if (ok.length) lines.push("", TALK.checkDetailOk(ok));
  lines.push("", TALK.checkDetailFoot(d.result_url));
  return lines.join("\n");
}
