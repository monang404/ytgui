function initPortal() {
    const role = localStorage.getItem("ytgui_user_role");
    if (role && role !== "client") {
        store.userRole = role;
    } else {
        store.userRole = "portal";
    }
    applyRoleUI();
}

function applyRoleUI() {
    if (store.userRole === "portal") {
        dom.portalScreen.classList.add("portal-active");
        dom.appContainer.classList.add("portal-active");
        document.body.classList.remove("client-mode");
        dom.logoutBtn.style.display = "none";
    } else if (store.userRole === "client") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.add("client-mode");
        switchTab("discover");
        dom.logoutBtn.style.display = "flex";
    } else if (store.userRole === "admin") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.remove("client-mode");
        dom.logoutBtn.style.display = "flex";
        switchTab("discover");
    }
    renderHeader();
}

function logout() {
    // 1. Stop local browser/client audio
    if (typeof localAudio !== "undefined" && localAudio) {
        try {
            localAudio.pause();
            localAudio.src = "";
            localAudio.removeAttribute("src");
            localAudio.load();
        } catch (e) {
            console.warn("Failed to stop browser audio:", e);
        }
    }
    if (typeof _lastLoadedVideoId !== "undefined") {
        _lastLoadedVideoId = null;
    }

    // 2. Stop server playback if admin
    if (store.userRole === "admin") {
        try {
            wsSend("stop");
        } catch (e) {
            console.warn("Failed to send stop command:", e);
        }
    }

    // 3. Clear store & local storage
    store.userRole = "portal";
    store.adminUsername = "";
    store.adminPassword = "";
    localStorage.removeItem("ytgui_user_role");
    localStorage.removeItem("ytgui_admin_username");
    localStorage.removeItem("ytgui_admin_password");
    localStorage.removeItem("ytgui_session_token");

    // 4. Close settings sheet UI if open
    if (typeof closeSettings === "function") {
        closeSettings();
    }

    // 5. Redirect or adjust view
    if (window.location.pathname !== "/admin") {
        setTimeout(() => {
            if (window.ws) {
                try {
                    window.ws.close();
                } catch (e) {}
            }
            window.location.href = "/admin";
        }, 150);
    } else {
        if (dom.portalClientBtn) {
            dom.portalClientBtn.style.display = "none";
        }
        applyRoleUI();
        if (window.ws) {
            try {
                window.ws.close();
            } catch (e) {}
        }
    }
}
