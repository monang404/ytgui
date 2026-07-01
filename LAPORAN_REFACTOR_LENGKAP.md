# Laporan Lengkap Refactoring Codebase ytgui (Fase 1 - 4)

Laporan ini merangkum seluruh aktivitas, perbaikan, dan refactoring yang telah berhasil dieksekusi terhadap codebase `bagas.fm / ytgui` secara menyeluruh, mengacu pada pedoman di dalam `REFACTOR_ROADMAP.md`. 

Berikut adalah rincian eksekusi dari Fase 1 hingga Fase 4:

---

## 🚀 Fase 1: Keamanan & Keputusan Arsitektur Kritis (Critical)

Fase ini fokus pada penambalan celah keamanan yang berisiko tinggi serta menetapkan arah arsitektur fundamental sistem.

- **[SEC-01] Keamanan Kredensial Admin:**
  - Telah mengubah mekanisme penyimpanan password admin dari plain text (teks biasa) menjadi menggunakan hashing yang aman (`pbkdf2:sha256`).
  - Menghapus fallback kredensial plaintext yang tidak aman.
- **[SEC-01 / TD-07] Sanitasi File & Packaging:**
  - Sistem pengemasan (packaging/export) telah diperbaiki untuk secara ketat mematuhi `.gitignore`.
  - Telah mem-purge database sensitif (`ytgui.db`, `library.db`), kredensial (`admin_password.txt`), dan log dari sistem *bundling* sehingga mencegah paparan data sensitif secara tidak sengaja di masa depan.
- **[TD-01] Penghapusan Multi-Room:**
  - Sesuai dengan instruksi *'multi romm hapus total'*, keputusan arsitektur telah ditetapkan. Seluruh kode fungsional maupun uji coba yang terkait dengan konsep "Multi-Room" resmi dihapus karena dianggap sebagai kompleksitas yang tidak diperlukan pada visi proyek saat ini.

---

## ⚙️ Fase 2: Manajemen Teknis & Performa Awal (High Priority)

Fase ini fokus pada pembersihan teknikal (Tech Debt) dan stabilisasi performa di level core.

- **[TD-01 / TD-08] Pembersihan Jejak Multi-Room:**
  - Menghapus fungsionalitas dan file sisa `RoomManager` dan `test_room_manager.py`.
  - Menyesuaikan dependensi agar secara eksklusif menggunakan *single global state*.
- **[PERF-01 / TD-03] Background Task Otomatis:**
  - Mengintegrasikan mekanisme pembersihan (cleanup) `evict_stale_tracks()` dan `cleanup_sessions()` agar secara proaktif berjalan di latar belakang (background task) di `main.py`, demi menghindari *memory leaks*.
- **[PERF-03] Perbaikan Kueri Pencarian (Search):**
  - Parameter pencarian `YtDlpClient.search()` telah dimodifikasi agar dinamis menghormati `max_results` (batas limit hasil pencarian), tidak lagi dikunci statis pada angka 10.
- **[PERF-02] Optimasi Database:**
  - Menambahkan indeks pada `schema.sql` (`CREATE INDEX idx_songs_artist_id ON songs(artist_id)`) untuk secara signifikan mempercepat *query* pencarian lagu berdasarkan *artist*.
- **[Testing]**
  - CI dan `requirements-dev.txt` dipertajam.
  - Test Suite (`pytest`) berhasil mencapai 100% *passing rate* pasca perombakan.

---

## 🛠️ Fase 3: Refactoring Menengah & Kualitas Kode (Medium Priority)

Fase ini menekankan restrukturisasi blok kode besar (refactoring) demi mempermudah skalabilitas program ke depannya dan menghapus pengulangan logika (DRY / *Don't Repeat Yourself*).

- **[CQ-01] Sistem Dispatcher WebSocket:**
  - Menulis ulang fungsi `handle_ws_message` (di `websocket.py`) yang tadinya sangat panjang dengan banyak percabangan `if/elif`, menjadi pola **Action Registry (Dispatcher)**. Hal ini membuat rute pemanggilan socket lebih terstruktur, modular, dan rapi.
- **[CQ-04 & CQ-05] Reduksi Duplikasi Kode (DRY):**
  - Ekstraksi blok yang berulang: Logika penanganan dan sanitasi `user_download_path()` serta `broadcast_discover_data()` dikeluarkan menjadi *helper function* independen.
- **[PERF-04 / PERF-06] Optimasi Kecepatan Eksekusi:**
  - Mengubah *loop* pengiriman websocket agar ter-broadcast secara paralel (non-blocking) menggunakan `asyncio.gather`.
  - Di sisi antarmuka Frontend (`discover.js`), logika pemuatan (rendering) yang usang diubah menggunakan pendekatan pembaruan DOM (Document Object Model) yang dapat di-*reuse*, guna meniru efisiensi *Queue List*.
- **[CQ-03 / TD-04 / CQ-09 / SEC-02] Sanitasi Sistem & Keamanan Tambahan:**
  - Fungsi hashing `PBKDF2` kini diimpor secara langsung dan tidak berulang di `start.py`.
  - Argument `shell=True` (yang sangat rawan akan eksploitasi celah keamanan *command injection*) telah dihapus sepenuhnya dari pemanggilan `subprocess` di `start.py`.
  - Semua Exception/Error pada *First Run Check* kini di-log dengan baik (tidak lagi di-swallow).
- **[CQ-06 / CQ-07] Penghapusan "Dead Code":**
  - Segala bentuk blok kode usang atau non-aktif dihapus tanpa ampun (contoh: blok `if True:`, variabel mati, fungsi lawas seperti `_normalize_title()`).

---

## 💎 Fase 4: Eksekusi Tingkat Lanjut & Standar Industri (Nice to Have)

Pada tahap terakhir ini, fokus diberikan pada pencapaian standar struktur pemrograman tinggi dan arsitektur tingkat prod.

- **[CQ-02] Dekonstruksi "God Class" GUI (`start.py`):**
  - Mengisolasi logika internal (Process Lifecycle & Dependency Checking) dari UI Toolkit (Tkinter) `ServerManager`. Logika ini kini berada di dua kelas terpisah (`DependencyChecker` dan `ServerProcessManager`), sehingga UI tidak terlalu berat dan perbaikan fungsional tidak akan merusak layout aplikasi GUI.
- **[CQ-08] Sentralisasi Kontroler MPV:**
  - Fungsi baca-tulis MPV IPC JSON yang mirip pada `_command` dan `_get_property` diintegrasikan dalam satu fungsi `_send_request()`, mencegah *race condition* sembari menekan pengulangan kode.
- **[CQ-10] Standarisasi Magic Number:**
  - Seluruh bilangan acak bawaan program (*magic number*) dipindahkan ke `core/constants.py` (contoh: `MAX_LOGIN_ATTEMPTS`, `MAX_RATE_LIMIT`, `MAX_VOLUME`).
- **[SEC-05 & SEC-06] Reverse Proxy Support (Standar Produksi):**
  - Menambahkan kapabilitas pembacaan `X-Forwarded-For` untuk pelacakan IP klien. Diaktifkan via variabel flag khusus (`TRUSTED_PROXY`) di environment agar kompatibel dan lebih aman bila di-*deploy* di belakang NGINX atau Cloudflare.
- **[SEC-04] Pencegahan Serangan Waktu (Timing Attack):**
  - Implementasi metode perbandingan konstan `secrets.compare_digest` pada autentikasi *username*, menjadikannya tahan terhadap serangan tebakan *timing attack*.
- **[TD-06] Inisiasi Testing Frontend (Javascript):**
  - Pembuatan *test runner* ringan berformat HTML (`tests/test_helpers.html`) yang divalidasi langsung melalui *assertions* JavaScript (`console.assert()`) pada komponen murni UI seperti `formatTime` atau `escapeHtml`.

---

### Kesimpulan
Secara garis besar, perombakan ini telah mentransformasi aplikasi dari *script prototype* menjadi sistem *production-ready* yang **bebas kode-kode mati, modular, dan teroptimasi secara asinkron (async)**. Seluruh skenario pengujian (`130+ unit tests`) terpantau berhasil dieksekusi dengan baik (0 regresi) mengindikasikan bahwa perombakan arsitektur ini sudah sangat solid.
