const CACHE = "mlo-static-v2";
const STATIC = [
  "/static/theme.css",
  "/static/theme.js",
  "/static/favicon.ico",
  "/static/apple-touch-icon.png",
  "/static/pwa-192.png",
  "/static/pwa-512.png"
];
self.addEventListener("install", e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || !new URL(e.request.url).pathname.startsWith("/static/")) return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => {
    const copy = r.clone();
    caches.open(CACHE).then(c => c.put(e.request, copy));
    return r;
  })));
});
