# 🤖 AGEN KONTEKS (INDEX) — YT Termux Player Pro v1.0

**Tipe Dokumen:** Agent Context / Developer Onboarding Index  
**Gunakan dokumen ini sebagai:** Entry point untuk AI Copilot (GitHub Copilot, Gemini, Claude) dan developer baru.  
**Terakhir diupdate:** v1.0 — Fase Pre-Development

---

## UNTUK AI COPILOT

Jika kamu adalah AI assistant yang membantu develop proyek ini, baca bagian ini dulu sebelum menulis kode apapun.

### Konteks Proyek dalam Satu Paragraf

YT Termux Player Pro adalah aplikasi CLI musik untuk Android (Termux), ditulis dalam Python 3.10+ dengan `asyncio`. Aplikasi mengontrol proses `mpv` via Unix socket IPC, mengambil audio dari YouTube via `yt-dlp` (dijalankan di thread executor karena synchronous), menyimpan cache di SQLite, dan menampilkan dashboard interaktif dengan `Rich`. Semua komunikasi antar modul melalui `EventBus` (pub/sub) dan `AppState` (shared dataclass). **Tidak boleh ada blocking call di event loop utama.**

### Aturan Kode yang TIDAK BOLEH Dilanggar

```
❌ JANGAN: import asyncio; asyncio.sleep(5)  # blocking event loop
✅ BOLEH:  await asyncio.sleep(5)

❌ JANGAN: result = yt_dlp_extract(url)  # langsung di event loop
✅ BOLEH:  result = await loop.run_in_executor(None, yt_dlp_extract, url)

❌ JANGAN: console.print("...")  # di luar Dashboard, merusak Rich Live
✅ BOLEH:  bus.publish(LOG_MESSAGE, "...")  # publish ke event, Dashboard yang print

❌ JANGAN: import engine.ytdlp_client in integrations.lyrics  # circular import
✅ BOLEH:  gunakan EventBus atau dependency injection

❌ JANGAN: try: ... except: pass  # silent failure
✅ BOLEH:  except Exception as e: await bus.publish(ERROR_OCCURRED, str(e))
```

### Stack Cheat Sheet

```python
# Cek apakah ada file lokal sebelum stream
track = state.current_track
uri = await cache_resolver.resolve(track)   # returns path atau URL

# Publish event
await bus.publish(TRACK_ENDED, {"reason": "eof"})

# Subscribe ke event
bus.subscribe(TRACK_PROGRESS, my_async_handler)

# Run blocking code safely
result = await asyncio.get_event_loop().run_in_executor(None, blocking_fn, arg1, arg2)

# Timeout untuk network calls
async with asyncio.timeout(5.0):
    data = await aiohttp_get(url)
```

---

## DOKUMEN REFERENSI

| Dokumen | Isi | Kapan Dibaca |
|---------|-----|-------------|
| `implementasi_plan.md` | Fase, milestone, kode skeleton semua modul | Sebelum mulai coding |
| `arsitektur.md` | Diagram sistem, ADR, dependency graph | Saat ragu soal struktur |
| `design.md` | Spesifikasi TUI, warna, layout, keyboard map | Saat implement layer UI |
| `agen_konteks.md` (ini) | Index cepat, context untuk AI, FAQ | Entry point pertama |

---

## PETA MODUL LENGKAP

```
ENTRY POINT
└── main.py
      ├── Inisialisasi AppState
      ├── Inisialisasi EventBus (singleton)
      ├── Start mpv subprocess
      ├── Connect MpvController ke IPC socket
      ├── asyncio.gather():
      │     ├── Dashboard.run()          ← TUI render loop
      │     ├── InputHandler.run()       ← Keyboard listener
      │     ├── MpvController.observe()  ← Event listener dari mpv
      │     └── HeartbeatTask.run()      ← Health check periodik
      └── Graceful shutdown hook

CORE (tidak ada dependency ke module lain)
├── core/state.py       → AppState, TrackInfo, PlayerStatus
├── core/event_bus.py   → EventBus singleton, konstanta event name
└── core/exceptions.py  → YtPlayerError, MpvConnectionError, dll

ENGINE (dependency: core)
├── engine/ytdlp_client.py    → search(), get_stream_url(), download_mp3()
├── engine/mpv_controller.py  → play(), pause(), seek(), volume()
├── engine/queue_manager.py   → add(), next(), prev(), clear()
├── engine/gapless_manager.py → pre-resolve URI untuk lagu berikut
└── engine/autoplay.py        → radio mode, related track injection

CACHE (dependency: core, engine.ytdlp_client)
├── cache/db.py         → aiosqlite wrapper, CRUD operations
├── cache/schema.sql    → DDL (diload saat startup)
└── cache/resolver.py   → local vs stream routing logic

INTEGRATIONS (dependency: core only — fire-and-forget pattern)
├── integrations/sponsorblock.py → get_skip_segments(video_id)
├── integrations/lyrics.py       → fetch_lyrics(title, artist, duration)
└── integrations/bluetooth.py    → MPRIS bridge, Termux API

TUI (dependency: core, read-only AppState)
├── tui/dashboard.py             → Rich Live root, layout manager
├── tui/input_handler.py         → Async keyboard, search input FSM
└── tui/panels/
      ├── now_playing.py          → Track info, equalizer, progress bar
      ├── queue_panel.py          → Queue list, radio mode indicator
      ├── lyrics_panel.py         → Synced lyrics window
      └── controls.py             → Keyboard hints footer
```

---

## EVENT CATALOG

Semua event yang beredar di EventBus. Setiap event harus terdefinisi sebagai konstanta string di `core/event_bus.py`.

### Player Events (dari mpv → Python)

| Event Constant | Data | Publisher | Subscribers |
|---------------|------|-----------|-------------|
| `TRACK_PROGRESS` | `float` (detik) | MpvController | Dashboard, GaplessManager, SponsorBlockHandler, LyricsSync |
| `TRACK_ENDED` | `{"reason": str}` | MpvController | QueueManager |
| `TRACK_STARTED` | `TrackInfo` | QueueManager | Dashboard, LyricsFetcher, SponsorBlock |
| `VOLUME_CHANGED` | `int` | MpvController | Dashboard |

### Queue Events

| Event Constant | Data | Publisher | Subscribers |
|---------------|------|-----------|-------------|
| `QUEUE_UPDATED` | `list[TrackInfo]` | QueueManager | Dashboard |
| `QUEUE_EMPTY` | `None` | QueueManager | AutoplayEngine |

### Integration Events

| Event Constant | Data | Publisher | Subscribers |
|---------------|------|-----------|-------------|
| `LYRICS_UPDATED` | `list[tuple[float, str]]` | LyricsFetcher | Dashboard |
| `LYRICS_SYNC` | `int` (active index) | LyricsSync | Dashboard |
| `SKIP_SEGMENT` | `tuple[float, float]` | SponsorBlock | MpvController |
| `SEARCH_RESULTS` | `list[TrackInfo]` | YtDlpClient | Dashboard |
| `DOWNLOAD_PROGRESS` | `{"percent": float}` | YtDlpClient | Dashboard |
| `DOWNLOAD_COMPLETE` | `str` (local_path) | YtDlpClient | CacheDB, Dashboard |

### Command Events (dari Input → Engine)

| Event Constant | Data | Publisher | Subscribers |
|---------------|------|-----------|-------------|
| `CMD_TOGGLE_PAUSE` | `None` | InputHandler | MpvController |
| `CMD_NEXT` | `None` | InputHandler | QueueManager |
| `CMD_PREV` | `None` | InputHandler | QueueManager |
| `CMD_STOP` | `None` | InputHandler | QueueManager, MpvController |
| `CMD_VOLUME_UP` | `None` | InputHandler | MpvController |
| `CMD_VOLUME_DOWN` | `None` | InputHandler | MpvController |
| `CMD_DOWNLOAD` | `None` | InputHandler | YtDlpClient |
| `CMD_SEARCH` | `str` (query) | InputHandler | YtDlpClient |
| `CMD_TOGGLE_RADIO` | `None` | InputHandler | AutoplayEngine |
| `CMD_QUEUE_SELECT` | `int` (index) | InputHandler | QueueManager |

### System Events

| Event Constant | Data | Publisher | Subscribers |
|---------------|------|-----------|-------------|
| `ERROR_OCCURRED` | `{"module": str, "error": str}` | Semua modul | Dashboard (log display) |
| `LOG_MESSAGE` | `str` | Semua modul | Dashboard (status bar) |
| `APP_SHUTDOWN` | `None` | InputHandler | Semua modul (cleanup) |

---

## ALUR STARTUP DETAIL

```python
# main.py — pseudocode alur startup

async def main():
    # 1. Setup direktori
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Init database
    db = Database(DB_PATH)
    await db.init()   # CREATE TABLE IF NOT EXISTS

    # 3. Start mpv subprocess
    mpv_proc = subprocess.Popen([
        "mpv", "--no-video", "--idle=yes",
        f"--input-ipc-server={MPV_SOCKET}",
        "--gapless-audio=yes",
        f"--volume={DEFAULT_VOLUME}",
    ])

    # 4. Connect IPC controller (retry loop 5 detik)
    mpv = MpvController()
    await mpv.connect()

    # 5. Init shared state
    state = AppState()

    # 6. Init semua komponen (inject dependencies)
    ytdlp       = YtDlpClient()
    resolver    = CacheResolver(db, ytdlp)
    queue_mgr   = QueueManager(state, mpv, resolver)
    gapless_mgr = GaplessManager(state, mpv, resolver)
    autoplay    = AutoplayEngine(ytdlp, state)
    dashboard   = Dashboard(state)
    input_hdlr  = InputHandler(state)

    # 7. Jalankan semua tasks concurrent
    try:
        await asyncio.gather(
            dashboard.run(),
            input_hdlr.run(),
            mpv.observe_events(),
            gapless_mgr.run(),
        )
    except KeyboardInterrupt:
        pass
    finally:
        # 8. Graceful shutdown
        mpv_proc.terminate()
        await db.close()
```

---

## FAQ DEVELOPER

**Q: Kenapa yt-dlp tidak dipanggil langsung di async function?**

A: yt-dlp adalah library synchronous yang melakukan blocking network I/O. Memanggil langsung di coroutine akan membekukan seluruh event loop (dan TUI) selama 2-5 detik. Selalu wrap dengan `run_in_executor`.

---

**Q: Kenapa mpv tidak pakai `python-mpv` library?**

A: `python-mpv` memerlukan `libmpv.so` shared library yang tidak tersedia di Termux ARM package manager. Alternatif: kontrol via Unix socket IPC (sudah built-in di mpv).

---

**Q: Bagaimana jika mpv crash saat lagu diputar?**

A: `MpvController._observe_events()` akan exit ketika koneksi socket terputus. `QueueManager` menangkap `MpvConnectionError` dan mencoba restart mpv subprocess, kemudian reconnect. Max 3 retry, setelah itu publish `ERROR_OCCURRED` dengan instruksi manual restart.

---

**Q: Bagaimana lirik disinkronisasi tanpa polling ketat?**

A: `TRACK_PROGRESS` event dipublish setiap ~0.5 detik dari `MpvController`. `LyricsSync` subscribe ke event ini, cari index baris aktif dengan binary search O(log n), dan publish `LYRICS_SYNC` hanya jika index berubah. Dashboard hanya re-render lyrics panel saat ada `LYRICS_SYNC` event.

---

**Q: Kenapa Rich Live bukan curses?**

A: curses di Termux sering bermasalah dengan `TERM=xterm-256color` dan resize event. Rich menangani ini otomatis dan lebih mudah di-compose (setiap panel adalah Renderable terpisah).

---

**Q: Bagaimana menambahkan fitur baru?**

Ikuti pola ini:
1. Tambah event constant baru di `core/event_bus.py`
2. Buat modul baru di layer yang sesuai (engine/integration/tui)
3. Subscribe/publish via `bus` — jangan import langsung modul lain di tier yang sama
4. Update `AppState` jika fitur memerlukan shared state
5. Update `main.py` untuk inject dependency baru
6. Tambah ke event catalog di dokumen ini

---

## CHECKLIST SEBELUM COMMIT

```
□ Tidak ada blocking call di event loop (cek dengan asyncio.debug mode)
□ Semua network call punya timeout
□ Semua exception di-catch dan di-publish ke ERROR_OCCURRED
□ Tidak ada console.print() di luar Dashboard
□ Type hints lengkap di function signature
□ Docstring singkat di setiap class
□ Tidak ada hardcoded path (semua dari config.py)
□ Test manual: jalankan, cari lagu, putar, next, volume
```

---

## ENVIRONMENT VARIABLES (Opsional)

```bash
# ~/.bashrc atau ~/.zshrc

export YT_PLAYER_SOCKET="/tmp/mpv-yt-player.sock"   # override default socket path
export YT_PLAYER_CACHE="$HOME/Music/yt-player"       # override cache dir
export YT_PLAYER_VOLUME="70"                          # default volume
export YT_PLAYER_RADIO="1"                            # default radio mode on
export NO_COLOR="1"                                   # disable warna (accessibility)
```

---

## GLOSSARY

| Term | Definisi |
|------|---------|
| **event loop** | asyncio's single-threaded concurrency engine |
| **executor** | Thread pool untuk menjalankan synchronous code tanpa blocking event loop |
| **IPC socket** | Inter-Process Communication via Unix domain socket |
| **gapless** | Transisi antar lagu tanpa jeda (silence 0ms) |
| **prebuffer** | Pre-resolve URI lagu berikutnya sebelum lagu saat ini selesai |
| **TTL** | Time-To-Live — berapa lama cache URL dianggap valid |
| **WAL mode** | Write-Ahead Logging — SQLite mode yang aman untuk concurrent access |
| **MPRIS** | Media Player Remote Interfacing Specification — standar Linux untuk kontrol media player |
| **SponsorBlock** | Layanan community untuk menandai dan skip segmen non-musik di YouTube |
| **LRC** | Format file lirik dengan timestamp `[mm:ss.xx]` |
| **radio mode** | Infinite autoplay — queue otomatis terisi dari related tracks |
