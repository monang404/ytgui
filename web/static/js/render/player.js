function renderPlayerBar() {
    document.body.dataset.playerState = store.status || "IDLE";
    const t = store.current_track;

    if (store.status === "LOADING") {
        dom.pbTrackInfo.innerHTML = '<span class="spinner" style="display:inline-block; margin-right:5px; vertical-align:-2px;"></span> Memuat... ' + escapeHtml(t ? t.title : "");
    } else if (t) {
        const title = typeof cleanTrackTitle === "function" ? cleanTrackTitle(t.title) : t.title;
        dom.pbTrackInfo.textContent = title + " — " + t.artist;
    } else {
        dom.pbTrackInfo.textContent = "";
    }

    renderPlayBtn();

    if (store.playback_mode === "RADIO") {
        dom.pbModeBadge.textContent = "📻 radio";
        dom.pbModeBadge.className = "pb-mode-badge radio";
    } else {
        dom.pbModeBadge.textContent = "≡ queue";
        dom.pbModeBadge.className = "pb-mode-badge queue";
    }

    if (dom.pbVolLabel) dom.pbVolLabel.textContent = store.volume + "%";
    if (dom.volSlider && !window.isDraggingVol) dom.volSlider.value = store.volume;

    if (t && t.local_path) {
        dom.pbCacheBadge.textContent = "✓ tersimpan";
        dom.pbCacheBadge.className = "pb-badge-sm cached";
        dom.pbCacheBadge.style.display = "inline-block";
    } else if (t) {
        dom.pbCacheBadge.textContent = "☁ stream";
        dom.pbCacheBadge.className = "pb-badge-sm stream";
        dom.pbCacheBadge.style.display = "inline-block";
    } else {
        dom.pbCacheBadge.textContent = "";
        dom.pbCacheBadge.style.display = "none";
    }

    dom.pbSbBadge.textContent = store.sponsorblock_active ? "SB: ON" : "";
    dom.pbSbBadge.style.display = store.sponsorblock_active ? "inline-block" : "none";

    if (store.download_progress != null) {
        dom.pbDlBadge.textContent = "⬇ " + Math.round(store.download_progress * 100) + "%";
        dom.pbDlBadge.style.display = "inline-block";
    } else {
        dom.pbDlBadge.textContent = "";
        dom.pbDlBadge.style.display = "none";
    }
}

function renderPlayBtn() {
    if (store.status === "PLAYING") {
        dom.btnPlay.innerHTML = '<svg viewBox="0 0 24 24" width="28" height="28" fill="#fff"><path d="M14,19H18V5H14M6,19H10V5H6V19Z"></path></svg>';
    } else {
        dom.btnPlay.innerHTML = '<svg viewBox="0 0 24 24" width="28" height="28" fill="#fff"><path d="M8,5.14V19.14L19,12.14L8,5.14Z"></path></svg>';
    }
}

let _rafProgressPending = false;

function renderProgress() {
    if (_rafProgressPending) return;
    _rafProgressPending = true;
    requestAnimationFrame(() => {
        _rafProgressPending = false;
        _renderProgressCore();
    });
}

function _renderProgressCore() {
    if (window.isDraggingPb) return;
    const dur = store.current_track ? store.current_track.duration : 0;
    const pos = store.position || 0;
    const pct = dur > 0 ? Math.min(100, (pos / dur) * 100) : 0;

    dom.pbProgressFill.style.width = pct + "%";
    
    // update thumb
    const thumb = dom.pbProgressTrack.querySelector('.pb-thumb');
    if(thumb) thumb.style.left = pct + "%";

    dom.pbTimePos.textContent = formatTime(pos);
    dom.pbTimeDur.textContent = formatTime(dur);
}
