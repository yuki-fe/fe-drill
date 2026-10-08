/* FE用語ドリル 運用LINE: LINE（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- LINE から届いたメッセージ（Webhook） ---------- */
function doPost(e) {
  if (!e || !e.parameter || e.parameter.key !== prop("WEBHOOK_KEY")) return ok();
  const body = JSON.parse((e.postData && e.postData.contents) || "{}");
  (body.events || []).forEach((ev) => {
    try { handleEvent(ev); } catch (err) { console.error(err); }
  });
  return ok();
}

function ok() {
  return ContentService.createTextOutput("OK");
}

function handleEvent(ev) {
  const user = ev.source && ev.source.userId;
  const owner = prop("OWNER_USER_ID");
  if (ev.type === "follow") return reply(ev.replyToken, owner && owner !== user ? TALK.notOwner : TALK.greeting);
  if (ev.type === "postback") {
    if (!owner || user !== owner) return reply(ev.replyToken, TALK.notOwner);
    const data = {};
    ev.postback.data.split("&").forEach((kv) => { const [k, v] = kv.split("="); data[k] = v; });
    if (data.ig) return reply(ev.replyToken, igAction(data.ig, data.k || "term", data.id || data.no));
    return;
  }
  if (ev.type !== "message" || ev.message.type !== "text") return;
  const text = ev.message.text.normalize("NFKC").trim();
  if (!owner) {
    const m = text.match(/^登録\s*(\d+)$/);
    if (m && m[1] === prop("SETUP_CODE")) {
      PROPS.setProperty("OWNER_USER_ID", user);
      return reply(ev.replyToken, TALK.registered + TALK.help);
    }
    return reply(ev.replyToken, TALK.needRegister);
  }
  if (user !== owner) return reply(ev.replyToken, TALK.notOwner);
  reply(ev.replyToken, answer(text));
}

/* 文字列か、LINE のメッセージの形（クイックリプライ付きなど）を返す */
function answer(text) {
  let m;
  if (/^(状況|じょうきょう|レポート|様子)/.test(text)) return buildReport(false);
  if (/^(グラフ|ぐらふ|アクセス|閲覧者)/.test(text)) return chartReply();
  if (/^(人気|ランキング|にんき)/.test(text)) return rankingText();
  if (/^(問い合わせ|問合せ|といあわせ|お問い合わせ)/.test(text)) return listText();
  if ((m = text.match(/^(済|対応済み?|done)\s*(\d+)/i))) return markDone(Number(m[2]));
  if ((m = text.match(/^ニュース\s*投稿\s*([\d\s、,]*)$/))) {
    if (!igReady()) return TALK.igOff;
    const nums = (m[1].match(/\d+/g) || []).map(Number);
    return nums.length ? newsChoose(nums) : newsDraftMessage();
  }
  if ((m = text.match(/^ニュース\s*(.*)$/))) {
    const g = m[1].trim();
    return g ? newsText([g], 5, TALK.newsGenreHead(g)) : newsText(selectedGenres(), 3, TALK.newsHead);
  }
  if ((m = text.match(/^ジャンル\s*(.*)$/))) {
    return m[1].trim() ? changeGenres(m[1].trim()) : TALK.genreList(selectedGenres(), Object.keys(NEWS_GENRES));
  }
  if ((m = text.match(/^(インスタ|instagram|下書き)\s*(.*)$/i))) {
    if (!igReady()) return TALK.igOff;
    const k = kindFromWord(m[2]);
    if (k) setKindToday(k);
    return igDraftMessage(undefined, k || kindToday());
  }
  if (/^投稿(する)?$/.test(text)) return igAction("post", kindToday());
  if (/^(素材|そざい)/.test(text)) return igAction("kit", kindToday());
  if (/^紹介リール/.test(text)) return igIntroKit();
  if (/^紹介コメント/.test(text)) return igReady() ? igPinLatest() : TALK.igOff;
  if (/^(コメント|こめんと)/.test(text)) return igReady() ? igCommentsList() : TALK.igOff;
  if (/^(ユーチューブ|ゆーちゅーぶ|youtube)/i.test(text)) return ytKitReply();
  if (/^(反応|はんのう|インサイト)/.test(text)) return igReady() ? igRecentText() : TALK.igOff;
  if (/^(リンク|りんく)/.test(text)) return TALK.igLink(igProfileLink());
  if (/^(使い方|つかいかた|ヘルプ|help|\?)/i.test(text)) return TALK.help;
  return pick(TALK.unknown);
}

/* ---------- LINE へ送る ---------- */
function lineApi(path, payload) {
  const res = UrlFetchApp.fetch("https://api.line.me/v2/bot/message/" + path, {
    method: "post", contentType: "application/json", muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + prop("LINE_TOKEN") },
    payload: JSON.stringify(payload),
  });
  if (res.getResponseCode() !== 200) console.error("LINE " + path + ": " + res.getResponseCode() + " " + res.getContentText());
}

/* 文字列・メッセージ・その配列を、LINE のメッセージの配列（最大5つ）にそろえる */
function toMessages(x) {
  return [].concat(x).slice(0, 5).map((m) => {
    const msg = typeof m === "string" ? { type: "text", text: m } : m;
    if (msg.text && msg.text.length > 4900) msg.text = msg.text.slice(0, 4900) + "…";
    return msg;
  });
}

/* 返信（無料・送信数に数えられない） */
function reply(token, x) {
  if (token) lineApi("reply", { replyToken: token, messages: toMessages(x) });
}

/* こちらから送る（無料プランでは月200通まで。1回の送信で吹き出し5つまでを1通として数える） */
function push(x) {
  const to = prop("OWNER_USER_ID");
  if (to) lineApi("push", { to, messages: toMessages(x) });
}
