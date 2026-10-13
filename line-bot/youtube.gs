/* FE用語ドリル 運用LINE: YouTube（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- YouTube の数字とコメント（読むだけ。投稿はアプリで手作業） ----------
 * YouTube Data API を、スクリプトの持ち主の Google アカウントの権限（youtube.readonly）で読む。
 * どのチャンネルを読むかは、スクリプト プロパティ YT_CHANNEL_ID（UC で始まる文字）。
 * setup を実行すると、持ち主のアカウントのチャンネルを探して自動で入れる。
 * コメントは youtube.readonly では読めないことがあるので、YT_API_KEY（API キー）があればそれで読む */
function ytReady() {
  return !!prop("YT_CHANNEL_ID");
}

function ytRequest(path) {
  return { url: "https://www.googleapis.com/youtube/v3/" + path, headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() } };
}

/* 公開されている情報を API キーで読む（キーがなければ、持ち主の権限で読む） */
function ytPublicRequest(path) {
  const key = prop("YT_API_KEY");
  return key ? { url: "https://www.googleapis.com/youtube/v3/" + path + "&key=" + encodeURIComponent(key) } : ytRequest(path);
}

/* 返事を読む。だめなときは、何を読もうとしたか（what）と、理由（YouTube のエラーの文）つきで止める */
function ytParse(res, what) {
  if (!res) throw new Error(what + ": 返事がなかった");
  const body = JSON.parse(res.getContentText() || "{}");
  if (res.getResponseCode() !== 200) throw new Error(what + ": " + ((body.error && body.error.message) || "エラー " + res.getResponseCode()));
  return body;
}

/* setup から呼ぶ: 持ち主のアカウントのチャンネルを探して YT_CHANNEL_ID に入れる。チャンネル名を返す */
function ytFindChannel() {
  const ch = (ytParse(fetchAll([ytRequest("channels?part=id,snippet&mine=true")])[0], "チャンネル").items || [])[0];
  if (!ch) throw new Error("このアカウントにはチャンネルがない");
  PROPS.setProperty("YT_CHANNEL_ID", ch.id);
  return ch.snippet.title;
}

/* エディタから実行して、YouTube を読めるか確かめる（LINE を使わない）。
 * 許可されている範囲と、問い合わせ1つずつの結果をログに出す（合言葉そのものは出さない） */
function testYouTube() {
  const res = UrlFetchApp.fetch("https://oauth2.googleapis.com/tokeninfo?access_token=" + ScriptApp.getOAuthToken(), { muteHttpExceptions: true });
  const info = JSON.parse(res.getContentText() || "{}");
  Logger.log("YouTube を読む許可: " + (String(info.scope || "").includes("youtube.readonly") ? "あり" : "なし（" + (info.scope || info.error_description || "不明") + "）"));
  Logger.log("チャンネル: " + (prop("YT_CHANNEL_ID") || "（YT_CHANNEL_ID がない）"));
  Logger.log("API キー（コメント用）: " + (prop("YT_API_KEY") ? "あり" : "なし"));
  if (!ytReady()) return;
  const reqs = ytRequests(5);
  const names = { ytChannel: "チャンネル", ytUploads: "動画の一覧", ytComments: "コメント" };
  const got = fetchNamed(reqs);
  Object.keys(names).forEach((k) => {
    try { ytParse(got[k], names[k]); Logger.log(names[k] + ": OK"); } catch (e) { Logger.log("× " + e.message); }
  });
  Logger.log(ytStatsText(false));
}

/* 最初にまとめて取りに行くもの（毎朝のレポートでは、ほかの数字と同時に取る） */
function ytRequests(count) {
  const id = prop("YT_CHANNEL_ID");
  return {
    ytChannel: ytRequest(`channels?part=statistics&id=${id}`),
    ytUploads: ytRequest(`playlistItems?part=contentDetails&maxResults=${count}&playlistId=UU${id.slice(2)}`),
    ytComments: ytPublicRequest(`commentThreads?part=snippet&allThreadsRelatedToChannelId=${id}&order=time&maxResults=20&textFormat=plainText`),
  };
}

/* 動画の名前: タイトルからハッシュタグを外して短くする */
const ytLabel = (title) => clip(String(title || "").replace(/#\S+/g, "").trim() || "（タイトルなし）", 18);

/* 登録者・最近の動画（新しい順）・コメント（新しい順）をまとめて取る。pre: 先に取ってあれば、その返事。
 * コメントだけ取れなかったときは comments を null にし、理由を commentsError に入れる（ほかの数字は出す） */
function ytCollect(count, pre) {
  const res = pre && pre.ytChannel ? pre : fetchNamed(ytRequests(count));
  const st = ((ytParse(res.ytChannel, "チャンネル").items || [])[0] || {}).statistics || {};
  const ids = (ytParse(res.ytUploads, "動画の一覧").items || []).map((it) => it.contentDetails.videoId);
  const me = prop("YT_CHANNEL_ID");
  let threads = [], commentsError = "";
  try {
    threads = (ytParse(res.ytComments, "コメント").items || []).map((t) => t.snippet.topLevelComment.snippet)
      .filter((c) => !(c.authorChannelId && c.authorChannelId.value === me));
  } catch (e) {
    console.warn("YouTube: " + e.message);
    commentsError = e.message;
  }
  // 動画の数字と、コメントが付いた動画の名前を、1回で取る
  const all = ids.concat(threads.map((c) => c.videoId).filter((v) => v && ids.indexOf(v) < 0));
  const byId = {};
  if (all.length) {
    (ytParse(fetchAll([ytRequest(`videos?part=snippet,statistics&id=${all.slice(0, 50).join(",")}`)])[0], "動画の数字").items || []).forEach((v) => {
      byId[v.id] = {
        label: ytLabel(v.snippet.title), date: v.snippet.publishedAt,
        views: Number(v.statistics.viewCount || 0), likes: Number(v.statistics.likeCount || 0), comments: Number(v.statistics.commentCount || 0),
      };
    });
  }
  return {
    subs: st.hiddenSubscriberCount ? null : Number(st.subscriberCount || 0),
    videos: ids.filter((v) => byId[v]).map((v) => byId[v]),
    comments: commentsError ? null : threads.map((c) => ({
      user: String(c.authorDisplayName || "?").replace(/^@/, ""), text: String(c.textOriginal || c.textDisplay || ""),
      label: (byId[c.videoId] || {}).label || "動画", t: new Date(c.publishedAt).getTime(),
    })),
    commentsError,
  };
}

/* 登録者数を1日1回記録して、前の記録との差を出す（非公開なら null） */
function ytSubscribers(n) {
  if (n === null) return { n: null, diff: null };
  const log = jsonProp("YT_SUBS", {});
  const today = fmt(new Date(), "yyyy-MM-dd");
  const before = Object.keys(log).filter((d) => d < today).sort();
  const diff = before.length ? n - log[before[before.length - 1]] : null;
  log[today] = n;
  Object.keys(log).sort().slice(0, -30).forEach((d) => delete log[d]);
  PROPS.setProperty("YT_SUBS", JSON.stringify(log));
  return { n, diff };
}

/* 毎朝のレポートの【YouTube】の欄。update: 毎朝だけ、コメントを「見た」記録を進める */
function ytStatsText(update, pre) {
  try {
    const d = ytCollect(5, pre);
    const lines = [];
    const v = d.videos[0];
    lines.push(v ? TALK.ytStatsVideo(fmt(new Date(v.date), "M/d"), v.label, v) : TALK.ytNoVideo);
    const s = ytSubscribers(d.subs);
    lines.push(TALK.ytSubs(s.n, s.diff));
    if (!d.comments) {
      lines.push(TALK.ytCommentsError(d.commentsError));
      return lines.join("\n");
    }
    const since = Number(prop("YT_COMMENTS_SEEN")) || Date.now() - 86400000;
    const fresh = d.comments.filter((c) => c.t > since);
    if (update) PROPS.setProperty("YT_COMMENTS_SEEN", String(Date.now()));
    if (fresh.length) lines.push(TALK.igCommentsNew(fresh.length), ...fresh.slice(0, 3).map((c) => TALK.igCommentLine(c.user, c.label, clip(c.text, 40))));
    return lines.join("\n");
  } catch (e) {
    console.warn("YouTube: " + e.message);
    return TALK.ytStatsError(e.message);
  }
}

/* LINE で「ユーチューブ 反応」: 最近5本の数字 */
function ytRecentText() {
  try {
    const d = ytCollect(5);
    if (!d.videos.length) return TALK.ytNoVideo;
    return [TALK.ytRecentHead, ""].concat(d.videos.map((v) =>
      `■ ${fmt(new Date(v.date), "M/d")}「${v.label}」\n再生 ${v.views}／高く評価 ${v.likes}／コメント ${v.comments}`)).join("\n");
  } catch (e) {
    console.warn(e);
    return TALK.ytStatsError(e.message);
  }
}

/* LINE で「ユーチューブ コメント」: この1週間のコメント */
function ytCommentsList() {
  try {
    const d = ytCollect(5);
    if (!d.comments) return TALK.ytCommentsError(d.commentsError);
    const list = d.comments.filter((c) => c.t > Date.now() - 7 * 86400000);
    if (!list.length) return TALK.ytCommentsNone;
    return [TALK.ytCommentsHead, ""].concat(list.slice(0, 10).map((c) => `${fmt(new Date(c.t), "M/d")} ` + TALK.igCommentLine(c.user, c.label, clip(c.text, 80)).slice(1))).join("\n");
  } catch (e) {
    console.warn(e);
    return TALK.ytStatsError(e.message);
  }
}
