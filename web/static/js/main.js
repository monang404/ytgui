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
        if (tab === "discover") {
            wsSend("discover");
        }
    };

    document.addEventListener("DOMContentLoaded", init);
})();
