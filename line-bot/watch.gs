/* FE用語ドリル 運用LINE: 試験の変更とカレンダー（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- 試験の変更の見張り（GitHub の自動実行が毎朝、試験の主催者などのページを見て、結果を watch-results のブランチに置く） ---------- */
function watchRequest() {
  return { url: CONFIG.watchUrl + "?t=" + Date.now() };
}

/* 結果を読む: { data } / { none: true }（まだ結果がない） / { error: true } */
function watchResult(res) {
  try {
    res = res || fetchAll([watchRequest()])[0];
    const code = res.getResponseCode();
    if (code === 404) return { none: true };
    if (code !== 200) return { error: true };
    return { data: JSON.parse(res.getContentText()) };
  } catch (e) {
    console.warn(e);
    return { error: true };
  }
}

const siteShort = (key) => (SITES.find((s) => s.key === key) || { short: key }).short;
const watchSites = (c) => c.sites.map(siteShort).join("・");

/* 1件の変更（増えた・消えた行をいくつか） */
function watchChangeText(c, n) {
  const lines = [TALK.watchChange(fmt(new Date(c.found_at), "M/d"), watchSites(c), c.name)];
  c.added.slice(0, n).forEach((x) => lines.push("  ＋ " + x.slice(0, 60)));
  c.removed.slice(0, n).forEach((x) => lines.push("  － " + x.slice(0, 60)));
  const more = c.added_n + c.removed_n - Math.min(n, c.added.length) - Math.min(n, c.removed.length);
  if (more > 0) lines.push(TALK.watchMoreLines(more));
  return lines.join("\n");
}

/* 毎朝のレポートの【試験の変更】の欄。前に読んだときより新しい変更だけを出す。
 * 取れないページは月曜だけ、結果が古い・取れないときも月曜だけ知らせる */
function watchSection(res) {
  const r = watchResult(res);
  const monday = new Date(fmt(new Date(), "yyyy/MM/dd")).getDay() === CONFIG.chartWeekday;
  const lines = [];
  if (r.data) {
    const seen = prop("WATCH_SEEN");
    const fresh = r.data.changes.filter((c) => !seen || c.found_at > seen);
    if (r.data.changes.length) PROPS.setProperty("WATCH_SEEN", r.data.changes[0].found_at);
    else if (!seen) PROPS.setProperty("WATCH_SEEN", r.data.checked_at);
    if (fresh.length) {
      lines.push(TALK.watchNew(fresh.length));
      fresh.slice(0, 3).forEach((c) => lines.push(watchChangeText(c, 2)));
      if (fresh.length > 3) lines.push(TALK.watchMore(fresh.length - 3));
      lines.push(TALK.watchFoot);
    }
    const days = Math.floor((Date.now() - new Date(r.data.checked_at).getTime()) / 86400000);
    if (monday && days >= CONFIG.watchStaleDays) lines.push(TALK.watchStale(days));
    if (monday && r.data.errors.length) lines.push(TALK.watchErrors(r.data.errors.map((e) => e.name)));
  } else if (monday) lines.push(r.none ? TALK.watchNone : TALK.watchError);
  return lines.join("\n");
}

/* LINE の「試験」: 直近30日の変更と、これからの試験の予定 */
function watchDetailText() {
  const lines = [];
  if (!CONFIG.watchUrl) lines.push(TALK.watchOff);
  else {
    const r = watchResult();
    if (!r.data) lines.push(r.none ? TALK.watchNone : TALK.watchError);
    else {
      const d = r.data;
      lines.push(TALK.watchDetailHead(fmt(new Date(d.checked_at), "M/d"), d.pages, d.changes.length));
      d.changes.slice(0, 5).forEach((c) => lines.push("", watchChangeText(c, 3)));
      if (d.changes.length > 5) lines.push("", TALK.watchMore(d.changes.length - 5));
      if (d.errors.length) lines.push("", TALK.watchErrors(d.errors.map((e) => e.name)));
      if (d.result_url) lines.push("", TALK.watchDetailFoot(d.result_url));
    }
  }
  const soon = upcomingExams(CONFIG.examListDays);
  lines.push("", soon.length ? TALK.examHead(CONFIG.examListDays) : TALK.examNone(CONFIG.examListDays));
  soon.forEach((x) => lines.push(TALK.examLine(examDateText(x), siteShort(x.site), x.title)));
  return lines.join("\n");
}

/* ---------- 試験の予定（config.gs の EXAM_DATES） ---------- */
const ymd = (s) => new Date(s.replace(/-/g, "/"));
const today0 = () => new Date(fmt(new Date(), "yyyy/MM/dd"));
const examDateText = (x) => fmt(ymd(x.date), "M/d") + (x.end ? "〜" + fmt(ymd(x.end), "M/d") : "");

/* 今日から days 日のうちに始まる（または続いている）予定。日付の順 */
function upcomingExams(days) {
  const t = today0().getTime(), until = t + days * 86400000;
  return EXAM_DATES.filter((x) => ymd(x.end || x.date).getTime() >= t && ymd(x.date).getTime() <= until)
    .sort((a, b) => ymd(a.date) - ymd(b.date));
}

/* 毎朝のレポートの1行: あと N 日の予定（CONFIG.examNoticeDays の日だけ） と、月に1回の用語の確認の日 */
function examNotices() {
  const t = today0().getTime(), out = [];
  EXAM_DATES.forEach((x) => {
    const n = Math.round((ymd(x.date).getTime() - t) / 86400000);
    if (CONFIG.examNoticeDays.includes(n)) out.push(n ? TALK.examSoon(n, examDateText(x), siteShort(x.site), x.title) : TALK.examToday(siteShort(x.site), x.title));
  });
  if (today0().getDate() === CONFIG.termReviewDay) out.push(TALK.termReviewDay);
  return out;
}

/* ---------- Google カレンダー（スクリプトの持ち主のカレンダーに「用語ドリルの運用」というカレンダーを作って入れる） ---------- */
function calendarReady() {
  return !!CONFIG.calendarName;
}

function opsCalendar() {
  const id = prop("CAL_ID");
  let cal = id ? CalendarApp.getCalendarById(id) : null;
  if (!cal) cal = CalendarApp.getCalendarsByName(CONFIG.calendarName)[0] || CalendarApp.createCalendar(CONFIG.calendarName);
  PROPS.setProperty("CAL_ID", cal.getId());
  return cal;
}

/* 終日の予定を入れる。前に入れたもの（key）は入れない。前もって知らせる日は CONFIG.calendarRemindDays */
function calendarAdd(cal, done, key, title, start, end, desc, remind) {
  if (done.includes(key)) return false;
  const ev = end ? cal.createAllDayEvent(title, start, new Date(end.getTime() + 86400000), { description: desc })
    : cal.createAllDayEvent(title, start, { description: desc });
  if (remind) {
    ev.removeAllReminders();
    CONFIG.calendarRemindDays.forEach((d) => ev.addPopupReminder(d * 1440 - 9 * 60));   // d 日前の朝9時（終日の予定は、その日の0時から数える）
  }
  done.push(key);
  return true;
}

/* 毎朝、カレンダーをそろえる: 試験の予定・見直す予定（試験の変更）・月に1回の用語の確認。入れた数を返す */
function calendarSync(watchData) {
  if (!calendarReady()) return 0;
  const done = jsonProp("CAL_DONE", []);
  const cal = opsCalendar();
  let n = 0;
  const t = today0().getTime();
  EXAM_DATES.forEach((x) => {
    if (ymd(x.end || x.date).getTime() < t) return;
    if (calendarAdd(cal, done, "exam:" + x.key, `【${siteShort(x.site)}】${x.title}`, ymd(x.date), x.end ? ymd(x.end) : null,
      TALK.calExamDesc(x.note || ""), true)) n++;
  });
  (watchData ? watchData.changes : []).forEach((c) => {
    const desc = [TALK.calWatchDesc(c.name, c.url), ...c.added.map((x) => "＋ " + x), ...c.removed.map((x) => "－ " + x)].join("\n");
    if (calendarAdd(cal, done, "watch:" + c.id + ":" + c.found_at, TALK.calWatchTitle(watchSites(c), c.name), ymd(c.found_at.slice(0, 10)), null, desc, false)) n++;
  });
  if (!done.includes("term-review")) {
    const first = today0(), late = first.getDate() > CONFIG.termReviewDay;
    first.setDate(1);   // 先に1日にしてから月を進める（31日に月を進めると、次の次の月になるため）
    if (late) first.setMonth(first.getMonth() + 1);
    first.setDate(CONFIG.termReviewDay);
    const rule = CalendarApp.newRecurrence().addMonthlyRule().onlyOnMonthDay(CONFIG.termReviewDay);
    cal.createAllDayEventSeries(TALK.calReviewTitle, first, rule, { description: TALK.calReviewDesc });
    done.push("term-review");
    n++;
  }
  PROPS.setProperty("CAL_DONE", JSON.stringify(done.slice(-300)));
  return n;
}

/* エディタで実行して、カレンダーに入るか確かめる */
function testCalendar() {
  const r = CONFIG.watchUrl ? watchResult() : {};
  Logger.log("カレンダー「" + CONFIG.calendarName + "」に " + calendarSync(r.data) + " 件入れました");
}
