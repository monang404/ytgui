// ── Service Worker — bagas.fm Phase 6 ──
// Strategy: Cache-first untuk static assets, network-first untuk API/WS

const CACHE_VERSION = 'bagas-fm-v6';
const STATIC_CACHE = `${CACHE_VERSION}-static`;

// Assets yang di-cache saat install
const PRECACHE_ASSETS = [
    '/',
    '/static/index.html',
    '/static/css/base.css',
    '/static/css/tokens.css',
    '/static/css/components.css',
    '/static/css/layout.css',
    '/static/css/player.css',
    '/static/css/tabs.css',
    '/static/css/portal.css',
    '/static/js/main.js',
    '/static/js/store.js',
    '/static/js/dom.js',
    '/static/js/ws.js',
    '/static/js/events.js',
    '/static/js/audio.js',
    '/static/js/utils.js',
    '/static/js/portal.js',
    '/static/js/render/player.js',
    '/static/js/render/tabs.js',
    '/static/js/render/lyrics.js',
    '/static/js/render/search.js',
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(PRECACHE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate: hapus cache lama
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(key => key !== STATIC_CACHE)
                    .map(key => caches.delete(key))
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch: cache-first untuk static, network-only untuk WS dan API
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip WebSocket dan API requests
    if (url.pathname.startsWith('/ws') || url.pathname.startsWith('/api')) {
        return; // Biarkan browser handle secara normal
    }

    // Cache-first untuk static assets
    if (event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request).then(cached => {
                if (cached) return cached;
                return fetch(event.request).then(response => {
                    // Cache response baru
                    if (response.ok) {
                        const cloned = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(event.request, cloned));
                    }
                    return response;
                });
            }).catch(() => {
                // Offline fallback
                if (event.request.headers.get('accept').includes('text/html')) {
                    return caches.match('/static/index.html');
                }
            })
        );
    }
});
