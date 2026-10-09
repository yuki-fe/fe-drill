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
  // 時間のかかる問い合わせは、先にまとめて同時に取りに行く
  const reqs = { search: searchRequest(), update: updateRequest() };
  if (gaReady()) Object.assign(reqs, { visitors: gaRequest(VISITORS_QUERY), igVisitors: gaRequest(IG_VISITORS_QUERY) });
  const pre = fetchNamed(reqs);
  if (gaReady()) {
    const st = visitorStats(pre.visitors);
    lines.push("【閲覧者】");
    if (!st) lines.push(TALK.gaError);
    else {
      const y = st.days[st.days.length - 1];
      lines.push(TALK.visitorsDay(y.users, y.views), TALK.visitorsWeek(st.week, st.week - st.prevWeek));
      const ig = igVisitorStats(pre.igVisitors);
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
  const s = searchStats(pre.search);
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
  const u = lastUpdate(pre.update);
  lines.push("", "【最後の更新】", u ? TALK.updated(u.date, u.message) : TALK.updatedUnknown);
  const n = openInquiries().length;
  lines.push("", "【お問い合わせ】", n ? TALK.inquirySome(n) : TALK.inquiryNone);
  return lines.join("\n");
}

/* ---------- 閲覧者（Google アナリティクス 4） ---------- */
function gaReady() {
  return !!prop("GA_PROPERTY_ID");
}

function gaRequest(body) {
  return {
    url: "https://analyticsdata.googleapis.com/v1beta/properties/" + prop("GA_PROPERTY_ID") + ":runReport",
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

function gaReport(body) {
  try {
    return gaParse(fetchAll([gaRequest(body)])[0]);
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
 * res: 先にまとめて取ってあれば、その返事（なければここで取りに行く） */
function visitorStats(res) {
  const r = res ? gaParse(res) : gaReport(VISITORS_QUERY);
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
function searchRequest() {
  const day = (n) => fmt(new Date(Date.now() - n * 86400000), "yyyy-MM-dd");
  return {
    url: "https://searchconsole.googleapis.com/webmasters/v3/sites/" + encodeURIComponent(CONFIG.siteUrl) + "/searchAnalytics/query",
    method: "post", contentType: "application/json",
    headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() },
    payload: JSON.stringify({ startDate: day(10), endDate: day(1), dimensions: ["date"] }),
  };
}

function searchStats(res) {
  try {
    res = res || fetchAll([searchRequest()])[0];
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
function updateRequest() {
  return { url: "https://github.com/" + CONFIG.githubRepo + "/commits/main.atom" };
}

function lastUpdate(res) {
  try {
    res = res || fetchAll([updateRequest()])[0];
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
