/* FE用語ドリル 運用LINE: ITニュース（ほかのファイルと合わせて1つのプログラム。分け方は config.gs の先頭） */

/* ---------- ITニュース（Google ニュースの検索結果の RSS を読む。毎朝のレポートに載せる） ---------- */
function selectedGenres() {
  return jsonProp("NEWS_GENRES", DEFAULT_GENRES);
}

function genreQuery(name) {
  return NEWS_GENRES[name] || name;
}

/* 1ジャンル分の、この24時間のニュース: [{ title, source, link }]。取れなかったときは null */
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
