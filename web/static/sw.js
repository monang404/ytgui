
const CACHE_VERSION = 'bagas-fm-20260701_1723';
const STATIC_CACHE = `${CACHE_VERSION}-static`;

const PRECACHE_ASSETS = [
    '/',
    '/static/css/tokens.css',
    '/static/css/base/reset.css',
    '/static/css/base/typography.css',
    '/static/css/base/animations.css',
    '/static/css/layout/app-shell.css',
    '/static/css/layout/nav.css',
    '/static/css/layout/grid.css',
    '/static/css/components/player-bar.css',
    '/static/css/components/player-controls.css',
    '/static/css/components/queue.css',
    '/static/css/components/search.css',
    '/static/css/components/settings-sheet.css',
    '/static/css/components/lyrics.css',
    '/static/css/components/cards.css',
    '/static/css/components/toasts.css',
    '/static/css/portal.css',
    '/static/css/platform/mobile.css',
    '/static/css/platform/tablet.css',
    '/static/css/platform/desktop.css',
    '/static/css/platform/landscape.css',
    '/static/css/platform/safe-area.css',
    '/static/js/main.js',
    '/static/js/store.js',
    '/static/js/dom.js',
    '/static/js/config.js',
    '/static/js/ws.js',
    '/static/js/audio.js',
    '/static/js/utils.js',
    '/static/js/portal.js',
    '/static/js/events/index.js',
    '/static/js/events/player-events.js',
    '/static/js/events/queue-events.js',
    '/static/js/events/settings-events.js',
    '/static/js/events/lyrics-events.js',
    '/static/js/services/auth.js',
    '/static/js/render/player.js',
    '/static/js/render/now-playing.js',
    '/static/js/render/queue.js',
    '/static/js/render/search.js',
    '/static/js/render/discover.js',
    '/static/js/render/favorites.js',
    '/static/js/render/lyrics.js',
    '/static/js/platform/keyboard.js',
    '/static/js/platform/touch.js',
    '/static/js/platform/viewport.js',
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
