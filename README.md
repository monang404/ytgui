# YT Termux Player Pro

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![MPV](https://img.shields.io/badge/Powered_by-MPV-purple.svg)
![Termux](https://img.shields.io/badge/Optimized_for-Termux-green.svg)

**YT Termux Player Pro** adalah aplikasi pemutar musik YouTube berbasis CLI (Command Line Interface) yang didesain secara khusus untuk tampil memukau di layar portrait HP (Termux) maupun desktop. Aplikasi ini memutar audio dengan sangat ringan di latar belakang menggunakan `mpv`, tanpa memuat video, sehingga sangat hemat kuota internet.

---

## ✨ Fitur Unggulan

- **🚀 TUI Modern & Responsif**: Antarmuka berbasis teks dengan animasi equalizer dan dukungan resize otomatis (Portrait/Landscape).
- **🎵 Sinkronisasi Lirik Real-Time**: Lirik berjalan otomatis (karaoke style) mengambil data dari LRCLIB.
- **⏭️ SponsorBlock Integration**: Otomatis melompati iklan/sponsor yang disematkan di dalam video YouTube.
- **📻 Smart Radio Autoplay**: Antrean kosong? Aplikasi akan otomatis mencari dan memutar lagu yang relevan tanpa henti.
- **💾 Smart Caching & Download**: Lagu yang pernah diputar atau di-download manual (`[M]`) akan disimpan secara lokal. Pemutaran ulang tidak akan menyedot kuota internet.
- **⚡ Super Ringan**: Dibangun dengan arsitektur *asynchronous event-driven*, menggunakan RAM & CPU seminimal mungkin.

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
   git clone https://github.com/username/ytcli.git
   cd ytcli
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
   cd ytcli
   pip install -r requirements.txt
   ```

---

## 🚀 Cara Menjalankan

Dari dalam direktori `ytcli`, jalankan perintah:

```bash
python main.py
```

> **Catatan Windows:** Di Windows, aplikasi akan otomatis membuka koneksi TCP internal ke MPV (via fallback) karena fitur Unix Socket tidak tersedia. Pastikan port lokal tidak terblokir firewall.

---

## 🎮 Panduan Penggunaan (Controls)

Setelah aplikasi berjalan, Anda dapat mengontrol pemutaran langsung melalui tombol keyboard tanpa perlu menekan `Enter`.

### 🔍 Mencari Lagu
- Tekan **`/`** untuk masuk ke **Mode Pencarian**. 
- Ketik nama lagu atau artis (Contoh: `coldplay yellow`).
- Tekan **`Enter`** untuk memutar hasil pertama dan memasukkan sisanya ke antrean.
- Tekan **`Esc`** untuk membatalkan pencarian.

### 🎧 Kontrol Pemutaran
| Tombol | Fungsi |
|--------|--------|
| `[P]` | Pause / Resume (Jeda/Putar kembali) |
| `[N]` | Next (Lompat ke lagu selanjutnya di antrean) |
| `[B]` | Previous (Kembali memutar lagu sebelumnya) |
| `[S]` | Stop (Hentikan pemutaran dan kosongkan antrean) |
| `[U]` | Volume Up (Naikkan volume 5%) |
| `[D]` | Volume Down (Turunkan volume 5%) |

### 🛠️ Fitur Tambahan
| Tombol | Fungsi |
|--------|--------|
| `[M]` | Download lagu yang sedang diputar untuk dimainkan secara offline (Cache) di masa depan |
| `[R]` | Toggle Radio Mode (Mode Autoplay lagu mirip saat antrean habis) |
| `[L]` | Sembunyikan/Tampilkan panel Lirik Sinkron |
| `[Q]` | Keluar dari aplikasi dengan aman |

---

## 📁 Struktur Direktori Cache

Aplikasi ini menggunakan sistem *smart caching*. Semua data akan disimpan di folder `cache/` pada root direktori:
- `cache/library.db` : Database SQLite penyimpan metadata, path file lokal, dan *play count*.
- `cache/<video_id>.mp3` : File audio hasil unduhan manual (`[M]`).

Anda bisa menghapus isi folder `cache` kapanpun jika ingin menghemat ruang penyimpanan.

---

## 📄 Lisensi

Didistribusikan di bawah lisensi MIT. Anda bebas memodifikasi, mendistribusikan, dan menggunakannya secara pribadi maupun komersial.

Enjoy your terminal music experience! 🎶
