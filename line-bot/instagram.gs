/* FE用語ドリル 運用LINE: Instagram（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

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
