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

    if (dom.discArtists && store.discover_featured_artists) {
        if (store.discover_featured_artists.length > 0) {
            dom.discArtists.innerHTML = store.discover_featured_artists.map((artist, idx) => {
                const name = typeof cleanTrackTitle === "function" ? escapeHtml(cleanTrackTitle(artist.nama)) : escapeHtml(artist.nama);
                const hashtag = "#" + name.replace(/\s+/g, '');
                
                // Generasi gaya acak untuk Word Cloud
                const hue = Math.floor(Math.random() * 360);
                const saturation = 60 + Math.floor(Math.random() * 30);
                const lightness = 50 + Math.floor(Math.random() * 20);
                const color = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
                // Algoritma: Ukuran dasar 14px. Membesar +2px tiap kali diklik (maks 28px)
                const clicks = artist.click_count || 0;
                const bonusSize = Math.min(clicks * 2, 14); // Max +14px
                const fontSize = 14 + bonusSize; // 14px - 28px
                
                return `<div class="hashtag-pill" data-artist="${escapeHtml(artist.nama)}" style="color: ${color}; --base-size: ${fontSize}px;">${hashtag}</div>`;
            }).join('');
            
            // Event delegation untuk hashtag click
            dom.discArtists.onclick = (e) => {
                const pill = e.target.closest('.hashtag-pill');
                if (pill && pill.dataset.artist) {
                    if (store.userRole !== 'admin') {
                        if (typeof showLogToast === 'function') showLogToast("Hanya admin yang bisa memutar musik");
                        return;
                    }
                    if (typeof showLogToast === 'function') showLogToast(`Memutar playlist dari ${pill.dataset.artist}...`);
                    wsSend('enqueue_artist_songs', { artist: pill.dataset.artist });
                    if (typeof switchTab === 'function') switchTab('home');
                }
            };
        } else {
            dom.discArtists.innerHTML = '';
        }
    }

    if (dom.discGenres && store.discover_featured_genres) {
        if (store.discover_featured_genres.length > 0) {
            dom.discGenres.innerHTML = store.discover_featured_genres.map((genre, idx) => {
                const name = typeof cleanTrackTitle === "function" ? escapeHtml(cleanTrackTitle(genre.nama_genre)) : escapeHtml(genre.nama_genre);
                const hashtag = "#" + name.replace(/\s+/g, '');
                
                // Generasi gaya acak untuk Word Cloud
                const hue = Math.floor(Math.random() * 360);
                const saturation = 60 + Math.floor(Math.random() * 30);
                const lightness = 50 + Math.floor(Math.random() * 20);
                const color = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
                
                // Algoritma: Ukuran dasar 14px. Membesar +2px tiap kali diklik (maks 28px)
                const clicks = genre.click_count || 0;
                const bonusSize = Math.min(clicks * 2, 14); // Max +14px
                const fontSize = 14 + bonusSize; // 14px - 28px
                
                return `<div class="hashtag-pill" data-genre="${escapeHtml(genre.nama_genre)}" style="color: ${color}; --base-size: ${fontSize}px;">${hashtag}</div>`;
            }).join('');
            
            // Event delegation untuk hashtag click
            dom.discGenres.onclick = (e) => {
                const pill = e.target.closest('.hashtag-pill');
                if (pill && pill.dataset.genre) {
                    if (store.userRole !== 'admin') {
                        if (typeof showLogToast === 'function') showLogToast("Hanya admin yang bisa memutar musik");
                        return;
                    }
                    if (typeof showLogToast === 'function') showLogToast(`Memutar playlist dari genre ${pill.dataset.genre}...`);
                    wsSend('enqueue_genre_songs', { genre: pill.dataset.genre });
                    if (typeof switchTab === 'function') switchTab('home');
                }
            };
        } else {
            dom.discGenres.innerHTML = '';
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
        if (isRadio) {
            if (store.status === "LOADING") {
                dom.rtSub.textContent = "Mencari stasiun...";
            } else {
                dom.rtSub.textContent = "24/7 Nonstop Music";
            }
        } else {
            dom.rtSub.textContent = "Aktifkan untuk putar otomatis";
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
