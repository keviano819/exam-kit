const cacheName = "__CACHE_NAME__";
const appFiles = ["./", "./index.html", "./data.js", "./manifest.json"];
self.addEventListener("install", event => event.waitUntil(caches.open(cacheName).then(cache => cache.addAll(appFiles)).then(() => self.skipWaiting())));
self.addEventListener("activate", event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("__CACHE_PREFIX__") && key !== cacheName).map(key => caches.delete(key))).then(() => self.clients.claim()))
));
self.addEventListener("fetch", event => {
  const requestUrl = new URL(event.request.url);
  const knownFile = appFiles.some(file => new URL(file, self.registration.scope).pathname === requestUrl.pathname);
  if (event.request.method !== "GET" || requestUrl.origin !== self.location.origin || !knownFile) return;
  event.respondWith(caches.open(cacheName).then(async cache => {
    const cached = await cache.match(event.request, { ignoreSearch: true });
    return cached || fetch(event.request);
  }));
});
