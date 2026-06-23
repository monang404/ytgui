# ANALISIS BUG AUDIO CLIENT — YTGUI / bagas.fm
> Tanggal: 22 Juni 2026  
> Gejala yang dilaporkan: Suara double di Windows (server+admin), tidak ada suara / suara kecil di HP client, delay panjang

---

## RINGKASAN EKSEKUTIF

Ditemukan **4 bug independen** yang saling tumpang tindih dan semuanya bersumber dari fitur **Browser Audio Streaming** yang diimplementasikan belakangan (commit `5009e8f`). Fitur ini dibangun di atas dua asumsi yang salah:

1. Redirect HTTP ke YouTube CDN bekerja dari mobile browser (tidak, karena CORS)
2. `syncBrowserAudio()` bisa dipanggil setiap 333ms tanpa efek samping (tidak, karena menyebabkan seek loop)

---

## BUG #1 — SUARA DOUBLE (Admin Windows)

### Gejala
MPV membunyikan suara lewat speaker Windows, DAN browser admin juga ikut memutar audio secara bersamaan.

### Akar Masalah: State `ytgui_local_audio` Tidak Di-reset

Fungsi `syncBrowserAudio()` menggunakan dua kondisi untuk memutuskan apakah browser harus memutar audio:

```javascript
// app.js:1024-1025
const localAudioEnabled = localStorage.getItem("ytgui_local_audio") === "true";
const isBrowser = store.userRole === "client" 
    || (store.audio_output === "browser" && localAudioEnabled);
```

**Skenario yang memicu bug:**

1. Admin pernah menekan tombol "💻 BROWSER" di sesi lalu → `ytgui_local_audio = "true"` tersimpan di localStorage browser admin
2. Di sesi baru, admin membuka halaman dan login
3. `wsConnect` `onopen` mengirim `set_output` dengan `savedOutput` dari `localStorage.ytgui_audio_output` — misalnya `"browser"`
4. Server menerima → `state.audio_output = "browser"` → MPV di-mute (`set_volume(0)`)
5. `syncBrowserAudio()` dipanggil: `isBrowser = true` (karena `audio_output === "browser"` AND `localAudioEnabled = true`)
6. Browser admin memutar audio via `/api/stream`

**Sejauh ini tidak double.** Bug terjadi saat `ytgui_local_audio` masih `"true"` dari sesi lama **tapi** `ytgui_audio_output` sudah kembali ke `"device"` (atau sebaliknya):

```
Kasus nyata: Admin tekan BROWSER → lagu jalan di browser. 
Lalu admin tekan DEVICE → set_output("device") → server: MPV volume restored
Tapi: localStorage.ytgui_local_audio MASIH "true"!
Karena: handler outputToggleBtn mengubah ytgui_local_audio hanya saat toggle ke browser=true/false
Tapi jika server restart dan audio_output kembali "device" dari state, 
localStorage.ytgui_local_audio bisa masih "true" dari sesi lama.
```

**Kasus lebih umum:** Server Windows menjalankan MPV (suara dari speaker), dan admin membuka browser. localStorage dari sesi sebelumnya masih punya `ytgui_local_audio = "true"`. State dari server bilang `audio_output = "device"` → `isBrowser = false`, tapi saat admin menekan BROWSER → kedua jalur jalan bersamaan karena MPV baru di-mute SETELAH state update diterima asinkron.

### Bukti di Kode

```javascript
// app.js:757-766 — outputToggleBtn handler
dom.outputToggleBtn.addEventListener("click", () => {
    if (store.userRole !== "admin") return;
    const newOutput = store.audio_output === "browser" ? "device" : "browser";
    localStorage.setItem("ytgui_audio_output", newOutput);
    wsSend("set_output", { output: newOutput });   // ← async, belum diproses server
    if (newOutput === "browser") {
        localStorage.setItem("ytgui_local_audio", "true");
        unlockBrowserAudio();
    } else {
        localStorage.setItem("ytgui_local_audio", "false");
    }
    syncBrowserAudio();   // ← dipanggil SEBELUM server konfirmasi!
    // Pada saat ini: store.audio_output masih nilai LAMA
    // tapi localAudioEnabled sudah diupdate
    // Race condition: isBrowser bisa salah di frame ini
});
```

`syncBrowserAudio()` dipanggil dengan `store.audio_output` masih nilai lama, tapi `ytgui_local_audio` sudah nilai baru → evaluasi `isBrowser` tidak konsisten.

---

## BUG #2 — TIDAK ADA SUARA / SUARA RANDOM DI CLIENT HP

### Gejala
Client HP yang buka via browser di IP address kadang tidak ada suara sama sekali, kadang ada tapi kecil.

### Akar Masalah A: CORS Redirect dari `/api/stream`

Endpoint `/api/stream/{video_id}` berperilaku berbeda tergantung cache:

```python
# server.py:260-288
async def handle_stream(request):
    # Kasus 1: Lagu sudah di-download → serve FileResponse (✅ OK)
    if cache_file.exists():
        return web.FileResponse(cache_file)
    
    # Kasus 2: Ada stream_url di DB → HTTP 302 redirect ke YouTube CDN (⚠️ MASALAH)
    if row and ...:
        return web.HTTPFound(row["stream_url"])  # ← REDIRECT ke googlevideo.com
    
    # Kasus 3: Minta URL baru dari yt-dlp → redirect lagi (⚠️ MASALAH + DELAY)
    url = await ytdlp.get_stream_url(video_id)
    return web.HTTPFound(url)  # ← REDIRECT ke googlevideo.com
```

Ketika client HP melakukan `audio.src = "http://192.168.x.x:8765/api/stream/VIDEO_ID"`:

1. Browser mengirim request ke server
2. Server mengirim `302 Found` ke URL seperti `https://rr3---sn-xxx.googlevideo.com/...`
3. Browser mobile mencoba mengikuti redirect ini
4. **CORS block:** YouTube CDN tidak menyertakan `Access-Control-Allow-Origin` header yang mengizinkan request dari origin `http://192.168.x.x:8765`
5. Browser mobile memblokir audio → tidak ada suara

**Mengapa kadang ada suara?** Saat lagu sudah di-download ke cache (`cache_file.exists()`), server langsung serve file lokal tanpa redirect → tidak ada masalah CORS → suara ada.

### Akar Masalah B: Seek Tidak Sinkron Setelah `audio.load()`

```javascript
// syncBrowserAudio() — urutan eksekusi yang bermasalah
audio.src = expectedSrc;
audio.load();          // ← Reset currentTime ke 0, batalkan buffering
// ...
if (audio.paused) {
    audio.play();      // ← Mulai dari detik 0
}
// Setelah ini baru cek drift:
const drift = Math.abs(audio.currentTime - store.position);
if (drift > 1.5) {
    audio.currentTime = store.position;  // ← Seek terjadi SETELAH play() sudah jalan
}
```

Ketika lagu sudah di posisi 2:30 di server, client baru membuka halaman:
1. `audio.load()` → reset ke 0
2. `audio.play()` → mulai dari detik 0 → user dengar suara dari awal lagu
3. `drift = |0 - 150| = 150 > 1.5` → seek ke detik 150
4. Seek pada streaming URL yang belum fully buffered → seek gagal / jitter
5. Hasilnya: suara mulai dari awal, lompat, atau tidak ada sama sekali

---

## BUG #3 — DELAY PANJANG DI CLIENT

### Gejala
Ada jeda 3–10 detik antara admin memulai lagu dan client bisa mendengar suara.

### Akar Masalah: `get_stream_url()` Blocking di Kunjungan Pertama

```python
# server.py handle_stream — Kasus 3
try:
    url = await ytdlp.get_stream_url(video_id)  # ← Panggil yt-dlp: 3-10 detik
    await db.upsert_track(track, stream_url=url)
    return web.HTTPFound(url)
```

Ketika client pertama kali akses `/api/stream/VIDEO_ID`:
- Jika track belum pernah di-resolve, server memanggil `yt-dlp` di thread executor
- `yt-dlp` butuh waktu 3–10 detik untuk ekstrak URL dari YouTube
- Selama itu, browser client menunggu (loading audio source)
- Baru setelah URL didapat, redirect dikirim, dan browser bisa mulai buffering
- Buffering sendiri butuh waktu lagi

**Total delay bisa 5–15 detik** sebelum audio terdengar, bahkan setelah MPV di server sudah mulai memutar dari detik pertama.

---

## BUG #4 — SEEK LOOP / GLITCH AUDIO SETIAP 333ms

### Gejala
Audio kadang terdengar stuttering/glitch terutama saat ada lag jaringan antara HP dan server.

### Akar Masalah: `syncBrowserAudio()` Dipanggil Terlalu Sering

`syncBrowserAudio()` dipanggil pada setiap pesan `"progress"` dari server:

```javascript
case "progress":
    store.position = msg.data.position;
    store.status = msg.data.status;
    renderProgress();
    renderPlayBtn();
    syncBrowserAudio();  // ← dipanggil setiap ~333ms
    break;
```

Di dalam `syncBrowserAudio()`:

```javascript
const drift = Math.abs(audio.currentTime - store.position);
if (drift > 1.5) {
    audio.currentTime = store.position;  // ← SEEK paksa
}
```

Masalahnya: `store.position` adalah posisi MPV di server. `audio.currentTime` adalah posisi browser audio yang streaming via HTTP. Keduanya **tidak akan pernah sinkron sempurna** karena:
- HTTP streaming memiliki buffer 1–5 detik
- Network jitter menambah variasi
- Seek paksa tiap 333ms membatalkan buffer yang sedang dibangun

Hasilnya: audio terdengar stuttering karena terus di-interrupt oleh seek.

---

## RINGKASAN ROOT CAUSE

```
┌─────────────────────────────────────────────────────────────────────┐
│                    POHON MASALAH                                     │
│                                                                     │
│  Desain Dasar Bermasalah:                                           │
│  /api/stream melakukan HTTP redirect ke YouTube CDN                 │
│        │                                                            │
│        ├─→ CORS: Mobile browser tidak bisa follow redirect          │
│        │         → BUG #2: Tidak ada suara di client HP             │
│        │                                                            │
│        └─→ First-hit delay: yt-dlp dipanggil saat HTTP request      │
│                  → BUG #3: Delay 5-15 detik                         │
│                                                                     │
│  State Management isBrowser Tidak Konsisten:                        │
│        │                                                            │
│        ├─→ ytgui_local_audio tidak di-reset dari server state       │
│        │         → BUG #1: Double audio admin Windows               │
│        │                                                            │
│        └─→ syncBrowserAudio() dipanggil setiap 333ms               │
│                  → BUG #4: Seek loop / stuttering                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## RENCANA PERBAIKAN

### Strategi Utama

Ganti arsitektur `/api/stream` dari **redirect** ke **proxy streaming langsung**. Ini menyelesaikan bug #2 dan #3 sekaligus. Untuk bug #1 dan #4, perbaiki logika `isBrowser` dan frekuensi seek.

---

### PERBAIKAN 1 — `web/server.py`: Proxy Stream, Jangan Redirect

**Sebelum:**
```python
# Masalah: redirect ke YouTube CDN yang di-block CORS & perlu yt-dlp on-demand
return web.HTTPFound(row["stream_url"])
```

**Sesudah** — server bertindak sebagai proxy transparan:

```python
async def handle_stream(request):
    video_id = request.match_info.get("video_id")
    if not video_id or not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
        return web.HTTPBadRequest(text="Invalid video_id")

    # ── Kasus 1: File sudah di-download ke cache lokal — serve langsung
    cache_file = CACHE_DIR / f"{video_id}.mp3"
    if cache_file.exists():
        return web.FileResponse(
            cache_file,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # ── Kasus 2: Cek DB apakah stream_url masih valid (< 6 jam)
    db = request.app["db"]
    ytdlp = request.app["ytdlp"]
    stream_url = None

    row = await db.get_track(video_id)
    if row and row.get("stream_url") and row.get("stream_url_ts"):
        if time.time() - row["stream_url_ts"] < 21600:
            stream_url = row["stream_url"]

    # ── Kasus 3: Ambil URL baru dari yt-dlp jika tidak ada
    if not stream_url:
        try:
            stream_url = await ytdlp.get_stream_url(video_id)
            track = TrackInfo(video_id=video_id, title="Temp", artist="Temp", duration=0)
            await db.upsert_track(track, stream_url=stream_url)
        except Exception as e:
            return web.HTTPInternalServerError(text=f"Gagal mencari stream: {e}")

    # ── PROXY: Teruskan request ke YouTube CDN, sertakan CORS header
    http_session = request.app.get("http_session")
    if not http_session:
        # Fallback jika session tidak tersedia
        return web.HTTPFound(stream_url)

    try:
        # Forward Range header jika ada (untuk seek di mobile)
        headers = {}
        if "Range" in request.headers:
            headers["Range"] = request.headers["Range"]

        async with http_session.get(stream_url, headers=headers) as upstream:
            # Tentukan status code (200 atau 206 Partial Content)
            resp_status = upstream.status

            response = web.StreamResponse(
                status=resp_status,
                headers={
                    "Content-Type": upstream.headers.get("Content-Type", "audio/mpeg"),
                    "Accept-Ranges": "bytes",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-store",
                }
            )
            if "Content-Range" in upstream.headers:
                response.headers["Content-Range"] = upstream.headers["Content-Range"]
            if "Content-Length" in upstream.headers:
                response.headers["Content-Length"] = upstream.headers["Content-Length"]

            await response.prepare(request)

            async for chunk in upstream.content.iter_chunked(65536):  # 64KB chunks
                await response.write(chunk)

            await response.write_eof()
            return response

    except Exception as e:
        logger.warning(f"Proxy stream error untuk {video_id}: {e}")
        # Fallback ke redirect jika proxy gagal
        return web.HTTPFound(stream_url)
```

**Tambahkan `http_session` ke app context di `create_app()`:**
```python
# Di dalam create_app(), tambahkan:
app["http_session"] = aiohttp.ClientSession()

# Dan di app cleanup / on_shutdown:
async def on_cleanup(app):
    await app["http_session"].close()
app.on_cleanup.append(on_cleanup)
```

---

### PERBAIKAN 2 — `web/static/app.js`: Perbaiki `isBrowser` dan Hapus Seek Loop

**2a. Sederhanakan `isBrowser` — jangan bergantung pada localStorage terpisah:**

```javascript
// SEBELUM — 2 kondisi berbeda yang bisa tidak konsisten
function syncBrowserAudio() {
    const localAudioEnabled = localStorage.getItem("ytgui_local_audio") === "true";
    const isBrowser = store.userRole === "client" 
        || (store.audio_output === "browser" && localAudioEnabled);
    // ...
}

// SESUDAH — satu sumber kebenaran: state dari server
function syncBrowserAudio() {
    // Client selalu pakai browser audio
    // Admin pakai browser audio hanya jika server state = "browser"
    const isBrowser = store.userRole === "client" 
        || store.audio_output === "browser";
    // ...
}
```

Hapus semua referensi ke `ytgui_local_audio` localStorage. `audio_output` dari server sudah cukup sebagai sumber kebenaran.

**2b. Seek sekali saja setelah audio siap, bukan tiap 333ms:**

```javascript
// SEBELUM — seek paksa tiap panggilan syncBrowserAudio
if (store.status === "PLAYING") {
    if (audio.paused) {
        audio.play();
    }
    const drift = Math.abs(audio.currentTime - store.position);
    if (drift > 1.5) {
        audio.currentTime = store.position;  // ← stuttering!
    }
}

// SESUDAH — seek hanya saat pertama kali load, bukan di setiap progress
let _lastLoadedVideoId = null;

function syncBrowserAudio() {
    const isBrowser = store.userRole === "client" || store.audio_output === "browser";
    const audio = getOrInitAudio();

    if (!isBrowser) {
        if (!audio.paused) audio.pause();
        return;
    }

    const track = store.current_track;
    if (!track) {
        if (!audio.paused) audio.pause();
        audio.src = "";
        _lastLoadedVideoId = null;
        return;
    }

    const expectedSrc = `${window.location.origin}/api/stream/${track.video_id}`;

    // Hanya load ulang jika track berganti (bukan setiap progress tick)
    if (_lastLoadedVideoId !== track.video_id) {
        _lastLoadedVideoId = track.video_id;
        audio.src = expectedSrc;
        
        // Seek ke posisi server saat audio siap (bukan langsung)
        audio.oncanplay = () => {
            if (store.position > 2 && Math.abs(audio.currentTime - store.position) > 2) {
                audio.currentTime = store.position;
            }
            audio.oncanplay = null;
        };
        
        audio.load();
    }

    // Update volume (boleh setiap saat, tidak ada efek samping)
    audio.volume = Math.max(0, Math.min(1, (store.volume || 80) / 100));

    // Play/pause sesuai state
    if (store.status === "PLAYING") {
        if (audio.paused && audio.src) {
            audio.play().catch(err => console.warn("Autoplay blocked:", err));
        }
        // TIDAK ada seek paksa di sini — biarkan browser buffer alami
    } else {
        if (!audio.paused) audio.pause();
    }
}
```

**2c. Perbaiki `outputToggleBtn` handler — jangan panggil `syncBrowserAudio()` sebelum server konfirmasi:**

```javascript
// SEBELUM — race condition
dom.outputToggleBtn.addEventListener("click", () => {
    if (store.userRole !== "admin") return;
    const newOutput = store.audio_output === "browser" ? "device" : "browser";
    localStorage.setItem("ytgui_audio_output", newOutput);
    wsSend("set_output", { output: newOutput });
    if (newOutput === "browser") {
        localStorage.setItem("ytgui_local_audio", "true");
        unlockBrowserAudio();
    } else {
        localStorage.setItem("ytgui_local_audio", "false");
    }
    syncBrowserAudio();  // ← race condition: store.audio_output belum diupdate
});

// SESUDAH — biarkan server state broadcast yang trigger sync
dom.outputToggleBtn.addEventListener("click", () => {
    if (store.userRole !== "admin") return;
    const newOutput = store.audio_output === "browser" ? "device" : "browser";
    if (newOutput === "browser") unlockBrowserAudio();
    wsSend("set_output", { output: newOutput });
    // Tidak panggil syncBrowserAudio() di sini.
    // Server akan broadcast state update dengan audio_output baru,
    // yang akan trigger renderFullState() → syncBrowserAudio() dengan state yang benar.
});
```

**2d. Bersihkan semua referensi `ytgui_local_audio`:**

```javascript
// Hapus baris-baris ini dari seluruh app.js:
localStorage.setItem("ytgui_local_audio", "true");
localStorage.setItem("ytgui_local_audio", "false");
localStorage.getItem("ytgui_local_audio")
// Juga hapus dari logout():
localStorage.removeItem("ytgui_local_audio");  // ← hapus ini juga tidak perlu
```

---

### PERBAIKAN 3 — `web/static/app.js`: Unlock Audio Otomatis untuk Client

Client mode tidak melakukan aksi `click` lebih dulu (langsung dari portal ke halaman utama), jadi `audio.play()` bisa diblokir browser karena belum ada user gesture.

```javascript
// SEBELUM — client tap "Client" → applyRoleUI() → tapi play() nanti bisa diblock
dom.portalClientBtn.addEventListener("click", () => {
    store.userRole = "client";
    localStorage.setItem("ytgui_user_role", "client");
    applyRoleUI();
    unlockBrowserAudio();   // ← ini sudah ada, tapi harus dipastikan SEBELUM syncBrowserAudio
    syncBrowserAudio();
});

// Pastikan urutan: unlock DULU baru sync
// (kode ini sudah benar di versi saat ini, tapi perlu dikonfirmasi)
```

Tambahkan handling error yang lebih informatif:

```javascript
function getOrInitAudio() {
    if (!localAudio) {
        localAudio = new Audio();
        localAudio.preload = "auto";
        localAudio.crossOrigin = "anonymous"; // ← TAMBAHKAN ini untuk CORS
        localAudio.onerror = (e) => {
            console.error("Browser audio error:", e, localAudio.error?.message);
            showLogToast("⚠️ Error audio: " + (localAudio.error?.message || "unknown"));
        };
    }
    return localAudio;
}
```

---

### PERBAIKAN 4 — `web/server.py`: Pre-resolve Stream URL saat Track Dimulai

Daripada menunggu client request `/api/stream`, server bisa pre-resolve URL segera setelah track mulai diputar:

```python
# Di _on_track_started callback di server.py
async def _on_track_started(track):
    # Pre-warm: resolve stream URL agar siap saat client request
    if track and track.video_id:
        asyncio.create_task(_prefetch_stream_url(track.video_id))
    
    await manager.broadcast({
        "type": "state",
        "data": _state_to_dict(state),
    })

async def _prefetch_stream_url(video_id: str):
    """Resolve dan cache stream URL di background, sebelum client request."""
    db = ...  # perlu akses db
    ytdlp = ...  # perlu akses ytdlp
    row = await db.get_track(video_id)
    if row and row.get("stream_url") and row.get("stream_url_ts"):
        if time.time() - row["stream_url_ts"] < 21600:
            return  # sudah ada, skip
    try:
        url = await ytdlp.get_stream_url(video_id)
        track = TrackInfo(video_id=video_id, title="Temp", artist="Temp", duration=0)
        await db.upsert_track(track, stream_url=url)
    except Exception as e:
        logger.warning(f"Pre-fetch stream URL gagal untuk {video_id}: {e}")
```

Dengan ini, saat client request `/api/stream/{id}` → URL sudah ada di DB → tidak perlu tunggu yt-dlp lagi → delay dari 5-15 detik menjadi < 1 detik.

---

## PRIORITAS IMPLEMENTASI

| # | Perbaikan | Dampak | Effort | Bug yang Diselesaikan |
|---|---|---|---|---|
| 1 | Proxy stream di server (Perbaikan 1) | 🔴 Critical | 2 jam | #2 (CORS), #3 (delay) |
| 2 | Hapus `ytgui_local_audio`, sederhanakan `isBrowser` (Perbaikan 2a) | 🔴 Critical | 30 menit | #1 (double audio) |
| 3 | Hapus seek loop, seek sekali setelah load (Perbaikan 2b) | 🟠 High | 1 jam | #4 (stuttering) |
| 4 | Perbaiki race condition outputToggleBtn (Perbaikan 2c) | 🟠 High | 15 menit | #1 (double audio) |
| 5 | Pre-resolve stream URL (Perbaikan 4) | 🟡 Medium | 1 jam | #3 (delay) |
| 6 | `crossOrigin = "anonymous"` (Perbaikan 3) | 🟡 Medium | 5 menit | #2 (CORS edge case) |

**Urutan pengerjaan yang disarankan:** 2a → 2c → 2b → 1 → 3 → 4

Perbaikan 2a+2c adalah perubahan JavaScript murni yang bisa dikerjakan tanpa restart server. Perbaikan 1 adalah perubahan server yang paling impactful dan sebaiknya dikerjakan setelah JS sudah stabil.

---

## CATATAN ARSITEKTUR

Setelah semua perbaikan di atas, alur audio untuk **client HP** akan menjadi:

```
Client buka browser → wsConnect → terima state (track + position)
→ syncBrowserAudio(): audio.src = /api/stream/{id}
→ Server: cek cache → proxy stream dari YouTube CDN
→ Client: buffer 1-2 detik → oncanplay → seek ke posisi → play
→ Suara mulai ±2 detik setelah halaman dibuka
```

Vs sebelumnya:
```
Client buka browser → /api/stream → yt-dlp (5-10 detik) → redirect → CORS block
→ Tidak ada suara, atau delay sangat panjang
```
