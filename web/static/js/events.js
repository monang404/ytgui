function initEvents() {
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
        
        wsSend("auth", { username: user, password: pass });
    });

    dom.adminPassword.addEventListener("keypress", (e) => {
        if (e.key === "Enter") dom.adminSubmitBtn.click();
    });

    dom.logoutBtn.addEventListener("click", logout);

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

    if (dom.volSlider) {
        window.isDraggingVol = false;
        dom.volSlider.addEventListener("input", () => {
            window.isDraggingVol = true;
            store.volume = parseInt(dom.volSlider.value);
            if (dom.pbVolLabel) dom.pbVolLabel.textContent = store.volume + "%";
            if (store.audio_output === "browser" && typeof getOrInitAudio === "function") {
                const audio = getOrInitAudio();
                if (audio) audio.volume = Math.max(0, Math.min(1, store.volume / 100));
            }
        });
        dom.volSlider.addEventListener("change", () => {
            if (store.userRole === "admin") {
                wsSend("volume_set", { volume: store.volume });
            }
            window.isDraggingVol = false;
        });
    }

    dom.btnDownload.addEventListener("click", () => {
        if (store.userRole === "admin") wsSend("download");
    });

    window.isDraggingPb = false;
    function updatePb(e) {
        if (store.userRole !== "admin") return 0;
        const rect = dom.pbProgressTrack.getBoundingClientRect();
        let pct = (e.clientX - rect.left) / rect.width;
        pct = Math.max(0, Math.min(1, pct));
        const dur = store.current_track ? store.current_track.duration : 0;
        if (dom.pbProgressFill) dom.pbProgressFill.style.width = (pct * 100) + "%";
        const thumb = dom.pbProgressTrack.querySelector('.pb-thumb');
        if (thumb) thumb.style.left = (pct * 100) + "%";
        if (dom.pbTimePos) dom.pbTimePos.textContent = formatTime(pct * dur);
        return pct;
    }
    dom.pbProgressTrack.addEventListener("pointerdown", (e) => {
        if (store.userRole !== "admin") return;
        window.isDraggingPb = true;
        dom.pbProgressTrack.setPointerCapture(e.pointerId);
        updatePb(e);
    });
    dom.pbProgressTrack.addEventListener("pointermove", (e) => {
        if (window.isDraggingPb) updatePb(e);
    });
    dom.pbProgressTrack.addEventListener("pointerup", (e) => {
        if (!window.isDraggingPb) return;
        window.isDraggingPb = false;
        dom.pbProgressTrack.releasePointerCapture(e.pointerId);
        const pct = updatePb(e);
        const dur = store.current_track ? store.current_track.duration : 0;
        if (dur > 0) {
            const targetPos = pct * dur;
            if (store.audio_output === "browser" && typeof getOrInitAudio === "function") {
                const audio = getOrInitAudio();
                if (audio && audio.src) {
                    audio.currentTime = targetPos;
                    store.position = targetPos;
                    renderProgress();
                }
            }
            wsSend("seek", { position: targetPos });
        }
    });

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

    if (dom.btnLyrics) {
        dom.btnLyrics.addEventListener("click", () => {
            dom.lyricsSheet.classList.add("open");
            dom.mainOverlay.classList.add("open");
            renderLyrics();
        });
    }

    if (dom.lyricsCloseBtn) {
        dom.lyricsCloseBtn.addEventListener("click", () => {
            dom.lyricsSheet.classList.remove("open");
            closeMainOverlay();
        });
    }

    if (dom.lyricOffsetMinus) {
        dom.lyricOffsetMinus.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            store.lyrics_offset = (store.lyrics_offset || 0) - 0.5;
            updateOffsetDisplay();
            if (typeof syncLocalLyrics === "function") syncLocalLyrics();
            wsSend("lyrics_offset", { offset: store.lyrics_offset });
        });
    }

    if (dom.lyricOffsetPlus) {
        dom.lyricOffsetPlus.addEventListener("click", () => {
            if (store.userRole !== "admin") return;
            store.lyrics_offset = (store.lyrics_offset || 0) + 0.5;
            updateOffsetDisplay();
            if (typeof syncLocalLyrics === "function") syncLocalLyrics();
            wsSend("lyrics_offset", { offset: store.lyrics_offset });
        });
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

    if (dom.mainOverlay) {
        dom.mainOverlay.addEventListener("click", closeMainOverlay);
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
            setTimeout(() => {
                if (dom.discRecent) {
                    dom.discRecent.scrollIntoView({ behavior: 'smooth' });
                }
            }, 300);
        });
    }

    dom.btnHelp.addEventListener("click", () => {
        dom.helpSheet.classList.add("open");
        dom.mainOverlay.classList.add("open");
    });

    dom.helpCloseBtn.addEventListener("click", () => {
        dom.helpSheet.classList.remove("open");
        closeMainOverlay();
    });

    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            switchTab(btn.dataset.tab);
        });
    });

    // EVENT DELEGATION UNTUK DISCOVER / SEED / SEARCH
    document.addEventListener("click", (e) => {
        // Chip clicks
        const chip = e.target.closest(".chip");
        if (chip && dom.chipWrap && dom.chipWrap.contains(chip)) {
            if (store.userRole !== "admin") return;
            const seed = chip.dataset.seed;
            dom.chipWrap.querySelectorAll('.chip.active').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            if (store.playback_mode !== "RADIO") wsSend("set_mode", { mode: "RADIO" });
            wsSend("radio_randomize", { seed_artist: seed });
            showLogToast("Menyetel radio dari artis: " + seed);
            return;
        }

        // Recent / Favorite / Cached / Search Results cards
        const card = e.target.closest(".disc-card, .fav-card, .search-result-item");
        if (card && card.dataset.vid) {
            let track = null;
            if (card.classList.contains("search-result-item") && card.dataset.searchTrackStr) {
                track = JSON.parse(card.dataset.searchTrackStr);
            } else {
                const vid = card.dataset.vid;
                // find in store lists
                const lists = [
                    store.discover_recent || [],
                    store.discover_favorites || [],
                    store.discover_cached || [],
                    store.queue || []
                ];
                for (const list of lists) {
                    track = list.find(t => t.video_id === vid);
                    if (track) break;
                }
            }
            if (track) showActionModal(track);
            return;
        }
    });

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

    dom.actionPlayNow.addEventListener("click", () => {
        if (window.pendingTrack) wsSend("play_track", window.pendingTrack);
        hideActionModal();
    });

    dom.actionEnqueue.addEventListener("click", () => {
        if (window.pendingTrack) wsSend("queue_add", window.pendingTrack);
        hideActionModal();
    });

    dom.actionCancel.addEventListener("click", hideActionModal);

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

    initQueueDragDrop();

    document.addEventListener("keydown", (e) => {
        if (store.userRole !== "admin") return;
        if (document.activeElement === dom.searchInput) {
            if (e.key === "Escape") dom.searchInput.blur();
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
                if (dom.lyricsSheet) {
                    const isOpen = dom.lyricsSheet.classList.contains("open");
                    if (isOpen) {
                        dom.lyricsSheet.classList.remove("open");
                        closeMainOverlay();
                    } else {
                        dom.lyricsSheet.classList.add("open");
                        dom.mainOverlay.classList.add("open");
                        renderLyrics();
                    }
                }
                break;
            case "/":
                e.preventDefault();
                switchTab("search");
                break;
            case "?":
                if (dom.helpSheet.classList.contains("open")) { 
                    dom.helpSheet.classList.remove("open"); closeMainOverlay(); 
                } else { 
                    dom.helpSheet.classList.add("open"); dom.mainOverlay.classList.add("open"); 
                }
                break;
            case "Escape":
                hideActionModal();
                if (dom.helpSheet) dom.helpSheet.classList.remove("open");
                break;
        }
    });
}

function openSettings() {
    dom.settingsSheet.classList.add("open");
    dom.mainOverlay.classList.add("open");
    renderSettingsSheet();
}

function closeSettings() {
    dom.settingsSheet.classList.remove("open");
    closeMainOverlay();
}

function renderSettingsSheet() {
    if (!dom.settingsSheet || !dom.settingsSheet.classList.contains("open")) return;
    if (dom.sbToggle) dom.sbToggle.dataset.on = store.sponsorblock_active ? "true" : "false";
    if (dom.ssOutSub && dom.ssOutBtn) {
        if (store.audio_output === "browser") {
            dom.ssOutSub.textContent = "Keluar via browser ini";
            dom.ssOutBtn.textContent = "💻 Browser";
        } else {
            dom.ssOutSub.textContent = "Keluar via perangkat (mpv)";
            dom.ssOutBtn.textContent = "📱 Device";
        }
    }
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
    if (dom.ssHistorySub) {
        dom.ssHistorySub.textContent = (store.history_count || 0) + " lagu diputar";
    }
}

function closeMainOverlay() {
    dom.mainOverlay.classList.remove("open");
    if (dom.settingsSheet) dom.settingsSheet.classList.remove("open");
    if (dom.actionSheet) dom.actionSheet.classList.remove("open");
    if (dom.helpSheet) dom.helpSheet.classList.remove("open");
}

let dragSrcIndex = null;
function initQueueDragDrop() {
    dom.queueList.addEventListener('dragstart', e => {
        const item = e.target.closest('.queue-item');
        if (!item || !item.hasAttribute('data-index')) return;
        dragSrcIndex = parseInt(item.dataset.index);
        item.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', dragSrcIndex);
    });

    dom.queueList.addEventListener('dragover', e => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const item = e.target.closest('.queue-item');
        if (item && item.hasAttribute('data-index')) {
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
