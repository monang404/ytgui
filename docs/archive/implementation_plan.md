# Rencana Implementasi Perbaikan Hasil Audit Teknis

Dokumen ini berisi rencana taktis untuk menyelesaikan temuan audit prioritas tinggi (P0/P1) dari laporan [HASIL_AUDIT_CLAUDE.md](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/HASIL_AUDIT_CLAUDE.md). Fokus utama adalah meningkatkan aspek **Keamanan (Security)**, **Stabilitas Backend**, **DevOps**, dan **User Experience (UX)**.

---

## User Review Required

> [!IMPORTANT]
> **Kredensial Default Dihapus**: Mulai versi ini, kredensial admin tidak lagi di-hardcode ke `bagasfm`/`bagasradio2626@`. Password acak akan digenerate otomatis saat startup pertama dan disimpan di file lokal `cache/admin_password.txt`. Pengguna juga dapat mengatur kredensial kustom via environment variables (`YTGUI_ADMIN_USER` dan `YTGUI_ADMIN_PASS`).
> 
> **Penyimpanan Session Token**: Kredensial tidak akan disimpan lagi secara plaintext di `localStorage` browser. Kami beralih menggunakan in-memory session token yang di-issue oleh server setelah login berhasil.

---

## Open Questions

Ada satu aspek opsional dalam audit:
* Apakah direktori `tui/` ingin dihapus atau dibiarkan saja? Berdasarkan audit, folder TUI (`tui/`) tampaknya tidak diintegrasikan langsung ke `main.py` setelah migrasi ke Web UI. Kami menyarankan untuk membiarkannya terlebih dahulu, namun jika Anda ingin menghapusnya untuk membersihkan codebase, beri tahu kami.

---

## Proposed Changes

### Core & Configuration

#### [MODIFY] [config.py](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/config.py)
* Hapus default fallback username (`bagasfm`) dan password (`bagasradio2626@`).
* Tambahkan deteksi environment variable `YTGUI_ADMIN_USER` (default: `admin`) dan `YTGUI_ADMIN_PASS`.
* Jika `YTGUI_ADMIN_PASS` tidak diset di environment, cari password acak dari `cache/admin_password.txt`. Jika tidak ada, buat password acak baru, simpan ke file tersebut, dan tandai variabel global `IS_PASSWORD_AUTO_GENERATED = True`.

#### [MODIFY] [README.md](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/README.md)
* Hapus paragraf yang menyebutkan kredensial plaintext `bagasfm`/`bagasradio2626@`.
* Tambahkan petunjuk baru mengenai login admin menggunakan password acak yang dicetak di konsol server saat pertama kali dijalankan, atau cara konfigurasi menggunakan environment variables.

---

### Web Server & Authentication

#### [MODIFY] [web/server.py](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/web/server.py)
* **Session Token Auth**: Tambahkan generator token `secrets.token_hex(16)` di server saat otentikasi login berhasil, simpan ke dalam set `ConnectionManager.session_tokens` in-memory. Dukung validasi login menggunakan session token untuk reconnect.
* **Rate Limiting Login**: Batasi percobaan login gagal per alamat IP klien (`request.remote`) maksimal 5 kali dalam periode 5 menit.
* **Information Disclosure Fix**: Modifikasi `_track_to_dict` agar tidak mengekspos `local_path` (path sistem file lokal) dan `stream_url` ke browser client. Kirim boolean `is_cached` sebagai gantinya.
* **Stream Video ID Validation**: Tambahkan pemeriksaan regex ketat (`^[a-zA-Z0-9_-]{11}$`) untuk `video_id` di endpoint `/api/stream/{video_id}` guna mencegah path traversal.
* **Health Check Endpoint**: Tambahkan route `GET /health` yang mengecek status database SQLite dan koneksi IPC MPV.

#### [MODIFY] [web/static/app.js](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/web/static/app.js)
* **Session Token Client**: Simpan `session_token` di `localStorage` setelah login berhasil daripada menyimpan password. Gunakan token ini untuk melakukan otentikasi otomatis saat menyambungkan kembali WebSocket.
* **UX Loading Indicator**: Tampilkan ikon loading spinner di bagian *Now Playing* ketika status track adalah `LOADING` agar pengguna mengetahui server sedang memuat track.
* **Race Condition client support**: Kirim parameter `video_id` saat mengirim perintah `next` agar server dapat memvalidasi jika track yang ingin dilewati memang track yang sedang aktif.

---

### Core Playback & Audio Engine

#### [MODIFY] [engine/playback_controller.py](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/engine/playback_controller.py)
* **Double-Skip Prevention**: Modifikasi `_on_next` untuk menerima parameter opsional `video_id`. Jika `video_id` dikirimkan dan tidak cocok dengan `current_track.video_id`, abaikan perintah lewati (skip) tersebut karena track tersebut sudah berubah/EOF sebelumnya.
* Kirimkan `video_id` secara otomatis dari handler `_on_track_ended` (EOF).

#### [MODIFY] [engine/radio_mode.py](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/engine/radio_mode.py)
* **Parallel Search Acceleration**: Hapus semaphore `self._search_lock` yang membatasi pencarian artis agar pencarian batch berjalan paralel sejati dalam thread pool (kecepatan pencarian radio meningkat 3-4x).
* **Queue Capping**: Batasi ukuran penyimpanan maksimal `radio_queue` menjadi 30 track agar terhindar dari kebocoran memori potensial.

#### [MODIFY] [main.py](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/main.py)
* **MPV Auto-Reconnect**: Tambahkan task background asinkron `mpv_reconnect_checker` yang berjalan setiap 5 detik. Jika mendeteksi `mpv.is_connected` bernilai `False`, panggil cleanup `close()` lalu reconnect/respawn via `connect()`.
* Cetak informasi kredensial acak ke terminal saat startup jika password digenerate otomatis.

---

### DevOps & Dependency

#### [MODIFY] [requirements.txt](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/requirements.txt)
* Pin semua library dependency inti ke versi stabil yang saat ini digunakan di sistem:
  ```
  yt-dlp==2026.3.17
  aiosqlite==0.22.1
  aiohttp==3.14.1
  syncedlyrics==1.0.1
  ```

#### [NEW] [start.sh](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/start.sh)
* Script pembungkus startup bash untuk Linux/Android Termux dengan petunjuk penggunaan environment variables.

#### [NEW] [start.bat](file:///c:/Users/PUTRA%20JAYA%20LIMBANGAN/Documents/ytgui/ytgui%20v2.0.0/ytgui/start.bat)
* Script pembungkus startup batch file untuk sistem operasi Windows.

---

## Verification Plan

### Automated Tests
* Kita akan menjalankan unit test event bus yang ada untuk memastikan tidak ada regresi:
  ```powershell
  pytest tests/test_event_bus.py
  ```

### Manual Verification
1. **Startup & Password Generation**:
   - Hapus/pindahkan file `cache/admin_password.txt` (jika ada).
   - Jalankan `python main.py`. Pastikan tercetak log warning keamanan di konsol beserta username (`admin`) dan password acak yang digenerate.
   - Periksa bahwa file `cache/admin_password.txt` telah dibuat.
   - Restart server dan pastikan password tidak berubah (dibaca dari file).
2. **Session Token & Login**:
   - Buka browser ke `http://localhost:8765`.
   - Cobalah login dengan password yang salah sebanyak 5 kali berturut-turut. Pastikan akun terkunci sementara dan muncul pesan lockout.
   - Tunggu sebentar/reset, login dengan username `admin` dan password acak yang tertera di file. Pastikan masuk ke mode Admin.
   - Periksa tab Application di browser Developer Tools untuk memastikan password tidak tersimpan di `localStorage` (hanya `ytgui_session_token` yang disimpan).
   - Segarkan (refresh) halaman browser, pastikan Anda otomatis ter-login kembali tanpa perlu mengetik ulang sandi.
3. **Double-Skip & Performance**:
   - Putar lagu, klik tombol **Selanjutnya** cepat berkali-kali. Pastikan lagu bergeser dengan benar satu per satu tanpa melompat dua kali (double advance).
   - Aktifkan Radio Mode, ukur durasi waktu tunggu lagu radio dimuat (pencarian paralel akan mempercepat durasi muat secara signifikan).
4. **MPV Recovery**:
   - Hentikan paksa proses `mpv` dari Task Manager / Process Hacker saat musik sedang berputar.
   - Amati terminal server. Pastikan background task mendeteksi diskoneksi dan berhasil menghidupkan kembali MPV secara otomatis dalam 5-10 detik.
5. **Aksesibilitas & Keamanan API**:
   - Panggil `GET http://localhost:8765/health` dari browser/curl, pastikan mengembalikan status `200 OK` dengan status `db: connected` dan `mpv: connected`.
   - Coba lakukan path traversal menggunakan url stream: `http://localhost:8765/api/stream/..%2f..%2fconfig.py`. Pastikan mengembalikan `400 Bad Request` karena kegagalan regex check.
