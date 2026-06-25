(function () {
    "use strict";

    function init() {
        initDOM();
        initPortal();
        initAudio();
        initEvents();
        wsConnect();
    }

    window.switchTab = function(tab) {
        store.active_tab = tab;
        document.body.dataset.activeTab = tab;

        TABS.forEach((t) => {
            const panel = dom["tab" + t.charAt(0).toUpperCase() + t.slice(1)];
            if (panel) {
                if (t === tab) panel.classList.add("active");
                else panel.classList.remove("active");
            }
        });

        document.querySelectorAll(".nav-btn").forEach((btn) => {
            if (btn.dataset.tab === tab) btn.classList.add("active");
            else btn.classList.remove("active");
        });

        if (tab === "search") {
            setTimeout(() => dom.searchInput.focus(), 100);
        }
        if (tab === "discover" || tab === "home") {
            wsSend("discover");
        }
    };

    document.addEventListener("DOMContentLoaded", init);
})();

// ── Visual Viewport Handler (Mobile Keyboard) ──
// Mencegah layout terdorong saat keyboard virtual muncul di iOS/Android
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
        const app = document.getElementById('app');
        if (app) {
            app.style.height = window.visualViewport.height + 'px';
        }
    });
}

// ── Service Worker Registration — Phase 6 ──
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => console.log('SW registered:', reg.scope))
            .catch(err => console.warn('SW registration failed:', err));
    });
}
