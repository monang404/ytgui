# IMPLEMENTASI AUDIT — YTGUI

**Versi Codebase:** `develop` branch (post Phase-3-security-cleanup merge)  
**Tanggal Dibuat:** 2026-06-23  
**Sumber Audit:** `docs/audit_*.md`  
**Status Cek:** Semua item diverifikasi langsung ke kode aktual

---

## Cara Membaca Dokumen Ini

- Setiap fase harus selesai sebelum fase berikutnya dimulai
- Setiap task memiliki: **File target** · **Masalah** · **Fix konkret** · **Cara verifikasi**
- Status task: `[ ]` belum · `[/]` sedang dikerjakan · `[x]` selesai · `[~]` skip/tidak relevan
- **Dependency antar fase wajib dipatuhi** — jangan loncat fase

---

## Ringkasan Score Audit

| Dimensi | Score | Target Setelah Fix |
|---|---|---|
| Overall Health | 62/100 | ~85/100 |
| Security | 55/100 | ~88/100 |
| Architecture | 70/100 | ~75/100 |
| Maintainability | 65/100 | ~72/100 |
| Scalability | 45/100 | ~55/100 |
| Concurrency | 58/100 | ~75/100 |

---

## FASE 0 — Quick Wins (< 1 jam total)

**Prasyarat:** Tidak ada  
**Risiko:** Sangat rendah  
**Dampak:** 5 bug langsung tertangani, tidak butuh refactor

---

### TASK-0.1 — `_TITLE_NOISE_WORDS` → `frozenset`

- **File:** `engine/radio_mode.py` baris 134
- **Severity:** 🟢 LOW
- **Masalah:** Variabel `_TITLE_NOISE_WORDS` bertipe `tuple`. Setiap pengecekan `if w not in _TITLE_NOISE_WORDS` pada baris 155 berjalan O(n). Dengan `frozenset`, pengecekan menjadi O(1).
- **Kondisi saat ini:**
  ```python
  _TITLE_NOISE_WORDS = (
      "official", "music", "video", ...
  )
  ```
- **Fix:**
  ```python
  _TITLE_NOISE_WORDS = frozenset({
      "official", "music", "video", ...
  })
  ```
- **Verifikasi:** Jalankan `python -c "from engine.radio_mode import _TITLE_NOISE_WORDS; assert isinstance(_TITLE_NOISE_WORDS, frozenset)"`

---

### TASK-0.2 — Reset `_retry_count` di `_on_stop()`

- **File:** `engine/playback_controller.py` baris 162
- **Severity:** 🟡 MEDIUM
- **Masalah:** `_on_stop()` tidak mereset `_retry_count`. Jika user stop setelah 2 kegagalan beruntun, lagu berikutnya hanya punya 1 kesempatan retry tersisa sebelum dihentikan paksa.
- **Kondisi saat ini:**
  ```python
  async def _on_stop(self, _data=None):
      await self.mpv.pause()
      self.state.status = PlayerStatus.IDLE
      self.state.current_track = None
      # ... TIDAK ada reset _retry_count
  ```
- **Fix:** Tambahkan `self._retry_count = 0` sebagai baris pertama `_on_stop`:
  ```python
  async def _on_stop(self, _data=None):
      self._retry_count = 0  # ← tambahkan ini
      await self.mpv.pause()
      ...
  ```
- **Verifikasi:** Cek baris pertama method `_on_stop` berisi `self._retry_count = 0`

---

### TASK-0.3 — Cancel `_bg_tasks` di `RadioMode.on_deactivated()`

- **File:** `engine/radio_mode.py` baris 192
- **Severity:** 🟡 MEDIUM
- **Masalah:** Saat user beralih dari Radio Mode ke Queue Mode, background task (`_fetch_and_play_initial`, `_prefetch_next`) yang sedang berjalan tidak di-cancel. Task bisa selesai belakangan dan memanggil `controller.play_track()` tanpa diminta, memaksa switch kembali ke Radio.
- **Kondisi saat ini:**
  ```python
  async def on_deactivated(self) -> None:
      self.state.radio_queue.clear()
      # ← TIDAK ada cancel task!
  ```
- **Fix:**
  ```python
  async def on_deactivated(self) -> None:
      self.state.radio_queue.clear()
      for task in list(self._bg_tasks):
          task.cancel()
      self._bg_tasks.clear()
  ```
- **Verifikasi:** Cek method `on_deactivated` punya loop cancel tasks

---

### TASK-0.4 — Fix `DownloadManager._on_download` Signature

- **File:** `engine/download_manager.py` baris 27
- **Severity:** 🟠 HIGH
- **Masalah:** `CommandBus.execute()` memanggil handler sebagai `handler(room_id, data)`. Tapi signature `_on_download(self, track=None)` hanya menerima 1 argumen — `room_id` akan masuk ke parameter `track`, dan `data` (TrackInfo asli) tidak pernah diteruskan. Ini menyebabkan `TypeError` jika dipanggil dengan track eksplisit.
- **Kondisi saat ini:**
  ```python
  async def _on_download(self, track: TrackInfo | None = None):
      target = track or self.state.current_track
  ```
- **Fix:**
  ```python
  async def _on_download(self, room_id: str, track: TrackInfo | None = None):
      target = track or self.state.current_track
  ```
- **Verifikasi:** `python -c "import inspect; from engine.download_manager import DownloadManager; sig = inspect.signature(DownloadManager._on_download); params = list(sig.parameters); assert 'room_id' in params"`

---

### TASK-0.5 — Evict Key `login_attempts` & `command_history`

- **File:** `web/server.py` — class `ConnectionManager`, method `_handle_ws_message`
- **Severity:** 🟡 MEDIUM
- **Masalah:** Entry dalam `login_attempts` dan `command_history` di-evict dari list (sliding window), tapi key dict tidak pernah dihapus. Untuk setiap IP unik yang pernah connect, key tetap ada selamanya → memory leak untuk server long-running.
- **Kondisi saat ini (baris ~479):**
  ```python
  attempts = manager.login_attempts.get(client_ip, [])
  attempts = [t for t in attempts if now - t < 300]
  # key lama tetap ada bahkan jika attempts = []
  ```
- **Fix:** Setelah filtering, hapus key jika hasilnya kosong:
  ```python
  attempts = [t for t in attempts if now - t < 300]
  if not attempts:
      manager.login_attempts.pop(client_ip, None)
  else:
      manager.login_attempts[client_ip] = attempts
  ```
  Lakukan hal sama untuk `command_history`.
- **Verifikasi:** Code review — pastikan `pop(client_ip, None)` ada setelah filter kosong untuk kedua dict

---

## FASE 1 — Critical Security (1–2 hari)

**Prasyarat:** FASE 0 selesai  
**Risiko:** Sedang (perubahan auth logic — test login setelah selesai)  
**Dampak:** 3 CRITICAL + 2 HIGH security vulnerabilities dieliminasi

> ⚠️ **PENTING:** TASK-1.1 dan TASK-1.2 harus dikerjakan **bersama-sama** dalam satu commit. Jika hanya salah satu yang diubah, sistem bisa lock out semua user.

---

### TASK-1.1 — Hapus Plaintext Fallback di `verify_password()`

- **File:** `core/security.py` baris 11–13
- **Severity:** 🔴 CRITICAL
- **Masalah:** Jika `hashed_password` tidak diawali `pbkdf2:sha256:`, fungsi melakukan perbandingan plaintext. Ini artinya password ENV var yang belum di-hash (lihat TASK-1.2) akan diterima langsung dalam bentuk teks mentah — password bocor ke process environment, log, dan `/proc/self/environ`.
- **Kondisi saat ini:**
  ```python
  def verify_password(password: str, hashed_password: str) -> bool:
      if not hashed_password.startswith("pbkdf2:sha256:"):
          # Fallback to plaintext for backwards compatibility or ENV vars
          return password == hashed_password  # ← BAHAYA
  ```
- **Fix:** Ganti fallback dengan `return False`:
  ```python
  def verify_password(password: str, hashed_password: str) -> bool:
      if not hashed_password.startswith("pbkdf2:sha256:"):
          return False  # Tolak semua yang bukan pbkdf2
      try:
          ...
  ```
- **Verifikasi:** 
  ```python
  from core.security import verify_password
  assert verify_password("admin", "admin") == False   # plaintext → ditolak
  assert verify_password("admin", "wrongformat") == False  # format salah → ditolak
  ```

---

### TASK-1.2 — Hash Password ENV Var di Startup

- **File:** `config.py` baris 46–47
- **Severity:** 🔴 CRITICAL
- **Masalah:** Jika `YTGUI_ADMIN_PASS` di-set via environment variable, password disimpan as-is tanpa hashing. Setelah TASK-1.1 menghapus plaintext fallback, user yang memakai ENV var tidak bisa login sama sekali.
- **Kondisi saat ini:**
  ```python
  if "YTGUI_ADMIN_PASS" in os.environ:
      ADMIN_PASSWORD = os.environ["YTGUI_ADMIN_PASS"]  # ← plaintext langsung!
  ```
- **Fix:** Hash password ENV var di situ juga:
  ```python
  if "YTGUI_ADMIN_PASS" in os.environ:
      _raw = os.environ["YTGUI_ADMIN_PASS"]
      if _raw.startswith("pbkdf2:sha256:"):
          ADMIN_PASSWORD = _raw  # sudah di-hash sebelumnya
      else:
          from core.security import hash_password
          ADMIN_PASSWORD = hash_password(_raw)  # hash dulu
  ```
- **Verifikasi:** Set `YTGUI_ADMIN_PASS=test123`, jalankan app, coba login dengan `test123` → harus berhasil. Cek bahwa `ADMIN_PASSWORD` tidak sama dengan `test123`.

---

### TASK-1.3 — Proteksi `/metrics` Endpoint

- **File:** `web/server.py` baris 430–434
- **Severity:** 🔴 CRITICAL
- **Masalah:** Endpoint `/metrics` (Prometheus) terbuka untuk publik tanpa autentikasi. Mengekspos room ID aktif, command history, jumlah koneksi per room — memungkinkan attacker enumerate room dan memahami pola penggunaan.
- **Kondisi saat ini:**
  ```python
  async def handle_metrics(request):
      content, content_type = get_metrics_content()
      ct = content_type.split(";")[0].strip()
      return web.Response(body=content, content_type=ct)
  ```
- **Fix:** Batasi akses ke localhost saja (atau tambah token opsional via env):
  ```python
  async def handle_metrics(request):
      client_ip = request.remote
      allowed_ips = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
      metrics_token = os.environ.get("YTGUI_METRICS_TOKEN")
      
      is_local = client_ip in allowed_ips
      has_valid_token = (
          metrics_token
          and request.headers.get("X-Metrics-Token") == metrics_token
      )
      
      if not is_local and not has_valid_token:
          return web.HTTPForbidden(text="Akses ditolak")
      
      content, content_type = get_metrics_content()
      ct = content_type.split(";")[0].strip()
      return web.Response(body=content, content_type=ct)
  ```
- **Verifikasi:** Akses `/metrics` dari browser (bukan localhost) → harus dapat `403 Forbidden`. Akses dari `curl http://127.0.0.1:8765/metrics` → harus dapat data metrics.

---

### TASK-1.4 — Validasi `room_id` di WebSocket Handler

- **File:** `web/server.py` baris 270–271
- **Severity:** 🟠 HIGH
- **Masalah:** `room_id` diambil langsung dari query param tanpa validasi. Bisa digunakan untuk: (1) membuat ribuan room → memory exhaustion, (2) path traversal via `../etc/passwd` karena `room_id` masuk ke socket path.
- **Kondisi saat ini:**
  ```python
  async def handle_websocket(request):
      room_id = request.query.get("room", "default")
      room = await room_manager.get_or_create_room(room_id)
  ```
- **Fix:** Tambahkan validasi sebelum `get_or_create_room`:
  ```python
  import re
  MAX_ROOMS = 10
  _ROOM_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
  
  async def handle_websocket(request):
      room_id = request.query.get("room", "default")
      
      if not _ROOM_ID_RE.match(room_id):
          return web.HTTPBadRequest(text="Invalid room_id: hanya huruf, angka, '-', '_', max 64 karakter")
      
      if room_id not in room_manager.rooms and len(room_manager.rooms) >= MAX_ROOMS:
          return web.HTTPTooManyRequests(text="Batas maksimum room tercapai")
      
      room = await room_manager.get_or_create_room(room_id)
  ```
  > Pastikan `_ROOM_ID_RE` dan `MAX_ROOMS` dideklarasikan di luar fungsi (level modul).
- **Verifikasi:**
  - `GET /ws?room=../etc/passwd` → harus `400 Bad Request`
  - `GET /ws?room=` → harus `400 Bad Request`
  - `GET /ws?room=AAAAAA...` (>64 char) → harus `400 Bad Request`
  - `GET /ws?room=default` → harus berhasil terkoneksi

---

### TASK-1.5 — Hapus Unauthenticated `next` Bypass

- **File:** `web/server.py` baris 512–523
- **Severity:** 🟠 HIGH
- **Masalah:** Ada pengecualian yang memperbolehkan siapapun mengirim command `next` jika mereka tahu `video_id` track yang sedang diputar. `video_id` YouTube bersifat publik dan dibroadcast via WebSocket state — artinya siapapun yang terhubung ke WebSocket bisa skip lagu tanpa login.
- **Kondisi saat ini:**
  ```python
  if not is_authenticated:
      is_valid_auto_skip = (
          action == "next" 
          and isinstance(data, dict) 
          and data.get("video_id") == getattr(state.current_track, "video_id", None)
      )
      if not is_valid_auto_skip:
          # reject
          return
      # LANJUT TANPA AUTH ← siapapun bisa skip!
  ```
- **Fix:** Hapus seluruh blok `is_valid_auto_skip` — semua command wajib autentikasi:
  ```python
  if not is_authenticated:
      await ws.send_str(json.dumps({
          "type": "error",
          "data": "Akses ditolak. Silakan login sebagai Admin.",
      }))
      return
  ```
- **Verifikasi:** Buka WebSocket tanpa login, kirim `{"type":"cmd","action":"next","data":{"video_id":"xxx"}}` → harus mendapat `{"type":"error","data":"Akses ditolak..."}` dan lagu tidak skip.

---

## FASE 2 — Stabilization / Bug Fixes (2–3 hari)

**Prasyarat:** FASE 1 selesai  
**Risiko:** Rendah — sebagian besar fix terisolasi  
**Dampak:** 5 bug HIGH/MEDIUM dieliminasi, resource leak dihentikan

---

### TASK-2.1 — Lock `_on_track_ended` (Cegah Double-Skip)

- **File:** `engine/playback_controller.py` baris 116–130
- **Severity:** 🟠 HIGH
- **Masalah:** `_on_track_ended` tidak dilindungi lock. Jika MPV mengirim dua event `end-file` secara bersamaan (bug MPV atau reconnect), dua coroutine bisa berjalan paralel. Keduanya membaca `video_id` sebelum state berubah → keduanya lolos guard di `_on_next` → double-skip.
- **Kondisi saat ini:**
  ```python
  async def _on_track_ended(self, event: TrackEndedEvent):
      reason = event.reason
      next_data = {}
      if self.state.current_track:
          next_data["video_id"] = self.state.current_track.video_id
      if reason == "eof":
          await self._on_next(next_data)  # lock baru ada di dalam _on_next
  ```
- **Fix:** Pindahkan lock ke `_on_track_ended`, dan panggil `_advance_to_next` langsung (hindari double-lock):
  ```python
  async def _on_track_ended(self, event: TrackEndedEvent):
      async with self._lock:
          reason = event.reason
          if not self.state.current_track:
              return  # sudah di-skip oleh handler lain
          next_data = {"video_id": self.state.current_track.video_id}
          if reason == "eof":
              await self._advance_to_next()
          elif reason == "error":
              self.state.status = PlayerStatus.ERROR
              await self.bus.publish(LogMessageEvent(message="Terjadi kesalahan pemutaran"))
              await asyncio.sleep(2)
              await self._advance_to_next()
  ```
  > ⚠️ Karena lock dipindah ke sini, pastikan `_on_next` **tidak** acquire lock lagi jika dipanggil dari `_on_track_ended`. Pertimbangkan refactor: pisahkan `_on_next` (untuk pemanggil eksternal, dengan lock) dan `_advance_to_next` (internal, tanpa lock — sudah dipanggil dalam lock).
- **Verifikasi:** Code review — pastikan `self._lock` di-acquire sebelum `reason = event.reason`

---

### TASK-2.2 — Fix Duplicate `http_session`

- **File:** `main.py` baris 54 + `web/server.py` baris 151
- **Severity:** 🟡 MEDIUM
- **Masalah:** `main.py` membuat satu `aiohttp.ClientSession()` dan meneruskannya ke Room (untuk lyrics/sponsorblock). `create_app()` juga membuat session baru sendiri (untuk proxy stream). Ada dua session yang hidup bersamaan — salah satunya bisa leak jika cleanup tidak berjalan dengan benar.
- **Kondisi saat ini:**
  ```python
  # main.py
  http_session = aiohttp.ClientSession()  # session #1
  
  # web/server.py create_app()
  app["http_session"] = aiohttp.ClientSession()  # session #2
  ```
- **Fix:** Teruskan `http_session` dari `main.py` ke `create_app()`:
  ```python
  # main.py
  http_session = aiohttp.ClientSession()
  app = create_app(room_manager, ytdlp, db, http_session=http_session)
  
  # web/server.py
  def create_app(room_manager, ytdlp, db, http_session=None) -> web.Application:
      app["http_session"] = http_session or aiohttp.ClientSession()
      # Hanya daftarkan on_cleanup jika session dibuat di sini
      if http_session is None:
          async def on_cleanup(app):
              await app["http_session"].close()
          app.on_cleanup.append(on_cleanup)
  ```
- **Verifikasi:** Pastikan `aiohttp.ClientSession()` hanya dipanggil sekali selama startup. Cek dengan grep: `grep -n "ClientSession()" main.py web/server.py` → harus hanya 1 baris.

---

### TASK-2.3 — Fix MPV Socket Poll Pakai Global `MPV_SOCKET`

- **File:** `engine/mpv_controller.py` baris 73
- **Severity:** 🟠 HIGH
- **Masalah:** Saat polling menunggu socket tersedia, kode menggunakan `MPV_SOCKET` (global dari config) bukan `self.socket_path`. Dalam skenario multi-room, room "room2" (dengan socket `/tmp/mpv-socket-room2`) akan polling keberadaan socket "default" — polling bisa langsung berhasil (karena room lain sudah punya socket) atau menunggu socket yang salah.
- **Kondisi saat ini:**
  ```python
  if os.name != 'nt':
      for _ in range(50):
          await asyncio.sleep(0.1)
          if os.path.exists(MPV_SOCKET):  # ← MPV_SOCKET global, bukan per-room!
              break
  ```
- **Fix:**
  ```python
  if os.name != 'nt':
      for _ in range(50):
          await asyncio.sleep(0.1)
          if os.path.exists(self.socket_path):  # ← per-room socket path
              break
  ```
- **Verifikasi:** Grep `MPV_SOCKET` di `mpv_controller.py` — tidak boleh ada lagi setelah fix (kecuali di error message di baris 101, yang bisa dibiarkan).

---

### TASK-2.4 — Fix `db.conn` vs `db._conn` di Health Check

- **File:** `web/server.py` baris 307
- **Severity:** 🟡 MEDIUM
- **Masalah:** Health check menggunakan `db.conn` (public attribute), tapi `Database` kemungkinan hanya punya `_conn` (private). Jika attribute tidak ada, health check crash dengan `AttributeError` dan mengembalikan error 500.
- **Kondisi saat ini:**
  ```python
  db_status = "connected" if db.conn else "disconnected"
  ```
- **Fix:** Gunakan `getattr` untuk keamanan, atau periksa attribute yang benar:
  ```python
  db_status = "connected" if getattr(db, "_conn", None) or getattr(db, "conn", None) else "disconnected"
  ```
- **Verifikasi:** Akses `/health` → harus mengembalikan JSON `{"status": "ok", ...}` tanpa error 500.

---

### TASK-2.5 — Fix Script Injection di Termux Notification

- **File:** `integrations/termux_notification.py` baris 71–73
- **Severity:** 🟠 HIGH
- **Masalah:** Script shell ditulis dengan format string tanpa escaping. `self._fifo_path` berasal dari `BASE_DIR` yang bisa dimanipulasi via `YT_PLAYER_BASE` env var. Jika path mengandung karakter khusus (spasi, tanda kutip, semicolon), script bisa berisi perintah yang tidak diinginkan.
- **Kondisi saat ini:**
  ```python
  script_path.write_text(
      f"{_SHEBANG}\necho '{token}' > '{self._fifo_path}' 2>/dev/null\n"
  )
  ```
- **Fix:** Gunakan `shlex.quote()` untuk semua variabel yang masuk ke shell script:
  ```python
  import shlex
  
  script_path.write_text(
      f"{_SHEBANG}\necho {shlex.quote(token)} > {shlex.quote(str(self._fifo_path))} 2>/dev/null\n"
  )
  ```
- **Verifikasi:** Pastikan `import shlex` ada di bagian atas file dan `shlex.quote()` dipakai di kedua tempat.

---

## FASE 3 — Architecture Refactor: Per-Room EventBus (3–5 hari)

**Prasyarat:** FASE 1 dan FASE 2 selesai  
**Risiko:** Tinggi — perubahan arsitektur mendasar, menyentuh hampir semua komponen  
**Dampak:** Multi-room benar-benar terisolasi, cross-room contamination dieliminasi

> ⚠️ **PENTING:** Kerjakan dalam branch terpisah (`feature/per-room-eventbus`). Ini adalah perubahan terbesar dan berpotensi breaking.

---

### Diagram Dependency FASE 3

```
EventBus (hapus singleton global)
    ↓ inject ke
Room.__init__() → self.event_bus = EventBus()
    ↓ inject ke
MpvController(event_bus=room.event_bus)
LyricsFetcher(event_bus=room.event_bus)
SponsorBlockHandler(event_bus=room.event_bus)
PlaybackController(bus=room.event_bus)
RadioMode (publish via injected bus)
    ↓
web/server.py subscribe ke room.event_bus per room
(bukan lagi ke global bus singleton)
```

---

### TASK-3.1 — Pastikan `EventBus` Bisa Diinstansiasi (Bukan Hanya Singleton)

- **File:** `core/event_bus.py`
- **Masalah:** Saat ini `bus` adalah singleton global. Perlu dipastikan class `EventBus` bisa diinstansiasi normal tanpa side effect.
- **Fix:** Pastikan `class EventBus` berdiri sendiri dan `bus = EventBus()` di bawahnya adalah singleton yang nantinya akan dihapus secara bertahap.
- **Verifikasi:** `python -c "from core.event_bus import EventBus; b1 = EventBus(); b2 = EventBus(); assert b1 is not b2"`

---

### TASK-3.2 — `Room` Buat `EventBus` Sendiri

- **File:** `core/room_manager.py`
- **Masalah:** `Room` saat ini menggunakan `from core.event_bus import bus` (global) untuk semua event.
- **Fix:**
  ```python
  from core.event_bus import EventBus
  
  class Room:
      def __init__(self, room_id, db, ytdlp, http_session):
          self.room_id = room_id
          self.state = AppState(room_id=room_id)
          self.event_bus = EventBus()  # ← per-room bus sendiri
          
          self.mpv = MpvController(
              socket_path=f"/tmp/mpv-socket-{room_id}",
              event_bus=self.event_bus  # ← inject
          )
          self.lyrics_fetcher = LyricsFetcher(
              self.state, session=http_session, event_bus=self.event_bus
          )
          self.sponsorblock = SponsorBlockHandler(
              self.mpv, state=self.state, session=http_session, event_bus=self.event_bus
          )
          self.controller = PlaybackController(
              self.room_id, self.event_bus, ...  # ← inject
          )
  ```
- **Verifikasi:** `room1.event_bus is not room2.event_bus` → True

---

### TASK-3.3 — Inject `event_bus` ke `MpvController`

- **File:** `engine/mpv_controller.py`
- **Masalah:** `MpvController._handle_event()` baris 206–212 publish ke global `bus` langsung.
- **Fix:** Tambah parameter `event_bus` ke constructor, simpan sebagai `self._bus`, ganti semua `bus.publish(...)` dengan `self._bus.publish(...)`.
- **Verifikasi:** Grep `from core.event_bus import bus` di `mpv_controller.py` → tidak boleh ada (hanya `EventBus` class saja jika diperlukan untuk type hint).

---

### TASK-3.4 — Inject `event_bus` ke `LyricsFetcher`

- **File:** `integrations/lyrics.py`
- **Masalah:** `LyricsFetcher.__init__` subscribe ke global `bus`. Dalam multi-room, semua `LyricsFetcher` menerima event dari semua room.
- **Fix:** Tambah parameter `event_bus: EventBus`, subscribe ke `event_bus` bukan `bus` global.
- **Verifikasi:** Instantiasi dua `LyricsFetcher` dengan dua `EventBus` berbeda. Publish event ke `bus1` → handler `fetcher2` tidak boleh terpanggil.

---

### TASK-3.5 — Inject `event_bus` ke `SponsorBlockHandler`

- **File:** `integrations/sponsorblock.py`
- **Masalah:** Sama dengan `LyricsFetcher` — subscribe ke global `bus`.
- **Fix:** Tambah parameter `event_bus: EventBus`, ganti semua referensi global `bus` dengan instance yang diinject.
- **Verifikasi:** Sama seperti TASK-3.4 tapi untuk `SponsorBlockHandler`.

---

### TASK-3.6 — Update `web/server.py` Subscribe Per-Room

- **File:** `web/server.py`
- **Masalah:** `create_app()` subscribe ke global `bus`. Setelah TASK-3.2–3.5, event dari room A tidak akan sampai ke global `bus` → WebSocket tidak akan mendapat update.
- **Fix:** Subscribe ke setiap `room.event_bus` saat room dibuat. Tambahkan callback ke `RoomManager`:
  ```python
  def _setup_room_subscriptions(room: Room):
      room.event_bus.subscribe(TrackStartedEvent, 
          lambda e: asyncio.ensure_future(_on_track_started(e)))
      room.event_bus.subscribe(TrackProgressEvent, 
          lambda e: asyncio.ensure_future(_on_track_progress(e)))
      # ... dst untuk semua event type
  ```
  Panggil `_setup_room_subscriptions(room)` setiap kali room baru dibuat di `RoomManager.get_or_create_room()`.
- **Verifikasi:** Buka dua browser tab dengan `?room=room1` dan `?room=room2`. Play lagu di room1 → room2 tidak boleh mendapat update. Play lagu di room2 → room1 tidak boleh mendapat update.

---

### TASK-3.7 — Hapus Penggunaan Global `bus` Singleton

- **File:** Semua file yang masih `import bus` dari `core.event_bus`
- **Masalah:** Setelah semua komponen sudah inject per-room `event_bus`, masih ada referensi ke global `bus` yang perlu dibersihkan.
- **Fix:** Grep semua file: `grep -rn "from core.event_bus import bus"` → hapus satu per satu setelah dipastikan tidak dipakai.
- **Verifikasi:** `grep -rn "from core.event_bus import bus" --include="*.py"` → hanya boleh ada di file yang memang masih butuh (misalnya `radio_mode.py` untuk publish ke room-level bus yang sudah diinject).

---

## FASE 4 — Performance (Opsional)

**Prasyarat:** FASE 3 selesai  
**Risiko:** Rendah  
**Dampak:** Lebih stabil di Termux / low-power device

---

### TASK-4.1 — `ThreadPoolExecutor` Dedicated untuk yt-dlp

- **File:** `engine/ytdlp_client.py`
- **Fix:** Buat `self._executor = ThreadPoolExecutor(max_workers=2)` di `__init__`, gunakan untuk semua `run_in_executor` calls.

### TASK-4.2 — Semaphore untuk Radio Batch Search

- **File:** `engine/radio_mode.py`
- **Fix:** Tambah `_RADIO_SEARCH_SEM = asyncio.Semaphore(2)` level module, wrap `_search_artist` dengan `async with _RADIO_SEARCH_SEM`.

### TASK-4.3 — Timeout untuk `syncedlyrics`

- **File:** `integrations/lyrics.py`
- **Fix:** `asyncio.wait_for(loop.run_in_executor(...), timeout=5.0)` untuk semua panggilan syncedlyrics.

### TASK-4.4 — Per-Room Progress Throttle

- **File:** `web/server.py`
- **Masalah:** `last_progress = {"t": 0.0}` adalah dict global yang dishare semua room — jika room A update progress, room B ikut ter-throttle.
- **Fix:** Pindahkan ke dict per-room: `last_progress: dict[str, float] = {}`, update dengan key `event.room_id`.

---

## Checklist Ringkas untuk Tracking

### FASE 0
- `[ ]` TASK-0.1 — `_TITLE_NOISE_WORDS` → frozenset
- `[ ]` TASK-0.2 — Reset `_retry_count` di `_on_stop`
- `[ ]` TASK-0.3 — Cancel `_bg_tasks` di `on_deactivated`
- `[ ]` TASK-0.4 — Fix `_on_download` signature
- `[ ]` TASK-0.5 — Evict key `login_attempts` & `command_history`

### FASE 1
- `[ ]` TASK-1.1 — Hapus plaintext fallback `verify_password`
- `[ ]` TASK-1.2 — Hash ENV password di startup *(kerjakan bersama 1.1)*
- `[ ]` TASK-1.3 — Proteksi `/metrics` endpoint
- `[ ]` TASK-1.4 — Validasi `room_id`
- `[ ]` TASK-1.5 — Hapus unauthenticated `next` bypass

### FASE 2
- `[ ]` TASK-2.1 — Lock `_on_track_ended`
- `[ ]` TASK-2.2 — Fix duplicate `http_session`
- `[ ]` TASK-2.3 — Fix MPV socket poll (`MPV_SOCKET` → `self.socket_path`)
- `[ ]` TASK-2.4 — Fix `db.conn` vs `db._conn`
- `[ ]` TASK-2.5 — Fix script injection termux notification

### FASE 3
- `[ ]` TASK-3.1 — Verifikasi `EventBus` bisa diinstansiasi
- `[ ]` TASK-3.2 — `Room` buat `event_bus` sendiri
- `[ ]` TASK-3.3 — Inject `event_bus` ke `MpvController`
- `[ ]` TASK-3.4 — Inject `event_bus` ke `LyricsFetcher`
- `[ ]` TASK-3.5 — Inject `event_bus` ke `SponsorBlockHandler`
- `[ ]` TASK-3.6 — Update `web/server.py` subscribe per-room
- `[ ]` TASK-3.7 — Hapus global `bus` singleton

### FASE 4 (Opsional)
- `[ ]` TASK-4.1 — `ThreadPoolExecutor` untuk yt-dlp
- `[ ]` TASK-4.2 — Semaphore radio batch search
- `[ ]` TASK-4.3 — Timeout syncedlyrics
- `[ ]` TASK-4.4 — Per-room progress throttle
