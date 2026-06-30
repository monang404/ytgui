function initEvents() {
    document.querySelectorAll(".mood-card").forEach(card => {
        card.addEventListener("click", () => {
            const mood = card.getAttribute("data-mood");
            if (mood && store.userRole === "admin") {
                if (typeof switchTab === "function") switchTab("search");
                if (dom.searchInput) {
                    dom.searchInput.value = mood + " mix";
                    if (typeof doSearch === "function") doSearch(mood + " mix");
                }
            }
        });
    });

    if (dom.portalClientBtn) {
        dom.portalClientBtn.addEventListener("click", () => {
            store.userRole = "client";
            if (window.safeStorage) {
                window.safeStorage.set("ytgui_user_role", "client");
            } else {
                localStorage.setItem("ytgui_user_role", "client");
            }
            if (typeof applyRoleUI === "function") applyRoleUI();
            if (typeof unlockBrowserAudio === "function") unlockBrowserAudio();
            if (typeof syncBrowserAudio === "function") syncBrowserAudio();
        });
    }

    if (dom.portalAdminBtn) {
        dom.portalAdminBtn.addEventListener("click", () => {
            if (dom.portalLoginForm) {
                dom.portalLoginForm.classList.toggle("hidden");
                if (!dom.portalLoginForm.classList.contains("hidden") && dom.adminUsername) {
                    dom.adminUsername.focus();
                }
            }
        });
    }

    if (dom.adminSubmitBtn) {
        dom.adminSubmitBtn.addEventListener("click", () => {
            const user = dom.adminUsername ? dom.adminUsername.value.trim() : "";
            const pass = dom.adminPassword ? dom.adminPassword.value : "";
            if (typeof login === 'function') {
                login(user, pass);
            }
        });
    }

    if (dom.adminPassword) {
        dom.adminPassword.addEventListener("keypress", (e) => {
            if (e.key === "Enter" && dom.adminSubmitBtn) dom.adminSubmitBtn.click();
        });
    }

    if (dom.logoutBtn) {
        dom.logoutBtn.addEventListener("click", () => {
            if (typeof logout === "function") logout();
        });
    }

    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (typeof switchTab === "function") switchTab(btn.dataset.tab);
        });
    });

    // Initialize sub-modules
    if (typeof initPlayerEvents === "function") initPlayerEvents();
    if (typeof initQueueEvents === "function") initQueueEvents();
    if (typeof initLyricsEvents === "function") initLyricsEvents();
    if (typeof initSettingsEvents === "function") initSettingsEvents();
}
