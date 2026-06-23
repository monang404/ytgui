# 📖 Manual Book & Pro Tips : YT Termux Player Pro

Selamat datang di buku panduan resmi **YT Termux Player Pro**! Aplikasi ini diciptakan khusus bagi Anda yang menginginkan pengalaman mendengarkan musik tanpa batas, hemat kuota (tanpa video), dengan kualitas studio, dan langsung dari genggaman terminal/CLI Anda.

---

## 🎯 1. Konsep Dasar Aplikasi

Berbeda dengan aplikasi YouTube biasa, YT Termux Player Pro dirancang dengan konsep **Asynchronous Fire & Forget**. Artinya:
- **Audio Langsung Jalan:** Saat Anda memilih lagu, mesin pemutar (`mpv`) langsung menarik aliran (stream) suaranya secara instan.
- **Lirik Diambil di Latar Belakang:** Mesin pencari lirik berlapis kita akan berburu teks lirik dari seluruh dunia tanpa menjeda jalannya lagu. Begitu dapat (biasanya 1-3 detik), lirik akan meluncur otomatis!
- **Auto-Filter Kompilasi:** Anda tidak perlu khawatir terjebak memutar video kompilasi/mix 1 jam. Sistem otomatis membuang hasil pencarian berdurasi di atas 15 menit atau yang mengandung judul 'compilation/mix'.
- **Multi-room Ready:** Arsitektur terbaru telah mendukung beberapa ruangan (*rooms*) terpisah. Walau saat ini UI masih berfokus pada ruang "default", sistem mesin telah terdesain menggunakan *Hexagonal Architecture* untuk mendukung pemutaran paralel independen!

---

## 🎧 2. Rahasia Kualitas Audio (High-Fidelity)

Aplikasi ini telah **dikunci secara paksa** untuk selalu menyedot audio dengan kualitas tertinggi (Highest Bitrate & Sample Rate) yang tersedia di peladen YouTube. Anda tidak perlu menyetel apa pun!

- **Pitch Correction Aktif:** Jika internet Anda tiba-tiba melambat, pemutar tidak akan membuat suara mendadak sember/berubah nada.
- **Anti-Distorsi:** Menggunakan engine `mpv` dengan instruksi `format-sort=abr,asr`, menjamin audio murni (lossless-like) masuk ke telinga Anda.

---

## 🎹 3. Panduan Navigasi & Kontrol (V2)

Aplikasi ini menggunakan antarmuka interaktif berbasis **Tab (TUI V2)**. Di bagian layar Anda terdapat:
- **Navigasi Tab (Bawah):** `🏠 Home` | `🔍 Search` | `📻 Radio` | `☰ Queue`
- **Player Bar (Menempel di atas Navigasi):** Berisi status pemutaran dan kontrol sentuh/klik `[ ⏮ ]` `[ ⏯ ]` `[ ⏭ ]`.

Anda bisa langsung menyentuh/mengklik nama Tab untuk berpindah halaman, atau mengklik **Progress Bar** pada Player Bar untuk *seek* (memajukan lagu) secara instan!

Selain menggunakan mouse/sentuhan, berikut adalah daftar *keyboard shortcut* layaknya seorang pro:

| Tombol Keyboard | Aksi / Perintah |
| :---: | :--- |
| **`/`** | Membuka kotak pencarian lagu (otomatis pindah ke Tab Search). |
| **`Enter`** | Memutar hasil pencarian pertama dan memasukkan hasil lainnya ke antrean. |
| **`Esc`** | Membatalkan / keluar dari mode pencarian atau panel fokus. |
| **`P`** | Memutar (Play) atau menjeda (Pause) lagu saat ini. |
| **`N`** | Melompat ke lagu selanjutnya di antrean (Next). |
| **`B`** | Kembali ke lagu sebelumnya (Previous). |
| **`S`** | Menghentikan pemutaran secara total dan mengosongkan antrean (Stop). |
| **`U` / `D`** | Menaikkan (`U`) atau menurunkan (`D`) volume pemutar sebesar 5%. |
| **`M`** | Mengunduh (Download) lagu yang sedang diputar agar kelak bisa didengarkan tanpa kuota internet! |
| **`R`** | Beralih antara Queue Mode (Antrean Normal) dan Radio Mode (Auto-play AI). |
| **`Q`** | Keluar dari aplikasi dengan aman (Quit). |

> **Pro Tip TUI:** Anda bisa langsung menggeser atau **meng-klik bagian Progress Bar** untuk memajukan (seek) lagu ke menit tertentu!

---

## 🧙‍♂️ 4. Pro Tips & Trik Rahasia

Berikut adalah trik-trik yang hanya diketahui oleh pengguna *Power User*:

### A. Trik Pencarian Super Spesifik
Karena sistem memiliki pembersih judul otomatis, Anda hanya perlu memasukkan kata kunci inti. 
- ❌ Jangan cari: `Coldplay Yellow Official Music Video 4K`
- ✅ Cari saja: `Coldplay Yellow` atau `Evaluasi Hindia`
Jika Anda mencari versi *cover* atau siaran langsung (*live*), tambahkan kata kuncinya, misal: `Tulus Hati Hati di Jalan Live`.

### B. Memanfaatkan Sistem Lirik 3 Lapis (Triple-Fallback)
Jika lirik tidak langsung muncul, **jangan panik!** Aplikasi kita menggunakan 3 lapis pelacakan:
1. **Lapis 1:** Mencari kecocokan durasi eksak di LRCLIB (0.5 detik).
2. **Lapis 2:** Mencari berdasarkan kedekatan nama di LRCLIB (1 detik).
3. **Lapis 3 (Pamungkas):** Memanggil pustaka *syncedlyrics* untuk menggeledah Musixmatch, NetEase, dan Megalobiz secara membabi buta. Proses ini butuh waktu 2-4 detik, tapi tingkat keberhasilannya mencapai 99% bahkan untuk lagu indie lokal!

### C. Melewati Lagu yang Diblokir (Auto-Skip)
Kadang-kadang, lagu dari YouTube berstatus 'Restricted' (dibatasi usia) atau tidak tersedia di Indonesia.
Dulu hal ini membuat aplikasi *stuck* (macet). Sekarang, aplikasi secara cerdas mendeteksi kegagalan tersebut dan akan **otomatis melompat ke lagu berikutnya** dalam antrean. Jika lagu tiba-tiba terlewati sendiri, berarti YouTube memblokir akses ke lagu tersebut!

### D. Hemat Kuota dengan Fitur "M" (Manual Cache)
Jika Anda punya lagu favorit yang sering diputar, tekan tombol **`M`** saat lagu sedang berjalan. Aplikasi akan mengunduhnya diam-diam ke folder `cache/`. Besoknya, saat Anda memutar lagu itu lagi, aplikasi akan membaca file lokal (100% tanpa menyedot kuota internet lagi!).

### E. Radio Mode Cerdas (Autonomous Playback)
Di V2, **Radio Mode** tidak lagi bergantung pada antrean kosong. Jika Anda mengaktifkannya (tombol `R` atau via Tab Radio), sistem akan memisahkan diri dan memutar lagu rekomendasi secara terus-menerus tanpa merusak antrean (*queue*) utama Anda. Jika Anda bosan, Anda bisa menjelajahi artis lain langsung dari dalam Tab Radio.

---

## 🚑 5. Penyelesaian Masalah (Troubleshooting)

**Masalah:** Pemutar tidak mau memutar musik / tidak ada suara, tapi antrean berjalan.
**Solusi:** Aplikasi ini dikendalikan oleh `mpv`. Pastikan `mpv` terinstal (`pkg install mpv` di Termux). Jika masih bermasalah, aplikasi sudah dibekali sistem *Auto-Reconnect*, cobalah matikan total (`Q`) dan buka ulang. Pastikan pustaka di-update berkala:
```bash
pip install -r requirements.txt --upgrade
```

**Masalah:** Pencarian selalu gagal (No results found).
**Solusi:** Berarti YouTube mengubah sistem mereka. Segera update mesin intinya (`yt-dlp`) dengan cara menjalankan `pip install yt-dlp --upgrade`.

**Masalah:** Aplikasi crash atau perilaku aneh tidak terduga.
**Solusi:** Anda dapat membuka dan membaca file `ytplayer.log` yang ada di root direktori. File ini menggunakan format **JSON Structured Logging** yang sangat detail dan rapi. Semua riwayat error sistem dan Exception dicatat di sana. Anda bisa mengirim isinya kepada Developer jika perlu melaporkan bug.

---

## 🌐 6. Panduan Web UI & Mode Portal (bagas.fm)

YT Termux Player Pro V2 kini dilengkapi dengan Web Server bawaan yang berjalan otomatis ketika aplikasi dijalankan. Fitur ini memungkinkan Anda untuk mengontrol atau melakukan streaming lagu langsung dari browser Laptop, PC, atau perangkat lainnya.

### A. Halaman Portal Awal
Saat pertama kali mengakses web `http://[IP_HP]:8765`, Anda akan disambut oleh halaman dashboard **bagas.fm** untuk memilih peran akses:
1. **Mode Client (Dengar Saja)**: Didesain murni untuk mendengarkan. Tanpa membutuhkan password.
2. **Mode Admin**: Untuk mengendalikan server. Jika Anda belum menyetel kredensial, periksa *log* di Terminal saat server baru dinyalakan. Password akan di-*generate* acak secara aman (di-hash) dan dicetak SEKALI SAJA di layar Anda. Jika lupa, Anda harus menghapus file `cache/admin_password.txt` untuk men-generate ulang.

### B. Penggunaan Mode Client (Intercom / Party Mode)
Ketika masuk sebagai **Client**, tampilan pemutar akan berubah menjadi minimalis secara total:
- **Hanya Menampilkan:** Equalizer visualizer aktif, judul dan artis lagu yang sedang berjalan, serta daftar antrean lagu (Queue) di bawahnya.
- **Tanpa Tombol Kontrol:** Seluruh tombol kontrol player, pengaturan volume, dan tombol pencarian disembunyikan. Klik progress bar (seek) dan keyboard shortcut juga dinonaktifkan demi keamanan.
- **Auto-Streaming Suara**: Musik yang diputar di server akan otomatis dialirkan (streaming) dan berbunyi di browser klien Anda. Cocok digunakan sebagai receiver audio nirkabel di ruangan lain.

### C. Penggunaan Mode Admin (Akses Kontrol Penuh)
Ketika masuk sebagai **Admin**, Anda akan disuguhkan antarmuka kontrol penuh yang canggih:
- **DJ Control**: Anda bebas memutar, menjeda, melewati lagu (skip), memajukan posisi (seek), mengatur antrean, serta mencari lagu lewat kolom pencarian.
- **Audio Output Toggle**: Terdapat tombol di kanan atas header untuk beralih jalur suara:
  - **📱 HP (Default)**: Lagu dimainkan dan berbunyi langsung di HP Termux Anda (sebagai speaker utama).
  - **💻 BROWSER**: HP Termux akan secara otomatis di-mute (volume 0), dan aliran suara dialihkan sepenuhnya ke browser Laptop/PC mana saja yang sedang mengakses web dalam mode dengar.

### D. Fitur Logout (Keluar / Ganti Peran)
Di sudut kanan atas antarmuka (baik mode Admin maupun Client), terdapat tombol **`Keluar`** (🚪 Keluar). 
Mengklik tombol ini akan:
- Menghapus riwayat login & peran browser dari penyimpanan lokal (`localStorage`).
- Memutuskan sesi WebSocket secara aman untuk mencegah penyalahgunaan kontrol.
- Mengembalikan Anda ke Halaman Portal secara instan.
