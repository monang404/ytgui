# BIG_PATCH.md — ytgui-ytclient
**Versi Dokumen:** 1.0.0  
**Tanggal:** 22 Juni 2026  
**Berdasarkan:** Audit Arsitektur 22 Juni 2026 + Analisis Bug Tersembunyi  
**Branch Target:** `develop`  
**Strategi Release:** Fase bertahap — setiap fase hanya di-push setelah lulus pengujian & validasi

---

## Daftar Isi

1. [Ringkasan Eksekutif & Penilaian Audit](#1-ringkasan-eksekutif--penilaian-audit)
2. [Bug Tersembunyi yang Ditemukan](#2-bug-tersembunyi-yang-ditemukan)
3. [Katalog Patch Lengkap](#3-katalog-patch-lengkap)
4. [Konvensi Penamaan & Penomoran](#4-konvensi-penamaan--penomoran)
5. [Strategi Commit](#5-strategi-commit)
6. [Strategi Release & Push ke GitHub](#6-strategi-release--push-ke-github)
7. [Checklist Pengujian & Validasi per Fase](#7-checklist-pengujian--validasi-per-fase)

---

## 1. Ringkasan Eksekutif & Penilaian Audit

### 1.1 Skor Kesehatan Arsitektur

| Dimensi | Skor Awal | Target Akhir | Catatan |
|---|---|---|---|
| Arsitektur | 5/10 | 8/10 | Setelah Phase 2: CommandBus + single-writer |
| Maintainability | 6/10 | 8/10 | Setelah Phase 2: Protocol/ABC + structured logging |
| Scalability | 2/10 | 4/10 | Terbatas oleh single-MPV; tidak perlu lebih tinggi untuk scope saat ini |
| Reliability | 5/10 | 9/10 | Setelah Phase 1: eliminasi silent crash + race condition |
| Observability | 2/10 | 6/10 | Setelah Phase 2: structlog + health metrics |
| Production Readiness | 3/10 | 7/10 | Setelah Phase 1+2: aman untuk multi-user terbatas |

**Penilaian keseluruhan:** Codebase ditulis dengan niat yang baik dan lebih rapi dari rata-rata proyek personal. Ada awareness terhadap asyncio, pemisahan modul, dan error handling. Namun ada **5 bug tersembunyi kritis** yang tidak tertangkap di audit awal, di samping 5 fatal flaw yang sudah diidentifikasi. Prioritas utama: stabilkan dulu sebelum refactor besar.

### 1.2 Ringkasan Temuan Audit (10 Fatal + 5 Hidden Bug)

| Kode | Judul | Severity | Fase Perbaikan |
|---|---|---|---|
| FATAL-01 | AppState mutable tanpa locking | Critical | Phase 1 |
| FATAL-02 | EventBus serial blocking | Critical | Phase 1 |
| FATAL-03 | `create_task` tanpa error propagation | Critical | Phase 1 |
| FATAL-04 | Lock di dalam event handler — potensi deadlock | Critical | Phase 1 |
| FATAL-05 | Auth token in-memory, hilang saat restart | High | Phase 1 |
| SEC-01 | Password plaintext di filesystem | Medium | Phase 1 |
| SEC-02 | SSRF via stream proxy | High | Phase 1 |
| PERF-01 | `renderFullState()` 3× per detik | High | Phase 0 |
| PERF-02 | EQ canvas 60fps tanpa throttle | High | Phase 0 |
| PERF-03 | Cache-Control: no-store di stream proxy | Medium | Phase 0 |
| **HIDDEN-01** | `AppState` tidak punya field `duration` — AttributeError saat restart | **Critical** | Phase 0 |
| **HIDDEN-02** | `LyricsFetcher.fetch()` — fallback search pakai `session` di luar `async with` | **Critical** | Phase 0 |
| **HIDDEN-03** | `_prefetch_stream_url` overwrite judul/artis track nyata dengan "Temp" | **High** | Phase 0 |
| **HIDDEN-04** | TTL mismatch — resolver pakai 21600s, server.py pakai 7200s | **Medium** | Phase 0 |
| **HIDDEN-05** | `_on_queue_remove` tidak di bawah `_lock` — race condition dengan `_on_queue_select` | **High** | Phase 1 |

---

## 2. Bug Tersembunyi yang Ditemukan

Bagian ini mendokumentasikan 5 bug yang **tidak tercakup dalam laporan audit awal** dan ditemukan melalui analisis kode mendalam.

---

### HIDDEN-01 — `AppState` Tidak Memiliki Field `duration` (Critical)

**File:** `core/state.py` + `engine/playback_controller.py:73`

**Deskripsi:**  
`play_track()` di `playback_controller.py` baris 73 melakukan `self.state.duration = float(track.duration)`, tetapi field `duration` **tidak dideklarasikan** di dataclass `AppState`. Python memperbolehkan penambahan atribut dinamis ke dataclass, sehingga ini tidak langsung melempar error saat runtime. Namun:

1. `_state_to_dict()` tidak tahu tentang `state.duration`, jadi durasi **tidak pernah dikirim ke browser**.
2. Setelah restart atau recreate objek `AppState`, atribut hilang — akses `state.duration` di tempat lain akan `AttributeError`.
3. Progress bar di browser tidak bisa menampilkan durasi yang benar karena data tidak ada di state JSON.

**Evidence:**
```python
# core/state.py — field 'duration' TIDAK ADA
@dataclass
class AppState:
    status: PlayerStatus = PlayerStatus.IDLE
    position: float = 0.0
    volume: int = 80
    # ... 'duration' tidak di sini

# engine/playback_controller.py:73 — ASSIGN ke atribut yang tidak ada di dataclass
self.state.duration = float(track.duration)  # ← dynamic attribute, bukan dataclass field

# web/server.py — _state_to_dict() tidak punya 'duration'
def _state_to_dict(state: AppState) -> dict:
    return {
        "status": state.status.name,
        "position": state.position,
        # ... 'duration' tidak ada di sini!
    }
```

**Fix:**
```python
# core/state.py — tambah field
@dataclass
class AppState:
    ...
    duration: float = 0.0  # ← tambah ini

# web/server.py — tambah ke _state_to_dict()
def _state_to_dict(state: AppState) -> dict:
    return {
        ...
        "duration": state.duration,  # ← tambah ini
    }
```

---

### HIDDEN-02 — `LyricsFetcher.fetch()` Menggunakan `session` di Luar Scope Context Manager (Critical)

**File:** `integrations/lyrics.py:50–85`

**Deskripsi:**  
`async with get_session() as session:` menutup di baris 61 (setelah permintaan pertama selesai). Namun variabel `session` kemudian digunakan lagi di baris 78 untuk fallback search — yaitu **setelah context manager sudah keluar dan session ditutup** (jika bukan shared session). Bila `self._session` tidak di-inject (mode standalone), `aiohttp.ClientSession` yang dibuat oleh `get_session()` sudah ditutup saat fallback dieksekusi.

**Evidence:**
```python
# integrations/lyrics.py — anotasi baris
async with get_session() as session:     # ← baris 50: session DIBUKA
    async with session.get(url_get, ...) as resp:  # ← baris 56: request pertama
        if resp.status == 200:
            lrc = data.get("syncedLyrics") ...
                                         # ← baris 61: context manager KELUAR, session DITUTUP
# ... clean_title, search_query dihitung ...

if not lrc:                              # ← baris 74
    url_search = f"..."
    async with session.get(url_search, ...) as resp:  # ← CRASH! session sudah closed
```

Ini **tidak crash** hanya karena `main.py` selalu meng-inject shared session lewat parameter `session=http_session`. Tapi bila dipakai tanpa inject (unit test, standalone), fallback search selalu gagal diam-diam dengan `RuntimeError: Session is closed`.

**Fix:**
```python
# Pindahkan SELURUH logika ke dalam satu context manager
async with get_session() as session:
    # Request 1: exact match
    async with session.get(url_get, ...) as resp:
        ...

    # Bersihkan judul (boleh di dalam)
    clean_title = ...
    search_query = ...

    # Request 2: fallback search — tetap di dalam scope
    if not lrc:
        async with session.get(url_search, ...) as resp:
            ...

    # Fallback 3: syncedlyrics (executor, tidak butuh session)
    if not lrc:
        lrc = await loop.run_in_executor(None, syncedlyrics.search, search_query)
```

---

### HIDDEN-03 — `_prefetch_stream_url` Menimpa Metadata Track dengan Data "Temp" (High)

**File:** `web/server.py:154–155` dan `web/server.py:312–313`

**Deskripsi:**  
Kedua fungsi `_prefetch_stream_url()` dan `handle_stream()` membuat `TrackInfo` palsu dengan `title="Temp", artist="Temp", duration=0`, lalu memanggil `db.upsert_track()`. Masalahnya, `ON CONFLICT DO UPDATE SET` di `db.py` **selalu menimpa `title`, `artist`, dan `duration`** dengan nilai dari excluded row:

```sql
ON CONFLICT(video_id) DO UPDATE SET
    title=excluded.title,      -- ← akan diset ke "Temp"
    artist=excluded.artist,    -- ← akan diset ke "Temp"
    duration=excluded.duration -- ← akan diset ke 0
```

Jadi jika browser client request `/api/stream/{video_id}` untuk track yang sudah ada di DB dengan metadata lengkap, **metadata track tersebut akan ditimpa "Temp"** di database. Library favorit pengguna rusak.

**Fix:**
```python
# Gunakan query UPDATE yang hanya update stream_url, bukan metadata
async def update_stream_url_only(self, video_id: str, stream_url: str):
    ts = int(time.time())
    await self._conn.execute(
        "UPDATE tracks SET stream_url=?, stream_url_ts=? WHERE video_id=?",
        (stream_url, ts, video_id)
    )
    # Jika track belum ada di DB, tidak perlu insert — hanya cache stream_url
    await self._conn.commit()

# web/server.py — ganti upsert_track dengan update_stream_url_only
await db.update_stream_url_only(video_id, stream_url)
```

---

### HIDDEN-04 — TTL Cache Mismatch: Resolver 21600s vs Server 7200s (Medium)

**File:** `cache/resolver.py:34` dan `web/server.py:149, 300`

**Deskripsi:**  
Ada dua tempat berbeda yang membaca `stream_url_ts` dan menentukan apakah URL masih segar:

- `CacheResolver.resolve()` → TTL **21600 detik (6 jam)**
- `_prefetch_stream_url()` di `web/server.py` → TTL **7200 detik (2 jam)**
- `handle_stream()` di `web/server.py` → TTL **7200 detik (2 jam)**

Efeknya: URL yang dianggap "segar" oleh resolver (jam ke-3 sampai ke-6) akan dianggap "basi" oleh stream proxy — memicu re-fetch tidak perlu via yt-dlp yang memperlambat playback di browser mode. Sebaliknya, skenario bisa terjadi di mana MPV berhasil play (resolver OK) tapi browser stream gagal (proxy re-fetch dan dapat URL berbeda format).

**Fix:**
```python
# config.py — satu konstanta untuk semua
STREAM_URL_TTL_SEC = 21600  # 6 jam — konsisten di semua tempat

# cache/resolver.py, web/server.py — pakai konstanta ini
from config import STREAM_URL_TTL_SEC
if time.time() - ts < STREAM_URL_TTL_SEC:
    ...
```

---

### HIDDEN-05 — `_on_queue_remove` Tidak Dilindungi Lock (High)

**File:** `engine/playback_controller.py:205–211`

**Deskripsi:**  
`_on_queue_select()` (baris 161) menggunakan `async with self._lock` karena ia membaca indeks queue lalu memanggil `popleft()` — operasi yang harus atomic. Namun `_on_queue_remove()` (baris 205) **tidak punya lock**, padahal ia pun membaca `len(self.state.queue)` lalu `del self.state.queue[index]`.

Skenario race:
1. User klik "select queue item 3" → `_on_queue_select` acquire lock, mulai iterasi
2. Bersamaan, user klik "remove queue item 2" → `_on_queue_remove` **langsung jalan** (tidak menunggu lock)
3. `del self.state.queue[2]` terjadi saat `_on_queue_select` sudah hitung indeks — indeks bergeser, lagu yang dimainkan salah

**Evidence:**
```python
async def _on_queue_select(self, index: int):
    async with self._lock:          # ← ada lock
        if 0 <= index < len(self.state.queue):
            ...

async def _on_queue_remove(self, index: int):
    # ← TIDAK ADA lock!
    if 0 <= index < len(self.state.queue):
        removed = self.state.queue[index]
        del self.state.queue[index]
```

**Fix:**
```python
async def _on_queue_remove(self, index: int):
    async with self._lock:          # ← tambah lock
        if 0 <= index < len(self.state.queue):
            removed = self.state.queue[index]
            del self.state.queue[index]
            await self.bus.publish(QUEUE_UPDATED)
            await self.bus.publish(LOG_MESSAGE, f"Dihapus dari antrean: {removed.title}")
```

---

## 3. Katalog Patch Lengkap

Setiap patch memiliki ID unik berformat `PATCH-[FASE]-[NOMOR]`. Total: **24 patch** tersebar di 4 fase.

### Phase 0 — Quick Wins & Critical Bugfix (Target: < 3 Hari)

| ID Patch | Judul | File | Estimasi |
|---|---|---|---|
| PATCH-0-01 | Fix `AppState.duration` field tidak ada | `core/state.py`, `web/server.py` | 30 mnt |
| PATCH-0-02 | Fix `LyricsFetcher` session scope bug | `integrations/lyrics.py` | 45 mnt |
| PATCH-0-03 | Fix `upsert_track` overwrite dengan Temp | `cache/db.py`, `web/server.py` | 1 jam |
| PATCH-0-04 | Fix TTL mismatch — konstanta `STREAM_URL_TTL_SEC` | `config.py`, `cache/resolver.py`, `web/server.py` | 30 mnt |
| PATCH-0-05 | Pisah `progress` handler dari `renderFullState()` | `web/static/app.js` | 45 mnt |
| PATCH-0-06 | Pause EQ animation saat tab non-home | `web/static/app.js` | 1 jam |
| PATCH-0-07 | Pre-bake EQ gradient objects | `web/static/app.js` | 30 mnt |
| PATCH-0-08 | Key-based diffing di `renderQueue()` | `web/static/app.js` | 2 jam |
| PATCH-0-09 | Tambah `defer` di script tag + Cache-Control static | `web/static/index.html`, `web/server.py` | 15 mnt |
| PATCH-0-10 | Perbaiki `Cache-Control` stream proxy ke `private, max-age=3600` | `web/server.py` | 10 mnt |
| PATCH-0-11 | Kurangi chunk size stream dari 64KB ke 16KB | `web/server.py` | 5 mnt |
| PATCH-0-12 | Optimistic UI untuk tombol play/next/prev | `web/static/app.js` | 2 jam |

### Phase 1 — Stabilisasi & Keamanan (Target: 1–2 Minggu)

| ID Patch | Judul | File | Estimasi |
|---|---|---|---|
| PATCH-1-01 | Implementasi `_safe_create_task()` helper | `core/task_utils.py` (baru) | 1 hari |
| PATCH-1-02 | Ganti semua bare `create_task()` dengan `_safe_create_task()` | Seluruh codebase | 1 hari |
| PATCH-1-03 | Concurrent dispatch di EventBus dengan `asyncio.gather` | `core/event_bus.py` | 3 jam |
| PATCH-1-04 | Fix `_on_queue_remove` tidak punya lock (HIDDEN-05) | `engine/playback_controller.py` | 30 mnt |
| PATCH-1-05 | Generation counter di `LyricsFetcher` untuk cancel fetch lama | `integrations/lyrics.py` | 2 jam |
| PATCH-1-06 | Timeout + circuit breaker di `_gather_batch()` radio | `engine/radio_mode.py` | 1 jam |
| PATCH-1-07 | Server-side timestamp di progress broadcast (drift correction) | `web/server.py`, `web/static/app.js` | 4 jam |
| PATCH-1-08 | SSRF validation di stream proxy | `web/server.py` | 1 jam |
| PATCH-1-09 | Hash admin password dengan `hashlib.pbkdf2_hmac` | `config.py`, `web/server.py` | 2 jam |
| PATCH-1-10 | Periodic cleanup `command_history` dan `login_attempts` | `web/server.py` | 1 jam |
| PATCH-1-11 | Session token persistence di SQLite | `cache/db.py`, `web/server.py` | 2 jam |
| PATCH-1-12 | Defense-in-depth path check di stream endpoint | `web/server.py` | 30 mnt |

### Phase 2 — Refactor Arsitektur (Target: 2–6 Minggu)

| ID Patch | Judul | File | Estimasi |
|---|---|---|---|
| PATCH-2-01 | Protocol/ABC untuk MpvAdapter, YtDlpAdapter, DBRepository | `core/ports.py` (baru) | 3 hari |
| PATCH-2-02 | CommandBus single-writer pattern | `core/command_bus.py` (baru) | 3 hari |
| PATCH-2-03 | Structured logging dengan `structlog` | Seluruh codebase | 2 hari |
| PATCH-2-04 | Ubah `audio_output` ke Enum | `core/state.py`, seluruh codebase | 1 hari |

---

## 4. Konvensi Penamaan & Penomoran

### 4.1 Format Patch ID

```
PATCH-[FASE]-[NOMOR]

Contoh: PATCH-0-01, PATCH-1-03, PATCH-2-02
```

- **FASE:** Angka integer (0, 1, 2) sesuai fase migrasi
- **NOMOR:** Dua digit dengan leading zero (01, 02, ..., 12)

### 4.2 Penamaan Branch

Semua pekerjaan dilakukan di sub-branch dari `develop`, dengan format:

```
patch/[FASE]-[NOMOR]-[slug-deskripsi]

Contoh:
  patch/0-01-fix-appstate-duration
  patch/0-05-decouple-progress-render
  patch/1-03-eventbus-concurrent-dispatch
  patch/1-08-ssrf-stream-validation
  patch/2-01-ports-abc-adapters
```

**Aturan:**
- Slug menggunakan huruf kecil dan tanda hubung (`-`)
- Maksimal 5 kata pada slug
- Setelah review dan merge ke `develop`, branch sub-patch **dihapus**

### 4.3 Penamaan Commit

Format: **Conventional Commits** dengan scope tambahan patch ID.

```
<type>(<scope>): <deskripsi singkat>

[body opsional — jelaskan mengapa, bukan apa]

Refs: PATCH-[FASE]-[NOMOR]
```

**Tipe yang digunakan:**

| Tipe | Penggunaan |
|---|---|
| `fix` | Memperbaiki bug |
| `feat` | Fitur baru |
| `refactor` | Refactor tanpa mengubah behavior |
| `perf` | Peningkatan performa |
| `security` | Perbaikan keamanan |
| `test` | Menambah/memperbaiki test |
| `docs` | Update dokumentasi |
| `chore` | Perubahan infrastruktur/build |

**Scope** menggunakan nama modul: `state`, `event-bus`, `playback`, `lyrics`, `radio`, `server`, `stream-proxy`, `ui`, `task-utils`

**Contoh commit yang benar:**
```
fix(state): tambah field duration ke AppState dataclass

AppState.duration tidak pernah dideklarasikan sebagai field
dataclass, hanya sebagai dynamic attribute. Akibatnya field
ini tidak termasuk dalam _state_to_dict() dan progress bar
browser tidak bisa menampilkan durasi.

Refs: PATCH-0-01
```

```
security(stream-proxy): validasi URL sebelum proxy ke upstream

Cegah SSRF — hanya izinkan domain *.youtube.com dan
*.googlevideo.com sebagai target proxy stream.

Refs: PATCH-1-08
```

```
perf(ui): pisah progress handler dari renderFullState

renderFullState() dipanggil 3x/detik pada setiap TRACK_PROGRESS
event. Sekarang progress update hanya memperbarui position bar
dan timestamp tanpa rebuild seluruh DOM.

Refs: PATCH-0-05
```

### 4.4 Penamaan Tag Release

```
v[MAJOR].[MINOR].[PATCH]-phase[N]

Contoh:
  v0.9.0-phase0   — selesai Phase 0 (quick wins)
  v1.0.0-phase1   — selesai Phase 1 (stabilisasi)
  v1.1.0-phase2   — selesai Phase 2 (refactor)

Untuk hotfix di tengah fase:
  v0.9.1-phase0   — hotfix setelah Phase 0 release
```

---

## 5. Strategi Commit

### 5.1 Prinsip Dasar

1. **Satu commit = satu concern.** Jangan campur fix bug dengan refactor dalam satu commit.
2. **Commit atomic** — setiap commit harus bisa di-revert tanpa merusak fungsi lain.
3. **Commit passing tests** — jangan commit kode yang menyebabkan test gagal.
4. **Tidak ada "WIP" commit di `develop`** — squash sebelum merge jika perlu.

### 5.2 Alur Kerja per Patch

```bash
# 1. Buat branch dari develop
git checkout develop
git pull origin develop
git checkout -b patch/0-01-fix-appstate-duration

# 2. Kerjakan perubahan
# edit core/state.py, web/server.py

# 3. Staging terselektif (jangan git add -A sembarangan)
git add core/state.py
git commit -m "fix(state): tambah field duration ke AppState dataclass

AppState.duration tidak pernah dideklarasikan sebagai field
dataclass, hanya sebagai dynamic attribute. Akibatnya field
ini tidak termasuk dalam _state_to_dict() dan progress bar
browser tidak bisa menampilkan durasi.

Refs: PATCH-0-01"

git add web/server.py
git commit -m "fix(server): sertakan duration dalam _state_to_dict()

Refs: PATCH-0-01"

# 4. Jalankan test lokal sebelum push
python -m pytest tests/ -v

# 5. Push branch dan buat PR
git push origin patch/0-01-fix-appstate-duration
# Buat Pull Request ke 'develop' via GitHub
```

### 5.3 Aturan Merge ke `develop`

- Wajib: minimal **1 review** dari maintainer lain (atau self-review dengan checklist)
- Wajib: semua item di **Checklist Validasi** (Bagian 7) untuk fase tersebut sudah hijau
- Gunakan **Squash & Merge** untuk patch tunggal, **Merge Commit** untuk grup patch satu fase
- Setelah merge: **hapus branch patch**

### 5.4 Urutan Commit yang Direkomendasikan per Fase

**Phase 0 (urutan wajib — ada dependency):**
```
PATCH-0-01  ← harus duluan (state.duration diperlukan PATCH-0-05 dan PATCH-0-12)
PATCH-0-02  ← bisa paralel dengan 0-01
PATCH-0-03  ← harus setelah db.py review
PATCH-0-04  ← bisa kapan saja di Phase 0
PATCH-0-09  ← bisa kapan saja (independent)
PATCH-0-10, PATCH-0-11  ← bersamaan (satu file)
PATCH-0-05  ← setelah 0-01
PATCH-0-06, PATCH-0-07, PATCH-0-08  ← bisa paralel (semua app.js, hindari conflict)
PATCH-0-12  ← terakhir di Phase 0 (butuh 0-05 selesai dulu)
```

**Phase 1 (urutan wajib):**
```
PATCH-1-01  ← task_utils.py harus ada duluan
PATCH-1-02  ← setelah 1-01
PATCH-1-04  ← bisa duluan (independent, satu baris fix)
PATCH-1-03  ← harus setelah 1-01 (butuh pattern baru)
PATCH-1-05  ← bisa paralel dengan 1-03
PATCH-1-06  ← independent
PATCH-1-07  ← setelah diskusi arsitektur audio sync
PATCH-1-08  ← security, bisa kapan saja
PATCH-1-09  ← security, bisa kapan saja (sebelum release)
PATCH-1-10  ← bisa kapan saja
PATCH-1-11  ← setelah 1-09 (schema DB baru)
PATCH-1-12  ← setelah 1-08 (defense in depth)
```

---

## 6. Strategi Release & Push ke GitHub

### 6.1 Overview Branch Strategy

```
main
  └── develop                    ← integrasi aktif (semua PR masuk sini)
        ├── patch/0-01-...       ← branch kerja per patch
        ├── patch/0-02-...
        ├── ...
        └── patch/1-01-...
```

**Aturan keras:**
- `main` hanya menerima merge dari `develop`, dan hanya setelah release tag dibuat
- Tidak ada commit langsung ke `main` atau `develop` (selalu via PR)
- Branch `patch/*` dihapus setelah merge ke `develop`

### 6.2 Alur Release per Fase

#### Phase 0 Release: `v0.9.0-phase0`

```bash
# Setelah semua PATCH-0-* sudah di-merge ke develop dan lulus validasi:

# 1. Pastikan develop up to date
git checkout develop
git pull origin develop

# 2. Jalankan full test suite
python -m pytest tests/ -v --tb=short

# 3. Buat tag release
git tag -a v0.9.0-phase0 -m "Phase 0: Quick wins + critical bugfix

Perubahan utama:
- fix: AppState.duration field (HIDDEN-01)
- fix: LyricsFetcher session scope bug (HIDDEN-02)
- fix: upsert_track tidak lagi overwrite metadata dengan Temp (HIDDEN-03)
- fix: TTL mismatch stream cache (HIDDEN-04)
- perf: progress event tidak trigger renderFullState()
- perf: EQ animation pause saat tab non-home
- perf: Cache-Control stream proxy ke private, max-age=3600
- perf: chunk size stream 64KB → 16KB
- feat: optimistic UI tombol player

Lihat BIG_PATCH.md untuk detail lengkap."

# 4. Push tag ke GitHub
git push origin v0.9.0-phase0

# 5. Merge develop ke main (Phase 0 stable)
git checkout main
git merge --no-ff develop -m "release: v0.9.0-phase0"
git push origin main
```

#### Phase 1 Release: `v1.0.0-phase1`

```bash
# Setelah semua PATCH-1-* lulus validasi di develop:

git checkout develop
git pull origin develop
python -m pytest tests/ -v

# Buat GitHub Release dengan notes
git tag -a v1.0.0-phase1 -m "Phase 1: Stabilisasi & keamanan

Perubahan utama:
- fix: safe_create_task() — eliminasi silent crash (PATCH-1-01, 1-02)
- fix: EventBus concurrent dispatch — tidak lagi serial blocking (PATCH-1-03)
- fix: _on_queue_remove di bawah lock (HIDDEN-05) (PATCH-1-04)
- fix: LyricsFetcher generation counter — race condition dihilangkan (PATCH-1-05)
- fix: circuit breaker + timeout di radio _gather_batch (PATCH-1-06)
- feat: audio drift correction dengan server-side timestamp (PATCH-1-07)
- security: SSRF validation di stream proxy (PATCH-1-08)
- security: password hashing pbkdf2 (PATCH-1-09)
- fix: session token persistence di SQLite (PATCH-1-11)

Breaking changes: NONE
Migration: jalankan 'python main.py --migrate-db' untuk schema baru (sessions table)"

git push origin v1.0.0-phase1
git checkout main
git merge --no-ff develop -m "release: v1.0.0-phase1"
git push origin main
```

#### Phase 2 Release: `v1.1.0-phase2`

```bash
git tag -a v1.1.0-phase2 -m "Phase 2: Refactor arsitektur

- refactor: Protocol/ABC ports untuk adapters
- refactor: CommandBus single-writer pattern
- feat: structured logging dengan structlog
- refactor: audio_output sebagai Enum
- test: unit test suite domain layer"

git push origin v1.1.0-phase2
git checkout main
git merge --no-ff develop -m "release: v1.1.0-phase2"
git push origin main
```

### 6.3 GitHub Release Notes Template

Setiap tag harus disertai GitHub Release dengan format:

```markdown
## ytgui-ytclient v[VERSION]

### Apa yang berubah
[Ringkasan 2-3 kalimat tentang fokus release ini]

### Bug fixes
- fix(state): [deskripsi] ([PATCH-ID])
- fix(lyrics): [deskripsi] ([PATCH-ID])

### Peningkatan performa
- perf(ui): [deskripsi] ([PATCH-ID])

### Keamanan
- security: [deskripsi] ([PATCH-ID])

### Breaking changes
[Daftar atau "Tidak ada"]

### Cara upgrade
```bash
git pull
pip install -r requirements.txt
# [instruksi migrasi jika ada]
```

### Known issues
[Daftar bug yang diketahui tapi belum diperbaiki di release ini]
```

### 6.4 Hotfix Strategy

Jika ada bug kritis ditemukan setelah release:

```bash
# Buat hotfix branch dari main (bukan develop)
git checkout main
git checkout -b hotfix/[PATCH-ID]-[slug]

# Kerjakan fix
git commit -m "fix([scope]): [deskripsi]

Refs: [PATCH-ID]
Hotfix untuk: v[VERSION]"

# Merge ke main DAN develop
git checkout main
git merge --no-ff hotfix/... -m "hotfix: [deskripsi singkat]"
git tag -a v[VERSION]+1-hotfix -m "Hotfix: [deskripsi]"
git push origin main v[VERSION]+1-hotfix

git checkout develop
git merge --no-ff hotfix/...
git push origin develop

git branch -d hotfix/...
```

---

## 7. Checklist Pengujian & Validasi per Fase

### 7.1 Checklist Phase 0

Setiap item wajib dicentang sebelum tag `v0.9.0-phase0` dibuat.

#### PATCH-0-01: AppState.duration
- [ ] `AppState().duration` tidak melempar `AttributeError`
- [ ] `_state_to_dict(state)` mengandung key `"duration"`
- [ ] Browser menerima `duration` dalam payload state WebSocket
- [ ] Progress bar browser menampilkan durasi yang benar

#### PATCH-0-02: LyricsFetcher session scope
- [ ] Lyrics muncul bahkan tanpa inject shared session (standalone mode)
- [ ] Fallback search (tanpa exact match) berhasil menemukan lirik
- [ ] Tidak ada `RuntimeError: Session is closed` di log

#### PATCH-0-03: upsert_track Temp overwrite
- [ ] Setelah browser request `/api/stream/{video_id}`, metadata track di DB tidak berubah
- [ ] `SELECT title, artist FROM tracks WHERE video_id = '...'` masih mengembalikan nilai asli
- [ ] Fungsi baru `update_stream_url_only()` ada di `cache/db.py`

#### PATCH-0-04: TTL mismatch
- [ ] `config.py` punya konstanta `STREAM_URL_TTL_SEC = 21600`
- [ ] `resolver.py` pakai `STREAM_URL_TTL_SEC` (bukan magic number)
- [ ] `web/server.py` pakai `STREAM_URL_TTL_SEC` (bukan 7200)
- [ ] `grep -rn "7200\|21600" .` hanya mengembalikan file config.py

#### PATCH-0-05: Decouple progress dari renderFullState
- [ ] Klik play/pause tidak lag
- [ ] Progress bar bergerak halus tanpa frame drop
- [ ] Chrome DevTools → Performance: tidak ada DOM rebuild masif tiap 333ms
- [ ] `renderFullState()` **tidak** dipanggil dari `case "progress":`

#### PATCH-0-06 & 0-07: EQ Animation
- [ ] Pindah ke tab Queue/Search → `cancelAnimationFrame` dipanggil (verifikasi via console.log)
- [ ] Kembali ke tab Home → EQ animation berjalan kembali
- [ ] Chrome DevTools → Performance: CPU usage turun >30% saat di tab non-home
- [ ] Gradient object dibuat sekali (bukan di tiap frame)

#### PATCH-0-08: Key-based diffing renderQueue
- [ ] Tambah 5 lagu ke queue → hanya item baru yang di-render ulang (bukan seluruh list)
- [ ] Remove item dari tengah queue → DOM update minimal
- [ ] Tidak ada flash/flicker pada queue saat progress update

#### PATCH-0-09–0-11: Performance server
- [ ] `index.html` punya `<script defer src="...">` 
- [ ] Static assets (`/static/*`) mengembalikan `Cache-Control: public, max-age=3600`
- [ ] Stream endpoint mengembalikan `Cache-Control: private, max-age=3600`
- [ ] Chunk size yang dikirim ke browser adalah 16384 bytes (bukan 65536)

#### PATCH-0-12: Optimistic UI
- [ ] Tombol play berubah state **instan** (sebelum konfirmasi dari server)
- [ ] Jika server gagal merespons, state tombol kembali ke semula dalam 3 detik
- [ ] Tidak ada double-action jika user klik cepat dua kali

#### Validasi Integrasi Phase 0
- [ ] Jalankan server, putar 5 lagu berturut-turut tanpa error
- [ ] Verifikasi lirik tampil dengan benar untuk 3 lagu yang berbeda
- [ ] Verifikasi radio mode berjalan 10 menit tanpa freeze
- [ ] Tidak ada log error di `stderr` selama 5 menit playback normal

---

### 7.2 Checklist Phase 1

#### PATCH-1-01 & 1-02: safe_create_task
- [ ] `core/task_utils.py` ada dengan fungsi `safe_create_task(coro, name, on_error)`
- [ ] `grep -rn "asyncio.create_task" .` (kecuali task_utils.py sendiri) mengembalikan 0 hasil
- [ ] Simulasikan crash di `_do_fetch` lyrics → error muncul di log, bukan silent
- [ ] Download gagal → pesan error muncul di UI (bukan diam-diam)

#### PATCH-1-03: EventBus concurrent dispatch
- [ ] Handler TRACK_PROGRESS berjalan paralel (ukur dengan timestamp log)
- [ ] Satu handler lambat (simulasikan `asyncio.sleep(2)`) tidak memblokir handler lain
- [ ] Tidak ada deadlock setelah 10 menit operasi normal
- [ ] Urutan handler yang berbeda tidak menyebabkan state inconsistency

#### PATCH-1-04: _on_queue_remove lock
- [ ] Kode `_on_queue_remove` menggunakan `async with self._lock:`
- [ ] Simulasikan concurrent remove + select: tidak ada `IndexError` atau lagu salah dimainkan

#### PATCH-1-05: LyricsFetcher generation counter
- [ ] Skip lagu 5x cepat → hanya lirik lagu terakhir yang tampil (bukan lirik lagu ke-3)
- [ ] Tidak ada `Task cancelled` warning di log yang berhubungan dengan lyrics
- [ ] `self._current_generation` dan `self._fetch_task` ada di `__init__`

#### PATCH-1-06: Radio circuit breaker
- [ ] Simulasikan yt-dlp lambat (mock dengan `asyncio.sleep(10)`) → radio tidak freeze
- [ ] `_gather_batch()` memiliki `asyncio.wait_for()` dengan timeout 30 detik
- [ ] Setelah timeout, radio mencoba lagi dengan seed artist berbeda

#### PATCH-1-07: Audio drift correction
- [ ] Payload `"progress"` dari server mengandung `"server_ts"` (float)
- [ ] Setelah 10 menit playback, selisih posisi MPV vs browser audio < 500ms
- [ ] Correction hanya dijalankan jika drift > 500ms (tidak jump jika normal)

#### PATCH-1-08 & 1-12: SSRF + path validation
- [ ] Request ke `http://169.254.169.254/` via manipulasi DB → HTTP 400/403
- [ ] Hanya URL dengan skema `https` dan domain `*.googlevideo.com` / `*.youtube.com` yang diizinkan
- [ ] `cache_file.resolve().is_relative_to(CACHE_DIR)` ada di `handle_stream`

#### PATCH-1-09: Password hashing
- [ ] Password di `admin_password.txt` tidak lagi plaintext
- [ ] Login masih berfungsi dengan password yang sama
- [ ] Verifikasi menggunakan `hashlib.pbkdf2_hmac` atau `bcrypt`

#### PATCH-1-10 & 1-11: Cleanup + session persistence
- [ ] `command_history` tidak tumbuh melebihi 1000 entry per IP
- [ ] Setelah server restart, admin yang sudah login sebelumnya bisa langsung akses tanpa login ulang
- [ ] Tabel `sessions` ada di schema SQLite

#### Validasi Integrasi Phase 1
- [ ] Simulasikan 3 client WebSocket bersamaan, semua send CMD_NEXT → tidak ada crash
- [ ] Jalankan 30 menit tanpa interaksi → tidak ada memory leak signifikan (`tracemalloc`)
- [ ] Restart server di tengah playback → auto-reconnect dalam < 5 detik
- [ ] Login attempt 10x dengan password salah → rate limiting aktif
- [ ] Semua log error memiliki format yang jelas (tidak "Task exception was never retrieved")

---

### 7.3 Checklist Phase 2

#### PATCH-2-01: Protocol/ABC
- [ ] `core/ports.py` ada dengan `MpvPort`, `YtDlpPort`, `DBPort` sebagai `Protocol`
- [ ] `MpvController`, `YtDlpClient`, `Database` mengimplementasikan protocol tersebut
- [ ] Unit test bisa menggunakan mock yang mengimplementasikan protocol (tanpa MPV nyata)

#### PATCH-2-02: CommandBus
- [ ] `core/command_bus.py` ada dengan single consumer loop
- [ ] Tidak ada `asyncio.Lock` di dalam event handler (lock tidak diperlukan lagi)
- [ ] Latency antara "klik play" sampai `play_track()` dipanggil < 50ms

#### PATCH-2-03: Structured logging
- [ ] `structlog` terpasang dan dikonfigurasi di `main.py`
- [ ] Setiap log entry mengandung `event`, `module`, `level`, `timestamp`
- [ ] Log bisa diparse sebagai JSON (`jq . < ytgui.log` berhasil)

#### PATCH-2-04: Enum audio_output
- [ ] `AudioOutput` Enum ada di `core/state.py` (`DEVICE`, `BROWSER`)
- [ ] `grep -rn '"device"\|"browser"' .` tidak mengembalikan hasil (kecuali dokumentasi)
- [ ] Semua perbandingan menggunakan `AudioOutput.DEVICE` / `AudioOutput.BROWSER`

#### Validasi Integrasi Phase 2
- [ ] Semua test dari Phase 0 dan Phase 1 masih lulus (regression)
- [ ] Unit test coverage domain layer > 60%
- [ ] Onboarding developer baru: bisa jalankan test tanpa MPV installed
- [ ] `mypy core/ engine/ cache/ integrations/` tidak ada error

---

## Ringkasan Jadwal

| Fase | Durasi Target | Tag Release | Kondisi Merge ke Main |
|---|---|---|---|
| Phase 0 | 3 hari | `v0.9.0-phase0` | Semua checklist 7.1 hijau |
| Phase 1 | 10–14 hari | `v1.0.0-phase1` | Semua checklist 7.2 hijau |
| Phase 2 | 14–42 hari | `v1.1.0-phase2` | Semua checklist 7.3 hijau |
| Hotfix | Kapan saja | `v*.*.*-hotfix` | Review + test singkat |

---

*Dokumen ini adalah living document. Update setiap kali ada patch baru yang ditambahkan atau checklist direvisi. Versi terakhir selalu ada di `develop` branch.*
