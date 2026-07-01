
const CACHE_VERSION = 'bagas-fm-20260627_1117-dev';
const STATIC_CACHE = `${CACHE_VERSION}-static`;

const PRECACHE_ASSETS = [
    '/',
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

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                return Promise.all(
                    PRECACHE_ASSETS.map(url => 
                        cache.add(url).catch(err => console.warn('Cache add failed for', url, err))
                    )
                );
            })
            .then(() => self.skipWaiting())
    );
});

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

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    if (url.pathname.startsWith('/ws') || url.pathname.startsWith('/api')) {
        return;
    }

    if (event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request).then(cached => {
                if (cached) return cached;
                return fetch(event.request).then(response => {
                    if (response.ok) {
                        const cloned = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(event.request, cloned));
                    }
                    return response;
                });
            }).catch(() => {
                if (event.request.headers.get('accept').includes('text/html')) {
                    return caches.match('/static/index.html');
                }
            })
        );
    }
});
