/* ══════════════════════════════════════════════════════════════
   YTGUI Web — Client Application
   WebSocket client + UI logic + Equalizer animation
   ══════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // Seed artists — sync dengan engine/radio_mode.py SEED_ARTISTS
    const SEED_ARTISTS = [
        "Nadin Amizah","Peterpan","NOAH","Dewa 19","Ungu","Nidji","Samsons",
        "ST12","Setia Band","Wali","The Changcuters","Kotak","Geisha","Drive",
        "d'Masiv","The Rain","Letto","Kerispatih","Vierra","Vierratale","Govinda",
        "Ada Band","Radja","Kangen Band","J-Rocks","Andra and The Backbone",
        "Padi Reborn","Armada","Cokelat","Gigi","Slank","Sheila On 7",
        "Maliq & D'Essentials","The Groove","Kahitna","Juicy Luicy","Hindia",
        "Lomba Sihir","Reality Club","Fourtwnty","Ariel NOAH","Afgan","Judika",
        "Glenn Fredly","Tompi","Marcell Siahaan","Ello","Virgoun","Rizky Febian",
        "Ardhito Pramono","Tulus","Pamungkas","Budi Doremi","Mahalini",
        "Tiara Andini","Lyodra","Ziva Magnolya"
    ];

    // ── State Store ──
    const store = {
        status: "IDLE",
        playback_mode: "QUEUE",
        audio_output: "device",
        userRole: "portal", // "portal" | "client" | "admin"
        adminUsername: "",
        adminPassword: "",
        current_track: null,
        position: 0,
        volume: 80,
        sponsorblock_active: false,
        queue: [],
        radio_queue: [],
        history_count: 0,
        lyrics_lines: [],
        lyrics_index: 0,
        lyrics_offset: 0,
        active_tab: "home",
        error_msg: null,
        is_online: true,
        download_progress: null,
    };

    // ── DOM Cache ──
    const $ = (id) => document.getElementById(id);
    const dom = {
        portalScreen: $("portal-screen"),
        portalClientBtn: $("portal-client-btn"),
        portalAdminBtn: $("portal-admin-btn"),
        portalLoginForm: $("portal-login-form"),
        adminUsername: $("admin-username"),
        adminPassword: $("admin-password"),
        adminSubmitBtn: $("admin-submit-btn"),
        loginErrorMsg: $("login-error-msg"),
        logoutBtn: $("logout-btn"),
        appContainer: $("app"),
        tabHome: $("tab-home"),
        tabQueue: $("tab-queue"),
        outputToggleBtn: $("output-toggle-btn"),
        statusDot: $("status-dot"),
        statusText: $("status-text"),
        // Now Playing
        npTitle: $("np-title"),
        npArtist: $("np-artist"),
        npThumbnail: $("np-thumbnail"),
        npDurMeta: $("np-dur-meta"),
        recentRow: $("recent-row"),
        eqCanvas: $("eq-canvas"),
        // Search
        searchInput: $("search-input"),
        searchMsg: $("search-msg"),
        searchResults: $("search-results"),
        // Radio
        radioToggleWrap: $("radio-toggle-wrap"),
        radioToggleBtn: $("radio-toggle-btn"),
        rtSub: $("rt-sub"),
        nextCard: $("next-card"),
        nextTitle: $("next-title"),
        nextMeta: $("next-meta"),
        nextThumb: $("next-thumb"),
        chipWrap: $("chip-wrap"),
        radioRandomizeBtn: $("radio-randomize-btn"),
        radioSkipBtn: $("radio-skip-btn"),
        // Queue
        queueList: $("queue-list"),
        queueFooter: $("queue-footer"),
        lyricsPanel: $("lyrics-panel"),
        lyricsToggleBtn: $("lyrics-toggle-btn"),
        lyricsContent: $("lyrics-content"),
        lyricOffsetMinus: $("lyric-offset-minus"),
        lyricOffsetPlus: $("lyric-offset-plus"),
        lyricOffsetDisplay: $("lyric-offset-display"),
        // Player Bar
        pbTrackInfo: $("pb-track-info"),
        pbModeBadge: $("pb-mode-badge"),
        pbTimePos: $("pb-time-pos"),
        pbTimeDur: $("pb-time-dur"),
        pbProgressTrack: $("pb-progress-track"),
        pbProgressFill: $("pb-progress-fill"),
        pbVolLabel: $("pb-vol-label"),
        volSlider: $("vol-slider"),
        btnPrev: $("btn-prev"),
        btnPlay: $("btn-play"),
        btnNext: $("btn-next"),
        btnStop: $("btn-stop"),
        btnSettings: $("btn-settings"),
        btnDownload: $("btn-download"),
        btnHelp: $("btn-help"),
        pbCacheBadge: $("pb-cache-badge"),
        pbSbBadge: $("pb-sb-badge"),
        pbDlBadge: $("pb-dl-badge"),
        // Settings Sheet
        settingsSheet: $("settings-sheet"),
        settingsOverlay: $("settings-overlay"),
        sbToggle: $("sb-toggle"),
        ssOutBtn: $("ss-out-btn"),
        ssOutSub: $("ss-out-sub"),
        ssStopBtn: $("ss-stop-btn"),
        ssDlRow: $("ss-dl-row"),
        ssDlTrack: $("ss-dl-track"),
        ssDlPct: $("ss-dl-pct"),
        ssDlFill: $("ss-dl-fill"),
        ssHistorySub: $("ss-history-sub"),
        ssHistoryBtn: $("ss-history-btn"),
        // Modals
        actionOverlay: $("action-modal-overlay"),
        actionTitle: $("action-modal-title"),
        actionPlayNow: $("action-play-now"),
        actionEnqueue: $("action-enqueue"),
        actionCancel: $("action-cancel"),
        helpOverlay: $("help-modal-overlay"),
        helpCloseBtn: $("help-close-btn"),
        // Toasts
        connectionToast: $("connection-toast"),
        logToast: $("log-toast"),
    };

    // ══════════════════════════════════════
    // WebSocket Manager
    // ══════════════════════════════════════

    let ws = null;
    let wsReconnectTimer = null;
    let wsConnected = false;

    function wsConnect() {
        const protocol = location.protocol === "https:" ? "wss:" : "ws:";
        const url = `${protocol}//${location.host}/ws`;

        showConnectionToast("Menghubungkan...", "connecting");

        ws = new WebSocket(url);

        ws.onopen = () => {
            wsConnected = true;
            hideConnectionToast();
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }
            
            // Re-authenticate if we are admin
            if (store.userRole === "admin") {
                const token = localStorage.getItem("ytgui_session_token");
                if (token) {
                    wsSend("auth", { token: token });
                }
                const savedOutput = localStorage.getItem("ytgui_audio_output") || "device";
                wsSend("set_output", { output: savedOutput });
            }
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
            wsConnected = false;
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

    // ══════════════════════════════════════
    // Message Handlers
    // ══════════════════════════════════════

    function handleServerMessage(msg) {
        switch (msg.type) {
            case "auth_status":
                if (msg.data.success) {
                    store.userRole = "admin";
                    localStorage.setItem("ytgui_user_role", "admin");
                    if (msg.data.token) {
                        localStorage.setItem("ytgui_session_token", msg.data.token);
                    }
                    localStorage.removeItem("ytgui_admin_password"); // Jangan simpan password
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
                syncBrowserAudio();
                break;
            case "progress":
                store.position = msg.data.position;
                store.status = msg.data.status;
                if (msg.data.server_ts) {
                    store.server_ts = msg.data.server_ts;
                }

                // PATCH-1-07: Audio drift correction
                if (store.audio_output === "browser" && store.status === "PLAYING") {
                    const audio = getOrInitAudio();
                    if (!audio.paused && audio.src) {
                        const diff = Math.abs(audio.currentTime - store.position);
                        if (diff > 0.5 && store.position > 2) {
                            console.log("Audio drift corrected by", diff.toFixed(3), "s");
                            audio.currentTime = store.position;
                        }
                    }
                }

                renderProgress();
                renderPlayBtn();
                syncBrowserAudio();
                break;
            case "lyrics":
                store.lyrics_lines = msg.data.lyrics_lines || [];
                store.lyrics_index = msg.data.lyrics_index || 0;
                store.lyrics_offset = msg.data.lyrics_offset || 0;
                renderLyrics();
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

    // ══════════════════════════════════════
    // Full State Render
    // ══════════════════════════════════════

    function renderFullState() {
        renderHeader();
        renderNowPlaying();
        renderProgress();
        renderPlayerBar();
        renderRadio();
        renderQueue();
        renderLyrics();
        renderSettingsSheet();
    }

    // ── Header ──
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

    // ── Now Playing ──
    function renderNowPlaying() {
        const t = store.current_track;

        // Thumbnail
        if (dom.npThumbnail) {
            if (t && t.thumbnail) {
                dom.npThumbnail.innerHTML = `<img src="${escapeHtml(t.thumbnail)}" alt="" loading="lazy">`;
            } else {
                dom.npThumbnail.innerHTML = '<span class="np-thumb-fallback">🎵</span>';
            }
        }

        // Title & Artist
        if (store.status === "LOADING") {
            dom.npTitle.innerHTML = '<span class="spinner" style="display:inline-block; margin-right:8px; vertical-align:-3px; width:20px; height:20px;"></span> ⏳ Memuat...';
            dom.npArtist.textContent = t ? t.title : "";
        } else if (t) {
            dom.npTitle.textContent = t.title;
            dom.npArtist.textContent = t.artist;
        } else {
            dom.npTitle.textContent = "Belum ada lagu yang diputar";
            dom.npArtist.textContent = "Cari lagu untuk memulai";
        }

        // Duration meta
        if (dom.npDurMeta && t) {
            dom.npDurMeta.textContent = formatTime(t.duration);
        } else if (dom.npDurMeta) {
            dom.npDurMeta.textContent = '';
        }

        renderRecentRow();
    }

    function renderRecentRow() {
        if (!dom.recentRow) return;
        // Jika ada discover data dari server, gunakan itu
        const items = (store.discover_recent && store.discover_recent.length > 0)
            ? store.discover_recent.slice(0, 5)
            : (store.queue || []).slice(0, 5);

        if (items.length === 0) {
            dom.recentRow.innerHTML = '<div class="discover-empty">Belum ada riwayat</div>';
            return;
        }
        dom.recentRow.innerHTML = items.map(track => `
            <div class="disc-card" data-vid="${escapeHtml(track.video_id || '')}">
                <div class="disc-thumb">
                    ${track.thumbnail
                        ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                        : '🎵'}
                    ${track.local_path ? '<span class="disc-tag">cache</span>' : ''}
                </div>
                <div class="disc-info">
                    <div class="disc-title">${escapeHtml(track.title)}</div>
                    <div class="disc-artist">${escapeHtml(track.artist || '')}</div>
                </div>
            </div>
        `).join('');

        dom.recentRow.querySelectorAll('.disc-card').forEach(card => {
            card.addEventListener('click', () => {
                const vid = card.dataset.vid;
                const track = items.find(t => t.video_id === vid);
                if (track) showActionModal(track);
            });
        });
    }

    function renderDiscoverTab() {
        const favEl = $('discover-favorites');
        const recentEl = $('discover-recent');
        const cachedEl = $('discover-cached');

        if (favEl && store.discover_favorites) {
            if (store.discover_favorites.length === 0) {
                favEl.innerHTML = '<div class="discover-empty">Belum ada data favorit</div>';
            } else {
                favEl.innerHTML = store.discover_favorites.map((track, i) => `
                    <div class="fav-card" data-vid="${escapeHtml(track.video_id || '')}">
                        <div class="fav-num">${i + 1}</div>
                        <div class="fav-thumb">
                            ${track.thumbnail
                                ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                                : '🎵'}
                        </div>
                        <div class="fav-info">
                            <div class="fav-title">${escapeHtml(track.title)}</div>
                            <div class="fav-cnt">${escapeHtml(track.artist || '')} · ${track.play_count || 0}×</div>
                        </div>
                    </div>
                `).join('');
                favEl.querySelectorAll('.fav-card').forEach(card => {
                    card.addEventListener('click', () => {
                        const vid = card.dataset.vid;
                        const track = store.discover_favorites.find(t => t.video_id === vid);
                        if (track) showActionModal(track);
                    });
                });
            }
        }

        if (recentEl && store.discover_recent) {
            if (store.discover_recent.length === 0) {
                recentEl.innerHTML = '<div class="discover-empty">Belum ada riwayat</div>';
            } else {
                recentEl.innerHTML = store.discover_recent.map(track => `
                    <div class="disc-card" data-vid="${escapeHtml(track.video_id || '')}">
                        <div class="disc-thumb">
                            ${track.thumbnail
                                ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                                : '🎵'}
                            ${track.local_path ? '<span class="disc-tag">cache</span>' : ''}
                        </div>
                        <div class="disc-info">
                            <div class="disc-title">${escapeHtml(track.title)}</div>
                            <div class="disc-artist">${escapeHtml(track.artist || '')}</div>
                        </div>
                    </div>
                `).join('');
                recentEl.querySelectorAll('.disc-card').forEach(card => {
                    card.addEventListener('click', () => {
                        const vid = card.dataset.vid;
                        const track = store.discover_recent.find(t => t.video_id === vid);
                        if (track) showActionModal(track);
                    });
                });
            }
        }

        if (cachedEl && store.discover_cached) {
            if (store.discover_cached.length === 0) {
                cachedEl.innerHTML = '<div class="discover-empty">Tidak ada file tersimpan</div>';
            } else {
                cachedEl.innerHTML = store.discover_cached.map(track => `
                    <div class="search-result-item" data-vid="${escapeHtml(track.video_id || '')}">
                        <div class="sr-thumb">
                            ${track.thumbnail
                                ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                                : '🎵'}
                        </div>
                        <div class="sr-info">
                            <div class="sr-title">${escapeHtml(track.title)}</div>
                            <div class="sr-meta">${escapeHtml(track.artist || '')} · ${formatTime(track.duration)}</div>
                        </div>
                        <span class="sr-badge cache">✓ Cache</span>
                    </div>
                `).join('');
                cachedEl.querySelectorAll('.search-result-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const vid = item.dataset.vid;
                        const track = store.discover_cached.find(t => t.video_id === vid);
                        if (track) showActionModal(track);
                    });
                });
            }
        }
    }

    // ── Progress ──
    function renderProgress() {
        const dur = store.current_track ? store.current_track.duration : 0;
        const pos = store.position || 0;
        const pct = dur > 0 ? Math.min(100, (pos / dur) * 100) : 0;

        dom.pbProgressFill.style.width = pct + "%";
        dom.pbTimePos.textContent = formatTime(pos);
        dom.pbTimeDur.textContent = formatTime(dur);
    }

    // ── Player Bar ──
    function renderPlayerBar() {
        const t = store.current_track;

        // Track Info
        if (store.status === "LOADING") {
            dom.pbTrackInfo.innerHTML = '<span class="spinner" style="display:inline-block; margin-right:5px; vertical-align:-2px;"></span> Memuat... ' + escapeHtml(t ? t.title : "");
        } else if (t) {
            dom.pbTrackInfo.textContent = t.title + " — " + t.artist;
        } else {
            dom.pbTrackInfo.textContent = "";
        }

        // Play button
        renderPlayBtn();

        // Mode badge
        if (store.playback_mode === "RADIO") {
            dom.pbModeBadge.textContent = "📻 radio";
            dom.pbModeBadge.className = "pb-mode-badge radio";
        } else {
            dom.pbModeBadge.textContent = "≡ queue";
            dom.pbModeBadge.className = "pb-mode-badge queue";
        }

        // Volume
        dom.pbVolLabel.textContent = store.volume + "%";
        if (dom.volSlider) dom.volSlider.value = store.volume;

        // Cache badge
        if (t && t.local_path) {
            dom.pbCacheBadge.textContent = "✓ tersimpan";
            dom.pbCacheBadge.className = "pb-badge cache-badge";
        } else if (t) {
            dom.pbCacheBadge.textContent = "☁ stream";
            dom.pbCacheBadge.className = "pb-badge stream-badge";
        } else {
            dom.pbCacheBadge.textContent = "";
        }

        // SponsorBlock badge
        dom.pbSbBadge.textContent = store.sponsorblock_active ? "SB: ON" : "";

        // Download badge
        if (store.download_progress != null) {
            dom.pbDlBadge.textContent = "⬇ " + Math.round(store.download_progress * 100) + "%";
        } else {
            dom.pbDlBadge.textContent = "";
        }
    }

    function renderPlayBtn() {
        if (store.status === "PLAYING") {
            dom.btnPlay.innerHTML = "<i class=\"ti ti-player-pause-filled\" style=\"font-size:15px;color:#fff\"></i>";
        } else {
            dom.btnPlay.innerHTML = "<i class=\"ti ti-player-play-filled\" style=\"font-size:15px;color:#fff\"></i>";
        }
    }

    // ── Radio ──
    function renderRadio() {
        const isRadio = store.playback_mode === 'RADIO';

        // Toggle button
        if (dom.radioToggleBtn) {
            dom.radioToggleBtn.dataset.on = isRadio ? 'true' : 'false';
        }


        // Sub text
        if (dom.rtSub) {
            dom.rtSub.textContent = isRadio
                ? 'Menyetel lagu otomatis...'
                : 'Aktifkan untuk putar otomatis';
        }

        // Next card
        if (dom.nextCard) {
            if (isRadio && store.radio_queue && store.radio_queue.length > 0) {
                const next = store.radio_queue[0];
                dom.nextCard.style.display = 'block';
                if (dom.nextTitle) dom.nextTitle.textContent = next.title || '-';
                if (dom.nextMeta) {
                    dom.nextMeta.textContent = (next.artist || '') + ' · ' + formatTime(next.duration);
                }
                if (dom.nextThumb) {
                    dom.nextThumb.innerHTML = next.thumbnail
                        ? `<img src="${escapeHtml(next.thumbnail)}" alt="" loading="lazy">`
                        : '🎵';
                }
            } else {
                dom.nextCard.style.display = 'none';
            }
        }

        // Artist chips (render sekali — tidak perlu re-render tiap state update)
        renderSeedChips();
    }

    function renderSeedChips() {
        if (!dom.chipWrap || dom.chipWrap.children.length > 0) return; // sudah dirender
        dom.chipWrap.innerHTML = SEED_ARTISTS.slice(0, 20).map(name => `
            <span class="chip" data-seed="${escapeHtml(name)}">${escapeHtml(name)}</span>
        `).join('');

        // Event listener for chips (Task 3.3)
        dom.chipWrap.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                if (store.userRole !== "admin") return;
                const seed = chip.dataset.seed;
                // Highlight chip
                dom.chipWrap.querySelectorAll('.chip.active').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                
                // Switch mode if not radio
                if (store.playback_mode !== "RADIO") {
                    wsSend("set_mode", { mode: "RADIO" });
                }
                // Send custom seed
                wsSend("radio_randomize", { seed_artist: seed });
                
                // Show notification locally for quick feedback
                showLogToast("Menyetel radio dari artis: " + seed);
            });
        });
    }

    function renderQueue() {
        const isRadio = store.playback_mode === "RADIO";
        const upcoming = isRadio ? store.radio_queue : store.queue;

        const allItems = [];
        if (store.current_track) {
            allItems.push({ track: store.current_track, index: -1, isCurrent: true });
        }
        upcoming.forEach((track, i) => allItems.push({ track, index: i, isCurrent: false }));

        if (allItems.length === 0) {
            dom.queueList.innerHTML = '<div class="queue-empty">' + (isRadio ? "Radio sedang menyiapkan lagu..." : "Cari lagu atau aktifkan Radio") + '</div>';
        } else {
            const existing = Array.from(dom.queueList.children);
            if (existing.length === 1 && existing[0].classList.contains('queue-empty')) {
                existing[0].remove();
                existing.shift();
            }

            allItems.forEach((item, i) => {
                let el = existing[i];
                if (!el) {
                    el = createQueueItemTemplate();
                    dom.queueList.appendChild(el);
                }
                updateQueueItem(el, item.track, item.index, item.isCurrent, isRadio);
            });

            while (dom.queueList.children.length > allItems.length) {
                dom.queueList.removeChild(dom.queueList.lastChild);
            }
        }

        const modeStr = isRadio
            ? '<span style="color:var(--status-ok)">RADIO</span>'
            : '<span style="color:var(--text-dim)">QUEUE</span>';
        dom.queueFooter.innerHTML = "Mode: " + modeStr + " | 📝 Lirik: Tekan L";
    }

    function createQueueItemTemplate() {
        const div = document.createElement("div");
        div.innerHTML = `
            <span class="qi-drag" aria-hidden="true">⠿</span>
            <span class="qi-index"></span>
            <div class="qi-info">
                <div class="qi-title"></div>
                <div class="qi-dur"></div>
            </div>
            <button class="qi-remove">✕</button>
        `;
        return div;
    }

    function updateQueueItem(div, track, index, isCurrent, isRadio) {
        div.className = "queue-item" + (isCurrent ? " current" : "");
        if (!isCurrent && !isRadio) {
            div.dataset.index = index;
            div.setAttribute('draggable', 'true');
        } else {
            div.removeAttribute("data-index");
            div.removeAttribute('draggable');
        }
        
        div.querySelector(".qi-index").textContent = isCurrent ? "▶" : index + 1;
        div.querySelector(".qi-title").textContent = track.title;
        div.querySelector(".qi-dur").textContent = track.artist + " · " + formatTime(track.duration);
        
        const rmBtn = div.querySelector(".qi-remove");
        if (isCurrent || isRadio) {
            rmBtn.style.display = "none";
        } else {
            rmBtn.style.display = "block";
            rmBtn.dataset.index = index;
        }
    }

    dom.queueList.addEventListener("click", (e) => {
        if (store.userRole !== "admin") return;
        const rmBtn = e.target.closest(".qi-remove");
        if (rmBtn) {
            e.stopPropagation();
            wsSend("queue_remove", { index: parseInt(rmBtn.dataset.index) });
            return;
        }
        const item = e.target.closest(".queue-item");
        if (item && item.hasAttribute("data-index")) {
            wsSend("queue_select", { index: parseInt(item.dataset.index) });
        }
    });

    // Drag-to-reorder queue
    let dragSrcIndex = null;

    function initQueueDragDrop() {
        dom.queueList.addEventListener('dragstart', e => {
            const item = e.target.closest('.queue-item');
            if (!item || !item.hasAttribute('data-index')) return;
            dragSrcIndex = parseInt(item.dataset.index);
            item.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        dom.queueList.addEventListener('dragover', e => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            const item = e.target.closest('.queue-item');
            if (item && item.hasAttribute('data-index')) {
                // Visual feedback
                document.querySelectorAll('.queue-item.drag-over')
                    .forEach(el => el.classList.remove('drag-over'));
                item.classList.add('drag-over');
            }
        });

        dom.queueList.addEventListener('drop', e => {
            e.preventDefault();
            const item = e.target.closest('.queue-item');
            if (!item || !item.hasAttribute('data-index') || dragSrcIndex === null) return;
            const toIndex = parseInt(item.dataset.index);
            if (toIndex !== dragSrcIndex) {
                wsSend('queue_reorder', { from_index: dragSrcIndex, to_index: toIndex });
            }
            cleanupDrag();
        });

        dom.queueList.addEventListener('dragend', cleanupDrag);
    }

    function cleanupDrag() {
        dragSrcIndex = null;
        document.querySelectorAll('.queue-item.dragging, .queue-item.drag-over')
            .forEach(el => el.classList.remove('dragging', 'drag-over'));
    }

    // ── Lyrics ──
    function renderLyrics() {
        if (!dom.lyricsPanel.classList.contains("active")) return;

        const lines = store.lyrics_lines;
        const idx = store.lyrics_index;

        if (!lines || lines.length === 0) {
            dom.lyricsContent.innerHTML = '<div style="color:var(--text-dim)">Tidak ada lirik tersedia</div>';
            return;
        }

        const start = Math.max(0, idx - 5);
        const end = Math.min(lines.length, idx + 6);

        let html = "";
        for (let i = start; i < end; i++) {
            const text = escapeHtml(lines[i]);
            if (i === idx) {
                html += '<div class="lyric-line active">▶ ' + text + " ◀</div>";
            } else if (i < idx) {
                html += '<div class="lyric-line past">' + text + "</div>";
            } else {
                html += '<div class="lyric-line future">' + text + "</div>";
            }
        }
        dom.lyricsContent.innerHTML = html;

        // Auto-scroll active line into view
        const activeLine = dom.lyricsContent.querySelector(".lyric-line.active");
        if (activeLine) {
            activeLine.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    // ══════════════════════════════════════
    // Search
    // ══════════════════════════════════════

    let searchTimer = null;
    let lastSearchQuery = "";

    dom.searchInput.addEventListener("input", (e) => {
        const q = e.target.value.trim();
        if (searchTimer) clearTimeout(searchTimer);

        if (!q) {
            dom.searchMsg.textContent = "Ketik nama lagu atau artis";
            dom.searchMsg.style.display = "block";
            dom.searchResults.innerHTML = "";
            dom.searchResults.style.display = "none";
            lastSearchQuery = "";
            return;
        }

        if (q !== lastSearchQuery) {
            lastSearchQuery = q;
            searchTimer = setTimeout(() => {
                dom.searchMsg.innerHTML = '<span class="spinner"></span> Mencari...';
                dom.searchMsg.style.display = "block";
                dom.searchResults.style.display = "none";
                wsSend("search", { query: q });
            }, 500);
        }
    });

    dom.searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const q = e.target.value.trim();
            if (q) {
                if (searchTimer) clearTimeout(searchTimer);
                lastSearchQuery = q;
                dom.searchMsg.innerHTML = '<span class="spinner"></span> Mencari...';
                dom.searchMsg.style.display = "block";
                dom.searchResults.style.display = "none";
                wsSend("search", { query: q });
            }
        }
    });

    function renderSearchResults(results) {
        dom.searchResults.innerHTML = "";
        if (!results || results.length === 0) {
            dom.searchMsg.textContent = "Tidak ditemukan hasil.";
            dom.searchMsg.style.display = "block";
            dom.searchResults.style.display = "none";
            return;
        }

        dom.searchMsg.style.display = "none";
        dom.searchResults.style.display = "flex";

        results.forEach((track) => {
            const item = document.createElement("div");
            item.className = "search-result-item";

            const thumb = document.createElement("div");
            thumb.className = "sr-thumb";
            if (track.thumbnail) {
                const img = document.createElement("img");
                img.src = track.thumbnail;
                img.alt = "";
                img.loading = "lazy";
                thumb.appendChild(img);
            } else {
                thumb.textContent = "🎵";
            }

            const info = document.createElement("div");
            info.className = "sr-info";

            const title = document.createElement("div");
            title.className = "sr-title";
            title.textContent = track.title;

            const meta = document.createElement("div");
            meta.className = "sr-meta";
            meta.textContent =
                track.artist + " · " + formatTime(track.duration);

            info.appendChild(title);
            info.appendChild(meta);

            const badge = document.createElement("span");
            badge.className = "sr-badge " + (track.local_path ? "cache" : "stream");
            badge.textContent = track.local_path ? "✓ Cache" : "☁ Stream";

            item.appendChild(thumb);
            item.appendChild(info);
            item.appendChild(badge);

            item.addEventListener("click", () => {
                showActionModal(track);
            });

            dom.searchResults.appendChild(item);
        });
    }

    // ══════════════════════════════════════
    // Action Modal
    // ══════════════════════════════════════

    let pendingTrack = null;

    function showActionModal(track) {
        pendingTrack = track;
        dom.actionTitle.textContent = track.title;
        dom.actionOverlay.classList.add("active");
    }

    function hideActionModal() {
        dom.actionOverlay.classList.remove("active");
        pendingTrack = null;
    }

    dom.actionPlayNow.addEventListener("click", () => {
        if (pendingTrack) wsSend("play_track", pendingTrack);
        hideActionModal();
    });

    dom.actionEnqueue.addEventListener("click", () => {
        if (pendingTrack) wsSend("queue_add", pendingTrack);
        hideActionModal();
    });

    dom.actionCancel.addEventListener("click", hideActionModal);

    dom.actionOverlay.addEventListener("click", (e) => {
        if (e.target === dom.actionOverlay) hideActionModal();
    });

    // ══════════════════════════════════════
    // Tab Navigation
    // ══════════════════════════════════════

    const tabs = ["home", "search", "radio", "queue", "discover"];

    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });

    function switchTab(tab) {
        store.active_tab = tab;

        // Tab panels
        tabs.forEach((t) => {
            const panel = $("tab-" + t);
            if (t === tab) {
                panel.classList.add("active");
            } else {
                panel.classList.remove("active");
            }
        });

        // Nav buttons
        document.querySelectorAll(".nav-btn").forEach((btn) => {
            if (btn.dataset.tab === tab) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });

        // Auto-focus search input
        if (tab === "search") {
            setTimeout(() => dom.searchInput.focus(), 100);
        }
        // Request discover data when opening discover tab
        if (tab === "discover") {
            wsSend("discover");
        }
    }

    // ══════════════════════════════════════
    // Player Controls & Portal UI Logics
    // ══════════════════════════════════════

    function applyRoleUI() {
        if (store.userRole === "portal") {
            dom.portalScreen.classList.add("portal-active");
            dom.appContainer.classList.add("portal-active");
            document.body.classList.remove("client-mode");
            // Kembalikan queue ke tab queue jika dari portal
            dom.tabQueue.insertBefore(dom.queueList, dom.queueFooter);
            dom.logoutBtn.style.display = "none";
        } else if (store.userRole === "client") {
            dom.portalScreen.classList.remove("portal-active");
            dom.appContainer.classList.remove("portal-active");
            document.body.classList.add("client-mode");
            switchTab("home");
            // Pindahkan queue list ke tab home untuk mode client
            dom.tabHome.appendChild(dom.queueList);
            dom.logoutBtn.style.display = "none";
        } else if (store.userRole === "admin") {
            dom.portalScreen.classList.remove("portal-active");
            dom.appContainer.classList.remove("portal-active");
            document.body.classList.remove("client-mode");
            // Kembalikan queue list ke tab queue untuk mode admin
            dom.tabQueue.insertBefore(dom.queueList, dom.queueFooter);
            dom.logoutBtn.style.display = "inline-flex";
        }
    }

    function logout() {
        store.userRole = "portal";
        store.adminUsername = "";
        store.adminPassword = "";
        localStorage.removeItem("ytgui_user_role");
        localStorage.removeItem("ytgui_admin_username");
        localStorage.removeItem("ytgui_admin_password");
        localStorage.removeItem("ytgui_session_token");
        if (window.location.pathname !== "/admin") {
            window.location.href = "/admin";
        } else {
            dom.portalClientBtn.style.display = "none";
            applyRoleUI();
            if (ws) {
                ws.close();
            }
        }
    }

    let audioUnlocked = false;
    function unlockBrowserAudio() {
        if (audioUnlocked) return;
        const audio = getOrInitAudio();
        
        // Force valid silent src to unlock iOS Safari
        if (!audio.src || audio.src === window.location.href || audio.src === window.location.origin + "/") {
            audio.src = "data:audio/mpeg;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU5LjI3LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAEAAABIAD+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+AAAAAExhdmM1OS4zNy4xMDBHAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0gAAAAARTmZ//MUZAYAAAGkAAAAAAAAA0gAAAAARTmZ//MUZAwAAAGkAAAAAAAAA0gAAAAARTmZ";
        }
        
        audio.volume = 0; // Mute just in case
        const p = audio.play();
        if (p !== undefined) {
            p.catch((err) => {
                console.warn("Unlock play failed:", err);
            }).finally(() => {
                audioUnlocked = true;
                syncBrowserAudio(); 
            });
        } else {
            audioUnlocked = true;
            syncBrowserAudio();
        }
    }

    // Dengarkan klik pertama di seluruh halaman untuk membuka kunci audio (berguna jika auto-login)
    document.addEventListener("click", unlockBrowserAudio, { once: true });
    document.addEventListener("touchstart", unlockBrowserAudio, { once: true });

    // Portal screen event listeners
    dom.portalClientBtn.addEventListener("click", () => {
        store.userRole = "client";
        localStorage.setItem("ytgui_user_role", "client");
        applyRoleUI();
        unlockBrowserAudio();
        syncBrowserAudio();
    });

    dom.portalAdminBtn.addEventListener("click", () => {
        dom.portalLoginForm.classList.toggle("hidden");
        if (!dom.portalLoginForm.classList.contains("hidden")) {
            dom.adminUsername.focus();
        }
    });

    dom.adminSubmitBtn.addEventListener("click", () => {
        const user = dom.adminUsername.value.trim();
        const pass = dom.adminPassword.value;
        if (!user || !pass) {
            dom.loginErrorMsg.textContent = "Isi username dan password!";
            return;
        }
        store.adminUsername = user;
        store.adminPassword = pass;
        
        if (wsConnected) {
            wsSend("auth", { username: user, password: pass });
        } else {
            dom.loginErrorMsg.textContent = "Koneksi terputus. Coba lagi nanti.";
        }
    });

    dom.adminPassword.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            dom.adminSubmitBtn.click();
        }
    });

    dom.logoutBtn.addEventListener("click", () => {
        logout();
    });

    dom.outputToggleBtn.addEventListener("click", () => {
        if (store.userRole !== "admin") return;
        const newOutput = store.audio_output === "browser" ? "device" : "browser";
        if (newOutput === "browser") unlockBrowserAudio();
        wsSend("set_output", { output: newOutput });
    });

    dom.btnPlay.addEventListener("click", () => {
        if (store.userRole === "admin") {
            store.status = store.status === "PLAYING" ? "PAUSED" : "PLAYING";
            renderPlayBtn();
            wsSend("toggle_pause");
        }
    });
    dom.btnNext.addEventListener("click", () => {
        if (store.userRole === "admin") {
            const data = {};
            if (store.current_track && store.current_track.video_id) {
                data.video_id = store.current_track.video_id;
            }
            store.status = "LOADING";
            renderNowPlaying();
            renderPlayerBar();
            wsSend("next", data);
        }
    });
    dom.btnPrev.addEventListener("click", () => {
        if (store.userRole === "admin") {
            store.status = "LOADING";
            renderNowPlaying();
            renderPlayerBar();
            wsSend("prev");
        }
    });

    if (dom.btnStop) {
        dom.btnStop.addEventListener('click', () => {
            if (store.userRole === 'admin') wsSend('stop');
        });
    }

    // Volume slider
    if (dom.volSlider) {
        dom.volSlider.addEventListener("input", () => {
            store.volume = parseInt(dom.volSlider.value);
            dom.pbVolLabel.textContent = store.volume + "%";
        });
        dom.volSlider.addEventListener("change", () => {
            if (store.userRole === "admin") {
                wsSend("volume_set", { volume: store.volume });
            }
        });
    }
    dom.btnDownload.addEventListener("click", () => {
        if (store.userRole === "admin") wsSend("download");
    });

    // Progress bar seek
    dom.pbProgressTrack.addEventListener("click", (e) => {
        if (store.userRole !== "admin") return;
        const rect = dom.pbProgressTrack.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        const dur = store.current_track ? store.current_track.duration : 0;
        if (dur > 0) {
            wsSend("seek", { position: pct * dur });
        }
    });

    // ══════════════════════════════════════
    // Radio Controls
    // ══════════════════════════════════════

    dom.radioToggleBtn.addEventListener("click", () => {
        if (store.userRole !== "admin") return;
        const newMode = store.playback_mode === "RADIO" ? "QUEUE" : "RADIO";
        wsSend("set_mode", { mode: newMode });
    });

    dom.radioRandomizeBtn.addEventListener("click", () => {
        if (store.userRole === "admin") wsSend("radio_randomize");
    });
    dom.radioSkipBtn.addEventListener("click", () => {
        if (store.userRole === "admin") {
            const data = {};
            if (store.current_track && store.current_track.video_id) {
                data.video_id = store.current_track.video_id;
            }
            wsSend("next", data);
        }
    });

    // ══════════════════════════════════════
    // Lyrics Toggle
    // ══════════════════════════════════════

    dom.lyricsToggleBtn.addEventListener("click", () => {
        dom.lyricsPanel.classList.toggle("active");
        renderLyrics();
    });

    // Lyrics offset controls
    if (dom.lyricOffsetMinus) {
        dom.lyricOffsetMinus.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            store.lyrics_offset = (store.lyrics_offset || 0) - 0.5;
            updateOffsetDisplay();
            wsSend("lyrics_offset", { offset: store.lyrics_offset });
        });
    }
    if (dom.lyricOffsetPlus) {
        dom.lyricOffsetPlus.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            store.lyrics_offset = (store.lyrics_offset || 0) + 0.5;
            updateOffsetDisplay();
            wsSend("lyrics_offset", { offset: store.lyrics_offset });
        });
    }
    function updateOffsetDisplay() {
        if (!dom.lyricOffsetDisplay) return;
        const val = store.lyrics_offset || 0;
        const sign = val >= 0 ? '+' : '';
        dom.lyricOffsetDisplay.textContent = sign + val.toFixed(1) + 's';
    }

    // Settings Sheet
    function openSettings() {
        dom.settingsSheet.classList.add("open");
        dom.settingsOverlay.classList.add("active");
        renderSettingsSheet();
    }
    function closeSettings() {
        dom.settingsSheet.classList.remove("open");
        dom.settingsOverlay.classList.remove("active");
    }
    function renderSettingsSheet() {
        if (!dom.settingsSheet || !dom.settingsSheet.classList.contains("open")) return;
        // SponsorBlock toggle
        if (dom.sbToggle) {
            dom.sbToggle.dataset.on = store.sponsorblock_active ? "true" : "false";
        }
        // Output
        if (dom.ssOutSub && dom.ssOutBtn) {
            if (store.audio_output === "browser") {
                dom.ssOutSub.textContent = "Keluar via browser ini";
                dom.ssOutBtn.textContent = "💻 Browser";
            } else {
                dom.ssOutSub.textContent = "Keluar via perangkat (mpv)";
                dom.ssOutBtn.textContent = "📱 Device";
            }
        }
        // Download progress
        if (dom.ssDlRow) {
            if (store.download_progress != null) {
                dom.ssDlRow.style.display = "flex";
                const pct = Math.round(store.download_progress * 100);
                if (dom.ssDlPct) dom.ssDlPct.textContent = pct + "%";
                if (dom.ssDlFill) dom.ssDlFill.style.width = pct + "%";
                if (dom.ssDlTrack && store.current_track) {
                    dom.ssDlTrack.textContent = store.current_track.title;
                }
            } else {
                dom.ssDlRow.style.display = "none";
            }
        }
        // History count
        if (dom.ssHistorySub) {
            dom.ssHistorySub.textContent = (store.history_count || 0) + " lagu diputar";
        }
    }

    if (dom.btnSettings) {
        dom.btnSettings.addEventListener("click", () => {
            if (dom.settingsSheet.classList.contains("open")) {
                closeSettings();
            } else {
                openSettings();
            }
        });
    }
    if (dom.settingsOverlay) {
        dom.settingsOverlay.addEventListener("click", closeSettings);
    }
    if (dom.sbToggle) {
        dom.sbToggle.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            const newVal = dom.sbToggle.dataset.on !== "true";
            wsSend("set_sponsorblock", { enabled: newVal });
        });
    }
    if (dom.ssOutBtn) {
        dom.ssOutBtn.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            const newOutput = store.audio_output === "browser" ? "device" : "browser";
            if (newOutput === "browser") unlockBrowserAudio();
            wsSend("set_output", { output: newOutput });
            closeSettings();
        });
    }
    if (dom.ssStopBtn) {
        dom.ssStopBtn.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            wsSend("stop");
            closeSettings();
        });
    }

    if (dom.ssHistoryBtn) {
        dom.ssHistoryBtn.addEventListener('click', () => {
            closeSettings();
            switchTab('discover');
            wsSend('discover', {});
            // Scroll ke recent section setelah data dimuat
            setTimeout(() => {
                if (dom.discRecentList) {
                    dom.discRecentList.scrollIntoView({ behavior: 'smooth' });
                }
            }, 300);
        });
    }

    // ══════════════════════════════════════
    // Help Modal
    // ══════════════════════════════════════

    dom.btnHelp.addEventListener("click", () => {
        dom.helpOverlay.classList.add("active");
    });

    dom.helpCloseBtn.addEventListener("click", () => {
        dom.helpOverlay.classList.remove("active");
    });

    dom.helpOverlay.addEventListener("click", (e) => {
        if (e.target === dom.helpOverlay) dom.helpOverlay.classList.remove("active");
    });

    // ══════════════════════════════════════
    // Keyboard Shortcuts
    // ══════════════════════════════════════

    document.addEventListener("keydown", (e) => {
        if (store.userRole !== "admin") return;
        // Don't capture keys when typing in search
        if (document.activeElement === dom.searchInput) {
            if (e.key === "Escape") {
                dom.searchInput.blur();
            }
            return;
        }

        switch (e.key) {
            case " ":
                e.preventDefault();
                wsSend("toggle_pause");
                break;
            case "n":
            case "N":
                wsSend("next");
                break;
            case "b":
            case "B":
                wsSend("prev");
                break;
            case "s":
            case "S":
                wsSend("stop");
                break;
            case "ArrowUp":
                e.preventDefault();
                wsSend("volume_up");
                break;
            case "ArrowDown":
                e.preventDefault();
                wsSend("volume_down");
                break;
            case "m":
            case "M":
                wsSend("download");
                break;
            case "r":
            case "R":
                const newMode = store.playback_mode === "RADIO" ? "QUEUE" : "RADIO";
                wsSend("set_mode", { mode: newMode });
                break;
            case "l":
            case "L":
                // Switch to queue tab and toggle lyrics
                switchTab("queue");
                dom.lyricsPanel.classList.toggle("active");
                renderLyrics();
                break;
            case "/":
                e.preventDefault();
                switchTab("search");
                break;
            case "?":
                dom.helpOverlay.classList.toggle("active");
                break;
            case "Escape":
                hideActionModal();
                dom.helpOverlay.classList.remove("active");
                break;
        }
    });

    // ══════════════════════════════════════
    // Equalizer Animation (Canvas)
    // ══════════════════════════════════════

    const eqCtx = dom.eqCanvas.getContext("2d");
    const NUM_BANDS = 12;
    const bandHeights = new Array(NUM_BANDS).fill(0);
    const bandTargets = new Array(NUM_BANDS).fill(0);
    
    // Pre-bake gradients (PATCH-0-07)
    const eqGradients = [];
    const _canvasH = dom.eqCanvas.height;
    for (let i = 0; i < NUM_BANDS; i++) {
        const grad = eqCtx.createLinearGradient(0, _canvasH, 0, 0);
        const hue = 340 + (i / NUM_BANDS) * 60;
        grad.addColorStop(0, `hsla(${hue}, 80%, 55%, 0.9)`);
        grad.addColorStop(0.5, `hsla(${hue + 20}, 70%, 50%, 0.7)`);
        grad.addColorStop(1, `hsla(${hue + 40}, 60%, 65%, 0.5)`);
        eqGradients.push(grad);
    }

    function tickEQ() {
        if (store.active_tab !== "home") {
            requestAnimationFrame(tickEQ);
            return;
        }

        const canvas = dom.eqCanvas;
        const w = canvas.width;
        const h = canvas.height;
        const isPlaying = store.status === "PLAYING";

        eqCtx.clearRect(0, 0, w, h);

        const gap = 4;
        const bandW = (w - gap * (NUM_BANDS - 1)) / NUM_BANDS;

        for (let i = 0; i < NUM_BANDS; i++) {
            // Animate towards targets
            if (isPlaying) {
                bandTargets[i] = Math.random() * h * 0.85 + h * 0.1;
            } else {
                bandTargets[i] = h * 0.05;
            }

            // Smooth interpolation
            bandHeights[i] += (bandTargets[i] - bandHeights[i]) * 0.18;

            const bh = bandHeights[i];
            const x = i * (bandW + gap);
            const y = h - bh;

            eqCtx.fillStyle = eqGradients[i];
            eqCtx.beginPath();
            // Rounded top
            const r = Math.min(bandW / 2, 4);
            eqCtx.moveTo(x, h);
            eqCtx.lineTo(x, y + r);
            eqCtx.quadraticCurveTo(x, y, x + r, y);
            eqCtx.lineTo(x + bandW - r, y);
            eqCtx.quadraticCurveTo(x + bandW, y, x + bandW, y + r);
            eqCtx.lineTo(x + bandW, h);
            eqCtx.closePath();
            eqCtx.fill();
        }

        requestAnimationFrame(tickEQ);
    }

    requestAnimationFrame(tickEQ);

    // ══════════════════════════════════════
    // Toast Utilities
    // ══════════════════════════════════════

    function showConnectionToast(text, type) {
        dom.connectionToast.textContent = text;
        dom.connectionToast.className = "active " + type;
    }

    function hideConnectionToast() {
        dom.connectionToast.className = "";
    }

    let logToastTimer = null;
    function showLogToast(text) {
        dom.logToast.textContent = text;
        dom.logToast.classList.add("active");
        if (logToastTimer) clearTimeout(logToastTimer);
        logToastTimer = setTimeout(() => {
            dom.logToast.classList.remove("active");
        }, 3000);
    }

    // ══════════════════════════════════════
    // Browser Audio Sync
    // ══════════════════════════════════════

    let localAudio = null;

    function getOrInitAudio() {
        if (!localAudio) {
            localAudio = new Audio();
            localAudio.preload = "auto";
            localAudio.crossOrigin = "anonymous";
            localAudio.onerror = (e) => {
                const errMsg = localAudio.error?.message || "unknown";
                if (errMsg.includes("Empty src") || !localAudio.getAttribute("src")) {
                    return; // Abaikan error reset src yang disengaja
                }
                console.error("Browser audio error:", e, errMsg);
                showLogToast("⚠️ Error audio: " + errMsg);
            };
        }
        return localAudio;
    }

    let _lastLoadedVideoId = null;

    function syncBrowserAudio() {
        const isBrowser = store.userRole === "client" || store.audio_output === "browser";
        const audio = getOrInitAudio();

        if (!isBrowser) {
            if (!audio.paused) audio.pause();
            return;
        }

        const track = store.current_track;
        if (!track) {
            if (!audio.paused) audio.pause();
            if (audio.hasAttribute("src") && audio.src && !audio.src.startsWith("data:")) {
                audio.removeAttribute("src");
                audio.load();
            }
            _lastLoadedVideoId = null;
            return;
        }

        const expectedSrc = window.location.origin + `/api/stream/${track.video_id}`;

        if (_lastLoadedVideoId !== track.video_id) {
            _lastLoadedVideoId = track.video_id;
            audio.src = expectedSrc;
            
            audio.oncanplay = () => {
                if (store.position > 2 && Math.abs(audio.currentTime - store.position) > 2) {
                    audio.currentTime = store.position;
                }
                audio.oncanplay = null;
            };
            
            audio.onended = () => {
                console.log("Browser audio ended, requesting next track");
                // Cek apakah output memang browser, jika ya kita trigger next
                if (store.audio_output === "browser") {
                    wsSend("next", { video_id: track.video_id });
                }
            };
            
            audio.load();
        }

        audio.volume = Math.max(0, Math.min(1, (store.volume || 80) / 100));

        if (store.status === "PLAYING") {
            if (audio.paused && audio.src) {
                const playPromise = audio.play();
                if (playPromise !== undefined) {
                    playPromise.catch(err => console.warn("Autoplay prevented:", err));
                }
            }
        } else {
            if (!audio.paused) {
                audio.pause();
            }
        }
    }

    // ══════════════════════════════════════
    // Utilities
    // ══════════════════════════════════════

    function formatTime(secs) {
        if (!secs || secs < 0) return "00:00";
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    }

    function escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // ══════════════════════════════════════
    // Init
    // ══════════════════════════════════════

    const path = window.location.pathname;

    if (path === "/admin") {
        const savedRole = localStorage.getItem("ytgui_user_role");
        if (savedRole === "admin") {
            store.userRole = "admin";
            applyRoleUI();
        } else {
            store.userRole = "portal";
            applyRoleUI();
            dom.portalClientBtn.style.display = "none";
            dom.portalAdminBtn.click();
        }
    } else {
        // Show portal (popup) for Client mode only
        store.userRole = "portal";
        localStorage.removeItem("ytgui_user_role"); // Force interaction on reload
        applyRoleUI();
        const adminWrapper = document.querySelector(".portal-admin-wrapper");
        if (adminWrapper) adminWrapper.style.display = "none";
    }

    initQueueDragDrop();
    wsConnect();
})();
