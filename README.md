# YT Termux Player Pro V2

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![MPV](https://img.shields.io/badge/Powered_by-MPV-purple.svg)
![Termux](https://img.shields.io/badge/Optimized_for-Termux-green.svg)

**bagas.fm (sebelumnya YT Termux Player)** adalah aplikasi web pemutar musik YouTube yang didesain secara khusus untuk tampil memukau di layar portrait HP maupun desktop. Aplikasi ini memutar audio di latar belakang menggunakan `mpv` (sebagai *engine*) dan diakses sepenuhnya melalui antarmuka web, sehingga ringan dan hemat kuota internet.

---

## ✨ Fitur Unggulan

- **🎵 Sinkronisasi Lirik Real-Time**: Lirik berjalan otomatis (karaoke style) mengambil data dari LRCLIB.
- **⏭️ SponsorBlock Integration**: Otomatis melompati iklan/sponsor yang disematkan di dalam video YouTube.
- **📻 Smart Radio Autoplay**: Antrean kosong? Aplikasi akan otomatis mencari dan memutar lagu yang relevan tanpa henti.
- **💾 Smart Caching & Download**: Lagu yang pernah diputar atau di-download manual (`[M]`) akan disimpan secara lokal. Pemutaran ulang tidak akan menyedot kuota internet.
- **🌐 Web UI Server-Client (bagas.fm)**: Dapat dijalankan sebagai backend server di Termux HP, lalu diakses secara nirkabel dari browser Laptop/PC atau HP lain di jaringan WiFi yang sama.
- **🔒 Portal Akses Ganda (Admin & Client)**:
  - **Admin Mode (Kontrol Penuh)**: Membutuhkan login username & password. Password dienkripsi secara kuat (*hashed*) demi keamanan tingkat enterprise.
  - **Client Mode (Dengar Saja / Intercom)**: Akses instan tanpa password. Musik akan otomatis dialirkan (streaming) ke browser klien.
  - **Fitur Logout & Switch Mode**: Memudahkan pengguna keluar dari sesi dan beralih peran.
- **⚡ Arsitektur Terstruktur**: Dibangun dengan *Hexagonal Architecture* (*Ports and Adapters*) dan pola *CommandBus & EventBus*. Dilengkapi dengan *Structured Logging* (JSON) untuk kemudahan *troubleshooting*.

---

## 🛠️ Prasyarat Instalasi

Aplikasi ini membutuhkan beberapa program eksternal untuk berjalan:
1. **Python** (versi 3.10 atau lebih baru)
2. **MPV** (sebagai engine pemutar audio utama)
3. **FFmpeg** (untuk ekstraksi dan konversi audio)

### 📱 Instalasi di Android (via Termux)

1. Buka Termux dan perbarui package list:
   ```bash
   pkg update && pkg upgrade -y
   ```
2. Instal dependensi sistem yang dibutuhkan:
   ```bash
   pkg install python mpv ffmpeg git -y
   ```
3. Clone repository ini (atau salin file project ke dalam Termux):
   ```bash
   pkg install socat termux-api -y
   git clone https://github.com/monang404/ytgui.git
   cd ytgui
   ```
4. Instal dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```

### 💻 Instalasi di Windows

1. Pastikan Anda sudah menginstal **Python 3.10+**.
2. Download dan instal **MPV** serta **FFmpeg**. Tambahkan keduanya ke dalam sistem PATH environment variables Anda.
   *(Saran: Gunakan package manager seperti Scoop: `scoop install mpv ffmpeg`)*
3. Buka Command Prompt / PowerShell, masuk ke direktori aplikasi:
   ```cmd
   cd ytgui
   pip install -r requirements.txt
   ```

---

## 🚀 Cara Menjalankan

Dari dalam direktori `ytgui`, jalankan perintah:

```bash
python main.py
```

> **Catatan Windows:** Di Windows, aplikasi akan otomatis membuka koneksi TCP internal ke MPV (via fallback) karena fitur Unix Socket tidak tersedia. Pastikan port lokal tidak terblokir firewall.

### 🌐 Mengakses Antarmuka Web (bagas.fm)
Saat Anda menjalankan aplikasi, server web otomatis aktif di latar belakang pada port `8765`.
1. Buka browser di Laptop/PC atau HP lain yang satu jaringan WiFi dengan HP Termux Anda.
2. Masukkan alamat IP HP Termux Anda dan port `8765` (Contoh: `http://192.168.1.5:8765`).
3. Anda akan disambut oleh halaman **Portal bagas.fm** untuk memilih mode:
   - **Mode Client (Dengar Saja)**: Langsung masuk tanpa sandi. Musik dari server akan otomatis dialirkan (streaming) dan berbunyi di browser Laptop/PC ini.
   - **Mode Admin**: Gunakan username **`admin`**. Password *raw* akan di-generate otomatis dan **hanya dicetak satu kali ke konsol saat pertama berjalan**. Demi keamanan, yang disimpan di file `cache/admin_password.txt` hanyalah *hash* kriptografinya. Jika lupa, hapus file tersebut untuk me-reset sandi. Anda juga bisa mengaturnya via Environment Variable `YTGUI_ADMIN_USER` dan `YTGUI_ADMIN_PASS`.
4. Klik tombol **`🚪 Keluar`** di pojok kanan atas UI Web untuk logout dan kembali ke halaman portal.

### 🔒 Deployment Aman (HTTPS / WSS Publik)
Secara default, bagas.fm berjalan di `http://` (teks biasa). Jika Anda ingin mengakses server ini dari luar jaringan WiFi rumah (Internet), **SANGAT DISARANKAN** untuk mengamankannya dengan HTTPS. Anda dapat menggunakan *Reverse Proxy* seperti Nginx, Caddy, atau layanan tunneling:
- **Ngrok / Tailscale / Cloudflare Tunnels**: Cara termudah menghubungkan server Termux Anda ke internet menggunakan enkripsi dari ujung ke ujung tanpa perlu setting port-forwarding manual.
- **Contoh Nginx Reverse Proxy**:
  Arahkan trafik HTTPS ke port `8765`, dan pastikan Anda me-*proxy* *header* WebSocket (`Upgrade: websocket`) agar *streaming* lirik dan perintah admin tidak terputus.

---

## 🎮 Panduan Penggunaan (Controls)

Setelah aplikasi berjalan, Anda dapat mengontrol pemutaran melalui sentuhan jari/mouse secara langsung pada elemen layar (klik tombol, *progress bar*, antrean) atau menggunakan tombol pintasan *keyboard* berikut:

### 🔍 Mencari Lagu
- Akses **Tab Pencarian** pada antarmuka web.
- Ketik nama lagu atau artis (Contoh: `coldplay yellow`).
- Klik hasil pencarian untuk memutar lagu dan menambahkannya ke antrean.

### 🎧 Kontrol Pemutaran
Gunakan tombol-tombol yang tersedia di **Player Bar** bagian bawah web UI untuk:
- Pause / Resume
- Next / Previous
- Menggeser (Seek) progress lagu
- Mengatur volume
- Toggle antrean (Queue)
- Mengaktifkan Radio Mode (Autoplay)
- Menampilkan Lirik Sinkron

---

## 📖 Buku Panduan Lengkap & Pro Tips

Untuk panduan yang lebih dalam mengenai rahasia kualitas audio, trik pencarian spesifik, dan fitur lirik 3-lapis, silakan baca **[Buku Panduan & Pro Tips (MANUAL_BOOK.md)](MANUAL_BOOK.md)**.

---

## 📁 Struktur Direktori & Sistem Log

Aplikasi ini menggunakan sistem *smart caching* dan memiliki sistem log tingkat lanjut:
- `cache/library.db` : Database SQLite penyimpan metadata, path file lokal, dan *play count*.
- `cache/<video_id>.mp3` : File audio hasil unduhan manual (`[M]`).
- `ytplayer.log` : Berkas log aplikasi dalam format JSON (Structured Logging) untuk observabilitas yang mudah dibaca oleh mesin/developer.

Anda bisa menghapus isi folder `cache` kapanpun jika ingin menghemat ruang penyimpanan.

---

## 📄 Lisensi

Didistribusikan di bawah lisensi MIT. Anda bebas memodifikasi, mendistribusikan, dan menggunakannya secara pribadi maupun komersial.

## 🤝 Berkontribusi & Arsitektur

Bagi para *developer* atau agen AI yang ingin berkontribusi, sangat diwajibkan untuk membaca dokumen berikut demi menjaga kualitas dan konsistensi kode:
- **[Panduan Kontribusi & Hukum Codebase (CONTRIBUTING.md)](docs/CONTRIBUTING.md)**
- **[Penjelasan Arsitektur (ARCHITECTURE.md)](docs/ARCHITECTURE.md)**

---
Enjoy your web music experience! 🎶
