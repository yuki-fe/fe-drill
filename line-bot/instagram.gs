/* FE用語ドリル 運用LINE: Instagram（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- Instagram（下書き → 素材を受け取って、運営者がアプリで投稿） ---------- */
function igReady() {
  return !!(prop("IG_TOKEN") && prop("IG_USER_ID"));
}

/* 今日の投稿の種類（下書きの「種類を変える」で変えたら、その日はそれを使う） */
function kindToday() {
  const o = jsonProp("IG_KIND_TODAY", null);
  if (o && o.date === fmt(new Date(), "yyyy-MM-dd") && IG_KINDS[o.kind]) return o.kind;
  return CONFIG.rotation[new Date(fmt(new Date(), "yyyy/MM/dd")).getDay()] || "term";
}

function setKindToday(kind) {
  PROPS.setProperty("IG_KIND_TODAY", JSON.stringify({ date: fmt(new Date(), "yyyy-MM-dd"), kind }));
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
      qr("素材を受け取る", "ig=kit&" + d),
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

/* 「素材を受け取る」: 自分でアプリから投稿する（音楽を付けるなど）ための一式を、保存・コピーしやすいように別々の吹き出しで送る。
 * 返信なので無料。投稿したら最後の吹き出しの「投稿した」で次へ進める */
function igKit(kind, p) {
  const media = kind === "reel"
    ? [{ type: "video", originalContentUrl: p.video, previewImageUrl: p.cover }, { type: "image", originalContentUrl: p.cover, previewImageUrl: p.cover }]
    : p.images.map((url) => ({ type: "image", originalContentUrl: url, previewImageUrl: url }));
  const d = `k=${kind}&id=${postId(p, kind)}`;
  return media.concat([
    kind === "reel" ? TALK.igKitReel : TALK.igKitImages,
    p.caption,
    { type: "text", text: PIN_COMMENTS[kind] || TALK.igKitFoot, quickReply: { items: [qr("投稿した", "ig=done&" + d)] } },
  ]);
}

/* 「投稿した」: 手で投稿したものを記録して、次の下書きへ進める。リールは YouTube 用のセットも返す */
function igManualDone(kind, p) {
  igAdvance(kind);
  if (kind !== "reel") return TALK.igManualDone;
  return [TALK.igManualDone].concat(ytKitMessages(p));
}

/* 下書き・素材のボタン（postback の ig=…）。id が今の下書きと違えば、前の下書きのボタン */
function igAction(action, kind, id) {
  if (!igReady()) return TALK.igOff;
  kind = IG_KINDS[kind] ? kind : "term";
  const K = IG_KINDS[kind];
  const cur = igCurrent(kind);
  if (!cur) return TALK.igEmpty(K.label, K.maker);
  if (id && id !== postId(cur, kind)) return TALK.igStale;
  if (action === "kit") return igKit(kind, cur);
  if (action === "done") return igManualDone(kind, cur);
  if (action === "next") { igAdvance(kind); return igDraftMessage(TALK.igNext, kind); }
  if (action === "kind") {
    const order = Object.keys(IG_KINDS);
    const nk = order[(order.indexOf(kind) + 1) % order.length];
    setKindToday(nk);
    return igDraftMessage(TALK.igKindChanged(IG_KINDS[nk].label), nk);
  }
  return TALK.igSkipped;   // 「今日はやめる」と、前にあった「今すぐ投稿」などのボタン
}

function igCall(path, params, method) {
  const opts = { method: method || "post", muteHttpExceptions: true };
  if (params) opts.payload = Object.assign({ access_token: prop("IG_TOKEN") }, params);
  return igParse(UrlFetchApp.fetch(params ? CONFIG.instagramApi + path : igUrl(path), opts));
}

/* 読み取り用の URL（合言葉付き）。fetchAll でまとめて取りに行くときにも使う */
function igUrl(path) {
  const sep = path.indexOf("?") >= 0 ? "&" : "?";
  return CONFIG.instagramApi + path + sep + "access_token=" + encodeURIComponent(prop("IG_TOKEN"));
}

function igParse(res) {
  const json = JSON.parse(res.getContentText() || "{}");
  if (json.error) throw new Error(json.error.message || "Instagram API エラー");
  return json;
}

/* 最近の投稿の一覧。数字とコメントの両方で使うので、1回の実行の中では取り直さない */
let igMediaCache = null;
function igMediaList(count) {
  if (!igMediaCache || igMediaCache.count < count) {
    const list = igCall(`/${prop("IG_USER_ID")}/media?fields=id,caption,timestamp,like_count,comments_count&limit=${count}`, null, "get").data || [];
    igMediaCache = { count, list };
  }
  return igMediaCache.list.slice(0, count);
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

/* YouTube ショート用: 説明・タイトル・本文を別々の吹き出しにして、長押しでコピーしやすくする */
function ytKitMessages(p) {
  return [TALK.ytKitHead(p.video), p.youtube.title, p.youtube.description];
}

/* ---------- Instagram のコメント ---------- */
function igComments(sinceMs) {
  const list = igMediaList(5);
  const me = igUsername();
  // 投稿ごとのコメントは、まとめて同時に取りに行く
  const res = fetchAll(list.map((m) => ({ url: igUrl(`/${m.id}/comments?fields=id,text,username,timestamp&limit=20`) })));
  const out = [];
  list.forEach((m, i) => {
    (igParse(res[i]).data || []).forEach((c) => {
      const t = new Date(c.timestamp).getTime();
      if (t > sinceMs && c.username !== me) out.push({ user: c.username || "?", text: String(c.text || ""), label: postLabel(m), t });
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

/* Instagram から来た閲覧者（参照元に instagram を含むものか「ig」。目印付きリンク、アプリ内ブラウザの l.instagram.com、Instagram が自分で付ける目印のどれも） */
const IG_VISITORS_QUERY = {
  dateRanges: [{ startDate: "14daysAgo", endDate: "yesterday" }],
  dimensions: [{ name: "date" }],
  metrics: [{ name: "activeUsers" }],
  // Instagram はプロフィールのリンクに自分で utm_source=ig を付けるので、「ig」ちょうども数える
  dimensionFilter: { orGroup: { expressions: [
    { filter: { fieldName: "sessionSource", stringFilter: { matchType: "CONTAINS", value: "instagram", caseSensitive: false } } },
    { filter: { fieldName: "sessionSource", stringFilter: { matchType: "EXACT", value: "ig", caseSensitive: false } } },
  ] } },
};

/* FE のサイトの、Instagram から来た閲覧者。res: 先にまとめて取ってあれば、その返事（なければここで取りに行く） */
function igVisitorStats(res) {
  if (!gaReady()) return null;
  const r = res ? gaParse(res) : gaReport(IG_VISITORS_QUERY, siteGa(mainSite()));
  if (!r) return null;
  const byDate = {};
  (r.rows || []).forEach((row) => { byDate[row.dimensionValues[0].value] = Number(row.metricValues[0].value); });
  const days = [];
  for (let n = 14; n >= 1; n--) days.push(byDate[fmt(new Date(Date.now() - n * 86400000), "yyyyMMdd")] || 0);
  const sum = (a) => a.reduce((t, x) => t + x, 0);
  return { yesterday: days[13], week: sum(days.slice(7)), prevWeek: sum(days.slice(0, 7)) };
}

function postLabel(m) {
  const first = String(m.caption || "").split("\n")[0].replace(/[【】]/g, "");
  return first.length > 18 ? first.slice(0, 18) + "…" : first || "（投稿文なし）";
}

/* 投稿ごとの数字。全部の投稿をまとめて同時に取りに行く。API のバージョンによって使える指標が違うので、
 * だめだった投稿だけ少ない指標で取り直す。取れなかった投稿は null にし、理由を igInsightsError に残す（LINE の知らせに出す） */
let igInsightsError = "";
function igMediaStatsAll(list) {
  const out = list.map(() => null);
  for (const metrics of ["reach,saved,likes,comments,shares", "reach,saved"]) {
    const todo = list.map((m, i) => i).filter((i) => !out[i]);
    if (!todo.length) break;
    const res = fetchAll(todo.map((i) => ({ url: igUrl(`/${list[i].id}/insights?metric=${metrics}`) })));
    todo.forEach((i, j) => {
      try {
        const v = {};
        (igParse(res[j]).data || []).forEach((x) => { v[x.name] = x.values && x.values[0] ? Number(x.values[0].value) : Number(x.total_value && x.total_value.value) || 0; });
        const m = list[i];
        out[i] = {
          reach: v.reach || 0, saved: v.saved || 0,
          likes: v.likes !== undefined ? v.likes : m.like_count || 0,
          comments: v.comments !== undefined ? v.comments : m.comments_count || 0,
        };
      } catch (e) {
        console.warn("Instagram insights: " + e.message);
        igInsightsError = e.message;
      }
    });
  }
  return out;
}

/* 最近の投稿（新しい順）と、それぞれの数字 */
function igRecent(count) {
  const list = igMediaList(count);
  const stats = igMediaStatsAll(list);
  return list.map((m, i) => ({ m, stats: stats[i] }));
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
      const date = fmt(new Date(latest.m.timestamp), "M/d");
      // リーチ・保存（insights）が取れなくても、いいね・コメントとフォロワーは出す
      if (latest.stats) lines.push(TALK.igStatsPost(date, postLabel(latest.m), latest.stats));
      else lines.push(TALK.igStatsBasic(date, postLabel(latest.m), latest.m.like_count || 0, latest.m.comments_count || 0), TALK.igStatsError(igInsightsError));
      const others = recent.slice(1).filter((x) => x.stats);
      if (latest.stats && others.length >= 3) {
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
    return TALK.igStatsError(e.message);
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
        (s ? `リーチ ${s.reach}／いいね ${s.likes}／保存 ${s.saved}／コメント ${s.comments}` : `いいね ${x.m.like_count || 0}／コメント ${x.m.comments_count || 0}（リーチ・保存は取れなかった）`);
    })).concat(recent.some((x) => !x.stats) ? ["", TALK.igStatsError(igInsightsError)] : []).join("\n");
  } catch (e) {
    console.warn(e);
    return TALK.igStatsError(e.message);
  }
}
