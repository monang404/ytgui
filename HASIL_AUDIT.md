# HASIL AUDIT CODEBASE

## Executive Summary
Proyek ini (YT Player Pro / ytgui) adalah aplikasi pemutar musik YouTube berbasis TUI (Text User Interface) menggunakan arsitektur Event-Driven (Event Bus), `asyncio`, `textual`, `yt-dlp`, dan `mpv`. Secara keseluruhan, arsitektur sudah tertata dengan baik dalam folder `core`, `engine`, `tui`, `cache`, dan `integrations`. Sebagian besar masalah concurrency dan blocking telah diatasi dengan baik menggunakan `run_in_executor`. Namun, proyek ini memiliki satu kelemahan sangat kritis yaitu **ketiadaan pengujian otomatis (Zero Tests)**. Selain itu, terdapat penanganan eksepsi yang terlalu luas (bare exceptions) dan potensi kebocoran sumber daya pada manajemen proses `mpv`.

## Skor Keseluruhan
| Area | Nilai (/10) |
|------|-------------|
| Architecture | 8.5 |
| Code Quality | 7.5 |
| Security | 7.0 |
| Performance | 8.0 |
| Maintainability | 7.5 |
| Testing | 0.0 |
| Documentation | 6.0 |

## Temuan Critical
- **Tidak ada Test Suite (Testing Gaps):** Folder `tests/` sama sekali tidak ada, dan tidak ada implementasi unit test maupun integration test. Hal ini sangat kritis karena aplikasi menggunakan komponen asinkron yang rawan *race condition* jika tidak diuji dengan benar.

## Temuan High
- **Subprocess mpv sinkronus:** Di `engine/mpv_controller.py`, pemanggilan `subprocess.Popen` dijalankan secara sinkronus (`subprocess.Popen` biasa, bukan `asyncio.create_subprocess_exec`). Meski cepat, ini berpotensi memblokir event loop sejenak.
- **Manajemen Proses mpv:** `_mpv_process.terminate()` pada method `close()` mungkin tidak membersihkan *child processes* jika `mpv` memanggil subprocess lain.
- **Bare Exceptions:** Terdapat banyak penggunaan `except Exception:` (misal di `main.py` line 82, `mpv_controller.py` line 151, 158, 176, 211, 228). Praktik ini ("swallowing exceptions") dapat menutupi bug yang tidak terduga.

## Temuan Medium
- **Manajemen State Global:** Kelas `AppState` banyak disentuh dari berbagai komponen secara langsung. Meskipun bersifat Event-Driven, beberapa modul secara langsung merubah atribut `AppState` (contoh: `QueueManager`).
- **Hardcoded API & URLs:** Terdapat hardcoded URL di beberapa tempat (contoh: `connectivitycheck.gstatic.com` di `main.py`, `lrclib.net/api` di `config.py`, dan `youtube.com/watch` di `ytdlp_client.py`).

## Temuan Low
- **Mix Logging & Event Bus:** `bus.publish(LOG_MESSAGE, ...)` dicampur dengan modul standar `logging`.
- **Inconsistent Typing:** Beberapa fungsi belum memiliki anotas tipe (type hinting) Python secara komprehensif, seperti `_on_progress`, parameter `data` di _handle_event.

## Dead Code
- Fungsi fallback Windows fallback TCP socket sudah diatur tapi masih ada percampuran antara `os.name == 'nt'` di config dan `mpv_controller`. Bisa disederhanakan.

## Unused Imports
- Terdapat beberapa import yang tidak digunakan, misalnya mungkin `import json` jika `json` bisa diganti `orjson` untuk performa, dan `import os` di beberapa file yang sudah memakai `pathlib`.

## Unused Dependencies
- `requirements.txt` cukup ramping (rich, yt-dlp, aiosqlite, aiohttp, textual). Semuanya tampak digunakan secara aktif.

## Duplicate Logic
- Logika resolusi URL / ID (misalnya pembentukan URL YouTube) ada di beberapa tempat (`ytdlp_client.py` dan `resolver.py` yang kemungkinan melakukan hal serupa).

## Security Findings
- **Medium Risk:** IPC Server Socket dibuat di `TMPDIR` untuk Unix. Socket di directory temporal berisiko terhadap eksploitasi path traversal/symlink attack dari pengguna lokal lain.
- **Low Risk:** Subprocess arguments untuk `mpv` dan `ytdlp_path` berasal dari environment variables atau resolusi lokal tanpa sanitasi ketat. 

## Performance Findings
- Penggunaan `asyncio.get_running_loop().run_in_executor` pada `yt_dlp` sangat baik untuk menghindari *blocking* event loop utama.
- Ekstraksi `extract_flat=True` untuk search meningkatkan performa drastis.
- Performa UI dapat menurun jika antrian (`Queue`) memuat ribuan track dan list diperbarui berulang kali karena `textual` akan melakukan re-render.

## Architecture Findings
- Arsitektur **Event Bus** meminimalisir *tight coupling* antara TUI dan Engine pemutar. Ini sangat bagus.
- Komponen `QueueManager` sedikit menjadi "God Object" karena terlalu banyak menerima event bus, mengatur volume, hingga integrasi `sponsorblock` dan `lyrics_fetcher`.

## Testing Gaps
- **Semua level test tidak ada.** (0% Code Coverage).
- Tidak ada validasi untuk struktur Database SQL `schema.sql`.

## Documentation Gaps
- `README.md` mungkin menjelaskan struktur dan instalasi, namun `docstrings` di banyak file (contoh: `main.py`, fungsi-fungsi spesifik di `ytdlp_client.py`) masih absen.
- Dokumentasi konfigurasi `.env` (environment variables seperti `YT_PLAYER_BASE`, `YT_PLAYER_SOCKET`) belum terpusat dengan baik di doc.

## Refactoring Recommendations
1. Ubah `subprocess.Popen` di `MpvController.connect()` menjadi `asyncio.create_subprocess_exec`.
2. Tangani eksepsi spesifik ketimbang menggunakan `except Exception: pass`.
3. Kurangi tanggung jawab `QueueManager` (Single Responsibility Principle). Misalnya, Volume Control harusnya ditangani terpisah, atau langsung dipanggil ke MpvController lewat mediator yang lebih kecil.
4. Buat folder `tests/` dan inisiasi menggunakan `pytest` dan `pytest-asyncio`.

## Prioritas Pengerjaan
1. Implementasikan `pytest` untuk event bus, db, dan yt-dlp client.
2. Ganti semua `except Exception: pass` dengan log error atau exception handling spesifik.
3. Gunakan `asyncio.create_subprocess_exec` untuk `mpv`.
4. Refactor `QueueManager` agar lebih modular.

## Quick Wins
- Menambahkan parameter `timeout` pada seluruh request jaringan HTTP `aiohttp.ClientSession()` di `lyrics_fetcher` dan `sponsorblock` (sudah ada di connectivity check, tapi pastikan ada di semua tempat).
- Membersihkan import yang redundan.

## Estimasi Dampak
- **Stabilitas:** Akan meningkat sangat tajam jika ada Test Suite dan penanganan exception lebih spesifik.
- **Keamanan:** Memindahkan direktori Unix Socket dari `/tmp` ke directory home user (`~/.local/state/ytgui/`) akan lebih aman.
- **Maintainability:** Akan jauh lebih baik jika `QueueManager` di-refactor.
- **Performa:** Sudah cukup baik, tidak perlu optimasi mayor.

## Kesimpulan
Proyek ini memiliki pondasi dan arsitektur asinkronus (berbasis Event-Driven) yang kuat. Solusi *blocking calls* dari `yt-dlp` telah ditangani secara elegan. Akan tetapi, kualitas kode ini secara profesional belum siap *production* murni dikarenakan absennya pengujian (Zero Tests). Pembuatan test-suite dan penghapusan *bare exceptions* harus menjadi fokus utama tim selanjutnya.
