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
        item.className = "sr-item";

        const thumb = document.createElement("div");
        thumb.className = "sr-thumb";
        if (track.thumbnail) {
            const img = document.createElement("img");
            img.src = track.thumbnail;
            img.alt = "";
            img.loading = "lazy";
            thumb.appendChild(img);
        } else {
            thumb.innerHTML = '<i class="ti ti-music"></i>';
        }

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

        item.dataset.searchTrackStr = JSON.stringify(track);

        dom.searchResults.appendChild(item);
    });
}

function showActionModal(track) {
    window.pendingTrack = track;
    dom.actionTitle.textContent = track.title;
    if(dom.actionSheet) dom.actionSheet.classList.add("open");
    if(dom.mainOverlay) dom.mainOverlay.classList.add("open");
}

function hideActionModal() {
    if(dom.actionSheet) dom.actionSheet.classList.remove("open");
    if(dom.mainOverlay) dom.mainOverlay.classList.remove("open");
    window.pendingTrack = null;
}
