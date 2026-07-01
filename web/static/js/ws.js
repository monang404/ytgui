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
            const savedOutput = localStorage.getItem("ytgui_audio_output") || "browser";
            wsSend("set_output", { output: savedOutput });
        } else if (store.userRole === "client") {
            if (store.active_tab === "home" || store.active_tab === "discover") {
                wsSend("discover");
            }
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
            if (dom.adminSubmitBtn) {
                dom.adminSubmitBtn.disabled = false;
                dom.adminSubmitBtn.textContent = "Login Admin";
            }
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
                if (store.active_tab === "home" || store.active_tab === "discover") {
                    showLogToast("Meminta data lagu...");
                    wsSend("discover");
                }
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
                if (!audio.paused && audio.src && !audio.src.startsWith("data:")) {
                    // Sync posisi
                    const diff = Math.abs(audio.currentTime - store.position);
                    if (diff > 0.5 && store.position > 2) {
                        audio.currentTime = store.position;
                    }
                } else if (audio.paused && audio.src && !audio.src.startsWith("data:") && audio.readyState >= 2) {
                    // FIX-RADIO-08: Audio stuck paused padahal status PLAYING.
                    // Terjadi saat AudioContext suspended (radio auto-switch tanpa user interaction).
                    // Coba resume AudioContext + play ulang tanpa menunggu user klik.
                    // audio.readyState >= 2 = HAVE_CURRENT_DATA — audio sudah ter-load, aman di-play.
                    // PATCH-ANDROID-AUDIO-01: kalau sebelumnya sudah ketauan diblock browser,
                    // jangan retry diam2 tiap detik (spam gagal) — tunggu user
                    // tap tombol "tap to play" (lihat audio.js), itu pasti lolos
                    // autoplay policy krn ada user gesture beneran.
                    if (!window.audioBlocked && typeof _resumeAndPlay === "function") {
                        _resumeAndPlay(audio);
                    }
                }
            }

            renderProgress();

            renderPlayBtn();
            // PATCH-ANDROID-AUDIO-01: dipanggil tiap tick (bukan cuma saat statusChanged)
            // supaya data-player-state / idle-view selalu sinkron dgn
            // store.status & store.current_track yang sebenarnya.
            if (typeof syncPlayerStateAttr === "function") syncPlayerStateAttr();
            if (statusChanged) {
                if (typeof renderNowPlaying === "function") renderNowPlaying();
                if (typeof renderQueue === "function") renderQueue();
                if (typeof renderRadio === "function") renderRadio();
                if (typeof updateSearchPlayingState === "function") updateSearchPlayingState();
                if (typeof updateDiscoverPlayingState === "function") updateDiscoverPlayingState();
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
            showLogToast("Menerima data lagu! " + (msg.data.recent ? msg.data.recent.length : 0) + " items");
            store.discover_recent = msg.data.recent || [];
            store.discover_favorites = msg.data.favorites || [];
            store.discover_cached   = msg.data.cached_tracks || [];
            store.discover_featured_artists = msg.data.featured_artists || [];
            store.discover_featured_genres = msg.data.featured_genres || [];
            renderDiscoverTab();
            renderRecentRow();
            break;
        case "favorite_status":
            if (store.current_track && store.current_track.video_id === msg.data.video_id) {
                store.current_track.is_favorite = msg.data.is_favorite;
                if (typeof renderNowPlaying === "function") renderNowPlaying();
            }
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
    if (typeof updateDiscoverPlayingState === "function") updateDiscoverPlayingState();
}

function renderHeader() {
    if (store.is_online) {
        dom.statusDot.classList.remove("offline");
        dom.statusText.textContent = "online";
    } else {
        dom.statusDot.classList.add("offline");
        dom.statusText.textContent = "offline";
    }

    const out = store.audio_output || "browser";
    if (out === "browser") {
        dom.outputToggleBtn.textContent = "💻 BROWSER";
        dom.outputToggleBtn.classList.add("browser");
    } else {
        dom.outputToggleBtn.textContent = "📱 HP";
        dom.outputToggleBtn.classList.remove("browser");
    }
}