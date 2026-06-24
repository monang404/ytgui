const SR_EQ_MINI_HTML =
    '<div class="eq-anim-icon sr-eq"><span></span><span></span><span></span></div>';

function buildSrThumbHtml(track) {
    if (track.thumbnail) {
        return `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`;
    }
    return '<i class="ti ti-music"></i>';
}

function renderSearchResults(results) {
    store.search_results = results || [];
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
        item.className = "sr-item";
        item.dataset.videoId = track.video_id;
        item.dataset.searchTrackStr = JSON.stringify(track);

        const thumb = document.createElement("div");
        thumb.className = "sr-thumb";
        thumb.innerHTML = buildSrThumbHtml(track);

        const info = document.createElement("div");
        info.className = "sr-info";

        const title = document.createElement("div");
        title.className = "sr-title";
        title.textContent = track.title;

        const meta = document.createElement("div");
        meta.className = "sr-meta";
        meta.textContent = track.artist + " · " + formatTime(track.duration);

        info.appendChild(title);
        info.appendChild(meta);

        const badge = document.createElement("span");
        badge.className = "sr-badge " + (track.local_path ? "cache" : "stream");
        badge.textContent = track.local_path ? "✓ Cache" : "☁ Stream";
        badge.style.display = "inline-block";

        item.appendChild(thumb);
        item.appendChild(info);
        item.appendChild(badge);

        dom.searchResults.appendChild(item);
    });

    updateSearchPlayingState();
}

function updateSearchPlayingState() {
    if (!dom.searchResults) return;

    const currentId = store.current_track && store.current_track.video_id;
    const isPlaying = store.status === "PLAYING";

    dom.searchResults.querySelectorAll(".sr-item").forEach((item) => {
        const isCurrent = currentId && item.dataset.videoId === currentId;
        item.classList.toggle("current", !!isCurrent);

        const thumb = item.querySelector(".sr-thumb");
        if (!thumb) return;

        if (isCurrent && isPlaying) {
            thumb.innerHTML = SR_EQ_MINI_HTML;
            thumb.classList.add("playing");
        } else {
            thumb.classList.remove("playing");
            let track = null;
            try {
                track = JSON.parse(item.dataset.searchTrackStr);
            } catch (_) {
                return;
            }
            thumb.innerHTML = buildSrThumbHtml(track);
        }
    });
}

function playSearchTrack(track) {
    if (store.userRole !== "admin" || !track) return;
    wsSend("play_track", track);
}

function showActionModal(track) {
    window.pendingTrack = track;
    dom.actionTitle.textContent = track.title;
    if (dom.actionSheet) dom.actionSheet.classList.add("open");
    if (dom.mainOverlay) dom.mainOverlay.classList.add("open");
}

function hideActionModal() {
    if (dom.actionSheet) dom.actionSheet.classList.remove("open");
    if (dom.mainOverlay) dom.mainOverlay.classList.remove("open");
    window.pendingTrack = null;
}
