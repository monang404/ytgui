(function () {
    "use strict";

    function init() {
        document.body.dataset.activeTab = (typeof store !== "undefined" && store.active_tab)
            ? store.active_tab
            : "home";
        initDOM();
        
        const initTab = document.body.dataset.activeTab;
        if (dom["tab" + initTab.charAt(0).toUpperCase() + initTab.slice(1)]) {
            dom["tab" + initTab.charAt(0).toUpperCase() + initTab.slice(1)].classList.add("active");
        }
        const navBtn = document.querySelector(`.nav-btn[data-tab="${initTab}"]`);
        if (navBtn) {
            navBtn.classList.add("active");
            navBtn.setAttribute("aria-selected", "true");
        }

        initPortal();
        initAudio();
        initEvents();
        wsConnect();
        
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(function(r) { console.log('SW registered'); })
                .catch(function(e) { console.error('SW failed', e); });
        }
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
            if (btn.dataset.tab === tab) {
                btn.classList.add("active");
                btn.setAttribute("aria-selected", "true");
            } else {
                btn.classList.remove("active");
                btn.setAttribute("aria-selected", "false");
            }
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


    
