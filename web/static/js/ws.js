let ws = null;
let wsReconnectTimer = null;

// ── Dirty Flag Rendering — Phase 4 ──
// Mencegah renderQueue dan renderRadio dipanggil setiap progress tick
let _lastQueueSnapshot = null;
let _lastRadioSnapshot = null;

function _queueChanged(newState) {
    const snap = JSON.stringify(newState.queue || []);
    if (snap !== _lastQueueSnapshot) {
        _lastQueueSnapshot = snap;
        return true;
    }
    return false;
}

function wsConnect() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${location.host}/ws`;

    showConnectionToast("Menghubungkan...", "connecting");

    // Tutup koneksi lama jika masih ada (BUG-003: mencegah concurrent connections)
    if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
    }

    ws = new WebSocket(url);
    window.ws = ws;

    ws.onopen = () => {
        store.is_online = true;
        hideConnectionToast();
        if (wsReconnectTimer) {
            clearTimeout(wsReconnectTimer);
            wsReconnectTimer = null;
        }
        
        if (store.userRole === "admin") {
            const token = localStorage.getItem("ytgui_session_token");
            if (token) {
                wsSend("auth", { token: token });
            }
            const savedOutput = localStorage.getItem("ytgui_audio_output") || "device";
            wsSend("set_output", { output: savedOutput });
        }
        renderHeader();
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleServerMessage(msg);
        } catch (e) {
            console.error("WS parse error:", e);
        }
    };

    ws.onclose = () => {
        store.is_online = false;
        renderHeader();
        showConnectionToast("Koneksi terputus. Reconnecting...", "disconnected");
        wsReconnectTimer = setTimeout(wsConnect, 2000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function wsSend(action, data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "cmd", action, data: data || {} }));
    }
}

function handleServerMessage(msg) {
    switch (msg.type) {
        case "auth_status":
            if (msg.data.success) {
                store.userRole = "admin";
                localStorage.setItem("ytgui_user_role", "admin");
                if (msg.data.token) {
                    localStorage.setItem("ytgui_session_token", msg.data.token);
                }
                localStorage.removeItem("ytgui_admin_password");
                dom.loginErrorMsg.textContent = "";
                dom.portalLoginForm.classList.add("hidden");
                applyRoleUI();
                showLogToast("Akses Admin Diterima!");
                renderFullState();
            } else {
                dom.loginErrorMsg.textContent = msg.data.message || "Login gagal.";
                if (store.userRole === "admin") {
                    logout();
                }
            }
            break;
        case "state":
            Object.assign(store, msg.data);
            renderFullState();
            // BUG-007: jangan sync audio saat user masih di portal screen
            if (store.userRole !== 'portal') {
                syncBrowserAudio();
            }
            break;
        case "progress":
            store.position = msg.data.position;
            let statusChanged = false;
            if (!window.lastToggleTime || Date.now() - window.lastToggleTime > 1000) {
                if (store.status !== msg.data.status) {
                    store.status = msg.data.status;
                    statusChanged = true;
                }
            }
            if (msg.data.server_ts) {
                store.server_ts = msg.data.server_ts;
            }

            if (store.audio_output === "browser" && store.status === "PLAYING") {
                const audio = getOrInitAudio();
                if (!audio.paused && audio.src) {
                    const diff = Math.abs(audio.currentTime - store.position);
                    if (diff > 0.5 && store.position > 2) {
                        audio.currentTime = store.position;
                    }
                }
            }

            renderProgress();
            renderPlayBtn();
            if (statusChanged) {
                if (typeof renderNowPlaying === "function") renderNowPlaying();
                if (typeof renderQueue === "function") renderQueue();
                if (typeof updateSearchPlayingState === "function") updateSearchPlayingState();
            }
            syncBrowserAudio();
            if (typeof syncLocalLyrics === "function") syncLocalLyrics();
            break;
        case "lyrics":
            store.lyrics_lines = msg.data.lyrics_lines || [];
            store.lyrics_timestamps = msg.data.lyrics_timestamps || [];
            store.lyrics_index = msg.data.lyrics_index || 0;
            store.lyrics_offset = msg.data.lyrics_offset || 0;
            store.lyrics_loading = msg.data.lyrics_loading || false;
            if (typeof renderLyrics === "function") renderLyrics();
            break;
        case "search_results":
            renderSearchResults(msg.data);
            break;
        case "discover_data":
            store.discover_recent   = msg.data.recent   || [];
            store.discover_favorites = msg.data.favorites || [];
            store.discover_cached   = msg.data.cached_tracks || [];
            renderDiscoverTab();
            renderRecentRow();
            break;
        case "log":
            showLogToast(msg.data);
            break;
        case "error":
            showLogToast("Error: " + msg.data);
            break;
    }
}

function syncLocalLyrics() {
    if (store.lyrics_timestamps && store.lyrics_timestamps.length > 0) {
        const pos = store.position + (store.lyrics_offset || 0);
        let newIdx = -1;
        for (let i = 0; i < store.lyrics_timestamps.length; i++) {
            if (pos >= store.lyrics_timestamps[i]) {
                newIdx = i;
            } else {
                break;
            }
        }
        newIdx = Math.max(0, newIdx);
        if (store.lyrics_index !== newIdx) {
            store.lyrics_index = newIdx;
            if (typeof renderLyrics === "function") renderLyrics();
        }
    }
}

function renderFullState() {
    renderHeader();
    renderNowPlaying();
    renderProgress();
    renderPlayerBar();
    renderRadio();
    renderQueue();
    renderLyrics();
    renderSettingsSheet();
    if (typeof updateSearchPlayingState === "function") updateSearchPlayingState();
}

function renderHeader() {
    if (store.is_online) {
        dom.statusDot.classList.remove("offline");
        dom.statusText.textContent = "online";
    } else {
        dom.statusDot.classList.add("offline");
        dom.statusText.textContent = "offline";
    }

    const out = store.audio_output || "device";
    if (out === "browser") {
        dom.outputToggleBtn.textContent = "💻 BROWSER";
        dom.outputToggleBtn.classList.add("browser");
    } else {
        dom.outputToggleBtn.textContent = "📱 HP";
        dom.outputToggleBtn.classList.remove("browser");
    }
}
