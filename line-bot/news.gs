/* FE用語ドリル 運用LINE: ITニュース（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- ITニュース（Google ニュースの検索結果の RSS を読む） ---------- */
function selectedGenres() {
  return jsonProp("NEWS_GENRES", DEFAULT_GENRES);
}

function genreQuery(name) {
  return NEWS_GENRES[name] || name;
}

/* 1ジャンル分のニュース: [{ title, source, link }]。取れなかったときは null */
function fetchNews(name, count) {
  try {
    const q = encodeURIComponent(genreQuery(name) + " when:1d");
    const res = UrlFetchApp.fetch("https://news.google.com/rss/search?q=" + q + "&hl=ja&gl=JP&ceid=JP:ja", { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return null;
    const items = XmlService.parse(res.getContentText()).getRootElement().getChild("channel").getChildren("item");
    return items.slice(0, count).map((it) => {
      const source = it.getChildText("source") || "";
      let title = it.getChildText("title") || "";
      if (source && title.endsWith(" - " + source)) title = title.slice(0, -(source.length + 3));
      return { title, source, link: it.getChildText("link") };
    });
  } catch (e) {
    console.warn(e);
    return null;
  }
}

function newsText(genres, perGenre, head) {
  const blocks = [head];
  genres.forEach((g) => {
    const items = fetchNews(g, perGenre);
    blocks.push("", "■ " + g);
    if (items === null) blocks.push(TALK.newsError);
    else if (!items.length) blocks.push(TALK.newsNone);
    else items.forEach((n) => blocks.push(`・${n.title}${n.source ? "（" + n.source + "）" : ""}\n${n.link}`));
  });
  return blocks.join("\n");
}

function changeGenres(arg) {
  const sel = selectedGenres();
  let m;
  if ((m = arg.match(/^追加\s*(.+)$/))) {
    const g = m[1].trim();
    if (sel.length >= 5) return TALK.genreTooMany;
    if (sel.indexOf(g) < 0) sel.push(g);
    PROPS.setProperty("NEWS_GENRES", JSON.stringify(sel));
    return TALK.genreAdded(g);
  }
  if ((m = arg.match(/^(外す|削除|消す)\s*(.+)$/))) {
    const g = m[2].trim();
    if (sel.indexOf(g) < 0) return TALK.genreMissing(g);
    PROPS.setProperty("NEWS_GENRES", JSON.stringify(sel.filter((x) => x !== g)));
    return TALK.genreRemoved(g);
  }
  const list = arg.split(/[、,\s]+/).map((s) => s.trim()).filter(Boolean);
  if (list.length > 5) return TALK.genreTooMany;
  PROPS.setProperty("NEWS_GENRES", JSON.stringify(list));
  return TALK.genreSet(list);
}
