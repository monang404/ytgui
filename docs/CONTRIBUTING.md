# Panduan Kontribusi (Contributing Guide)

Selamat datang di repositori `bagas.fm`! Panduan ini dirancang khusus untuk memastikan kode Anda konsisten dengan struktur yang ada, baik saat Anda adalah kontributor manusia maupun agen AI.

## Struktur Direktori Utama

- `core/`: Infrastruktur bersama (EventBus, State, Logging, Security). *Tidak boleh import dari domain lain*.
- `engine/`: Domain pemutaran (MPV, Queue, Radio).
- `server/`: Handler HTTP dan WebSocket (aiohttp).
- `cache/`: Layanan persistence dan SQLite.
- `plugins/`: Integrasi eksternal (SponsorBlock, Lyrics, Termux Notifications).
- `web/static/`: Frontend Vanilla (HTML/CSS/JS).

## 10 Hukum Codebase (Laws of This Codebase)

Ini adalah aturan baku yang TIDAK BOLEH DILANGGAR. Harap patuhi aturan ini dalam setiap Pull Request atau modifikasi otomatis.

### Backend

**LAW 1 — IMPORT DIRECTION**
```text
core ← engine ← server ← main  (satu arah)
```
- `core` **TIDAK BOLEH** import dari `engine` atau `server`.
- `engine` **TIDAK BOLEH** import dari `server`.
- `engine` boleh mengakses `plugins` **HANYA** melalui *ports/interfaces* yang didefinisikan di `core/ports.py`.

**LAW 2 — COMMANDS GO DOWN**
- `main` mengirim instruksi ke `engine` melalui `command_bus`.
- `engine` **TIDAK BOLEH** tahu atau menangani hal yang berkaitan dengan WebSocket atau HTTP.

**LAW 3 — EVENTS GO UP**
- `engine` mempublikasikan (*publish*) kejadian (*events*), dan `server` mendengarkannya (*subscribe*).
- Tidak ada pemanggilan fungsi secara langsung (*direct call*) dari `engine` ke `server`.

**LAW 4 — MAIN.PY = WIRING ONLY**
- Tidak boleh ada *business logic* di `main.py`.
- Target ukuran `main.py`: `< 100 baris` (Pengecualian: saat ini mencakup setup daemon & gracefull shutdown, namun tetap minimalis).

### Frontend

**LAW 5 — TOKENS ONLY DI TOKENS.CSS**
- **TIDAK ADA hex color (`#xxxxx`) di file CSS lain selain `tokens.css`.** Gunakan `var(--fm-*)`.
- *Pengecualian*: Saat ini masih ada ratusan hex usang di CSS lain, ditunda hingga fase *polishing* selesai. Jangan ubah sebagian-sebagian.

**LAW 6 — RENDER FUNCTIONS = PURE I/O**
- Fungsi `render/*.js` harus murni I/O DOM: Inputnya membaca `store.*`, outputnya merubah DOM.
- Fungsi render **TIDAK BOLEH** memanggil `wsSend()`.
- Fungsi render **TIDAK BOLEH** melakukan *attach* event dengan `addEventListener()`.

**LAW 7 — EVENTS ONLY DI EVENTS.JS**
- Tidak ada atribut *inline* seperti `onclick` di dalam file HTML.
- Semua pemanggilan `addEventListener()` harus dipusatkan di `events.js`.

**LAW 8 — STORE = SATU-SATUNYA STATE**
- Segala *state* aplikasi harus disimpan di `store.js`.
- Jangan menyimpan *state* pada elemen DOM (misalnya menggunakan atribut `dataset`).

**LAW 9 — DOM CACHE DI DOM.JS**
- Semua referensi elemen (hasil `document.getElementById()`) harus disimpan dan diekspor dari `dom.js`.
- Tidak ada pencarian elemen berulang di luar `dom.js`.

**LAW 10 — TAB CONTENT = JS-DRIVEN**
- Setiap *tab* konten harus berupa fungsi JavaScript yang me-return string HTML (dikelola oleh `render/tabs.js`).

## Panduan Pengujian

- Semua test file baru wajib ditempatkan di `tests/unit/` dengan mengelompokkannya sesuai folder domain (`core/`, `server/`, dsb).
- Gunakan `pytest tests/` untuk menjalankan semua pengujian. Pastikan *PASS* sebelum *commit*.
