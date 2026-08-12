/* Cache-first for versioned /static/* assets. Scope is /static/. */
const CACHE_NAME = "nopaste-static-v1";

self.addEventListener("install", (event) => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) =>
            cache.addAll([
                "/static/css/style.css",
                "/static/js/app.js",
                "/static/fonts/inter-400.woff2",
                "/static/images/goldfinches_logo.png",
                "/static/images/favicon.png",
            ]).catch(() => undefined)
        )
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) =>
                Promise.all(
                    keys
                        .filter((key) => key.startsWith("nopaste-static-") && key !== CACHE_NAME)
                        .map((key) => caches.delete(key))
                )
            )
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") return;

    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) return;
    if (!url.pathname.startsWith("/static/")) return;
    if (url.pathname === "/static/sw.js") return;

    event.respondWith(
        caches.open(CACHE_NAME).then(async (cache) => {
            const cached = await cache.match(event.request);
            if (cached) return cached;
            const response = await fetch(event.request);
            if (response.ok) {
                cache.put(event.request, response.clone());
            }
            return response;
        })
    );
});
