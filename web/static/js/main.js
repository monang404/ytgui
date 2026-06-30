(function () {
    "use strict";

    function init() {
        // FIX BUG-1: set data-active-tab SEBELUM DOM diinit supaya CSS selector
        // body:not([data-active-tab="home"]) tidak aktif saat #app pertama muncul.
        // Tanpa ini, player-bar jadi position:absolute dan menutupi navbar.
        document.body.dataset.activeTab = (typeof store !== "undefined" && store.active_tab)
            ? store.active_tab
            : "home";
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


// ── Service Worker Registration — Phase 6 ──
// DISABLED selama development — biar nggak ke-cache stale.
// Aktifkan lagi kalau sudah siap "production" (uncomment di bawah).
// if ('serviceWorker' in navigator) {
//     window.addEventListener('load', () => {
//         navigator.serviceWorker.register('/static/sw.js')
//             .then(reg => console.log('SW registered:', reg.scope))
//             .catch(err => console.warn('SW registration failed:', err));
//     });
// }
    
