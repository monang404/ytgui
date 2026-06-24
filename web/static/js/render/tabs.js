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
        dom.npTitle.textContent = t.title;
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
            dom.discFavorites.innerHTML = '<div class="discover-empty">Belum ada data favorit</div>';
        } else {
            dom.discFavorites.innerHTML = store.discover_favorites.map((track, i) => `
                <div class="fav-card" data-vid="${escapeHtml(track.video_id || '')}">
                    <div class="fav-num">${i + 1}</div>
                    <div class="fav-thumb">
                        ${track.thumbnail
                            ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                            : '<i class="ti ti-music"></i>'}
                    </div>
                    <div class="fav-info">
                        <div class="fav-title">${escapeHtml(track.title)}</div>
                        <div class="fav-cnt">${escapeHtml(track.artist || '')} · ${track.play_count || 0}×</div>
                    </div>
                </div>
            `).join('');
        }
    }

    if (dom.discRecent && store.discover_recent) {
        if (store.discover_recent.length === 0) {
            dom.discRecent.innerHTML = '<div class="discover-empty">Belum ada riwayat</div>';
        } else {
            dom.discRecent.innerHTML = store.discover_recent.map(track => `
                <div class="disc-card" data-vid="${escapeHtml(track.video_id || '')}">
                    <div class="disc-thumb">
                        ${track.thumbnail
                            ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                            : '<i class="ti ti-music"></i>'}
                        ${track.local_path ? '<span class="disc-tag">cache</span>' : ''}
                    </div>
                    <div class="disc-info">
                        <div class="disc-title">${escapeHtml(track.title)}</div>
                        <div class="disc-artist">${escapeHtml(track.artist || '')}</div>
                    </div>
                </div>
            `).join('');
        }
    }

    if (dom.discCached && store.discover_cached) {
        if (store.discover_cached.length === 0) {
            dom.discCached.innerHTML = '<div class="discover-empty">Tidak ada file tersimpan</div>';
        } else {
            dom.discCached.innerHTML = store.discover_cached.map(track => `
                <div class="search-result-item" data-vid="${escapeHtml(track.video_id || '')}">
                    <div class="sr-thumb">
                        ${track.thumbnail
                            ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                            : '<i class="ti ti-music"></i>'}
                    </div>
                    <div class="sr-info">
                        <div class="sr-title">${escapeHtml(track.title)}</div>
                        <div class="sr-meta">${escapeHtml(track.artist || '')} · ${formatTime(track.duration)}</div>
                    </div>
                    <span class="sr-badge cache" style="display:inline-block">✓ Cache</span>
                </div>
            `).join('');
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
                    : '<i class="ti ti-music"></i>';
            }
        } else {
            dom.nextCard.style.display = 'none';
        }
    }

    renderSeedChips();
}

function renderSeedChips() {
    if (!dom.chipWrap || dom.chipWrap.children.length > 0) return;
    dom.chipWrap.innerHTML = SEED_ARTISTS.slice(0, 20).map(name => `
        <span class="chip" data-seed="${escapeHtml(name)}">${escapeHtml(name)}</span>
    `).join('');
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
        ? '<span style="color:var(--fm-green)">RADIO</span>'
        : '<span style="color:var(--fm-text-5)">QUEUE</span>';
    dom.queueFooter.innerHTML = "Mode: " + modeStr;
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
window.renderLyrics = function() {
    if (!dom.lyricsCurrent || !dom.lyricsPrev || !dom.lyricsNext) return;

    if (!store.lyrics_lines || store.lyrics_lines.length === 0) {
        if (store.lyrics_loading) {
            dom.lyricsPrev.textContent = "";
            dom.lyricsCurrent.textContent = "Mencari lirik...";
            dom.lyricsCurrent.className = "lyrics-line current lyrics-empty";
            dom.lyricsNext.textContent = "";
        } else {
            dom.lyricsPrev.textContent = "";
            dom.lyricsCurrent.textContent = "Lirik tidak tersedia";
            dom.lyricsCurrent.className = "lyrics-line current lyrics-empty";
            dom.lyricsNext.textContent = "";
        }
        return;
    }

    dom.lyricsCurrent.className = "lyrics-line current";

    const idx = store.lyrics_index || 0;
    const lines = store.lyrics_lines;

    dom.lyricsPrev.textContent = idx > 0 ? lines[idx - 1] : "";
    dom.lyricsCurrent.textContent = lines[idx] || "";
    dom.lyricsNext.textContent = idx < lines.length - 1 ? lines[idx + 1] : "";
};
