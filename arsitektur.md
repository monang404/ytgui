# 🏛️ ARSITEKTUR SISTEM — YT Termux Player Pro v1.0

**Tipe Dokumen:** Architecture Decision Record (ADR) + System Design  
**Audience:** Developer yang akan implement atau maintain sistem ini

---

## PRINSIP ARSITEKTUR

1. **Single Event Loop** — Satu `asyncio` event loop untuk seluruh aplikasi. Tidak ada threading kecuali untuk memanggil library synchronous.
2. **Shared State, Not Shared Logic** — Modul tidak saling memanggil langsung. Semua komunikasi via `EventBus` dan `AppState`.
3. **Fail Gracefully** — Setiap integration boleh gagal tanpa menghentikan playback. SponsorBlock mati = lagu tetap jalan. Lyrics timeout = panel kosong.
4. **I/O di Executor** — `yt-dlp`, file I/O besar, dan database query blocking dijalankan di `loop.run_in_executor()`.

---

## DIAGRAM ARSITEKTUR TINGKAT TINGGI

```
┌──────────────────────────────────────────────────────────────────┐
│                    TERMUX ANDROID ENVIRONMENT                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               PYTHON ASYNCIO EVENT LOOP                 │    │
│  │                                                         │    │
│  │  ┌──────────────┐    ┌──────────────┐                  │    │
│  │  │  TUI Layer   │    │  Input Layer │                  │    │
│  │  │  (Rich Live) │    │  (aioconsole)│                  │    │
│  │  └──────┬───────┘    └──────┬───────┘                  │    │
│  │         │                   │                           │    │
│  │         └────────┬──────────┘                           │    │
│  │                  ▼                                       │    │
│  │  ┌───────────────────────────────┐                      │    │
│  │  │         AppState              │ ← Single Source      │    │
│  │  │   (dataclass, in-memory)      │   of Truth           │    │
│  │  └───────────────┬───────────────┘                      │    │
│  │                  │                                       │    │
│  │  ┌───────────────▼───────────────┐                      │    │
│  │  │           EventBus            │ ← Pub/Sub decoupled  │    │
│  │  └──┬────────┬──────┬────────┬──┘                      │    │
│  │     │        │      │        │                           │    │
│  │     ▼        ▼      ▼        ▼                           │    │
│  │  ┌──────┐ ┌─────┐ ┌──────┐ ┌──────────┐               │    │
│  │  │Queue │ │Cache│ │Lyrics│ │Autoplay  │               │    │
│  │  │Mgr   │ │Resol│ │Fetchr│ │Engine    │               │    │
│  │  └──┬───┘ └──┬──┘ └──┬───┘ └──┬───────┘               │    │
│  │     │        │        │        │                         │    │
│  │     └────────┴────────┴────────┘                         │    │
│  │                  │                                       │    │
│  │  ┌───────────────▼───────────────┐                      │    │
│  │  │      Thread Pool Executor     │ ← Sync I/O isolation │    │
│  │  │  [yt-dlp] [sqlite] [download] │                      │    │
│  │  └───────────────────────────────┘                      │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  mpv process │    │ SQLite DB    │    │ YouTube API      │  │
│  │  (IPC Socket)│    │ library.db   │    │ (via yt-dlp)     │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  EXTERNAL SERVICES                                         │ │
│  │  [SponsorBlock API] [lrclib.net] [YouTube Data]           │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## DIAGRAM ALIRAN DATA — PLAY TRACK

```
User input "[P]lay" atau search
         │
         ▼
  InputHandler.handle()
         │
         ▼
  QueueManager.play_next()
         │
         ├──► CacheResolver.resolve(track)
         │         │
         │         ├── [DB query] local_path ada & file exist?
         │         │         YES → return local_path
         │         │         NO  → check stream_url freshness
         │         │                   FRESH → return cached url
         │         │                   STALE → yt-dlp.get_stream_url()
         │         │                              → DB upsert → return url
         │         ▼
         │    resolved_uri (path atau stream URL)
         │
         ├──► MpvController.play(resolved_uri)
         │         │
         │         └── [Unix Socket IPC] → mpv process
         │
         ├──► SponsorBlock.get_segments(video_id)  [async, non-blocking]
         │         │
         │         └── store in AppState.skip_segments
         │
         ├──► LyricsFetcher.fetch(title, artist, duration)  [async]
         │         │
         │         └── bus.publish(LYRICS_UPDATED, lines)
         │
         └──► AutoplayEngine.check_queue()
                   │
                   └── if queue <= threshold AND radio_mode:
                           yt-dlp.search(related_query)
                           → AppState.queue.extend(new_tracks)
```

---

## DIAGRAM ALIRAN — GAPLESS PLAYBACK

```
TrackProgress event (position update tiap 0.5 detik)
        │
        ▼
   GaplessManager.on_progress(pos, duration)
        │
        ├── remaining = duration - pos
        │
        ├── if remaining <= PREBUFFER_THRESHOLD (15 detik):
        │       if next_track NOT yet buffered:
        │           asyncio.create_task(
        │               CacheResolver.resolve(next_track)  ← pre-resolve URL
        │           )
        │           AppState.next_uri_ready = True
        │
        └── TrackEnded event
                │
                ▼
           MpvController.play(AppState.next_uri_ready)
               → Gapless transition < 0.5 detik
```

---

## KOMPONEN DETAIL

### Layer 1: TUI Layer

| Komponen | Tanggung Jawab | Refresh Rate |
|----------|---------------|--------------|
| `Dashboard` | Root layout manager, Rich Live | 4 fps |
| `NowPlayingPanel` | Track info, equalizer animasi, progress bar | 4 fps |
| `QueuePanel` | List queue, indikator radio mode | On event |
| `LyricsPanel` | Lirik tersinkronisasi, highlight baris aktif | On event |
| `ControlsPanel` | Keyboard shortcut hints | Static |

**Pola render:** Semua panel adalah fungsi murni `render(state) → Renderable`. Tidak ada state di dalam panel. Dashboard yang mengatur timing render.

### Layer 2: Core Engine

| Komponen | Pattern | Tanggung Jawab |
|----------|---------|----------------|
| `AppState` | Dataclass, mutable singleton | Global state container |
| `EventBus` | Observer pattern | Decoupled communication |
| `QueueManager` | State machine | IDLE → LOADING → PLAYING → ENDED |
| `GaplessManager` | Timer + prefetch | Pre-resolve URI untuk zero-gap transition |

### Layer 3: Integration Adapters

Setiap adapter mengimplementasikan interface yang sama:

```python
class BaseAdapter:
    async def fetch(self, **kwargs) -> Any:
        """Gagal dengan graceful — tidak pernah raise exception ke caller."""
        try:
            return await self._fetch_impl(**kwargs)
        except Exception as e:
            await bus.publish(ERROR_OCCURRED, {"adapter": self.__class__.__name__, "error": str(e)})
            return self._default_value()

    def _default_value(self):
        return None  # Override per adapter
```

### Layer 4: Media Backend (mpv)

mpv dijalankan sebagai **proses terpisah** (bukan library), dikontrol via Unix domain socket IPC dengan protokol JSON.

**Alasan tidak embed libmpv:**
- Termux tidak menyediakan `libmpv.so` dengan Python bindings
- Proses terpisah lebih stabil: crash mpv tidak crash Python
- IPC socket memungkinkan kontrol dari Termux Widget tanpa Python runtime

**mpv startup command:**
```bash
mpv --no-video \
    --idle=yes \
    --input-ipc-server=/tmp/mpv-yt-player.sock \
    --script=/path/to/mpv-mpris/mpris.so \
    --ytdl=no \
    --volume=80 \
    --gapless-audio=yes
```

---

## KEPUTUSAN ARSITEKTUR (ADR)

### ADR-001: asyncio vs Threading

**Keputusan:** `asyncio` untuk semua I/O, `ThreadPoolExecutor` hanya untuk blocking calls.

**Alasan:** Threading di Termux Android menyebabkan race conditions yang sulit di-debug di terminal kecil. asyncio memberikan single-threaded concurrency yang deterministik. yt-dlp dan sqlite hanya dipindahkan ke executor, bukan di-thread secara bebas.

**Trade-off:** Blocking call di executor akan menunda event loop sebentar. Mitigasi: timeout pada semua executor calls.

---

### ADR-002: mpv sebagai Proses, Bukan Library

**Keputusan:** Jalankan mpv sebagai subprocess, kontrol via IPC socket.

**Alasan:**
- `python-mpv` memerlukan `libmpv.so` yang tidak tersedia di Termux ARM
- Subprocess crash isolation: Python tetap jalan jika mpv crash
- Widget shortcuts bisa kontrol mpv tanpa perlu Python runtime

**Trade-off:** Latency tambahan ~1ms per command via socket (tidak terasa oleh user).

---

### ADR-003: SQLite, Bukan Redis/JSON

**Keputusan:** SQLite dengan WAL mode untuk caching.

**Alasan:** Termux tidak punya Redis. JSON file rentan corrupt jika proses mati di tengah write. SQLite dengan WAL mode aman untuk concurrent read dari proses berbeda (mpv + Python).

---

### ADR-004: Rich Live, Bukan curses

**Keputusan:** `rich.Live` untuk TUI, bukan `curses` langsung.

**Alasan:** curses di Termux Android sering bermasalah dengan encoding dan terminal resize. Rich menangani escape codes dengan benar lintas terminal emulator (Termux, JuiceSSH, dll).

**Trade-off:** Ketergantungan pada library third-party. Mitigasi: Rich sangat mature dan stabil.

---

## KEAMANAN & PRIVACY

- Tidak ada data pengguna yang dikirim ke server eksternal kecuali:
  - video_id ke SponsorBlock (privacy policy mereka: no tracking)
  - title + artist ke lrclib.net (lyrics lookup)
- SQLite DB tersimpan lokal, tidak disinkronkan
- Stream URL dari YouTube disimpan di DB lokal dengan TTL — tidak dibagikan

---

## PERFORMANCE TARGETS

| Metrik | Target | Pengukuran |
|--------|--------|-----------|
| Cold start → audio | < 5 detik | `time python main.py` |
| Search response | < 3 detik | Timer di `ytdlp_client.search()` |
| Track transition (stream) | < 1 detik | Manual stopwatch |
| Track transition (cache) | < 0.2 detik | Manual stopwatch |
| UI refresh lag | < 50ms | Rich profiler |
| Memory footprint | < 150MB | `top -p $(pgrep python)` |
| CPU idle (playing) | < 5% | `top` saat lagu jalan tanpa interaksi |

---

## DEPENDENCY GRAPH

```
main.py
  └── Dashboard (tui)
        └── AppState (core)
              └── EventBus (core)
                    ├── QueueManager (engine)
                    │     ├── CacheResolver (cache)
                    │     │     ├── Database (cache)
                    │     │     └── YtDlpClient (engine)
                    │     └── MpvController (engine)
                    ├── AutoplayEngine (engine)
                    │     └── YtDlpClient (engine)
                    ├── LyricsFetcher (integrations)
                    └── SponsorBlock (integrations)
```

Tidak ada circular dependency. Semua dependency mengalir ke bawah, semua komunikasi ke atas melalui EventBus.
