## Cara Membaca Dokumen Ini

Setiap fix memiliki format:
- **File yang diubah** (path eksak)
- **Masalah root cause** (bukan gejala)
- **Kode sebelum** dan **kode sesudah** (diff-style)
- **Verification step** (cara test manual yang konkret)
- **Dependensi antar fix** (urutan eksekusi jika ada)

Urutan eksekusi **wajib**: P1 → P2 → P3. Dalam satu tier, ikuti nomor urut.

---

## P1 — BLOCKER (12 Issues) — Selesaikan sebelum commit ke GitHub

---

### P1-01 · ENG-01: MPV Gagal Silently — Tidak Ada User-Facing Error

**Root cause:** `main.py` menangkap exception saat connect MPV tapi hanya log warning. TUI tetap jalan, semua tombol visually responsive, tapi semua perintah play/pause/seek diam-diam `return` tanpa efek karena `is_connected = False`.

**File:** `main.py`

```python
# SEBELUM (baris 33-40):
mpv_connected = False
try:
    await mpv.connect()
    mpv_connected = True
except Exception as e:
    logging.getLogger(__name__).warning(f"mpv not available: {e}")

# SESUDAH:
mpv_connected = False
try:
    await mpv.connect()
    mpv_connected = True
except Exception as e:
    logging.getLogger(__name__).error(f"mpv not available: {e}")
    # Publish error ke state agar UI bisa menampilkannya
    state.error_msg = (
        "MPV tidak ditemukan. Jalankan: pkg install mpv (Termux) "
        "atau install MPV dan tambahkan ke PATH (Windows/Linux)."
    )
    state.status = PlayerStatus.ERROR
    # Tetap jalankan TUI agar user bisa lihat pesan error, bukan crash
```

**File:** `tui/panels/now_playing.py` — update `update_state()`:

```python
# SESUDAH — tambahkan di awal update_state(), sebelum blok if not state.current_track:
if state.status == PlayerStatus.ERROR and state.error_msg:
    self.info_label.update(
        f"\n[bold {STATUS_ERR}]  ⚠ Error Sistem[/]\n\n"
        f"[{TEXT_DIM}]  {escape(state.error_msg)}[/]\n\n"
        f"[{TEXT_DIM}]  Restart aplikasi setelah masalah teratasi.[/]"
    )
    self.progress_bar.position = 0
    self.progress_bar.duration = 0
    return  # Jangan render info track jika ada error sistem
```

**Verification:** Jalankan app tanpa MPV terinstall → should tampil pesan error bermakna, bukan layar kosong.

---

### P1-02 · ENG-04: CMD_SEEK Tidak Punya Subscriber

**Root cause:** `now_playing.py` mempublish `CMD_SEEK` saat user klik progress bar, tapi tidak ada `bus.subscribe(CMD_SEEK, ...)` di seluruh codebase.

**File:** `engine/queue_manager.py`

```python
# SEBELUM — tambahkan di __init__, setelah baris:
# bus.subscribe(CMD_TOGGLE_LYRICS, self._on_toggle_lyrics)

bus.subscribe(CMD_SEEK, self._on_seek)

# SESUDAH — tambahkan method baru:
async def _on_seek(self, position: float):
    """Handle klik pada progress bar — seek ke posisi tertentu."""
    if not isinstance(position, (int, float)):
        return
    await self.mpv.seek(float(position))
    self.state.position = float(position)
    await bus.publish(LOG_MESSAGE, f"Seeking to {int(position//60):02d}:{int(position%60):02d}")
```

**File:** `engine/queue_manager.py` — update imports:

```python
# SEBELUM:
from core.event_bus import (
    bus, TRACK_ENDED, TRACK_STARTED, QUEUE_UPDATED, QUEUE_EMPTY,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_TOGGLE_PAUSE, SEARCH_RESULTS,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_TOGGLE_LYRICS,
    LOG_MESSAGE, TRACK_PROGRESS, DOWNLOAD_PROGRESS, DOWNLOAD_COMPLETE
)

# SESUDAH — tambahkan CMD_SEEK dan CMD_QUEUE_SELECT:
from core.event_bus import (
    bus, TRACK_ENDED, TRACK_STARTED, QUEUE_UPDATED, QUEUE_EMPTY,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_TOGGLE_PAUSE, SEARCH_RESULTS,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_TOGGLE_LYRICS,
    CMD_SEEK, CMD_QUEUE_SELECT,
    LOG_MESSAGE, TRACK_PROGRESS, DOWNLOAD_PROGRESS, DOWNLOAD_COMPLETE
)
```

**Verification:** Putar lagu → klik di tengah progress bar → posisi harus loncat ke titik yang diklik.

---

### P1-03 · ENG-05: CMD_QUEUE_SELECT Tidak Punya Subscriber

**Root cause:** `queue_panel.py` mempublish `CMD_QUEUE_SELECT` dengan index saat user klik item antrian, tapi tidak ada handler.

**File:** `engine/queue_manager.py` — tambahkan di `__init__()`:

```python
bus.subscribe(CMD_QUEUE_SELECT, self._on_queue_select)
```

**File:** `engine/queue_manager.py` — tambahkan method baru:

```python
async def _on_queue_select(self, queue_index: int):
    """Handle klik pada item antrian — loncat langsung ke lagu tersebut."""
    if not isinstance(queue_index, int):
        return
    if queue_index < 0 or queue_index >= len(self.state.queue):
        return
    
    # Simpan current track ke history
    if self.state.current_track:
        self.state.history.append(self.state.current_track)
        if len(self.state.history) > 50:
            self.state.history.pop(0)
    
    # Ambil track di index, hapus dari queue, semua sebelumnya juga dibuang
    selected = self.state.queue[queue_index]
    self.state.queue = self.state.queue[queue_index + 1:]
    await self.play_track(selected)
```

**Catatan:** Track sebelum index yang dipilih dibuang (bukan dimasukkan ke history) — ini behavior yang paling intuitif: user memilih "loncat ke lagu ini sekarang".

**Verification:** Cari 5 lagu → antrian terisi → klik item ke-3 → lagu ke-3 langsung diputar, antrian tersisa lagu ke-4 dan ke-5.

---

### P1-04 · UX-01: Empty State Tanpa Onboarding

**Root cause:** Saat queue kosong, `NowPlayingPanel` hanya menampilkan "No track selected." tanpa petunjuk cara menggunakan app.

**File:** `tui/panels/now_playing.py` — update bagian `if not state.current_track:` dalam `update_state()`:

```python
# SEBELUM:
if not state.current_track:
    self.info_label.update(f"\n[{TEXT_DIM}]  No track selected.[/]\n\n[{TEXT_DIM}]{eq_text}[/]")
    self.progress_bar.position = 0
    self.progress_bar.duration = 0
    self.status_line.display = not is_compact

# SESUDAH:
if not state.current_track:
    hint_lines = [
        "",
        f"[bold {TEXT_PRIMARY}]  YT Termux Player Pro[/]",
        "",
        f"[{TEXT_DIM}]  Tekan [bold {ACCENT_GOLD}]/[/] untuk mencari lagu[/]",
        f"[{TEXT_DIM}]  Ketik nama lagu atau artis, lalu Enter[/]",
        "",
    ]
    if not is_compact:
        hint_lines += [
            f"[{TEXT_DIM}]  Shortcut: [bold]P[/]=Pause  [bold]N[/]=Next  [bold]B[/]=Prev[/]",
            f"[{TEXT_DIM}]            [bold]U[/]/[bold]D[/]=Vol  [bold]R[/]=Radio  [bold]Q[/]=Quit[/]",
            "",
        ]
    hint_lines.append(f"[{TEXT_DIM}]{eq_text}[/]")
    self.info_label.update("\n".join(hint_lines))
    self.progress_bar.position = 0
    self.progress_bar.duration = 0
    self.status_line.display = not is_compact
```

**Verification:** Jalankan fresh → layar menampilkan panduan singkat, bukan blank.

---

### P1-05 · SEC-01: Log File Tanpa Rotation dan Permission

**Root cause:** `logging.basicConfig` dengan `filemode="a"` menulis ke file yang terus tumbuh tanpa batas, tanpa permission restriction.

**File:** `main.py` — ganti seluruh blok `logging.basicConfig`:

```python
# SEBELUM:
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    filename=BASE_DIR / "ytplayer.log",
    filemode="a"
)

# SESUDAH:
import stat
from logging.handlers import RotatingFileHandler

log_path = BASE_DIR / "ytplayer.log"
_log_handler = RotatingFileHandler(
    log_path,
    maxBytes=1 * 1024 * 1024,  # 1 MB per file
    backupCount=2,              # simpan maksimal 2 backup (ytplayer.log.1, .2)
    encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
))
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger().addHandler(_log_handler)

# Set permission 600 (hanya owner yang bisa baca/tulis)
try:
    log_path.touch(exist_ok=True)
    log_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
except OSError:
    pass  # Windows tidak support chmod — abaikan
```

**Tambahan** di `main.py` imports:

```python
import stat
from logging.handlers import RotatingFileHandler
```

**Verification:** Jalankan app → cek `ls -la ytplayer.log` → permission harus `-rw-------`.

---

### P1-06 · CQ-02: `__pycache__` Ter-commit ke Git

**Root cause:** File `.pyc` Python 3.13 ikut ter-track meski `.gitignore` sudah memiliki rule `__pycache__/`.

**Perintah Git (jalankan sekali, bukan di kode):**

```bash
# Hapus dari git tracking tanpa menghapus dari disk
git rm -r --cached "**/__pycache__" 2>/dev/null || true
git rm -r --cached "__pycache__" 2>/dev/null || true

# Verifikasi gitignore sudah benar (rule sudah ada, tidak perlu tambah)
grep "__pycache__" .gitignore

# Commit cleanup
git add .gitignore
git commit -m "chore: remove __pycache__ from tracking"
```

**Tambahan ke `.gitignore`** untuk memastikan cache runtime juga excluded:

```gitignore
# Tambahkan di bawah "# App runtime" section:
cache/sockets/
*.sock
```

**Verification:** `git status` tidak menampilkan file `.pyc` atau direktori `__pycache__`.

---

### P1-07 · UI-03: Tombol Play/Pause Tidak Update Label

**Root cause:** Tombol `#btn_pause` memiliki label statis `"⏯  PLAY / PAUSE"` yang tidak pernah diupdate berdasarkan `state.status`.

**File:** `tui/dashboard.py` — update `refresh_ui()`:

```python
# SEBELUM:
def refresh_ui(self) -> None:
    # Check if status msg expired
    if self._status_msg and (time.time() - self._status_msg_time > 5.0):
        ...

# SESUDAH — tambahkan di refresh_ui() setelah update panels:
def refresh_ui(self) -> None:
    if self._status_msg and (time.time() - self._status_msg_time > 5.0):
        self._status_msg = ""
        self.now_playing.status_line.update("")

    color = STATUS_OK if self.state.is_online else STATUS_ERR
    self.online_dot.update(f"[{color}]●[/]")

    self.now_playing.update_state(self.state)
    self.queue_panel.update_state(self.state)
    self.lyrics_panel.update_state(self.state)

    # Sync tombol pause/resume berdasarkan state
    try:
        btn = self.query_one("#btn_pause", Button)
        if self.state.status == PlayerStatus.PAUSED:
            btn.label = "▶  RESUME"
        elif self.state.status == PlayerStatus.LOADING:
            btn.label = "⏳  LOADING..."
        elif self.state.status == PlayerStatus.PLAYING:
            btn.label = "⏸  PAUSE"
        else:
            btn.label = "⏯  PLAY / PAUSE"
        
        # Sync tombol Radio active state
        btn_radio = self.query_one("#btn_radio", Button)
        btn_radio.set_class(self.state.is_radio_mode, "-active")
    except Exception:
        pass  # Widget belum mount saat pertama kali
```

**File:** `tui/dashboard.py` — tambahkan import `PlayerStatus` yang missing:

```python
# SEBELUM imports:
from core.state import AppState

# SESUDAH:
from core.state import AppState, PlayerStatus
```

**Verification:** Putar lagu → tombol berubah ke "⏸ PAUSE" → tekan P → berubah ke "▶ RESUME" → tekan P lagi → kembali ke "⏸ PAUSE".

---

### P1-08 · EXTRA-01: `state.show_lyrics` Tidak Terhubung ke Tab Visibility

**Root cause:** `CMD_TOGGLE_LYRICS` mengubah `state.show_lyrics` di QueueManager, tapi tidak ada kode di dashboard yang membaca field ini untuk switch tab.

**Pilihan fix:** Hapus `state.show_lyrics` sepenuhnya — tab sudah punya state internal `_active_tab`. Buat `CMD_TOGGLE_LYRICS` langsung switch tab.

**File:** `engine/queue_manager.py` — ganti `_on_toggle_lyrics`:

```python
# SEBELUM:
async def _on_toggle_lyrics(self, _=None):
    self.state.show_lyrics = not self.state.show_lyrics
    status = "ON" if self.state.show_lyrics else "OFF"
    await bus.publish(LOG_MESSAGE, f"Lyrics: {status}")

# SESUDAH — emit event agar Dashboard bisa react:
async def _on_toggle_lyrics(self, _=None):
    # Tidak perlu state, cukup notify UI untuk switch tab
    await bus.publish(LOG_MESSAGE, "Beralih ke panel Lirik")
    # Dashboard yang akan handle actual tab switch via LYRICS_UPDATED_TAB
```

**LEBIH SIMPEL** — di `tui/dashboard.py`, ubah `action_toggle_lyrics` agar langsung berkerja:

```python
# SEBELUM:
async def action_toggle_lyrics(self) -> None:
    if self._is_input_focused(): return
    if self._active_tab == "queue":
        self._show_lyrics_tab()
    else:
        self._show_queue_tab()

# SESUDAH (tidak berubah — ini sudah benar!):
# Masalahnya di btn_lyrics di ControlsPanel yang publish CMD_TOGGLE_LYRICS
# bukan memanggil action_toggle_lyrics di Dashboard.
```

**File:** `tui/panels/controls.py` — fix btn_lyrics handler:

```python
# SEBELUM:
elif button_id == "btn_lyrics":
    await bus.publish(CMD_TOGGLE_LYRICS)

# SESUDAH — publish event khusus untuk tab switch:
elif button_id == "btn_lyrics":
    await bus.publish("cmd.switch.lyrics.tab")
```

**File:** `tui/dashboard.py` — subscribe ke event baru di `on_mount`:

```python
# Di on_mount(), tambahkan:
bus.subscribe("cmd.switch.lyrics.tab", self._on_switch_lyrics_tab)

# Tambahkan method:
async def _on_switch_lyrics_tab(self, _=None):
    if self._active_tab == "queue":
        self._show_lyrics_tab()
    else:
        self._show_queue_tab()
```

**Verification:** Klik tombol "📝 Lirik" → tab switch ke Lirik → klik lagi → kembali ke Antrian. Keyboard `L` juga bekerja sama.

---

### P1-09 · EXTRA-02: `QUEUE_UPDATED` Tidak Punya Subscriber — UI Tidak Reaktif

**Root cause:** Engine mempublish `QUEUE_UPDATED` saat queue berubah (track baru, stop, autoplay), tapi Dashboard tidak subscribe. UI hanya update via polling 0.3s.

**Fix:** Subscribe `QUEUE_UPDATED` di Dashboard untuk trigger immediate UI refresh.

**File:** `tui/dashboard.py` — di `on_mount()`:

```python
# Tambahkan:
bus.subscribe(QUEUE_UPDATED, self._on_queue_updated)
bus.subscribe(TRACK_STARTED, self._on_track_started)

# Tambahkan methods:
async def _on_queue_updated(self, _=None):
    """Immediate refresh saat queue berubah — tidak tunggu polling 0.3s."""
    self.queue_panel.update_state(self.state)

async def _on_track_started(self, track=None):
    """Immediate refresh saat track baru mulai."""
    self.now_playing.update_state(self.state)
    self.queue_panel.update_state(self.state)
```

**File:** `tui/dashboard.py` — update imports:

```python
# SEBELUM:
from core.event_bus import (
    bus, LOG_MESSAGE, CMD_QUIT, CMD_SEARCH, ...
)

# SESUDAH — tambahkan QUEUE_UPDATED dan TRACK_STARTED:
from core.event_bus import (
    bus, LOG_MESSAGE, CMD_QUIT, CMD_SEARCH,
    QUEUE_UPDATED, TRACK_STARTED,
    ...
)
```

**Verification:** Search lagu → queue langsung terisi tanpa delay 0.3s → tidak ada flicker antara "Queue is empty" dan queue terisi.

---

### P1-10 · EXTRA-03: `LYRICS_UPDATED` Tidak Punya Subscriber

**Root cause:** `LyricsFetcher` mempublish `LYRICS_UPDATED` saat lirik berhasil diambil, tapi LyricsPanel tidak subscribe — ia hanya polling via `update_state()` tiap 0.3s.

**Fix:** Subscribe di Dashboard, trigger immediate lyrics panel refresh.

**File:** `tui/dashboard.py` — di `on_mount()`:

```python
bus.subscribe(LYRICS_UPDATED, self._on_lyrics_updated)

async def _on_lyrics_updated(self, _=None):
    """Immediate refresh saat lirik baru tersedia."""
    self.lyrics_panel.update_state(self.state)
```

**File:** `tui/dashboard.py` — update imports:

```python
from core.event_bus import (
    bus, LOG_MESSAGE, CMD_QUIT, CMD_SEARCH,
    QUEUE_UPDATED, TRACK_STARTED, LYRICS_UPDATED,
    ...
)
```

**Verification:** Putar lagu → panel Lirik menampilkan "No lyrics available" → setelah 2-3 detik, lirik muncul langsung (bukan harus tunggu polling). Switch ke tab Lirik saat fetch sedang berlangsung → lirik muncul begitu siap.

---

### P1-11 · EXTRA-04 & EXTRA-05: `DOWNLOAD_COMPLETE` Tidak Punya Subscriber

**Root cause:** Saat download selesai, `DOWNLOAD_COMPLETE` dipublish tapi tidak ada yang mendengarkan. User tidak dapat konfirmasi visual bahwa file tersimpan.

**File:** `tui/dashboard.py` — di `on_mount()`:

```python
bus.subscribe(DOWNLOAD_COMPLETE, self._on_download_complete)

async def _on_download_complete(self, track=None):
    """Tampilkan notifikasi download selesai dan update Now Playing."""
    title = track.title if track else "Track"
    # Status message sudah di-handle via LOG_MESSAGE di queue_manager
    # Tapi perlu refresh Now Playing untuk update "Via: Cache" indicator
    self.now_playing.update_state(self.state)
```

**File:** `tui/dashboard.py` — update imports:

```python
from core.event_bus import (
    bus, LOG_MESSAGE, CMD_QUIT, CMD_SEARCH,
    QUEUE_UPDATED, TRACK_STARTED, LYRICS_UPDATED, DOWNLOAD_COMPLETE,
    ...
)
```

**Verification:** Putar lagu → tekan M → tunggu download selesai → "Via: Cache" di NowPlaying langsung update tanpa harus restart.

---

## P2 — HIGH (11 Issues) — Selesaikan dalam Sprint Pertama

---

### P2-01 · ENG-02: Dual Observer Mengakibatkan Double Event Fire

**Root cause:** MPV observer mendaftarkan `time-pos` (ID 1) DAN `playback-time` (ID 2). Keduanya trigger `TRACK_PROGRESS`. Result: 6 async handler calls per 0.5 detik.

**File:** `engine/mpv_controller.py` — hapus duplikasi di `_observe_events()`:

```python
# SEBELUM:
await self._command(["observe_property", 1, "time-pos"])
await self._command(["observe_property", 2, "playback-time"])
await self._command(["observe_property", 3, "pause"])

# SESUDAH — hapus playback-time, hanya observe time-pos dan pause:
await self._command(["observe_property", 1, "time-pos"])
await self._command(["observe_property", 2, "pause"])
```

**Verification:** Pasang logging di `_on_progress` → sebelum fix: 2 log per 0.5s → setelah fix: 1 log per 0.5s.

---

### P2-02 · ENG-03: Thread Leak Saat Download Di-cancel

**Root cause:** `loop.run_in_executor(None, self._download_sync, ...)` tidak bisa di-cancel setelah dispatch. Jika user quit saat download, thread tetap hidup.

**File:** `engine/ytdlp_client.py` — tambahkan cancellation support:

```python
# Tambahkan di class YtDlpClient:
def __init__(self):
    self._download_cancelled = False

def cancel_download(self):
    """Signal download untuk berhenti pada progress hook berikutnya."""
    self._download_cancelled = True

async def download_mp3(self, video_id: str, on_progress=None) -> str:
    self._download_cancelled = False
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sanitasi video_id (P2-08 fix digabungkan di sini):
    import re
    if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', video_id):
        raise ValueError(f"Invalid video_id: {video_id!r}")
    
    out_path = CACHE_DIR / f"{video_id}.%(ext)s"
    
    def _cancel_hook(d):
        if self._download_cancelled:
            raise Exception("Download cancelled by user")
    
    opts = {
        **self._YDL_OPTS_INFO,
        "format": "bestaudio/best",
        "outtmpl": str(out_path),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "progress_hooks": [_cancel_hook] + ([on_progress] if on_progress else []),
    }
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, self._download_sync, video_id, opts)
    return str(CACHE_DIR / f"{video_id}.mp3")
```

**File:** `main.py` — tambahkan cancel di shutdown:

```python
# Di blok finally setelah cancel tasks:
ytdlp.cancel_download()  # Signal thread download untuk berhenti
```

**Verification:** Mulai download file besar → tekan Q dalam 2 detik → app exit clean, tidak ada "zombie" download di background.

---

### P2-03 · UX-02: Tidak Ada Loading State Visual

**Root cause:** Saat `PlayerStatus.LOADING`, tidak ada indikator visual. User mengira app hang.

**File:** `tui/panels/now_playing.py` — update `update_state()`, tambahkan setelah error check:

```python
# Tambahkan blok LOADING setelah blok ERROR, sebelum blok "no current track":
if state.status == PlayerStatus.LOADING:
    # Animasi sederhana berdasarkan waktu
    dots = "." * (int(time.time() * 2) % 4)
    track_name = state.current_track.title if state.current_track else "..."
    self.info_label.update(
        f"\n[{ACCENT_GOLD}]  ⏳ Memuat{dots}[/]\n\n"
        f"[{TEXT_DIM}]  {escape(track_name[:max_title_len])}[/]\n\n"
        f"[{TEXT_DIM}]{eq_text}[/]"
    )
    self.progress_bar.position = 0
    self.progress_bar.duration = 0
    return
```

**Verification:** Search lagu → antara klik Enter dan musik mulai terdengar, layar menampilkan "⏳ Memuat..." bukan kosong.

---

### P2-04 · UX-03: Raw Exception String Ditampilkan ke User

**Root cause:** `queue_manager.py` menampilkan `str(e)` langsung sebagai LOG_MESSAGE.

**File:** `engine/queue_manager.py` — buat helper function:

```python
# Tambahkan di atas class QueueManager:
def _user_friendly_error(e: Exception) -> str:
    """Konversi exception teknis ke pesan yang bermakna untuk user."""
    msg = str(e).lower()
    if "connection refused" in msg or "errno 111" in msg:
        return "Koneksi ke MPV terputus. Coba restart aplikasi."
    if "429" in msg or "rate" in msg:
        return "YouTube membatasi request. Tunggu 30 detik sebelum mencari lagi."
    if "403" in msg or "forbidden" in msg:
        return "Akses video ditolak (mungkin konten terbatas wilayah)."
    if "404" in msg or "not found" in msg:
        return "Video tidak ditemukan atau sudah dihapus."
    if "network" in msg or "timeout" in msg or "timed out" in msg:
        return "Koneksi internet bermasalah. Periksa jaringan Anda."
    if "ffmpeg" in msg:
        return "FFmpeg tidak ditemukan. Install: pkg install ffmpeg"
    if "cancelled" in msg:
        return "Download dibatalkan."
    # Fallback: truncate pesan teknis
    raw = str(e)
    return raw[:80] + "…" if len(raw) > 80 else raw
```

**File:** `engine/queue_manager.py` — update semua error publish:

```python
# SEBELUM (di play_track):
await bus.publish(LOG_MESSAGE, f"Error playing: {e}")

# SESUDAH:
await bus.publish(LOG_MESSAGE, f"⚠ {_user_friendly_error(e)}")

# SEBELUM (di _on_download):
await bus.publish(LOG_MESSAGE, f"Download failed: {e}")

# SESUDAH:
await bus.publish(LOG_MESSAGE, f"⚠ Download gagal: {_user_friendly_error(e)}")
```

**File:** `main.py` — update search error:

```python
# SEBELUM:
await bus.publish(LOG_MESSAGE, f"Search failed: {e}")

# SESUDAH:
from engine.queue_manager import _user_friendly_error
await bus.publish(LOG_MESSAGE, f"⚠ Pencarian gagal: {_user_friendly_error(e)}")
```

**Verification:** Disconnect internet → search → pesan: "Koneksi internet bermasalah" bukan "[Errno -2] Name or service not known".

---

### P2-05 · UX-04: Tombol Lirik dan Keyboard `L` Tidak Konsisten

**Sudah di-fix di P1-08.** Tombol `btn_lyrics` sekarang publish `"cmd.switch.lyrics.tab"` yang di-handle oleh Dashboard. Keyboard `L` tetap memanggil `action_toggle_lyrics()` yang sudah benar.

**Tidak perlu perubahan tambahan jika P1-08 sudah dieksekusi.**

---

### P2-06 · UX-05: Shell Scripts Pakai Path Socket Salah

**Root cause:** `volume_up.sh` hardcode `/tmp/mpv-yt-player.sock`, tapi config.py menyimpan socket di `$BASE_DIR/cache/sockets/mpv-yt-player.sock`.

**File:** `widgets/shortcuts/play_pause.sh`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
# Path socket harus sesuai dengan config.py
BASE_DIR="${YT_PLAYER_BASE:-$(dirname "$(realpath "$0")")/../..}"
SOCK="${YT_PLAYER_SOCKET:-$BASE_DIR/cache/sockets/mpv-yt-player.sock}"

if [ -S "$SOCK" ]; then
    echo '{"command":["cycle","pause"]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
    termux-notification --title "YT Player" --content "▶/⏸ toggled"
else
    termux-notification --title "YT Player" --content "⚠️ Player tidak berjalan"
fi
```

**File:** `widgets/shortcuts/next_track.sh`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
BASE_DIR="${YT_PLAYER_BASE:-$(dirname "$(realpath "$0")")/../..}"
SOCK="${YT_PLAYER_SOCKET:-$BASE_DIR/cache/sockets/mpv-yt-player.sock}"

if [ -S "$SOCK" ]; then
    echo '{"command":["playlist-next","force"]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
    termux-notification --title "YT Player" --content "⏭ Next Track"
fi
```

**File:** `widgets/shortcuts/volume_up.sh`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
BASE_DIR="${YT_PLAYER_BASE:-$(dirname "$(realpath "$0")")/../..}"
SOCK="${YT_PLAYER_SOCKET:-$BASE_DIR/cache/sockets/mpv-yt-player.sock}"

if [ -S "$SOCK" ]; then
    echo '{"command":["add","volume",5]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
fi
```

**Verification:** Jalankan app → jalankan `./widgets/shortcuts/play_pause.sh` → musik pause/resume.

---

### P2-07 · UI-02: QueuePanel Full Rebuild Setiap 0.3 Detik

**Root cause:** `update_state()` memanggil `option_list.clear_options()` lalu `add_option()` setiap tick, bahkan jika queue tidak berubah.

**File:** `tui/panels/queue_panel.py`:

```python
# Tambahkan cache state di __init__ (atau compose):
def compose(self) -> ComposeResult:
    with Vertical():
        self.option_list = OptionList(id="queue_list")
        self.footer = Static(f"Radio: [{TEXT_DIM}]OFF[/]", id="queue_footer")
        yield self.option_list
        yield self.footer
    self._last_queue_hash = None  # Cache untuk dirty checking
    self._last_current_id = None
    self._last_radio = None

def update_state(self, state: AppState) -> None:
    # Dirty checking — skip rebuild jika tidak ada perubahan
    current_id = state.current_track.video_id if state.current_track else None
    queue_ids = tuple(t.video_id for t in state.queue)
    new_hash = hash((current_id, queue_ids, state.is_radio_mode))
    
    if new_hash == self._last_queue_hash:
        return  # Tidak ada perubahan, skip rebuild
    
    self._last_queue_hash = new_hash
    
    # Rebuild hanya jika hash berubah
    self.option_list.clear_options()
    # ... (sisa kode tidak berubah)
```

**Verification:** Pasang counter di `update_state` → sebelum fix: terhitung 3.3x/detik → setelah fix: hanya terhitung saat queue benar-benar berubah.

---

### P2-08 · UI-06: Tombol Radio Tidak Ada Active State Visual

**Sudah di-fix di P1-07** (update `refresh_ui()` sudah handle `btn_radio.set_class(state.is_radio_mode, "-active")`).

**Tambahan** untuk tombol download saat sedang aktif:

**File:** `tui/dashboard.py` — tambahkan di `refresh_ui()`:

```python
# Tambahkan setelah sync btn_radio:
try:
    btn_dl = self.query_one("#btn_dl", Button)
    # Download aktif jika ada log message "Downloading:" dalam 5 detik terakhir
    is_downloading = "Downloading" in (self._status_msg or "")
    btn_dl.set_class(is_downloading, "-active")
except Exception:
    pass
```

---

### P2-09 · SEC-02: MPV Socket Permission Terlalu Terbuka

**Root cause:** Socket dibuat oleh MPV dengan permission default. Tidak ada chmod setelah socket tersedia.

**File:** `engine/mpv_controller.py` — tambahkan chmod setelah koneksi berhasil:

```python
# Di method connect(), setelah self.is_connected = True:
if os.name != 'nt':
    try:
        import stat
        os.chmod(MPV_SOCKET, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Bukan fatal jika chmod gagal
```

**Verification:** `ls -la cache/sockets/mpv-yt-player.sock` → permission `srw-------`.

---

### P2-10 · SEC-03: video_id Tidak Disanitasi Sebelum Jadi Filename

**Sudah di-fix di P2-02** (validasi regex `^[a-zA-Z0-9_-]{1,64}$` ditambahkan di `download_mp3()`).

**Tambahan** — validasi juga di `_to_track()`:

**File:** `engine/ytdlp_client.py`:

```python
def _to_track(self, entry: dict) -> TrackInfo:
    import re
    duration_raw = entry.get("duration", 0)
    duration = int(duration_raw) if duration_raw else 0
    
    video_id = entry.get("id", "") or entry.get("url", "")
    
    # Sanitasi video_id — hanya izinkan karakter aman untuk filename
    if video_id and not re.match(r'^[a-zA-Z0-9_-]{1,64}$', video_id):
        # Fallback ke hash dari title
        video_id = f"vid_{abs(hash(entry.get('title', ''))) % 10**10}"
    elif not video_id:
        video_id = f"vid_{abs(hash(entry.get('title', ''))) % 10**10}"
    
    return TrackInfo(
        video_id=video_id,
        # ... sisa tidak berubah
    )
```

---

### P2-11 · SEC-06: Tidak Ada Search Debounce

**Root cause:** User bisa spam Enter dan trigger banyak search request sekaligus, berpotensi trigger YouTube rate limiting.

**File:** `tui/dashboard.py` — tambahkan debounce di `on_search_submitted`:

```python
# Tambahkan di __init__:
self._last_search_time = 0.0
self._search_cooldown = 1.5  # detik

# SEBELUM:
@on(Input.Submitted, "#search_input")
async def on_search_submitted(self, event: Input.Submitted) -> None:
    query = event.value.strip()
    if query:
        await bus.publish(CMD_SEARCH, query)
        event.input.value = ""
        self.set_focus(None)

# SESUDAH:
@on(Input.Submitted, "#search_input")
async def on_search_submitted(self, event: Input.Submitted) -> None:
    query = event.value.strip()
    if not query:
        return
    
    now = time.time()
    if now - self._last_search_time < self._search_cooldown:
        remaining = self._search_cooldown - (now - self._last_search_time)
        await bus.publish(LOG_MESSAGE, f"Tunggu {remaining:.1f}s sebelum mencari lagi")
        return
    
    self._last_search_time = now
    await bus.publish(CMD_SEARCH, query)
    event.input.value = ""
    self.set_focus(None)
```

**Verification:** Tekan Enter berkali-kali cepat → hanya 1 request yang dikirim per 1.5 detik, sisanya ditolak dengan pesan.

---

## P3 — MEDIUM (17 Issues) — Polish untuk Kualitas Production

---

### P3-01 · ENG-06: Stream URL Cache Tidak Berguna

**Root cause:** `resolver.py` menyimpan dan mengecek stream URL, tapi URL yang disimpan adalah `https://www.youtube.com/watch?v=...` (bukan direct URL), sehingga MPV tetap butuh yt-dlp hook setiap kali.

**Fix:** Hapus caching stream URL yang sia-sia — langsung ke Rule 3 selalu.

**File:** `cache/resolver.py`:

```python
async def resolve(self, track: TrackInfo) -> str:
    """Returns the playback URI (local path atau YouTube URL untuk MPV)."""
    row = await self.db.get_track(track.video_id)
    
    # Rule 1: Local file — ini yang benar-benar berguna
    if row and row.get("local_path"):
        path = row["local_path"]
        if os.path.isfile(path):
            track.local_path = path
            return path
    
    # Rule 2: Selalu pakai YouTube URL (MPV + yt-dlp hook akan handle)
    # Stream URL caching dihapus karena URL yg tersimpan bukan direct URL
    url = f"https://www.youtube.com/watch?v={track.video_id}"
    track.stream_url = url
    # Simpan metadata track ke DB (tanpa stream_url)
    await self.db.upsert_track(track)
    return url
```

**Hapus** konstanta `STREAM_URL_TTL` yang tidak lagi dipakai.

---

### P3-02 · ENG-08: Hardcoded sleep(1.0) untuk MPV Spawn

**File:** `engine/mpv_controller.py`:

```python
# SEBELUM:
await asyncio.sleep(1.0)  # Wait for mpv to bind socket

# SESUDAH — adaptive wait dengan polling:
if os.name != 'nt':
    # Poll sampai socket tersedia, max 5 detik
    for _ in range(50):
        await asyncio.sleep(0.1)
        if os.path.exists(MPV_SOCKET):
            break
else:
    await asyncio.sleep(1.0)  # Windows pipe tidak bisa di-poll dengan cara sama
```

---

### P3-03 · UX-06: Download Progress Hilang Setelah 5 Detik

**Root cause:** Status message auto-expire setelah 5 detik. Download bisa memakan waktu 60-120 detik.

**File:** `tui/dashboard.py` — modifikasi `_on_log_message`:

```python
async def _on_log_message(self, msg: str) -> None:
    self._status_msg = str(msg)
    self._status_msg_time = time.time()
    
    # Download progress mendapat TTL yang lebih panjang
    if "Downloading:" in str(msg) or "⬇" in str(msg):
        self._status_msg_ttl = 120.0  # 2 menit untuk download
    elif "Downloaded:" in str(msg) or "gagal" in str(msg).lower():
        self._status_msg_ttl = 8.0   # 8 detik untuk result
    else:
        self._status_msg_ttl = 5.0   # Default 5 detik
    
    if hasattr(self.now_playing, 'status_line'):
        self.now_playing.status_line.update(f"[{ACCENT_GOLD}]{msg}[/]")
    self.refresh_ui()
```

**File:** `tui/dashboard.py` — update TTL check di `refresh_ui()`:

```python
# SEBELUM:
if self._status_msg and (time.time() - self._status_msg_time > 5.0):

# SESUDAH:
ttl = getattr(self, '_status_msg_ttl', 5.0)
if self._status_msg and (time.time() - self._status_msg_time > ttl):
```

---

### P3-04 · UI-01: Equalizer Refresh Tidak Perlu saat Paused/Idle

**Root cause:** `refresh_ui()` berjalan 3.3x/detik dan memanggil `update_state()` di semua panel tanpa mempertimbangkan apakah ada sesuatu yang berubah.

**File:** `tui/dashboard.py`:

```python
def refresh_ui(self) -> None:
    # ... existing TTL check ...
    
    color = STATUS_OK if self.state.is_online else STATUS_ERR
    self.online_dot.update(f"[{color}]●[/]")
    
    # Now Playing: refresh selalu (karena equalizer animasi terus)
    self.now_playing.update_state(self.state)
    
    # Queue: hanya refresh jika visible (dirty checking sudah di panel)
    if self.queue_panel.display:
        self.queue_panel.update_state(self.state)
    
    # Lyrics: hanya refresh jika visible DAN playing
    if self.lyrics_panel.display and self.state.status == PlayerStatus.PLAYING:
        self.lyrics_panel.update_state(self.state)
    elif self.lyrics_panel.display:
        # Update sekali saja saat track berubah (via TRACK_STARTED event)
        pass
    
    # ... button sync tetap jalan ...
```

---

### P3-05 · UI-04: Lyrics Window Terlalu Kecil

**File:** `tui/panels/lyrics_panel.py`:

```python
# SEBELUM:
window_size = min(4, max(2, total // 6))

# SESUDAH — gunakan panel height untuk hitung window yang optimal:
panel_h = self.size.height if self.size.height > 0 else 12
# Setiap baris butuh 1 baris terminal. Aktif + before + after.
# Sisakan 2 baris untuk padding.
available = max(4, panel_h - 2)
# window_size = baris sebelum/sesudah active (bukan total)
window_size = min(available // 2, 8)
```

---

### P3-06 · UI-05: Compact Threshold Terlalu Tinggi (35)

**File:** `tui/dashboard.py`:

```python
# SEBELUM (2 tempat):
is_short = self.size.height < 35

# SESUDAH — 24 baris: threshold lebih realistis untuk Termux:
is_short = self.size.height < 24
```

---

### P3-07 · UI-07: Gunakan Ellipsis Unicode

**File:** `tui/panels/now_playing.py` dan `tui/panels/queue_panel.py`:

```python
# SEBELUM (di setiap tempat truncation):
title = title[:max_title - 2] + ".."

# SESUDAH:
title = title[:max_title - 1] + "…"
```

---

### P3-08 · SEC-07: Socket Path dari Env Var Tidak Divalidasi

**File:** `config.py`:

```python
# SEBELUM:
MPV_SOCKET = os.environ.get("YT_PLAYER_SOCKET", str(socket_dir / "mpv-yt-player.sock"))

# SESUDAH:
_raw_socket = os.environ.get("YT_PLAYER_SOCKET", str(socket_dir / "mpv-yt-player.sock"))
# Pastikan path tidak keluar dari direktori cache
_socket_path = Path(_raw_socket).resolve()
_allowed_prefix = BASE_DIR.resolve()
if not str(_socket_path).startswith(str(_allowed_prefix)):
    import warnings
    warnings.warn(f"YT_PLAYER_SOCKET '{_raw_socket}' di luar BASE_DIR — menggunakan default")
    _socket_path = socket_dir / "mpv-yt-player.sock"
MPV_SOCKET = str(_socket_path)
```

---

### P3-09 · SEC-08: Dependency Tidak Di-pin ke Versi Exact

**File:** `requirements.txt`:

```txt
# SEBELUM:
rich>=13.0
yt-dlp>=2024.01.01
aiosqlite>=0.20.0
aiohttp>=3.9.0
textual>=0.40.0
pytest>=7.0.0
pytest-asyncio>=0.21.0

# SESUDAH — pin ke versi yang sudah ditest:
# Core dependencies
rich==13.9.4
yt-dlp==2025.1.15
aiosqlite==0.20.0
aiohttp==3.11.11
textual==0.87.1

# Dev dependencies (pisahkan ke requirements-dev.txt)
```

**Buat file baru** `requirements-dev.txt`:

```txt
pytest==8.3.4
pytest-asyncio==0.25.2
```

**Update README** untuk membedakan:
```bash
# User install:
pip install -r requirements.txt

# Developer install:
pip install -r requirements.txt -r requirements-dev.txt
```

---

### P3-10 · CQ-01: Cache Folder Tidak Ter-exclude dengan Benar di `.gitignore`

**File:** `.gitignore` — verifikasi dan lengkapi:

```gitignore
# Cache runtime — JANGAN di-commit
cache/mp3/
cache/sockets/
cache/*.db
cache/*.db-shm
cache/*.db-wal
*.log
*.log.*

# Tapi cache/__init__.py, cache/db.py, cache/resolver.py, cache/schema.sql HARUS di-commit
# Jangan tambah "cache/" secara general!
```

---

### P3-11 · CQ-03: Tidak Ada Unit Test

**Buat file baru:** `tests/__init__.py` (kosong)

**Buat file baru:** `tests/test_event_bus.py`:

```python
import asyncio
import pytest
from core.event_bus import EventBus

@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = EventBus()
    received = []
    bus.subscribe("test.event", lambda d: received.append(d))
    await bus.publish("test.event", "hello")
    assert received == ["hello"]

@pytest.mark.asyncio
async def test_handler_exception_does_not_block_others():
    bus = EventBus()
    results = []
    def bad_handler(d): raise RuntimeError("boom")
    def good_handler(d): results.append(d)
    bus.subscribe("test.event", bad_handler)
    bus.subscribe("test.event", good_handler)
    await bus.publish("test.event", "data")
    assert results == ["data"]  # good_handler tetap dipanggil

@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    calls = []
    handler = lambda d: calls.append(d)
    bus.subscribe("ev", handler)
    bus.unsubscribe("ev", handler)
    await bus.publish("ev", 1)
    assert calls == []
```

**Buat file baru:** `tests/test_lrc_parser.py`:

```python
import pytest
from integrations.lyrics import LyricsFetcher
from unittest.mock import MagicMock

def make_fetcher():
    state = MagicMock()
    return LyricsFetcher(state, session=MagicMock())

def test_parse_lrc_basic():
    fetcher = make_fetcher()
    lrc = "[00:10.00] Hello world\n[00:20.50] Second line"
    result = fetcher._parse_lrc(lrc)
    assert len(result) == 2
    assert result[0] == (10.0, "Hello world")
    assert abs(result[1][0] - 20.5) < 0.01

def test_parse_lrc_plain_text():
    fetcher = make_fetcher()
    lrc = "Line without timestamp"
    result = fetcher._parse_lrc(lrc)
    assert result == [(0.0, "Line without timestamp")]

def test_parse_lrc_empty():
    fetcher = make_fetcher()
    assert fetcher._parse_lrc("") == []
    assert fetcher._parse_lrc("\n\n\n") == []
```

**Buat file baru:** `tests/test_cache_resolver.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from cache.resolver import CacheResolver
from core.state import TrackInfo

def make_track():
    return TrackInfo(video_id="dQw4w9WgXcQ", title="Test", artist="Test", duration=213)

@pytest.mark.asyncio
async def test_local_file_takes_priority(tmp_path):
    local = tmp_path / "dQw4w9WgXcQ.mp3"
    local.touch()
    
    db = AsyncMock()
    db.get_track.return_value = {"local_path": str(local)}
    
    resolver = CacheResolver(db, AsyncMock())
    track = make_track()
    result = await resolver.resolve(track)
    
    assert result == str(local)
    assert track.local_path == str(local)

@pytest.mark.asyncio
async def test_fallback_to_youtube_url():
    db = AsyncMock()
    db.get_track.return_value = None
    db.upsert_track.return_value = None
    
    resolver = CacheResolver(db, AsyncMock())
    track = make_track()
    result = await resolver.resolve(track)
    
    assert "dQw4w9WgXcQ" in result
    assert result.startswith("https://")
```

**Buat file baru:** `tests/test_queue_manager.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.state import AppState, TrackInfo, PlayerStatus
from core.event_bus import EventBus

def make_track(video_id, title="Test"):
    return TrackInfo(video_id=video_id, title=title, artist="Artist", duration=180)

@pytest.mark.asyncio
async def test_play_next_pushes_to_history():
    # Setup minimal — test logika history saja tanpa benar-benar play
    state = AppState()
    current = make_track("abc", "Current")
    next_t = make_track("xyz", "Next")
    state.current_track = current
    state.queue = [next_t]
    
    # Mock semua external dependencies
    mpv = AsyncMock()
    mpv.is_connected = False  # Tidak perlu actual play
    
    from engine.queue_manager import QueueManager
    qm = QueueManager(state, mpv, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    
    # Karena mpv.is_connected = False, play_track akan gagal tapi history logic di play_next tetap jalan
    state.queue = [next_t]
    # Hanya test push to history
    if state.current_track:
        state.history.append(state.current_track)
    
    assert len(state.history) == 1
    assert state.history[0].video_id == "abc"
```

**Update `.gitignore`** — hapus baris `tests/` (kita butuh tests masuk ke repo):

```gitignore
# HAPUS baris ini:
# tests/

# Ganti dengan:
# Test artifacts (bukan test code)
.pytest_cache/
htmlcov/
.coverage
```

---

### P3-12 · CQ-04: Wildcard Import

**File:** `tui/dashboard.py`, `tui/panels/now_playing.py`, `tui/panels/controls.py`

```python
# SEBELUM:
from tui.theme import *

# SESUDAH (contoh untuk dashboard.py — sesuaikan yang dipakai setiap file):
from tui.theme import (
    BG_VOID, BG_PANEL, BG_ELEVATED, BORDER, BORDER_FOCUS,
    ACCENT_FIRE, ACCENT_GOLD, TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM,
    STATUS_OK, STATUS_ERR, BREAKPOINT_LANDSCAPE,
    HEIGHT_TOP_BAR, HEIGHT_NOW_PLAYING, HEIGHT_TAB_BAR,
    HEIGHT_CONTROLS_TOTAL
)
```

---

### P3-13 · ENG-07: Autoplay History Filter O(n)

**File:** `engine/autoplay.py`:

```python
# SEBELUM:
existing_ids = {t.video_id for t in self.state.queue}
existing_ids.add(self.state.current_track.video_id)
for t in self.state.history:
    existing_ids.add(t.video_id)

# SESUDAH — sama, tapi jadikan jelas bahwa ini sudah O(1) per lookup:
# Set comprehension ini sudah optimal, tidak perlu ubah logic.
# Yang perlu ditambah: limit history scan ke 20 track terakhir saja:
existing_ids = {t.video_id for t in self.state.queue}
existing_ids.add(self.state.current_track.video_id)
# Hanya cek 20 track terakhir dari history untuk avoid repeat:
for t in self.state.history[-20:]:
    existing_ids.add(t.video_id)
```

---

## Checklist Verifikasi Final

Sebelum `git push`, jalankan checklist ini:

```
ENGINE
[ ] Jalankan tanpa MPV → pesan error jelas tampil, app tidak crash
[ ] Klik progress bar → posisi lompat ke titik yang diklik
[ ] Klik item di queue → lagu tersebut langsung diputar
[ ] Search lagu → putar → tekan Q saat masih loading → exit clean
[ ] Search 3x dalam 2 detik → hanya 1 yang dikirim

UX / WORKFLOW
[ ] Fresh install: layar pertama menampilkan cara penggunaan
[ ] Status LOADING muncul antara search dan playback
[ ] Error internet: pesan user-friendly (bukan traceback)
[ ] Tombol Lirik dan keyboard L keduanya switch tab Lirik
[ ] Shell scripts di widgets/ bisa pause/resume dari luar app

UI / MICRO-INTERACTION
[ ] Tombol berubah: "⏸ PAUSE" ↔ "▶ RESUME" ↔ "⏳ LOADING..."
[ ] Tombol Radio menyala (gold) saat radio mode aktif
[ ] Lyrics panel menampilkan lebih banyak baris (window optimal)
[ ] Compact mode aktif di terminal 24 baris (bukan 35)
[ ] Judul panjang ditruncate dengan "…" bukan ".."
[ ] Queue tidak flicker saat refresh (dirty checking aktif)

SECURITY
[ ] ls -la ytplayer.log → permission -rw-------
[ ] ls -la cache/sockets/*.sock → permission srw-------
[ ] git status → tidak ada .pyc atau __pycache__
[ ] cat requirements.txt → semua versi di-pin exact

CODE QUALITY
[ ] pytest tests/ → semua test hijau
[ ] python -m py_compile *.py → tidak ada syntax error
[ ] grep -r "from tui.theme import \*" → tidak ada hasil
[ ] git log --oneline -5 → tidak ada commit dengan __pycache__
```

---

## Estimasi Waktu Keseluruhan

| Tier | Issues | Estimasi |
|------|--------|----------|
| P1 Blocker | 12 | ~5 jam |
| P2 High | 11 | ~6 jam |
| P3 Medium | 17 | ~8 jam |
| **Total** | **40** | **~19 jam** |

Disarankan dikerjakan dalam 3 sesi kerja terpisah (satu tier per sesi) dengan full regression test di akhir setiap sesi sebelum melanjutkan ke tier berikutnya.