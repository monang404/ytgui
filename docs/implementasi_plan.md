# bagas.fm — Implementation Plan (Agent-Ready)

**Tanggal:** 2026-06-23  
**Versi Codebase:** `ytweb` (aiohttp + Vanilla JS + CSS)  
**Referensi Desain:** `bagas_fm_ui_mockup.html`  
**Referensi Audit:** `ytweb_ui_audit.md`

---

## Aturan Kerja Agent

Sebelum menyentuh file apapun, agent harus:

1. Baca file target dari disk — jangan berasumsi dari konteks.
2. Buat perubahan **incremental per task**. Satu task = satu commit logis.
3. Jangan ubah file yang tidak disebut di task tersebut.
4. Jangan hapus kode yang tidak digantikan — komentari dulu jika ragu.
5. Test setelah tiap task: reload browser, cek console untuk error JS.
6. **Token desain wajib** — jangan hardcode warna. Gunakan CSS variables yang sudah ada (`--bg-void`, `--accent-fire`, dll) atau tambah variable baru di `:root`.

### Mapping File
```
web/static/index.html   → Struktur HTML
web/static/style.css    → Semua styling
web/static/app.js       → Semua logika JS + WebSocket
web/server.py           → WebSocket action handler + event bridge
core/command_bus.py     → Konstanta CMD_*
engine/radio_mode.py    → SEED_ARTISTS list
services/discover_service.py → DiscoverService (sudah ada, belum dipakai)
main.py                 → Inisialisasi service
```

### Design Token yang Sudah Ada (JANGAN UBAH NILAINYA)
```css
--bg-void:      #1a1a2e   /* background utama */
--bg-panel:     #16213e   /* card/panel */
--bg-elevated:  #0f3460   /* elevated element */
--accent-fire:  #e94560   /* aksen utama merah-pink */
--accent-gold:  #f59e0b   /* warning, badges */
--accent-blue:  #3b82f6   /* info, links */
--accent-green: #10b981   /* success, cache badge */
--text-primary: #f1f5f9   /* teks utama */
--text-muted:   #94a3b8   /* teks sekunder */
--text-dim:     #64748b   /* hint, placeholder */
```

---

## FASE 1 — Quick Wins (CSS + JS Only, Tanpa Perubahan Backend)

> Estimasi: 2–3 jam. Tidak butuh restart server. Semua perubahan di `web/static/`.

---

### Task 1.1 — Seek Bar: Tambah Visual Thumb

**File:** `web/static/style.css`  
**Kondisi saat ini:** `#pb-progress-fill::after` sudah ada di CSS dengan `opacity: 0`, tetapi `position: relative` belum ada di `#pb-progress-fill` sehingga pseudo-element tidak tampil dengan benar.

**Perubahan:**

Cari blok `.pb-progress-fill` di `style.css`. Pastikan ada `position: relative`:

```css
/* CARI blok ini — tambah position: relative jika belum ada */
#pb-progress-fill, .pb-progress-fill {
    height: 100%;
    background: var(--accent-fire);
    border-radius: 2px;
    position: relative;         /* ← TAMBAH INI jika belum ada */
    transition: width 0.3s linear;
}

/* Pastikan ::after sudah seperti ini (sesuai mockup: warna putih, ukuran 11px) */
#pb-progress-fill::after, .pb-progress-fill::after {
    content: '';
    position: absolute;
    right: -5px;
    top: 50%;
    transform: translateY(-50%);
    width: 11px;
    height: 11px;
    background: #fff;
    border-radius: 50%;
    opacity: 0;
    transition: opacity 150ms;
    pointer-events: none;
}

/* Tampilkan saat hover di track */
#pb-progress-track:hover #pb-progress-fill::after,
.pb-progress-track:hover .pb-progress-fill::after {
    opacity: 1;
}
```

**Tidak ada perubahan JS.** Seek click sudah berfungsi di `app.js`.

**Verifikasi:** Hover di progress bar → muncul lingkaran putih di ujung fill.

---

### Task 1.2 — Volume Slider (Ganti 2 Tombol Jadi Range Input)

**File:** `web/static/index.html` — bagian `pb-secondary-controls` kiri  
**File:** `web/static/style.css` — tambah class `.vol-grp` dan `.vol-slider`  
**File:** `web/static/app.js` — update `dom` cache + tambah event listener

#### 1.2a — HTML (`index.html`)

Cari blok ini (volume control kiri di player bar):
```html
<div class="pb-secondary-controls">
    <button class="pb-btn" id="btn-voldown" title="Volume -">🔉</button>
    <span class="pb-vol-label" id="pb-vol-label">80%</span>
    <button class="pb-btn" id="btn-volup" title="Volume +">🔊</button>
</div>
```

Ganti dengan:
```html
<div class="pb-secondary-controls vol-grp">
    <span class="vol-icon">🔉</span>
    <input type="range" id="vol-slider" class="vol-slider" min="0" max="100" value="80">
    <span class="pb-vol-label" id="pb-vol-label">80%</span>
</div>
```

> **PENTING:** Elemen `btn-voldown` dan `btn-volup` dihapus dari HTML, jadi hapus juga dari `dom` cache di `app.js`. Tombol volume keyboard (ArrowUp/ArrowDown) tetap berfungsi karena pakai `wsSend("volume_up")` langsung.

#### 1.2b — CSS (`style.css`)

Tambahkan di bagian player bar styles:
```css
.vol-grp {
    display: flex;
    align-items: center;
    gap: 5px;
    flex: 1;
}

.vol-icon {
    font-size: 15px;
    color: var(--text-dim);
}

.vol-slider {
    width: 65px;
    height: 3px;
    cursor: pointer;
    accent-color: var(--accent-fire);
    border-radius: 2px;
}
```

#### 1.2c — JS (`app.js`)

**Bagian 1: Update `dom` cache.** Cari objek `dom = { ... }`:
- Hapus: `btnVolDown: $("btn-voldown")`, `btnVolUp: $("btn-volup")`
- Tambah: `volSlider: $("vol-slider")`

**Bagian 2: Hapus event listener lama.**  
Cari dan hapus:
```js
dom.btnVolUp.addEventListener('click', () => { ... });
dom.btnVolDown.addEventListener('click', () => { ... });
```

**Bagian 3: Tambah event listener baru** (setelah blok keyboard shortcuts atau di bagian Player Controls):
```js
// Volume slider — update label real-time, kirim ke server saat selesai geser
dom.volSlider.addEventListener('input', () => {
    store.volume = parseInt(dom.volSlider.value);
    dom.pbVolLabel.textContent = store.volume + '%';
});
dom.volSlider.addEventListener('change', () => {
    // Kirim set volume absolut. Backend akan diupdate di Fase 2.2
    // Sementara, kirim volume_up/down tidak cocok untuk slider.
    // Gunakan volume_set jika sudah ada, atau skip send sampai Fase 2.2.
    if (typeof wsSend === 'function') {
        wsSend('volume_set', { volume: store.volume });
    }
});
```

**Bagian 4: Update `renderPlayerBar()`.**  
Cari baris `dom.pbVolLabel.textContent = store.volume + '%';`  
Tambah setelah baris itu:
```js
if (dom.volSlider) dom.volSlider.value = store.volume;
```

> **CATATAN Backend (Fase 2.2):** Saat ini `volume_set` action belum ada di `web/server.py`. Slider akan mengirim command yang di-ignore server sampai backend ditambahkan. Keyboard shortcut ArrowUp/ArrowDown tetap berfungsi via `volume_up`/`volume_down`.

**Verifikasi:** Geser slider → label persentase berubah real-time.

---

### Task 1.3 — Now Playing: Tambah Thumbnail + Metadata

**File:** `web/static/index.html` — `#tab-home`  
**File:** `web/static/style.css` — tambah class `.np-header`, `.np-thumbnail`, dll  
**File:** `web/static/app.js` — update `renderNowPlaying()`

#### 1.3a — HTML (`index.html`)

Cari section `#tab-home`:
```html
<section id="tab-home" class="tab-panel active">
    <canvas id="eq-canvas" width="280" height="140"></canvas>
    <div class="np-title" id="np-title">Belum ada lagu yang diputar</div>
    <div class="np-artist" id="np-artist">Cari lagu untuk memulai</div>
</section>
```

Ganti dengan:
```html
<section id="tab-home" class="tab-panel active">
    <!-- Now Playing Header: thumbnail + metadata -->
    <div class="np-header" id="np-header">
        <div class="np-thumbnail" id="np-thumbnail">
            <span class="np-thumb-fallback">🎵</span>
        </div>
        <div class="np-track-meta">
            <div class="np-title" id="np-title">Belum ada lagu yang diputar</div>
            <div class="np-artist" id="np-artist">Cari lagu untuk memulai</div>
            <div class="np-dur-meta" id="np-dur-meta"></div>
        </div>
    </div>

    <!-- EQ Canvas — lebih compact -->
    <canvas id="eq-canvas" width="280" height="80"></canvas>

    <!-- Section "Baru Diputar" — akan diisi JS -->
    <div class="section-label">Baru Diputar</div>
    <div class="discover-row" id="recent-row">
        <div class="discover-empty">Belum ada riwayat</div>
    </div>
</section>
```

> **PENTING:** Canvas height berubah dari 140 → 80. Tidak ada perubahan JS untuk EQ karena EQ menggunakan `canvas.height` secara dinamis.

#### 1.3b — CSS (`style.css`)

Tambahkan:
```css
/* Now Playing Header */
.np-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px 10px;
}

.np-thumbnail {
    width: 72px;
    height: 72px;
    border-radius: 12px;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    flex-shrink: 0;
    overflow: hidden;
}

.np-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 12px;
}

.np-track-meta {
    flex: 1;
    min-width: 0;
}

.np-thumb-fallback {
    font-size: 28px;
}

.np-dur-meta {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 4px;
}

/* Section labels */
.section-label {
    font-size: 11px;
    color: var(--text-dim);
    padding: 10px 16px 6px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Discover row di Now Playing */
.discover-row {
    display: flex;
    gap: 10px;
    padding: 0 14px 4px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.discover-row::-webkit-scrollbar { display: none; }

.disc-card {
    background: var(--bg-panel);
    border-radius: 12px;
    min-width: 108px;
    overflow: hidden;
    flex-shrink: 0;
    cursor: pointer;
}
.disc-card:hover { background: var(--bg-elevated); }

.disc-thumb {
    width: 108px;
    height: 72px;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    position: relative;
    overflow: hidden;
}
.disc-thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.disc-tag {
    position: absolute;
    top: 4px;
    right: 4px;
    font-size: 9px;
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-green);
    padding: 1px 5px;
    border-radius: 3px;
}

.disc-info { padding: 6px 8px; }

.disc-title {
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-primary);
}

.disc-artist {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 1px;
}

.discover-empty {
    font-size: 12px;
    color: var(--text-dim);
    padding: 8px 0;
}
```

#### 1.3c — JS (`app.js`)

**Bagian 1: Tambah ke `dom` cache:**
```js
npThumbnail: $('np-thumbnail'),
npDurMeta:   $('np-dur-meta'),
recentRow:   $('recent-row'),
```

**Bagian 2: Update `renderNowPlaying()`.**  
Cari fungsi `renderNowPlaying()` dan ganti isinya:
```js
function renderNowPlaying() {
    const t = store.current_track;

    // Thumbnail
    const thumbEl = dom.npThumbnail;
    if (thumbEl) {
        if (t && t.thumbnail) {
            thumbEl.innerHTML = `<img src="${escapeHtml(t.thumbnail)}" alt="" loading="lazy">`;
        } else {
            thumbEl.innerHTML = '<span class="np-thumb-fallback">🎵</span>';
        }
    }

    // Title & Artist
    if (store.status === 'LOADING') {
        dom.npTitle.innerHTML = '<span class="spinner" style="display:inline-block;margin-right:8px;vertical-align:-3px;width:20px;height:20px;"></span> ⏳ Memuat...';
        dom.npArtist.textContent = t ? t.title : '';
    } else if (t) {
        dom.npTitle.textContent = t.title;
        dom.npArtist.textContent = t.artist;
    } else {
        dom.npTitle.textContent = 'Belum ada lagu yang diputar';
        dom.npArtist.textContent = 'Cari lagu untuk memulai';
    }

    // Duration meta
    if (dom.npDurMeta && t) {
        dom.npDurMeta.textContent = formatTime(t.duration);
    } else if (dom.npDurMeta) {
        dom.npDurMeta.textContent = '';
    }

    // Recent row — akan diupdate di Fase 2 setelah DiscoverService terhubung
    // Fase 1: tampilkan recent dari store.queue[0..3] sebagai preview sementara
    renderRecentRowFallback();
}

function renderRecentRowFallback() {
    if (!dom.recentRow) return;
    // Placeholder — akan diganti di Fase 2 dengan data dari DiscoverService
    // Tampilkan 3 item dari queue sebagai preview
    const items = (store.queue || []).slice(0, 4);
    if (items.length === 0) {
        dom.recentRow.innerHTML = '<div class="discover-empty">Belum ada riwayat</div>';
        return;
    }
    dom.recentRow.innerHTML = items.map(track => `
        <div class="disc-card" data-vid="${escapeHtml(track.video_id)}">
            <div class="disc-thumb">
                ${track.thumbnail
                    ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
                    : '🎵'}
                ${track.local_path ? '<span class="disc-tag">cache</span>' : ''}
            </div>
            <div class="disc-info">
                <div class="disc-title">${escapeHtml(track.title)}</div>
                <div class="disc-artist">${escapeHtml(track.artist)}</div>
            </div>
        </div>
    `).join('');

    // Click handler: play track
    dom.recentRow.querySelectorAll('.disc-card').forEach(card => {
        card.addEventListener('click', () => {
            const vid = card.dataset.vid;
            const track = (store.queue || []).find(t => t.video_id === vid);
            if (track) showActionModal(track);
        });
    });
}
```

**Verifikasi:** Putar lagu → thumbnail muncul di header Now Playing. Canvas EQ lebih kecil di bawah.

---

### Task 1.4 — Queue: Tambah Drag Handle Visual

**File:** `web/static/style.css` — tambah class `.qi-drag`  
**File:** `web/static/app.js` — update `createQueueItemTemplate()` dan `updateQueueItem()`

> **SCOPE TASK INI:** Hanya visual drag handle (ikon ≡). Fungsionalitas drag-to-reorder dikerjakan di Fase 3.1 karena butuh backend action `queue_reorder`.

#### 1.4a — CSS (`style.css`)

Tambahkan di bagian queue item styles:
```css
.qi-drag {
    color: var(--text-dim);
    font-size: 16px;
    cursor: grab;
    flex-shrink: 0;
    padding: 0 4px;
    opacity: 0;
    transition: opacity 150ms;
}

.queue-item:hover .qi-drag {
    opacity: 1;
}

/* Sembunyikan drag handle untuk item current dan radio */
.queue-item.current .qi-drag,
.queue-item.radio-item .qi-drag {
    display: none;
}
```

#### 1.4b — JS (`app.js`)

Cari fungsi `createQueueItemTemplate()` dan ganti:
```js
function createQueueItemTemplate() {
    const div = document.createElement('div');
    div.innerHTML = `
        <span class="qi-drag" aria-hidden="true">⠿</span>
        <span class="qi-index"></span>
        <div class="qi-info">
            <div class="qi-title"></div>
            <div class="qi-dur"></div>
        </div>
        <div class="qi-right">
            <button class="qi-remove" aria-label="Hapus">✕</button>
        </div>
    `;
    return div;
}
```

> Tidak ada perubahan lain. `updateQueueItem()` tidak perlu diubah.

**Verifikasi:** Hover queue item → ikon ≡ muncul di kiri.

---

### Task 1.5 — Lyrics: Tambah Kontrol Offset ±

**File:** `web/static/index.html` — bagian `#lyrics-panel`  
**File:** `web/static/style.css` — tambah class `.lyric-offset`  
**File:** `web/static/app.js` — tambah offset controls + event listener

#### 1.5a — HTML (`index.html`)

Cari `#lyrics-panel`:
```html
<div id="lyrics-panel">
    <button class="lyrics-toggle-btn" id="lyrics-toggle-btn">📝 Lirik ▾</button>
    <div id="lyrics-content">
        <div style="color: var(--text-dim)">Tidak ada lirik</div>
    </div>
</div>
```

Ganti dengan:
```html
<div id="lyrics-panel">
    <div class="lyric-hdr">
        <button class="lyrics-toggle-btn" id="lyrics-toggle-btn">📝 Lirik Tersinkron</button>
        <div class="lyric-offset-ctrl" id="lyric-offset-ctrl">
            <span>Offset</span>
            <button id="lyric-offset-minus" class="offset-btn" aria-label="Offset minus">−</button>
            <span id="lyric-offset-display">+0.0s</span>
            <button id="lyric-offset-plus" class="offset-btn" aria-label="Offset plus">+</button>
        </div>
    </div>
    <div id="lyrics-content">
        <div style="color: var(--text-dim)">Tidak ada lirik</div>
    </div>
</div>
```

#### 1.5b — CSS (`style.css`)

```css
.lyric-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    cursor: default;
}

.lyric-offset-ctrl {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-dim);
}

.offset-btn {
    background: var(--bg-elevated);
    border: none;
    color: var(--text-muted);
    width: 22px;
    height: 22px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.offset-btn:hover {
    background: var(--accent-fire);
    color: white;
}

#lyric-offset-display {
    min-width: 36px;
    text-align: center;
    font-variant-numeric: tabular-nums;
}
```

#### 1.5c — JS (`app.js`)

**Bagian 1: Tambah ke `dom` cache:**
```js
lyricOffsetMinus:   $('lyric-offset-minus'),
lyricOffsetPlus:    $('lyric-offset-plus'),
lyricOffsetDisplay: $('lyric-offset-display'),
```

**Bagian 2: Tambah event listeners** (setelah blok Lyrics Toggle):
```js
// Lyrics offset controls
if (dom.lyricOffsetMinus) {
    dom.lyricOffsetMinus.addEventListener('click', () => {
        if (store.userRole !== 'admin') return;
        store.lyrics_offset = (store.lyrics_offset || 0) - 0.5;
        updateOffsetDisplay();
        wsSend('lyrics_offset', { offset: store.lyrics_offset });
    });
}

if (dom.lyricOffsetPlus) {
    dom.lyricOffsetPlus.addEventListener('click', () => {
        if (store.userRole !== 'admin') return;
        store.lyrics_offset = (store.lyrics_offset || 0) + 0.5;
        updateOffsetDisplay();
        wsSend('lyrics_offset', { offset: store.lyrics_offset });
    });
}

function updateOffsetDisplay() {
    if (!dom.lyricOffsetDisplay) return;
    const val = store.lyrics_offset || 0;
    const sign = val >= 0 ? '+' : '';
    dom.lyricOffsetDisplay.textContent = sign + val.toFixed(1) + 's';
}
```

**Bagian 3: Update `renderLyrics()`** — tambah call `updateOffsetDisplay()` di awal fungsi:
```js
function renderLyrics() {
    updateOffsetDisplay();   // ← tambah baris ini di paling atas
    // ... sisa kode yang sudah ada tidak berubah ...
}
```

> **CATATAN:** Action `lyrics_offset` belum ada di `web/server.py`. Tombol akan mengirim command yang di-ignore server. Backend akan ditambahkan di Fase 2.3.

**Verifikasi:** Buka lyrics panel → tampil header "Lirik Tersinkron" dan kontrol Offset −/+.

---

## FASE 2 — Backend + UI (Medium Effort)

> Estimasi: 1 hari kerja. Perlu restart server setelah perubahan Python.

---

### Task 2.1 — Backend: CMD_VOLUME_SET

**File:** `core/command_bus.py`  
**File:** `engine/volume_service.py` (atau `engine/command_router.py`)  
**File:** `web/server.py`

#### 2.1a — `core/command_bus.py`

Cari blok konstanta CMD_*. Tambahkan setelah `CMD_VOLUME_DOWN`:
```python
CMD_VOLUME_SET    = "cmd.volume.set"       # data: int (0-100)
```

#### 2.1b — Handler di command router

Cari file yang me-handle `CMD_VOLUME_UP` dan `CMD_VOLUME_DOWN` (kemungkinan `engine/command_router.py` atau `engine/volume_service.py`). Tambahkan handler untuk `CMD_VOLUME_SET` dengan pola yang sama, misalnya:

```python
# Contoh — sesuaikan dengan pola yang ada:
@command_bus.handler(CMD_VOLUME_SET)
async def handle_volume_set(room_id: str, volume: int):
    room = room_manager.rooms.get(room_id)
    if not room: return
    volume = max(0, min(100, int(volume)))
    room.state.volume = volume
    await room.mpv.set_volume(volume)   # sesuaikan nama method
    await broadcast_state(room)
```

> Agent: baca terlebih dahulu bagaimana `CMD_VOLUME_UP` di-handle, tiru polanya persis untuk `CMD_VOLUME_SET`.

#### 2.1c — `web/server.py`

Tambah import `CMD_VOLUME_SET` di blok import command_bus.

Cari blok action handler WebSocket (sekitar baris 606–639). Tambahkan setelah `elif action == "volume_down":`:
```python
elif action == "volume_set":
    volume = data.get("volume", 80)
    await command_bus.execute(CMD_VOLUME_SET, room_id, int(volume))
```

**Verifikasi:** Geser volume slider → volume di mpv berubah, label di UI ikut.

---

### Task 2.2 — Backend: Settings Sheet + SponsorBlock Toggle

**File:** `core/command_bus.py` — tambah `CMD_SET_SPONSORBLOCK`  
**File:** `web/server.py` — tambah action handler  
**File:** `web/static/index.html` — tambah Settings Sheet HTML  
**File:** `web/static/style.css` — tambah CSS Settings Sheet  
**File:** `web/static/app.js` — tambah logika Settings Sheet

#### 2.2a — `core/command_bus.py`

Tambahkan:
```python
CMD_SET_SPONSORBLOCK = "cmd.set.sponsorblock"   # data: bool
CMD_LYRICS_OFFSET    = "cmd.lyrics.offset"       # data: float
```

#### 2.2b — Handler SponsorBlock

Di file command router, tambahkan handler untuk `CMD_SET_SPONSORBLOCK`:
```python
@command_bus.handler(CMD_SET_SPONSORBLOCK)
async def handle_set_sponsorblock(room_id: str, enabled: bool):
    room = room_manager.rooms.get(room_id)
    if not room: return
    room.state.sponsorblock_active = bool(enabled)
    # Kirim state update ke semua client
    await broadcast_state(room)
```

> Agent: baca bagaimana sponsorblock saat ini di-set di `integrations/sponsorblock.py` dan `core/state.py`. Sesuaikan agar toggle memengaruhi pemrosesan segmen secara runtime.

#### 2.2c — Handler Lyrics Offset

```python
@command_bus.handler(CMD_LYRICS_OFFSET)
async def handle_lyrics_offset(room_id: str, offset: float):
    room = room_manager.rooms.get(room_id)
    if not room: return
    room.state.lyrics_offset = float(offset)
    await broadcast_state(room)
```

#### 2.2d — `web/server.py` — tambah action handler

```python
elif action == "set_sponsorblock":
    enabled = bool(data.get("enabled", False))
    await command_bus.execute(CMD_SET_SPONSORBLOCK, room_id, enabled)

elif action == "lyrics_offset":
    offset = float(data.get("offset", 0.0))
    await command_bus.execute(CMD_LYRICS_OFFSET, room_id, offset)
```

Tambah import di blok import command_bus: `CMD_SET_SPONSORBLOCK, CMD_LYRICS_OFFSET`

#### 2.2e — HTML Settings Sheet (`index.html`)

Tambahkan **di dalam `<div id="app">`**, sebelum tag `</div>` penutup app, dan setelah `<nav id="nav-bar">`:

```html
<!-- ═══ Settings Sheet (Bottom Drawer) ═══ -->
<div id="settings-sheet" class="settings-sheet">
    <div class="ss-handle"></div>
    <div class="ss-title">Pengaturan Pemutaran</div>

    <!-- SponsorBlock Toggle -->
    <div class="ss-row">
        <div class="ss-label">
            <span class="ss-icon">🛡️</span>
            <div>
                <div class="ss-label-text">SponsorBlock</div>
                <div class="ss-label-sub">Lewati sponsor, intro, outro</div>
            </div>
        </div>
        <button class="ss-toggle" id="sb-toggle" data-on="false" aria-label="Toggle SponsorBlock">
            <div class="toggle-dot"></div>
        </button>
    </div>

    <!-- Output Audio -->
    <div class="ss-row">
        <div class="ss-label">
            <span class="ss-icon">🔊</span>
            <div>
                <div class="ss-label-text">Output Audio</div>
                <div class="ss-label-sub" id="ss-out-sub">Keluar via perangkat (mpv)</div>
            </div>
        </div>
        <button class="ss-out-btn" id="ss-out-btn">📱 Device</button>
    </div>

    <!-- Stop Button -->
    <div class="ss-row">
        <div class="ss-label">
            <span class="ss-icon">⏹️</span>
            <div>
                <div class="ss-label-text">Stop Pemutaran</div>
                <div class="ss-label-sub">Hentikan lagu sepenuhnya</div>
            </div>
        </div>
        <button class="ss-action-btn" id="ss-stop-btn">⏹ Stop</button>
    </div>

    <!-- Download Progress (hidden by default) -->
    <div class="ss-row" id="ss-dl-row" style="display:none">
        <div style="width:100%">
            <div class="ss-label" style="margin-bottom:6px">
                <span class="ss-icon">⬇️</span>
                <div>
                    <div class="ss-label-text">Mengunduh...</div>
                    <div class="ss-label-sub" id="ss-dl-track">-</div>
                </div>
            </div>
            <div class="ss-dl-bar-wrap">
                <div class="ss-dl-label">
                    <span>Progress</span>
                    <span id="ss-dl-pct">0%</span>
                </div>
                <div class="ss-dl-bar">
                    <div class="ss-dl-fill" id="ss-dl-fill" style="width:0%"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Riwayat -->
    <div class="ss-row">
        <div class="ss-label">
            <span class="ss-icon">📋</span>
            <div>
                <div class="ss-label-text">Riwayat Putar</div>
                <div class="ss-label-sub" id="ss-history-sub">0 lagu diputar</div>
            </div>
        </div>
        <button class="ss-view-btn" id="ss-history-btn">Lihat</button>
    </div>
</div>

<!-- Overlay untuk Settings Sheet -->
<div id="settings-overlay" class="settings-overlay"></div>
```

Tambahkan tombol ⚙️ di player bar. Cari bagian `pb-secondary-controls` kanan:
```html
<div class="pb-secondary-controls">
    <button class="pb-btn" id="btn-download" title="Download">⬇️</button>
    <button class="pb-btn" id="btn-help" title="Help">❓</button>
</div>
```

Tambah tombol settings:
```html
<div class="pb-secondary-controls">
    <button class="pb-btn" id="btn-settings" title="Pengaturan">⚙️</button>
    <button class="pb-btn" id="btn-download" title="Download">⬇️</button>
    <button class="pb-btn" id="btn-help" title="Help">❓</button>
</div>
```

#### 2.2f — CSS Settings Sheet (`style.css`)

```css
/* ── Settings Sheet ── */
.settings-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-panel);
    border-radius: 20px 20px 0 0;
    border-top: 1px solid var(--bg-elevated);
    padding: 16px;
    transform: translateY(100%);
    transition: transform 0.25s ease;
    z-index: 100;
    max-height: 75vh;
    overflow-y: auto;
}

.settings-sheet.open {
    transform: translateY(0);
}

.settings-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
}

.settings-overlay.active {
    display: block;
}

.ss-handle {
    width: 36px;
    height: 3px;
    background: var(--bg-elevated);
    border-radius: 2px;
    margin: 0 auto 16px;
}

.ss-title {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.ss-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--bg-void);
}
.ss-row:last-child { border-bottom: none; }

.ss-label {
    display: flex;
    align-items: center;
    gap: 10px;
}

.ss-icon { font-size: 18px; }

.ss-label-text {
    font-size: 13px;
    color: var(--text-primary);
}

.ss-label-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 1px;
}

/* Toggle button (SponsorBlock) */
.ss-toggle {
    width: 44px;
    height: 24px;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    position: relative;
    background: var(--bg-elevated);
    transition: background 0.2s;
    flex-shrink: 0;
}
.ss-toggle[data-on="true"] { background: var(--accent-fire); }

.toggle-dot {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 18px;
    height: 18px;
    background: #fff;
    border-radius: 50%;
    transition: left 0.2s;
}
.ss-toggle[data-on="true"] .toggle-dot { left: 23px; }

/* Output & action buttons */
.ss-out-btn, .ss-action-btn, .ss-view-btn {
    background: var(--bg-elevated);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 5px 12px;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    white-space: nowrap;
}
.ss-out-btn:hover, .ss-action-btn:hover, .ss-view-btn:hover {
    color: var(--text-primary);
    border-color: var(--accent-fire);
}

/* Download bar */
.ss-dl-bar-wrap {
    background: var(--bg-void);
    border-radius: 6px;
    padding: 8px 10px;
}
.ss-dl-label {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
}
.ss-dl-bar {
    height: 4px;
    background: var(--bg-elevated);
    border-radius: 2px;
}
.ss-dl-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--accent-fire), var(--accent-blue));
}
```

#### 2.2g — JS Settings Sheet (`app.js`)

**Bagian 1: Tambah ke `dom` cache:**
```js
settingsSheet:   $('settings-sheet'),
settingsOverlay: $('settings-overlay'),
btnSettings:     $('btn-settings'),
sbToggle:        $('sb-toggle'),
ssOutBtn:        $('ss-out-btn'),
ssOutSub:        $('ss-out-sub'),
ssStopBtn:       $('ss-stop-btn'),
ssDlRow:         $('ss-dl-row'),
ssDlTrack:       $('ss-dl-track'),
ssDlPct:         $('ss-dl-pct'),
ssDlFill:        $('ss-dl-fill'),
ssHistorySub:    $('ss-history-sub'),
ssHistoryBtn:    $('ss-history-btn'),
```

**Bagian 2: Fungsi buka/tutup settings:**
```js
function openSettings() {
    dom.settingsSheet.classList.add('open');
    dom.settingsOverlay.classList.add('active');
    renderSettingsSheet();
}
function closeSettings() {
    dom.settingsSheet.classList.remove('open');
    dom.settingsOverlay.classList.remove('active');
}
```

**Bagian 3: Render Settings Sheet** (dipanggil saat dibuka dan saat state berubah):
```js
function renderSettingsSheet() {
    if (!dom.settingsSheet || !dom.settingsSheet.classList.contains('open')) return;

    // SponsorBlock toggle
    if (dom.sbToggle) {
        dom.sbToggle.dataset.on = store.sponsorblock_active ? 'true' : 'false';
    }

    // Output
    if (dom.ssOutSub && dom.ssOutBtn) {
        if (store.audio_output === 'browser') {
            dom.ssOutSub.textContent = 'Keluar via browser ini';
            dom.ssOutBtn.textContent = '💻 Browser';
        } else {
            dom.ssOutSub.textContent = 'Keluar via perangkat (mpv)';
            dom.ssOutBtn.textContent = '📱 Device';
        }
    }

    // Download progress
    if (dom.ssDlRow) {
        if (store.download_progress != null) {
            dom.ssDlRow.style.display = 'flex';
            const pct = Math.round(store.download_progress * 100);
            if (dom.ssDlPct) dom.ssDlPct.textContent = pct + '%';
            if (dom.ssDlFill) dom.ssDlFill.style.width = pct + '%';
            if (dom.ssDlTrack && store.current_track) {
                dom.ssDlTrack.textContent = store.current_track.title;
            }
        } else {
            dom.ssDlRow.style.display = 'none';
        }
    }

    // History count
    if (dom.ssHistorySub) {
        dom.ssHistorySub.textContent = (store.history_count || 0) + ' lagu diputar';
    }
}
```

**Bagian 4: Event Listeners:**
```js
// Buka settings
if (dom.btnSettings) {
    dom.btnSettings.addEventListener('click', () => {
        if (dom.settingsSheet.classList.contains('open')) {
            closeSettings();
        } else {
            openSettings();
        }
    });
}

// Tutup settings via overlay
if (dom.settingsOverlay) {
    dom.settingsOverlay.addEventListener('click', closeSettings);
}

// SponsorBlock toggle
if (dom.sbToggle) {
    dom.sbToggle.addEventListener('click', () => {
        if (store.userRole !== 'admin') return;
        const newVal = dom.sbToggle.dataset.on !== 'true';
        wsSend('set_sponsorblock', { enabled: newVal });
    });
}

// Output toggle dari settings sheet
if (dom.ssOutBtn) {
    dom.ssOutBtn.addEventListener('click', () => {
        if (store.userRole !== 'admin') return;
        const newOutput = store.audio_output === 'browser' ? 'device' : 'browser';
        if (newOutput === 'browser') unlockBrowserAudio();
        wsSend('set_output', { output: newOutput });
        closeSettings();
    });
}

// Stop button
if (dom.ssStopBtn) {
    dom.ssStopBtn.addEventListener('click', () => {
        if (store.userRole !== 'admin') return;
        wsSend('stop');
        closeSettings();
    });
}
```

**Bagian 5: Tambah `renderSettingsSheet()` ke `renderFullState()`:**
```js
function renderFullState() {
    renderHeader();
    renderNowPlaying();
    renderProgress();
    renderPlayerBar();
    renderRadio();
    renderQueue();
    renderLyrics();
    renderSettingsSheet();   // ← tambah ini
}
```

**Verifikasi:** Klik ⚙️ → bottom sheet muncul. Toggle SponsorBlock → badge `SB: ON` di player bar berubah.

---

### Task 2.3 — DiscoverService: Terhubung ke WebSocket + Tab Discover

**File:** `main.py` — instantiasi `DiscoverService`  
**File:** `web/server.py` — tambah action handler `discover` + message type `discover_data`  
**File:** `web/static/index.html` — tambah tab ke-5 "Discover"  
**File:** `web/static/style.css` — tambah CSS tab Discover  
**File:** `web/static/app.js` — tambah tab handling + message handler

#### 2.3a — `main.py`

Cari bagian inisialisasi service. Tambahkan:
```python
from services.discover_service import DiscoverService

# Di dalam fungsi main(), setelah db.init():
discover_service = DiscoverService(db)

# Pass ke create_app jika perlu, atau simpan sebagai app-level:
app['discover_service'] = discover_service
```

> Agent: baca bagaimana `db` dan service lain dipass ke `create_app()` di `main.py`. Ikuti pola yang sama untuk `discover_service`.

#### 2.3b — `web/server.py`

Import:
```python
from services.discover_service import DiscoverService
```

Di dalam fungsi `create_app()`, tambahkan helper untuk serialize track:
```python
def _track_to_dict_discover(track) -> dict:
    """Sama seperti _track_to_dict tapi juga sertakan play_count jika ada."""
    d = _track_to_dict(track)
    if d and hasattr(track, 'play_count'):
        d['play_count'] = track.play_count
    return d
```

Di blok action handler WebSocket, tambahkan setelah `elif action == "set_output":`:
```python
elif action == "discover":
    discover_svc = app.get("discover_service")
    if discover_svc:
        recent = await discover_svc.get_recent(20)
        favorites = await discover_svc.get_favorites(10)
        await ws.send_str(json.dumps({
            "type": "discover_data",
            "data": {
                "recent": [_track_to_dict(t) for t in recent],
                "favorites": [_track_to_dict(t) for t in favorites],
            }
        }, ensure_ascii=False))
```

> **PENTING:** `discover_svc` diambil dari `app` object. Pastikan `main.py` menyimpannya dengan `app['discover_service'] = discover_service` (lihat 2.3a).

#### 2.3c — HTML (`index.html`)

**Tab Discover di nav:**
```html
<!-- Tambahkan sebagai tombol ke-5 di <nav id="nav-bar"> -->
<button class="nav-btn" data-tab="discover" id="nav-discover">
    <span class="nav-icon">🧭</span>
    <span>Discover</span>
</button>
```

**Tab panel Discover:**
```html
<!-- Tambahkan sebelum penutup </main> -->
<section id="tab-discover" class="tab-panel">
    <div class="section-label">Paling Sering Diputar</div>
    <div class="disc-fav-row" id="disc-fav-row">
        <div class="discover-empty">Memuat...</div>
    </div>

    <div class="section-label">Baru Diputar</div>
    <div id="disc-recent-list">
        <div class="discover-empty">Memuat...</div>
    </div>
</section>
```

#### 2.3d — CSS (`style.css`)

```css
/* Favorites row di Discover tab */
.disc-fav-row {
    display: flex;
    gap: 10px;
    padding: 0 14px 4px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.disc-fav-row::-webkit-scrollbar { display: none; }

.fav-card {
    background: var(--bg-panel);
    border-radius: 10px;
    min-width: 130px;
    overflow: hidden;
    cursor: pointer;
    padding: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}
.fav-card:hover { background: var(--bg-elevated); }

.fav-num {
    font-size: 18px;
    font-weight: 700;
    color: var(--bg-elevated);
    min-width: 24px;
    text-align: center;
}

.fav-thumb {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
    overflow: hidden;
}
.fav-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 6px; }

.fav-info { flex: 1; min-width: 0; }

.fav-title {
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-primary);
}

.fav-cnt {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 1px;
}

/* Recent list di Discover tab */
#disc-recent-list .sr-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--bg-void);
    cursor: pointer;
}
#disc-recent-list .sr-item:hover { background: var(--bg-panel); }
```

#### 2.3e — JS (`app.js`)

**Bagian 1: Tambah `discover` ke array tabs:**
```js
const tabs = ['home', 'search', 'radio', 'queue', 'discover'];
```

**Bagian 2: Tambah ke `dom` cache:**
```js
tabDiscover: $('tab-discover'),
discFavRow:  $('disc-fav-row'),
discRecentList: $('disc-recent-list'),
```

**Bagian 3: Tambah case handler di `handleServerMessage()`:**
```js
case 'discover_data':
    renderDiscoverTab(msg.data);
    break;
```

**Bagian 4: Fungsi render Discover:**
```js
function renderDiscoverTab(data) {
    // Favorites
    if (dom.discFavRow) {
        const favs = (data && data.favorites) || [];
        if (favs.length === 0) {
            dom.discFavRow.innerHTML = '<div class="discover-empty">Belum ada data</div>';
        } else {
            dom.discFavRow.innerHTML = favs.map((t, i) => `
                <div class="fav-card" data-vid="${escapeHtml(t.video_id)}">
                    <div class="fav-num">${i + 1}</div>
                    <div class="fav-thumb">
                        ${t.thumbnail
                            ? `<img src="${escapeHtml(t.thumbnail)}" alt="" loading="lazy">`
                            : '🎵'}
                    </div>
                    <div class="fav-info">
                        <div class="fav-title">${escapeHtml(t.title)}</div>
                        <div class="fav-cnt">${escapeHtml(t.artist)} · ${t.play_count || 0}×</div>
                    </div>
                </div>
            `).join('');

            dom.discFavRow.querySelectorAll('.fav-card').forEach(card => {
                card.addEventListener('click', () => {
                    const vid = card.dataset.vid;
                    const track = favs.find(t => t.video_id === vid);
                    if (track) showActionModal(track);
                });
            });
        }
    }

    // Recent
    if (dom.discRecentList) {
        const recents = (data && data.recent) || [];
        if (recents.length === 0) {
            dom.discRecentList.innerHTML = '<div class="discover-empty" style="padding:8px 14px">Belum ada riwayat</div>';
        } else {
            dom.discRecentList.innerHTML = recents.map(t => `
                <div class="sr-item" data-vid="${escapeHtml(t.video_id)}">
                    <div class="sr-thumb">
                        ${t.thumbnail
                            ? `<img src="${escapeHtml(t.thumbnail)}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover;border-radius:8px">`
                            : '🎵'}
                    </div>
                    <div class="sr-info">
                        <div class="sr-title">${escapeHtml(t.title)}</div>
                        <div class="sr-meta">${escapeHtml(t.artist)} · ${formatTime(t.duration)}</div>
                    </div>
                    <span class="sr-badge ${t.is_cached ? 'cache' : 'stream'}">${t.is_cached ? '✓ Cache' : '☁ Stream'}</span>
                </div>
            `).join('');

            dom.discRecentList.querySelectorAll('.sr-item').forEach(item => {
                item.addEventListener('click', () => {
                    const vid = item.dataset.vid;
                    const track = recents.find(t => t.video_id === vid);
                    if (track) showActionModal(track);
                });
            });
        }
    }
}
```

**Bagian 5: Request data discover saat tab dibuka.**  
Update fungsi `switchTab()`:
```js
function switchTab(tab) {
    store.active_tab = tab;
    tabs.forEach(t => {
        const panel = $('tab-' + t);
        if (panel) {
            if (t === tab) panel.classList.add('active');
            else panel.classList.remove('active');
        }
    });
    document.querySelectorAll('.nav-btn').forEach(btn => {
        if (btn.dataset.tab === tab) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    // Auto-focus search
    if (tab === 'search') setTimeout(() => dom.searchInput.focus(), 100);

    // Request discover data
    if (tab === 'discover') wsSend('discover', {});
}
```

**Verifikasi:** Klik tab Discover → muncul favorites + recent tracks dari database.

---

### Task 2.4 — Radio Tab: Seed Chips + Next Card

**File:** `web/static/index.html` — update `#tab-radio`  
**File:** `web/static/style.css` — tambah CSS chip + next-card  
**File:** `web/static/app.js` — update `renderRadio()`  
**File:** `web/server.py` — tambah action `get_seed_artists` (opsional — lihat catatan)

> **CATATAN:** SEED_ARTISTS adalah konstanta di `engine/radio_mode.py`. Cara paling sederhana adalah embed list ini langsung di JS (hardcode), tanpa perlu backend action baru. Jika di masa depan user bisa custom, baru buat backend endpoint.

#### 2.4a — HTML (`index.html`)

Ganti seluruh isi `#tab-radio`:
```html
<section id="tab-radio" class="tab-panel">
    <!-- Toggle Radio -->
    <div class="radio-toggle-wrap" id="radio-toggle-wrap">
        <div class="rt-left">
            <div class="rt-icon" id="rt-icon">📻</div>
            <div>
                <div class="rt-title">Radio Mode</div>
                <div class="rt-sub" id="rt-sub">Aktifkan untuk putar otomatis</div>
            </div>
        </div>
        <button class="radio-toggle-btn" id="radio-toggle-btn">📻 RADIO: OFF</button>
    </div>

    <!-- Next Track Card (muncul saat radio ON) -->
    <div class="next-card" id="next-card" style="display:none">
        <div class="next-header">
            <span class="next-label">Selanjutnya</span>
            <button class="next-skip" id="radio-skip-btn">⏭ Skip</button>
        </div>
        <div class="next-item" id="next-item">
            <div class="next-thumb" id="next-thumb">🎵</div>
            <div class="next-info">
                <div class="next-title" id="next-title">-</div>
                <div class="next-meta" id="next-meta">-</div>
            </div>
        </div>
    </div>

    <!-- Seed Artist Chips -->
    <div class="section-label">Benih Artis</div>
    <div class="chip-wrap" id="chip-wrap"></div>

    <!-- Tombol Acak Ulang -->
    <div class="radio-actions" style="padding: 10px 14px 0">
        <button id="radio-randomize-btn">🎲 Acak Ulang</button>
    </div>
</section>
```

> **PENTING:** Hapus `<div class="radio-info" id="radio-info">` dari DOM (tidak lagi digunakan). Update referensi `dom.radioInfo` di JS — hapus atau ganti.

#### 2.4b — CSS (`style.css`)

```css
/* Radio Toggle Wrap */
.radio-toggle-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 12px 14px 0;
    background: var(--bg-panel);
    border-radius: 14px;
    padding: 14px;
}

.rt-left {
    display: flex;
    align-items: center;
    gap: 10px;
}

.rt-icon {
    font-size: 24px;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.rt-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
}

.rt-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 1px;
}

/* Next Card */
.next-card {
    margin: 10px 14px;
    background: var(--bg-panel);
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid var(--bg-elevated);
}

.next-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px 8px;
    border-bottom: 1px solid var(--bg-void);
}

.next-label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.next-skip {
    background: none;
    border: none;
    font-size: 11px;
    color: var(--accent-fire);
    cursor: pointer;
}

.next-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
}

.next-thumb {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    overflow: hidden;
}
.next-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; }

.next-info { flex: 1; min-width: 0; }

.next-title {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.next-meta {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 1px;
}

/* Artist Chips */
.chip-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 0 14px;
    margin-bottom: 2px;
}

.chip {
    font-size: 11px;
    background: var(--bg-elevated);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 4px 10px;
    color: var(--text-muted);
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
```

#### 2.4c — JS (`app.js`)

**SEED_ARTISTS dari `engine/radio_mode.py` — embed sebagai konstanta JS:**

Tambahkan di atas IIFE atau di awal blok setelah `"use strict"`:
```js
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
```

**Update `dom` cache** — tambah:
```js
radioToggleWrap: $('radio-toggle-wrap'),
rtSub:           $('rt-sub'),
nextCard:        $('next-card'),
nextTitle:       $('next-title'),
nextMeta:        $('next-meta'),
nextThumb:       $('next-thumb'),
chipWrap:        $('chip-wrap'),
```

Hapus dari dom cache: `radioInfo` (tidak ada lagi di HTML).

**Update `renderRadio()`** — ganti seluruh fungsi:
```js
function renderRadio() {
    const isRadio = store.playback_mode === 'RADIO';

    // Toggle button
    if (dom.radioToggleBtn) {
        dom.radioToggleBtn.textContent = isRadio ? '📻 RADIO: ON' : '📻 RADIO: OFF';
        if (isRadio) dom.radioToggleBtn.classList.add('active');
        else dom.radioToggleBtn.classList.remove('active');
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
        <span class="chip">${escapeHtml(name)}</span>
    `).join('');
}
```

**Verifikasi:** Tab Radio ON → "Next Card" muncul dengan track berikutnya. Chip artis tampil di bawah.

---

## FASE 3 — Polish & Features Baru

> Estimasi: 1–2 hari. Semua item Fase 3 bersifat opsional dan independent.

---

### Task 3.1 — Stop Button di Player Bar

**Deskripsi:** Tambah tombol ⏹ langsung di player bar, bukan hanya di settings sheet.

**File:** `web/static/index.html`  
**File:** `web/static/app.js`

Di HTML, cari `pb-main-controls`:
```html
<div class="pb-main-controls">
    <button class="pb-btn" id="btn-prev" title="Previous">⏮</button>
    <button class="pb-btn play-btn" id="btn-play" title="Play/Pause">▶</button>
    <button class="pb-btn" id="btn-next" title="Next">⏭</button>
</div>
```

Tambah tombol stop:
```html
<div class="pb-main-controls">
    <button class="pb-btn" id="btn-prev" title="Previous">⏮</button>
    <button class="pb-btn play-btn" id="btn-play" title="Play/Pause">▶</button>
    <button class="pb-btn" id="btn-next" title="Next">⏭</button>
    <button class="pb-btn" id="btn-stop" title="Stop" style="font-size:14px">⏹</button>
</div>
```

Di JS, tambah ke `dom` cache: `btnStop: $('btn-stop')`  
Tambah event listener:
```js
if (dom.btnStop) {
    dom.btnStop.addEventListener('click', () => {
        if (store.userRole === 'admin') wsSend('stop');
    });
}
```

---

### Task 3.2 — Queue Drag-to-Reorder (Full Implementation)

> Ini task paling kompleks di Fase 3. Butuh backend action baru.

**File:** `core/command_bus.py` — tambah `CMD_QUEUE_REORDER`  
**File:** `web/server.py` — tambah action handler  
**File:** Command router — tambah handler  
**File:** `web/static/app.js` — implementasi drag-and-drop

#### 3.2a — Backend

`core/command_bus.py`:
```python
CMD_QUEUE_REORDER = "cmd.queue.reorder"  # data: {"from_index": int, "to_index": int}
```

Command router — handler:
```python
@command_bus.handler(CMD_QUEUE_REORDER)
async def handle_queue_reorder(room_id: str, from_index: int, to_index: int):
    room = room_manager.rooms.get(room_id)
    if not room: return
    q = room.state.queue
    if 0 <= from_index < len(q) and 0 <= to_index < len(q):
        item = q.pop(from_index)
        q.insert(to_index, item)
        # Broadcast queue update
        await broadcast_state(room)
```

`web/server.py`:
```python
elif action == "queue_reorder":
    from_idx = int(data.get("from_index", 0))
    to_idx = int(data.get("to_index", 0))
    await command_bus.execute(CMD_QUEUE_REORDER, room_id, from_idx, to_idx)
```

#### 3.2b — Frontend Drag-and-Drop

Di `app.js`, tambahkan setelah fungsi `renderQueue()`:

```js
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
```

Update `createQueueItemTemplate()` — tambah `draggable="true"` pada non-current items:
```js
// Di updateQueueItem(), tambah:
if (!isCurrent && !isRadio) {
    div.setAttribute('draggable', 'true');
} else {
    div.removeAttribute('draggable');
}
```

Panggil `initQueueDragDrop()` di bagian init (setelah wsConnect):
```js
initQueueDragDrop();
```

CSS untuk drag feedback:
```css
.queue-item.dragging { opacity: 0.4; }
.queue-item.drag-over { border-top: 2px solid var(--accent-fire); }
```

---

### Task 3.3 — Discover Tab: Tampilkan Riwayat Lengkap (History View)

**Deskripsi:** Tombol "Lihat" di Settings Sheet → buka tab Discover dan scroll ke recent list.

Di `app.js`, tambah event listener untuk `ssHistoryBtn`:
```js
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
```

---

## Checklist Implementasi

### Fase 1 (CSS + JS)
- [ ] Task 1.1: Seek bar thumb CSS visible saat hover
- [ ] Task 1.2: Volume slider menggantikan 2 tombol vol
- [ ] Task 1.3: Thumbnail tampil di Now Playing + canvas lebih kecil
- [ ] Task 1.4: Drag handle visual ≡ di queue items
- [ ] Task 1.5: Kontrol offset ± di lyrics panel

### Fase 2 (Backend + UI)
- [ ] Task 2.1: `CMD_VOLUME_SET` + handler di server + slider functional
- [ ] Task 2.2: Settings Sheet + SponsorBlock toggle + Stop button + history count
- [ ] Task 2.3: DiscoverService connected → tab Discover dengan recent + favorites
- [ ] Task 2.4: Radio tab: next-card + seed chips

### Fase 3 (Polish)
- [x] Task 3.1: Stop button di player bar
- [x] Task 3.2: Queue drag-to-reorder
- [x] Task 3.3: History view via Settings → Discover

---

## Catatan Penting untuk Agent

### Hal yang TIDAK Boleh Dilakukan
- Jangan ubah event listeners yang sudah ada untuk `auth`, `search`, modal action — tidak ada di scope ini.
- Jangan ubah WebSocket reconnect logic.
- Jangan ubah `syncBrowserAudio()` — tidak ada di scope ini.
- Jangan hapus keyboard shortcuts yang sudah ada.
- Jangan ganti `--bg-void`, `--accent-fire`, dll. Hanya tambah variable baru jika diperlukan.

### Urutan Wajib
1. Selalu baca file sebelum edit — jangan berasumsi.
2. Kerjakan task dalam urutan yang tertera. Task 1.x tidak dependensi satu sama lain, tapi task 2.x bergantung pada 1.x selesai.
3. Task 2.2 (Settings Sheet) harus selesai sebelum Task 2.1 karena tombol stop ada di settings sheet.
4. Task 2.3 (Discover) bergantung pada `main.py` diupdate untuk instantiasi `DiscoverService`.

### Saat Debug
- Jika WebSocket action tidak merespons, periksa `web/server.py` apakah action handler sudah ditambahkan.
- Jika `$('element-id')` mengembalikan `null`, pastikan elemen ada di `index.html` sebelum script dijalankan.
- Jika CSS class tidak berlaku, pastikan CSS variable yang digunakan ada di `:root`.
- Console browser adalah sumber kebenaran pertama — buka DevTools sebelum report bug.
