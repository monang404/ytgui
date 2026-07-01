function renderNowPlaying() {
    const t = store.current_track;

    if (dom.vinylCover) {
        if (t && t.video_id) {
            dom.vinylCover.style.display = "none";
            if (dom.vinylIcon) dom.vinylIcon.style.display = "block";
            window.getCoverArt(t).then(url => {
                if (url && store.current_track && store.current_track.video_id === t.video_id) {
                    dom.vinylCover.src = url;
                    dom.vinylCover.style.display = "block";
                    if (dom.vinylIcon) dom.vinylIcon.style.display = "none";
                    if (typeof window.extractDominantColor === "function" && dom.tabHome) {
                        window.extractDominantColor(dom.vinylCover, (color) => {
                            if (color && color.r !== undefined) {
                                dom.tabHome.style.setProperty("--color-r", color.r);
                                dom.tabHome.style.setProperty("--color-g", color.g);
                                dom.tabHome.style.setProperty("--color-b", color.b);
                            }
                        });
                    }
                }
            });
        } else {
            dom.vinylCover.src = "";
            dom.vinylCover.style.display = "none";
            if (dom.vinylIcon) dom.vinylIcon.style.display = "block";
        }
    }

    if (dom.npThumbIcon && dom.npEqAnim) {
        if (store.status === "PLAYING") {
            dom.npThumbIcon.style.display = "none";
            dom.npEqAnim.style.display = "flex";
            if (dom.vinylRecord) {
                const isBrowser = store.userRole === "client" || store.audio_output === "browser";
                dom.vinylRecord.classList.add(isBrowser ? "visualizer-active" : "playing");
                dom.vinylRecord.classList.remove(isBrowser ? "playing" : "visualizer-active");
            }
        } else {
            dom.npThumbIcon.style.display = "block";
            dom.npEqAnim.style.display = "none";
            if (dom.vinylRecord) {
                dom.vinylRecord.classList.remove("playing");
                dom.vinylRecord.classList.remove("visualizer-active");
            }
        }
    }

    if (dom.homeEqualizer) {
        const hasLyrics = store.lyrics_lines && store.lyrics_lines.length > 0;
        dom.homeEqualizer.style.display = (!hasLyrics && store.status === "PLAYING") ? "flex" : "none";
    }

    if (dom.vinylRecord) {
        if (store.status === "PLAYING") {
            dom.vinylRecord.classList.add("playing");
        } else {
            dom.vinylRecord.classList.remove("playing");
        }
    }

    // PATCH-ANDROID-AUDIO-01: satu-satunya tempat yang nentuin data-player-state,
    // dipanggil juga dari player.js & ws.js (progress tick) supaya nggak
    // ada dua sumber kebenaran yang bisa desync.
    syncPlayerStateAttr();

    if (store.status === "LOADING") {
        dom.npTitle.innerHTML = '<span class="spinner" style="display:inline-block; margin-right:8px; vertical-align:-3px; width:20px; height:20px;"></span> ⏳ Memuat...';
        dom.npArtist.textContent = t ? t.title : "";
    } else if (t) {
        const cleanedTitle = typeof cleanTrackTitle === "function" ? cleanTrackTitle(t.title) : t.title;
        dom.npTitle.textContent = cleanedTitle.toLowerCase().replace(/(?:^|\s|-)\S/g, function(a) { return a.toUpperCase(); });
        dom.npArtist.textContent = t.artist;
    } else {
        dom.npTitle.textContent = "Belum ada lagu yang diputar";
        dom.npArtist.textContent = "Cari lagu untuk memulai";
    }

    if (dom.npDurMeta && t) {
        dom.npDurMeta.textContent = formatTime(t.duration);
    } else if (dom.npDurMeta) {
        dom.npDurMeta.textContent = '';
    }

    if (dom.btnFavorite) {
        if (t && t.is_favorite) {
            dom.btnFavorite.classList.add("active");
        } else {
            dom.btnFavorite.classList.remove("active");
        }
    }
}

// PATCH-ANDROID-AUDIO-01
function syncPlayerStateAttr() {
    const t = store.current_track;
    if (!t || (!t.video_id && store.status !== "LOADING")) {
        document.body.setAttribute("data-player-state", "IDLE");
    } else {
        document.body.setAttribute("data-player-state", store.status);
    }
}
