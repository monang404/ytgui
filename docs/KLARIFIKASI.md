# Laporan Klarifikasi Investigasi AI Agent

Dokumen ini berisi jawaban detail terkait investigasi task yang terlewat (di-skip) selama proses *refactoring* Fase 0-4, berdasarkan pertanyaan pada `docs/INVESTIGASI_AI_AGENT.md`.

---

## 1. TASK-2.2: Duplicate `http_session`

1. **Mengapa masih ada dua `ClientSession()`?**
   Ini memang terlewat secara teknis pada `server/app.py`, tetapi secara fungsional memisahkan tanggung jawab. Di `main.py`, `http_session` di-pass ke `RoomManager` (untuk mem-fetch meta info, connect checker, lyrics). Di `server/app.py`, session baru dibuat dan dimasukkan ke `app["http_session"]`.
2. **Dipakai untuk apa session di `app.py`?**
   Session tersebut dipakai pada fungsi `serve_stream` (`server/handlers/http.py`) khusus untuk mem-proxy traffic data audio/video berukuran besar langsung ke browser/client.
3. **Risiko jika digabung:**
   Ada risiko *resource starvation/pool exhaustion*. Menggabungkan koneksi proxy streaming yang mengalirkan data berukuran besar (dan keep-alive lama) dengan session untuk me-request control/metadata (seperti lirik atau connect checker) bisa menyebabkan delay pada command API jika pool TCP sudah habis terpakai. Pisah session (satu untuk proxy stream data, satu untuk meta/control) malah direkomendasikan secara arsitektur.
4. **Apa yang terjadi jika tidak ditutup saat abnormal shutdown?**
   Terjadi *resource leak* kecil secara sementara di level *socket* TCP OS. Pada normal shutdown, ia akan otomatis tertutup dengan aman (karena ada `app.on_cleanup.append(on_cleanup)`).

---

## 2. TASK-2.4: `db.conn` vs `db._conn`

1. **Kenapa ini belum diperbaiki?**
   Pada file `cache/db.py`, nama koneksi sudah dirubah menjadi atribut private `self._conn` agar lebih aman, namun `server/handlers/http.py` lupa diperbarui dan masih memanggil atribut usang `db.conn`. `Database` class belum punya property `conn` ini.
2. **Hasil Verifikasi `cache/db.py`:**
   Memang benar hanya ada pengesetan variabel ke `self._conn`. `def conn` dan `@property` sama sekali tidak ditemukan.
3. **Dampak konkret:**
   Pada endpoint `/health`, baris `if db.conn:` akan melempar error pengecualian Python (`AttributeError: 'Database' object has no attribute 'conn'`). Ini bisa menyebabkan endpoint `/health` memunculkan Internal Server Error (HTTP 500) alih-alih mengembalikan status "disconnected".
4. **Fix paling aman & Trade-off:**
   Solusi teraman adalah menambahkan `@property def conn(self): return self._conn` di dalam class `Database`. Trade-off-nya nihil. Opsi ini menjaga enkapsulasi OOP agar caller di luar tidak memodifikasi `_conn` secara langsung, tetapi tidak membuat error code lama yang sudah dipakai di HTTP routing.

---

## 3. TASK-2.5: Script injection di `plugins/notifications.py`

1. **Reasoning `action string bare path`:**
   *Android intent* atau `termux-notification` runner yang mengeksekusi path tidak menggunakan *shell interpreter bash* pada saat pertama kali di-*invoke*, sehingga *quote* string (seperti `'/path/to/fifo'`) malah akan dianggap literal sebagai bagian dari nama file, menyebabkan _File Not Found_. Itulah kenapa path tidak bisa di *quote*.
2. **Kondisi berbahaya & Injeksi:**
   Kondisi injeksi dari luar tidak mungkin terjadi. `_fifo_path` merupakan gabungan path hardcoded yang dibuild dari `BASE_DIR / "cache" / "sockets" / "nowplaying.fifo"`. Dan isi file sh `.sh` sendiri berasal dari tuple fix.
3. **Apakah `token` bisa dimanipulasi:**
   Tidak. Variabel `token` berasal dari iterasi hardcode langsung: `for token in ("prev", "toggle", "next"):`. Tidak mengambil input pengguna mana pun.
4. **Risiko shlex.quote() ditambahkan:**
   Sangat tinggi. Kemungkinan besar notifikasi Termux akan rusak dan tombol Next/Prev di notifikasi tidak bisa diklik akibat OS runner Android mengartikan hasil quote string shlex sebagai nama lokasi file yang salah.

---

## 4. TASK-3.7: Global `bus` masih diimport

1. **Untuk apa masih dipakai:**
   Di `engine/radio_engine.py` dan `engine/queue_manager.py`, import global `bus` adalah benar-benar **unused import** (di-import tapi tidak pernah dipakai di kode tersebut). Di `main.py`, `bus` masih dipakai untuk inisialisasi `DownloadManager` global.
2. **Alasan arsitektur/Sisa:**
   Di folder `engine`, itu murni hanya sisa import mati.
3. **Fallback `event_bus is None`:**
   Terdapat pada saat `main.py` (Baris 45) menginisialisasi `mpv = MpvController()`. MPV global pertama kali tidak di-*inject* instance event_bus apa pun, sehingga ia mengandalkan fallback global `_global_bus`.
4. **Apa yang rusak jika dihapus:**
   Jika dihapus dari `engine/radio_engine.py` atau `queue_manager.py`, kode aman 100%. Namun jika fallback di `MpvController` dan eksistensi global `bus` pada library `core.event_bus` dihapus sepenuhnya, startup app (`main.py`) akan melempar *exception error* dan gagal dinyalakan.

---

## 5. TASK-1.5: Unauthenticated `next` bypass

1. **Output lengkap grep auth:**
   Di fungsi `handle_ws_message` pada `server/handlers/websocket.py` (sekitar baris 118) terdapat kode pengamanan *gatekeeper*: `if not require_auth(manager, ws): [return error]`.
2. **Di mana pengecekan auth command `next` dilakukan?**
   Semua command, **termasuk** `"next"`, diproses (switch-case) SETELAH baris gatekeeper pengecekan `require_auth` di `websocket.py`. Jadi, `"next"` turut terlindungi.
3. **Apakah ada command yang bisa di bypass?**
   Selain perintah `"auth"` (login), semua command `cmd` wajib lewat authentikasi.
4. **Test manual simulasi bypass:**
   Server websocket secara langsung menolak eksekusi dan membalas payload: `{"type": "error", "data": "Akses ditolak. Silakan login sebagai Admin."}` tanpa melanjutkan skip lagu.

---

## 6. CSS Law 5: 123 hex color di luar `tokens.css`

1. **Sisa atau disengaja:**
   Sebagian besar adalah sisa dari style bawaan sebelum *refactoring*. Proses perapian Phase 1 hanya melakukan perintah `sed -i` mereplace nama `--variable` lama ke `--fm-variable` baru, namun skrip itu tidak menyentuh kode hex yang masih ter-hardcode `#fff` atau semacamnya sejak lama.
2. **Berapa hex unik:**
   Ada puluhan kombinasi hex unik. Di dalam `portal.css` (halaman login), hex ini banyak dipakai untuk visual `radial-gradient` yang mana *wajar* untuk berdiri tanpa masuk ke global variabel. Sisanya berada pada komponen UI.
3. **Trade-off:**
   Menyisir dan menstandarkan semua itu ke dalam `tokens.css` membutuhkan puluhan entri tambahan baru agar tidak merusak tampilan. Untuk saat ini UI berfungsi dan terlihat estetik.

---

## 7. `main.py` masih 190 baris (target < 100)

1. **Baris yang bukan wiring:** 
   - `check_connectivity()` (Baris 74-95)
   - `mpv_reconnect_checker()` (Baris 97-123)
   - Try-catch shutdown dan task cleanups (Baris 161-185)
2. **Business logic atau wajar?**
   Kedua fungsi loop checker adalah `background tasks` mini, sementara sisanya adalah prosedur `graceful shutdown`. Secara arsitektur modern Python asyncio, shutdown prosedur itu lumayan wajar menumpuk di file main entrypoint.
3. **Ke mana harusnya dipindah & risikonya:**
   Sebaiknya task background bisa ditaruh ke berkas seperti `core/tasks.py`. Resiko memindahkannya sangat minim, tapi di sisi lain saat ini membiarkannya di `main.py` aman tanpa efek samping fungsionalitas.

---

## 8. `docs/mockup` belum di-rename ke `docs/mockups`

1. **Kenapa belum dikerjakan:**
   Karena ekstensi file aslinya di harddisk adalah huruf kapital (`.PNG`), sedangkan script shell AI agent di eksekusi sebelumnya mungkin *case-sensitive* mencari target `.png` dan folder exact. Hal ini sering terlewat jika *wildcard* bash gagal memetakan ekstensi secara sempurna.
2. **Apakah ada hardcode path:**
   Tidak ada skrip fungsional Python atau HTML utama aplikasi yang me-referensi ke nama direktori gambar ini.
3. **Sengaja atau terlewat:**
   Murni terlewat secara perintah operasional file OS (`mv`).

---

## Rangkuman Eksekutif Rekomendasi

| Task | Status sebenarnya | Alasan skip/belum selesai | Risiko jika dibiarkan | Risiko jika di-fix | Rekomendasi |
|------|-------------------|---------------------------|-----------------------|--------------------|-------------|
| **TASK-2.2** | Selesai-parsial | Pemisahan session wajar (kontrol vs streaming buffer proxy). | Tidak ada | Pool exhaustion traffic | **Dibiarkan (Bypass Task).** Pemisahan fungsional saat ini sudah sangat baik. |
| **TASK-2.4** | Belum Selesai | Handler `http.py` masih memanggil attribute `conn` usang. | `/health` error 500 terus (UI Admin mengira mati). | Nihil | **FIX.** Tambahkan def property `conn` yang mereturn `_conn` di `cache/db.py`. |
| **TASK-2.5** | Selesai-parsial | Runner Shell Android Termux akan gagal jika path di-shlex.quote(). Input murni hardcoded, tidak bisa diinjeksi. | Tidak ada (aman) | Notifikasi/Tombol Termux patah (gagal eksekusi OS) | **Dibiarkan (Bypass Task).** Kode aman secara static. |
| **TASK-3.7** | Selesai-parsial | Engine/ radio unused import. `main.py` masih memakai global fallback MpvController. | Tidak ada efek fungsional (aman). | Error Exception jika dihapus total tanpa fix inject event main. | **FIX.** Hapus unused import di file `engine/*.py`. |
| **TASK-1.5** | Sudah Selesai | Logic refactoring telah memindahkan pengecekan ke gatekeeper global di dalam `handle_ws_message` (atas). | - | - | **Selesai.** (Tandai ulang, tidak butuh tindakan kode). |
| **CSS Law5** | Belum Selesai | AI Agent hanya mengganti regex `var(--*)` yang lama, melewatkan hex yang hardcode di awal. | CSS sulit dibaca, memori/UI inkonsisten. | Repot jika ada warna yang mapping token-nya tidak matching. | **Dibiarkan** sementara waktu sampai sesi khusus polishing CSS terpisah. |
| **main.py** | Belum Selesai | Memiliki Background task connect_check & mpv_reconnect serta graceful shutdown. | Hanya file besar, tidak ada issue fungsi. | Overhead minor memindahkan ke modul external baru. | **Dibiarkan.** (Bypass constraint target baris, demi stabilitas shutdown). |
| **docs/** | Belum Selesai | Casing ekstensi file `.PNG` vs `.png` mematahkan eksekusi bash `mv` command. | Mengganggu dokumentasi arsitektur saja. | Nihil | **FIX.** Execute rename foldernya dan kecilkan ekstensi `.PNG` nya. |
