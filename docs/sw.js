// FE用語ドリル のサービスワーカー（build.py が作る。直接編集しない）
const CACHE = "fe-drill-96e6118412";
const PRECACHE = ["./", "index.html", "offline.html", "app.html", "terms/index.html", "b/index.html", "b/trace.html", "b/fill.html", "b/notation.html", "b/security.html", "b/simulator.html", "favicon.svg", "icon-192.png", "manifest.webmanifest", "assets/app.js", "assets/b-data.js", "assets/b.js", "assets/fig.js", "assets/layout.css", "assets/pseudo.js", "assets/style.css", "assets/term.js", "assets/terms.js", "assets/typing.js"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const fonts = url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";
  if (url.origin !== location.origin && !fonts) return;            // アクセス解析などは、そのままネットへ
  if (url.pathname.includes("/ig/")) return;                       // 動画や SNS の画像は保存しない
  if (req.mode === "navigate") {                                   // ページ: ネット優先、だめなら保存したもの
    e.respondWith(fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then((r) => r || caches.match("offline.html"))));
    return;
  }
  e.respondWith(caches.match(req).then((hit) => {                  // CSS・JS・画像・フォント: 保存したものをすぐ、裏で新しく
    const net = fetch(req).then((res) => {
      if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => hit || caches.match(req, { ignoreSearch: true }));   // 電波がないときは、版の印が違っても保存したものを出す
    return hit || net;
  }));
});
