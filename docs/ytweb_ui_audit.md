# bagas.fm — UI/UX Audit & Rencana Implementasi

**Tanggal Audit:** 2026-06-23  
**Codebase:** `ytweb` (aiohttp + Vanilla JS + CSS)  
**Auditor:** Claude Sonnet 4.6

---

## Ringkasan Eksekutif

Backend sangat mature: multi-room, per-room EventBus, SponsorBlock, LyricsFetcher, DiscoverService, audio streaming, rate limiting, session auth — semuanya sudah proper. Tapi sekitar **7 fitur backend tidak punya UI sama sekali**, dan **5 area UI existing perlu upgrade signifikan**. Prioritas utama: Now Playing yang kosong, Discover yang belum terkoneksi, dan Radio yang terlalu bare-bones.

---

## Temuan: Fitur Backend Tanpa UI

### 1. DiscoverService — Tidak Terhubung Sama Sekali
**File:** `services/discover_service.py`  
**Masalah:** `get_recent()` dan `get_favorites()` sudah bisa query SQLite (`last_played`, `play_count`), tapi `discover_service` tidak diinstansiasi di `main.py`, tidak di-expose ke server WebSocket, dan tidak ada action handler di `web/server.py`.  
**Impact:** Seluruh riwayat dan favorit user tak terlihat.  
**Fix:** Tambah `discover` action di WebSocket handler, kirim data via `state` atau response terpisah. Buat tab "Discover" di UI (5th tab).

---

### 2. Thumbnail Track — Ada di Backend, Tidak Ditampilkan
**File:** `core/state.py` → `TrackInfo.thumbnail`, `web/server.py` → `_track_to_dict()` (field `thumbnail` sudah disertakan)  
**Masalah:** `thumbnail` dikirim ke frontend via WebSocket, tersimpan di `store.current_track.thumbnail`, tapi `renderNowPlaying()` di `app.js` hanya merender teks title + artist. Canvas EQ mengisi seluruh ruang visual.  
**Impact:** Now Playing tab terasa kosong dan generik.  
**Fix:** Render thumbnail di Now Playing tab — `<img src={thumbnail}>` dengan fallback icon musik.

---

### 3. History Count — Dikirim, Tidak Ditampilkan
**File:** `web/server.py` → `_state_to_dict()` menyertakan `history_count: len(state.history)`  
**Masalah:** Nilai ini ada di `store.history_count` tapi tidak dirender di mana pun.  
**Fix:** Tampilkan di tab Discover atau Settings sheet.

---

### 4. SponsorBlock — Badge Ada, Toggle Tidak Ada
**File:** `integrations/sponsorblock.py`, `app.js` → `pb-sb-badge`  
**Masalah:** Badge `SB: ON` muncul di player bar, tapi user tidak bisa enable/disable SponsorBlock dari UI. Tidak ada `set_sponsorblock` action di WebSocket.  
**Fix:** Tambah toggle SB di Settings sheet (⚙️). Perlu endpoint baru di server.

---

### 5. Audio Output Toggle — Tombol Ada, Feedback Tidak
**File:** `app.js` → `output-toggle-btn`, `wsSend("set_output", ...)`  
**Masalah:** Tombol toggle ada, tapi tidak ada feedback visual yang jelas tentang apa yang terjadi saat switching (stream ke browser vs device mpv). User di mode Client tidak tahu output sedang apa.  
**Fix:** Settings sheet yang lebih eksplisit dengan deskripsi.

---

### 6. Radio Seeds — Tidak Terlihat User
**File:** `engine/radio_mode.py` → `SEED_ARTISTS` (53 artis Indonesia)  
**Masalah:** List artis benih sudah bagus (Peterpan, SO7, Dewa 19, dll) tapi user tidak tahu artis apa yang jadi benih, tidak bisa tambah/hapus dari UI. Hanya ada tombol "Acak Ulang".  
**Fix:** Tampilkan seed artists sebagai chips di Radio tab dengan tombol ×.

---

### 7. Lyrics Offset — State Ada, Kontrol Tidak Ada
**File:** `core/state.py` → `AppState.lyrics_offset`, dikirim via WebSocket  
**Masalah:** `lyrics_offset` ada di state dan dikirim ke browser, tapi tidak ada kontrol ± untuk adjust offset di UI.  
**Fix:** Tambah kontrol offset di lyrics panel.

---

## Temuan: UI Existing yang Perlu Upgrade

### 8. Now Playing Tab — Terlalu Minimalis
**Masalah:** Hanya canvas EQ + dua baris teks. Tidak ada thumbnail, tidak ada metadata tambahan (durasi, view count), tidak ada visual hierarki.  
**Sekarang:** EQ 280×140px → title → artist (3 elemen doang)  
**Fix:** Layout 2-kolom: thumbnail + metadata, EQ lebih compact, tambah section "Baru Diputar" di bawah.

---

### 9. Progress Bar — Tidak Ada Drag Handle
**File:** `app.js` → `pb-progress-track` click handler (seek sudah berfungsi)  
**Masalah:** Seek sudah bisa diklik, tapi tidak ada visual thumb/handle. User tidak tahu area ini bisa di-interact.  
**Fix:** Tambah elemen thumb (lingkaran kecil) yang bergerak dengan progress. CSS-only.

---

### 10. Volume Control — Hanya Dua Tombol
**Masalah:** `🔉 80% 🔊` — dua tombol step ±5. Tidak ada slider untuk kontrol presisi.  
**Fix:** Ganti jadi `<input type="range">` slim dengan label persentase. Kirim `volume_set` action (atau tetap `volume_up/down` dengan rapid fire).

---

### 11. Queue Tab — Tidak Bisa Reorder
**Masalah:** Items bisa di-remove, bisa diklik untuk play, tapi tidak bisa drag-to-reorder. Drag handle tidak ada.  
**Fix:** Tambah ikon drag di kiri tiap item + implementasi drag-and-drop sederhana. Perlu `queue_reorder` action baru di backend.

---

### 12. Radio Tab — Terlalu Sparse
**Masalah:** Toggle button + satu paragraf info + 2 tombol. Tidak ada konteks tentang lagu berikutnya, tidak ada artis chips.  
**Fix:** Preview card "Selanjutnya" + artist seed chips (lihat mockup).

---

### 13. Stop Button — Keyboard Only
**Masalah:** `S` key → stop, tapi tidak ada tombol stop di UI. User mobile tidak bisa stop.  
**Fix:** Tambah tombol stop (⏹) di player bar atau settings sheet.

---

## Rencana Implementasi

### Fase 1 — Quick Wins (CSS + JS Only, No Backend Changes)
Estimasi: 2-3 jam pengerjaan

| # | Item | File | Effort |
|---|------|------|--------|
| 1.1 | Seek bar thumb — elemen CSS | `style.css`, `app.js` | 15 menit |
| 1.2 | Volume slider `<input type=range>` | `index.html`, `style.css`, `app.js` | 30 menit |
| 1.3 | Thumbnail di Now Playing tab | `app.js` → `renderNowPlaying()` | 20 menit |
| 1.4 | Drag handle visual di Queue items | `style.css`, `app.js` → `createQueueItemTemplate()` | 20 menit |
| 1.5 | Lyrics offset `± button` | `index.html`, `app.js` | 30 menit |
| 1.6 | "Baru Diputar" section di Now Playing | `index.html`, `app.js` | 45 menit |

### Fase 2 — Backend + UI (Medium Effort)
Estimasi: 1 hari

| # | Item | Backend | Frontend | Effort |
|---|------|---------|----------|--------|
| 2.1 | Settings sheet (SponsorBlock toggle, Output, History count) | Tambah `CMD_SET_SPONSORBLOCK` | `index.html`, `app.js` | 2 jam |
| 2.2 | DiscoverService terhubung ke WebSocket | `services/discover_service.py` + `web/server.py` | Tab Discover baru (5th tab) | 3 jam |
| 2.3 | Radio seed chips display | Tidak perlu — pakai `SEED_ARTISTS` existing | Radio tab chips | 1 jam |
| 2.4 | Track "next in radio" preview | Sudah ada `radio_queue[0]` di state | Radio tab card | 30 menit |

### Fase 3 — Polish & New Features
Estimasi: 1-2 hari

| # | Item | Deskripsi |
|---|------|-----------|
| 3.1 | Queue drag-to-reorder | Drag handle + `queue_reorder` action baru |
| 3.2 | Stop button di UI | Tombol `⏹` di player bar atau Settings sheet |
| 3.3 | History view | Modal/halaman riwayat lengkap dari `DiscoverService.get_recent()` |
| 3.4 | Thumbnail cache | Service worker untuk cache thumbnail |
| 3.5 | Radio custom seeds | UI tambah/hapus artis dari seed list, simpan ke localStorage |

---

## Spesifikasi Desain (Bagi Agent Implementasi)

### Seek Bar Thumb (Fase 1.1)
```css
/* Tambahkan ke .pb-progress-fill */
#pb-progress-fill {
    position: relative;
}
#pb-progress-fill::after {
    content: '';
    position: absolute;
    right: -5px;
    top: 50%;
    transform: translateY(-50%);
    width: 11px;
    height: 11px;
    background: var(--accent-fire);
    border-radius: 50%;
    opacity: 0;
    transition: opacity 150ms;
}
#pb-progress-track:hover #pb-progress-fill::after {
    opacity: 1;
}
```

### Volume Slider (Fase 1.2)
```html
<!-- Ganti dua tombol vol di player bar dengan ini: -->
<div class="pb-vol-group">
    <span class="pb-vol-icon">🔉</span>
    <input type="range" id="vol-slider" class="vol-slider" min="0" max="100" value="80">
    <span class="pb-vol-label" id="pb-vol-label">80%</span>
</div>
```
```js
// Di app.js:
dom.volSlider.addEventListener('input', () => {
    store.volume = parseInt(dom.volSlider.value);
    dom.pbVolLabel.textContent = store.volume + '%';
});
dom.volSlider.addEventListener('change', () => {
    // Kirim volume_set jika ada, atau wsSend("volume_up/down") per-step
    wsSend("volume_set", { volume: store.volume });
});
// Perlu tambah CMD_VOLUME_SET di backend
```

### Now Playing dengan Thumbnail (Fase 1.3)
```js
// renderNowPlaying() — update section ini:
function renderNowPlaying() {
    const t = store.current_track;
    // ...existing loading state...
    
    // Tambahkan thumbnail rendering:
    const thumbEl = document.getElementById('np-thumbnail');
    if (thumbEl && t && t.thumbnail) {
        thumbEl.style.backgroundImage = `url(${t.thumbnail})`;
        thumbEl.classList.add('has-thumb');
    }
}
```
```html
<!-- Di tab-home, tambahkan sebelum canvas: -->
<div class="np-header">
    <div class="np-thumbnail" id="np-thumbnail">
        <span class="np-thumb-fallback">🎵</span>
    </div>
    <div class="np-track-meta">
        <div class="np-title" id="np-title">...</div>
        <div class="np-artist" id="np-artist">...</div>
    </div>
</div>
```

### Tab Discover (Fase 2.2)
Nav bar: tambahkan tombol ke-5 "Discover" (icon: 🧭).

WebSocket action baru: `"discover"` → server panggil `DiscoverService.get_recent(20)` + `get_favorites(10)` → kembalikan sebagai message type `"discover_data"`.

```json
{
  "type": "discover_data",
  "data": {
    "recent": [ { "video_id": "...", "title": "...", "artist": "...", "thumbnail": "...", "duration": 245 } ],
    "favorites": [ { ...track, "play_count": 47 } ],
    "cached_tracks": [ ...tracks with local_path ]
  }
}
```

### Settings Sheet (Fase 2.1)
Bottom sheet yang muncul saat klik tombol ⚙️ di player bar. Berisi:
- Toggle SponsorBlock (perlu `CMD_SET_SPONSORBLOCK` baru)
- Output selector (device/browser) — lebih eksplisit dari tombol kecil di header
- Tombol Stop (⏹)
- Riwayat: "24 lagu diputar" → link ke history view
- Download progress bar (tampil saat `store.download_progress != null`)

---

## Token Desain yang Sudah Ada (Jangan Ganti)

Dari `style.css` yang ada, gunakan token ini konsisten:

| Token | Nilai | Penggunaan |
|-------|-------|-----------|
| `--bg-void` | `#1a1a2e` | Background utama |
| `--bg-panel` | `#16213e` | Card/panel |
| `--bg-elevated` | `#0f3460` | Elevated element |
| `--accent-fire` | `#e94560` | Aksen utama (merah-pink) |
| `--accent-gold` | `#f59e0b` | Warning, badges |
| `--accent-blue` | `#3b82f6` | Info, links |
| `--accent-green` | `#10b981` | Success, cache badge |
| `--text-primary` | `#f1f5f9` | Teks utama |
| `--text-muted` | `#94a3b8` | Teks sekunder |
| `--text-dim` | `#64748b` | Hint, placeholder |

---

## Kesimpulan

Backend sudah sangat solid — tidak perlu refactor apapun. Semua yang dibutuhkan adalah:
1. **Sambungkan** DiscoverService ke WebSocket (1 file: `server.py` + 1 service call)
2. **Tambahkan** beberapa HTML element yang sudah ada datanya (thumbnail, seek thumb, volume slider)
3. **Bangun** 2 UI baru: tab Discover + Settings sheet
4. **Polish** 2 tab: Now Playing + Radio

Total estimasi: **1.5-2 hari kerja** untuk semua 3 fase.
