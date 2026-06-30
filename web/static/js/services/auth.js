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
        switchTab("home");
        dom.logoutBtn.style.display = "flex";
    } else if (store.userRole === "admin") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.remove("client-mode");
        dom.logoutBtn.style.display = "flex";
        switchTab("home");
        // FIX BUG-1: setelah #app visible, paksa recalculate tinggi viewport.
        // Android Chrome tidak auto-fire visualViewport resize saat element
        // berubah dari display:none ke display:flex, sehingga nav-bar bisa
        // terpotong sampai user scroll atau resize manual.
        if (window.visualViewport) {
            const _app = document.getElementById("app");
            if (_app) {
                _app.style.height = window.visualViewport.height + "px";
            }
        }
    }
    renderHeader();
}

function login(user, pass) {
    if (!user || !pass) {
        dom.loginErrorMsg.textContent = "Isi username dan password!";
        return;
    }
    
    if (dom.adminSubmitBtn) {
        dom.adminSubmitBtn.disabled = true;
        dom.adminSubmitBtn.textContent = "Menghubungkan...";
    }
    dom.loginErrorMsg.textContent = "";
    
    store.adminUsername = user;
    store.adminPassword = pass;
    
    if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        wsSend("auth", { username: user, password: pass });
    } else {
        dom.loginErrorMsg.textContent = "Koneksi server terputus. Silakan tunggu/refresh.";
        if (dom.adminSubmitBtn) {
            dom.adminSubmitBtn.disabled = false;
            dom.adminSubmitBtn.textContent = "Login Admin";
        }
    }
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
    safeStorage.remove("ytgui_user_role");
    safeStorage.remove("ytgui_admin_username");
    safeStorage.remove("ytgui_admin_password");
    safeStorage.remove("ytgui_session_token");

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
