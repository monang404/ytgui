function renderNowPlaying() {
    const t = store.current_track;

    if (dom.vinylCover) {
        if (t && t.thumbnail) {
            dom.vinylCover.src = t.thumbnail;
            dom.vinylCover.style.display = "block";
            if (dom.vinylIcon) dom.vinylIcon.style.display = "none";
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
        } else {
            dom.npThumbIcon.style.display = "block";
            dom.npEqAnim.style.display = "none";
        }
    }

    if (dom.vinylRecord) {
        if (store.status === "PLAYING") {
            dom.vinylRecord.classList.add("playing");
        } else {
            dom.vinylRecord.classList.remove("playing");
        }
    }

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
}


function renderDiscoverTab() {
    if (dom.discFavorites && store.discover_favorites) {
        if (store.discover_favorites.length === 0) {
            dom.discFavorites.innerHTML = '<div class="discover-empty"><i class="ti ti-heart-broken" style="font-size:32px; opacity:0.6; margin-bottom:12px; display:block;"></i>Belum ada data favorit</div>';
        } else {
            dom.discFavorites.innerHTML = store.discover_favorites.map((track, i) => {
                const title = typeof cleanTrackTitle === "function" ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
                const playCnt = track.play_count > 0 ? ` · ${track.play_count}×` : '';
                return `
                <div class="fav-card" data-vid="${escapeHtml(track.video_id || '')}">
                    <div class="fav-num">${i + 1}</div>
                    <div class="fav-thumb">
                        ${track.thumbnail ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">` : '<i class="ti ti-music"></i>'}
                    </div>
                    <div class="fav-info">
                        <div class="fav-title">${title}</div>
                        <div class="fav-cnt">${escapeHtml(track.artist || '')}${playCnt}</div>
                    </div>
                </div>
            `}).join('');
        }
    }

    if (dom.discRecent && store.discover_recent) {
        if (store.discover_recent.length === 0) {
            dom.discRecent.innerHTML = '<div class="discover-empty"><i class="ti ti-history" style="font-size:32px; opacity:0.6; margin-bottom:12px; display:block;"></i>Belum ada riwayat</div>';
        } else {
            dom.discRecent.innerHTML = store.discover_recent.map(track => {
                const title = typeof cleanTrackTitle === "function" ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
                return `
                <div class="sr-item" data-vid="${escapeHtml(track.video_id || '')}">
                    <div class="sr-thumb">
                        ${track.thumbnail ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">` : '<i class="ti ti-music"></i>'}
                        ${track.local_path ? '<span class="disc-tag">cache</span>' : ''}
                    </div>
                    <div class="sr-info">
                        <div class="sr-title">${title}</div>
                        <div class="sr-meta">${escapeHtml(track.artist || '')}</div>
                    </div>
                </div>
            `}).join('');
        }
    }

    if (dom.discCached && store.discover_cached) {
        if (store.discover_cached.length === 0) {
            dom.discCached.innerHTML = '<div class="discover-empty"><i class="ti ti-box-off" style="font-size:32px; opacity:0.6; margin-bottom:12px; display:block;"></i>Tidak ada file tersimpan</div>';
        } else {
            dom.discCached.innerHTML = store.discover_cached.map(track => {
                const title = typeof cleanTrackTitle === "function" ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
                return `
                <div class="sr-item" data-vid="${escapeHtml(track.video_id || '')}">
                    <div class="sr-thumb">
                        ${track.thumbnail ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">` : '<i class="ti ti-music"></i>'}
                    </div>
                    <div class="sr-info">
                        <div class="sr-title">${title}</div>
                        <div class="sr-meta">${escapeHtml(track.artist || '')} · ${formatTime(track.duration)}</div>
                    </div>
                    <span class="sr-badge cache" style="display:inline-block">✓ Cache</span>
                </div>
            `}).join('');
        }
    }
}

function renderRadio() {
    const isRadio = store.playback_mode === 'RADIO';

    if (dom.radioToggleBtn) {
        if (isRadio) {
            dom.radioToggleBtn.classList.add("on");
            dom.radioToggleBtn.classList.remove("off");
            dom.radioToggleBtn.dataset.on = "true";
        } else {
            dom.radioToggleBtn.classList.add("off");
            dom.radioToggleBtn.classList.remove("on");
            dom.radioToggleBtn.dataset.on = "false";
        }
    }

    if (dom.rtSub) {
        dom.rtSub.textContent = isRadio
            ? 'Menyetel lagu otomatis...'
            : 'Aktifkan untuk putar otomatis';
    }


}

function renderQueue() {
    const isRadio = store.playback_mode === "RADIO";
    
    // Render the manual queue in Queue Tab
    renderList(dom.queueList, store.queue, false, store.playback_mode === "QUEUE");
    
    // Render the radio queue in Radio Tab
    if (dom.radioQueueList) {
        renderList(dom.radioQueueList, store.radio_queue, true, isRadio);
    }

    const modeStr = isRadio
        ? '<span style="color:var(--fm-green)">RADIO</span>'
        : '<span style="color:var(--fm-text-5)">QUEUE</span>';
    if (dom.queueFooter) {
        dom.queueFooter.innerHTML = "Mode: " + modeStr;
    }
}

function renderList(container, items, isRadioList, isCurrentActiveMode) {
    if (!container) return;
    
    const allItems = [];
    if (isCurrentActiveMode && store.current_track) {
        allItems.push({ track: store.current_track, index: -1, isCurrent: true });
    }
    items.forEach((track, i) => allItems.push({ track, index: i, isCurrent: false }));

    if (allItems.length === 0) {
        container.innerHTML = '<div class="queue-empty">' + (isRadioList ? "Tekan 'Acak Ulang' untuk memulai radio" : "Cari lagu atau putar dari Discover") + '</div>';
    } else {
        const existing = Array.from(container.children);
        if (existing.length === 1 && existing[0].classList.contains('queue-empty')) {
            existing[0].remove();
            existing.shift();
        }

        allItems.forEach((item, i) => {
            let el = existing[i];
            if (!el) {
                el = createQueueItemTemplate();
                container.appendChild(el);
            }
            updateQueueItem(el, item.track, item.index, item.isCurrent, isRadioList);
        });

        while (container.children.length > allItems.length) {
            container.removeChild(container.lastChild);
        }
    }
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
    div.className = "queue-item" + (isCurrent ? " current" : "") + (isRadio ? " radio-item" : "");
    if (!isCurrent && !isRadio) {
        div.dataset.index = index;
        div.setAttribute('draggable', 'true');
    } else {
        div.removeAttribute("data-index");
        div.removeAttribute('draggable');
    }
    
    if (isCurrent) {
        if (store.status === "PLAYING") {
            div.querySelector(".qi-index").innerHTML = `<div class="eq-anim-icon" style="height:12px; width:14px; gap:2px;"><span style="width:3px; background: currentColor;"></span><span style="width:3px; background: currentColor;"></span><span style="width:3px; background: currentColor;"></span></div>`;
        } else {
            div.querySelector(".qi-index").textContent = "▶";
        }
    } else {
        div.querySelector(".qi-index").textContent = index + 1;
    }
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
