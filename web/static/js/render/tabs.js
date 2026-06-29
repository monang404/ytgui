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
                    if (dom.ambientBg1 && dom.ambientBg2) {
                        const activeBg = dom.ambientBg1.classList.contains('active') ? dom.ambientBg1 : dom.ambientBg2;
                        const inactiveBg = activeBg === dom.ambientBg1 ? dom.ambientBg2 : dom.ambientBg1;
                        inactiveBg.style.backgroundImage = `url(${url})`;
                        inactiveBg.classList.add('active');
                        activeBg.classList.remove('active');
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

    if (dom.btnFavorite) {
        if (t && t.is_favorite) {
            dom.btnFavorite.classList.add("active");
        } else {
            dom.btnFavorite.classList.remove("active");
        }
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
                        <img class="lazy-cover" data-vid="${escapeHtml(track.video_id || '')}" data-title="${escapeHtml(track.title || '')}" data-artist="${escapeHtml(track.artist || '')}" data-thumb="${escapeHtml(track.thumbnail || '')}" src="" alt="">
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
                let artistName = track.artist || "";
                if (artistName.length > 25) {
                    artistName = artistName.substring(0, 22) + "...";
                }
                const trackStr = JSON.stringify(track).replace(/'/g, "&apos;");
                return `
                <div class="sr-item" data-vid="${escapeHtml(track.video_id || '')}" data-track-str='${trackStr}'>
                    <div class="sr-thumb">
                        <img class="lazy-cover" data-vid="${escapeHtml(track.video_id || '')}" data-title="${escapeHtml(track.title || '')}" data-artist="${escapeHtml(track.artist || '')}" data-thumb="${escapeHtml(track.thumbnail || '')}" src="" alt="">
                        <div class="thumb-eq-overlay">
                            <div class="eq-anim-icon">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                        ${track.local_path ? '<span class="disc-tag">cache</span>' : ''}
                    </div>
                    <div class="sr-info">
                        <div class="sr-title">${title}</div>
                        <div class="sr-meta">${escapeHtml(artistName)}</div>
                    </div>
                    <div class="sr-duration">${formatTime(track.duration)}</div>
                    <button class="sr-more-btn" aria-label="More">
                        <i class="ti ti-dots-vertical"></i>
                    </button>
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
                let artistName = track.artist || "";
                if (artistName.length > 25) {
                    artistName = artistName.substring(0, 22) + "...";
                }
                const trackStr = JSON.stringify(track).replace(/'/g, "&apos;");
                return `
                <div class="sr-item" data-vid="${escapeHtml(track.video_id || '')}" data-track-str='${trackStr}'>
                    <div class="sr-thumb">
                        <img class="lazy-cover" data-vid="${escapeHtml(track.video_id || '')}" data-title="${escapeHtml(track.title || '')}" data-artist="${escapeHtml(track.artist || '')}" data-thumb="${escapeHtml(track.thumbnail || '')}" src="" alt="">
                        <div class="thumb-eq-overlay">
                            <div class="eq-anim-icon">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                    <div class="sr-info">
                        <div class="sr-title">${title}</div>
                        <div class="sr-meta">${escapeHtml(artistName)}</div>
                    </div>
                    <div class="sr-duration">${formatTime(track.duration)}</div>
                    <button class="sr-more-btn" aria-label="More">
                        <i class="ti ti-dots-vertical"></i>
                    </button>
                </div>
            `}).join('');
        }
    }
    
    if (typeof window.loadLazyCovers === "function") {
        window.loadLazyCovers();
    }
    
    updateDiscoverPlayingState();
}

function updateDiscoverPlayingState() {
    const currentId = store.current_track && store.current_track.video_id;
    const isPlaying = store.status === "PLAYING";

    // Update Home recent items
    const homeRecentContainer = document.getElementById('home-recent-list');
    if (homeRecentContainer) {
        homeRecentContainer.querySelectorAll(".home-recent-item").forEach(item => {
            const isCurrent = currentId && item.dataset.vid === currentId;
            item.classList.toggle("current", !!isCurrent);
            item.classList.toggle("playing", !!(isCurrent && isPlaying));
        });
    }

    // Update Discover recent items
    if (dom.discRecent) {
        dom.discRecent.querySelectorAll(".sr-item").forEach(item => {
            const isCurrent = currentId && item.dataset.vid === currentId;
            item.classList.toggle("current", !!isCurrent);
            item.classList.toggle("playing", !!(isCurrent && isPlaying));
        });
    }

    // Update Discover cached items
    if (dom.discCached) {
        dom.discCached.querySelectorAll(".sr-item").forEach(item => {
            const isCurrent = currentId && item.dataset.vid === currentId;
            item.classList.toggle("current", !!isCurrent);
            item.classList.toggle("playing", !!(isCurrent && isPlaying));
        });
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
    document.body.dataset.queueEmpty = (store.queue.length === 0) ? "true" : "false";
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
                el = createQueueItemTemplate(isRadioList);
                container.appendChild(el);
            }
            updateQueueItem(el, item.track, item.index, item.isCurrent, isRadioList);
        });

        while (container.children.length > allItems.length) {
            container.removeChild(container.lastChild);
        }
        
        if (isRadioList && typeof window.loadLazyCovers === "function") {
            window.loadLazyCovers();
        }
    }
}

function createQueueItemTemplate(isRadio) {
    const div = document.createElement("div");
    if (isRadio) {
        div.className = "home-recent-item";
        div.innerHTML = `
            <div class="home-recent-thumb">
                <img class="lazy-cover" src="" alt="">
                <div class="thumb-eq-overlay">
                    <div class="eq-anim-icon">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
            <div class="home-recent-info">
                <div class="home-recent-title"></div>
                <div class="home-recent-artist"></div>
            </div>
        `;
    } else {
        div.className = "queue-item";
        div.innerHTML = `
            <span class="qi-drag" aria-hidden="true">⠿</span>
            <span class="qi-index"></span>
            <div class="qi-info">
                <div class="qi-title"></div>
                <div class="qi-dur"></div>
            </div>
            <button class="qi-remove">✕</button>
        `;
    }
    return div;
}

function updateQueueItem(div, track, index, isCurrent, isRadio) {
    if (isRadio) {
        div.className = "home-recent-item" + (isCurrent ? " current" : "") + (isCurrent && store.status === "PLAYING" ? " playing" : "");
        div.dataset.vid = track.video_id || '';
        
        const titleEl = div.querySelector(".home-recent-title");
        const artistEl = div.querySelector(".home-recent-artist");
        
        const title = typeof cleanTrackTitle === "function" ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
        if (titleEl) titleEl.textContent = title;
        if (artistEl) artistEl.textContent = (track.artist || '') + " · " + formatTime(track.duration);
        
        const img = div.querySelector(".lazy-cover");
        if (img) {
            // Only update datasets and reset cover if track changed to avoid disappear/flicker bug
            if (img.dataset.vid !== (track.video_id || '')) {
                img.dataset.vid = track.video_id || '';
                img.dataset.title = track.title || '';
                img.dataset.artist = track.artist || '';
                img.dataset.thumb = track.thumbnail || '';
                img.src = '';
                img.classList.remove('loaded');
            }
        }
    } else {
        div.className = "queue-item" + (isCurrent ? " current" : "");
        if (!isCurrent) {
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
        if (isCurrent) {
            rmBtn.style.display = "none";
        } else {
            rmBtn.style.display = "block";
            rmBtn.dataset.index = index;
        }
    }
}

function renderRecentRow() {
    const container = document.getElementById('home-recent-list');
    if (!container) return;

    const items = store.discover_recent || [];
    if (items.length === 0) {
        container.innerHTML = '<div style="padding:24px 20px; color:var(--text-3); font-size:14px; text-align:center;">Belum ada riwayat putar</div>';
        return;
    }

    const currentId = store.current_track && store.current_track.video_id;
    container.innerHTML = items.slice(0, 5).map(track => {
        const title = typeof cleanTrackTitle === 'function' ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
        const isCurrent = track.video_id && track.video_id === currentId;
        return `
        <div class="home-recent-item${isCurrent ? ' current' : ''}" data-vid="${escapeHtml(track.video_id || '')}">
            <div class="home-recent-thumb">
                <img class="lazy-cover" data-vid="${escapeHtml(track.video_id || '')}" data-title="${escapeHtml(track.title || '')}" data-artist="${escapeHtml(track.artist || '')}" data-thumb="${escapeHtml(track.thumbnail || '')}" src="" alt="">
            </div>
            <div class="home-recent-info">
                <div class="home-recent-title">${title}</div>
                <div class="home-recent-artist">${escapeHtml(track.artist || '')}</div>
            </div>
            <button class="home-recent-more" data-track='${JSON.stringify(track).replace(/'/g, "&apos;")}' aria-label="More">
                <i class="ti ti-dots-vertical"></i>
            </button>
        </div>`;
    }).join('');

    if (typeof window.loadLazyCovers === "function") {
        window.loadLazyCovers();
    }

    /* Click handlers */
    container.querySelectorAll('.home-recent-item').forEach(el => {
        el.addEventListener('click', (e) => {
            if (e.target.closest('.home-recent-more')) return;
            if (store.userRole !== 'admin') return;
            const vid = el.dataset.vid;
            if (!vid) return;
            const track = (store.discover_recent || []).find(t => t.video_id === vid);
            if (track) wsSend('play_track', track);
        });
    });

    container.querySelectorAll('.home-recent-more').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            try {
                const track = JSON.parse(btn.dataset.track);
                if (typeof showActionModal === 'function') showActionModal(track);
            } catch(_) {}
        });
    });
}
