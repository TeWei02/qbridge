/* Offline shell for the QBridge demo.
 *
 * The simulator is a handful of static files, so a cache-first strategy is
 * enough: pages load from the cache, and the cache is refreshed in the
 * background on every version bump.
 */
var CACHE = "qbridge-v1";
var ASSETS = [
  ".",
  "index.html",
  "styles.css",
  "qbridge.js",
  "app.js",
  "reference.json",
  "manifest.json",
  "icon-192.png",
  "icon-512.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names.map(function (name) {
          return name === CACHE ? null : caches.delete(name);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then(function (cached) {
      var network = fetch(event.request)
        .then(function (response) {
          if (response && response.status === 200) {
            var copy = response.clone();
            caches.open(CACHE).then(function (cache) {
              cache.put(event.request, copy);
            });
          }
          return response;
        })
        .catch(function () {
          return cached;
        });
      return cached || network;
    })
  );
});
