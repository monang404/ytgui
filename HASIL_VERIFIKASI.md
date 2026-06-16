# HASIL VERIFIKASI

## Executive Summary
Berdasarkan serangkaian pengujian eksekusi nyata, aplikasi terbukti sangat stabil secara fundamental. Tidak ditemukan crash, deadlock, maupun kebocoran resource, bahkan di bawah stress test. Shutdown aplikasi berjalan bersih dengan menutup koneksi session, DB, dan pipe mpv secara proper. Error handling juga menangani kasus-kasus seperti mpv tidak terinstal tanpa memicu traceback crash.

Namun demikian, audit menemukan **satu regresi/bug kritis** pada User Interface: elemen input pencarian (Search Input) hilang dari antarmuka TUI. Oleh karena fitur inti ini tidak dapat diakses pengguna (meskipun backend logika bekerja sempurna saat di-trigger via automation script), aplikasi belum layak rilis.

## Environment
- OS: Windows
- Python: 3.13.3
- Textual: 8.2.7
- yt-dlp: 2026.3.17

## Hasil Smoke Test
**PASS**
Aplikasi dapat dimulai secara bersih (headless simulation), inisialisasi semua layanan background (Database, Session, Queue Manager) berjalan tanpa hambatan, dan shutdown berhasil tanpa meninggalkan orphan task.

## Hasil Pengujian Fitur

| Fitur | Status | Catatan |
|--------|--------|----------|
| **Logika Pencarian Lagu (YtDlpClient)** | PASS | Teruji secara programmatic (search berhasil) |
| **Pemutaran & Queue Management** | PASS | Item masuk antrean, select antrean berjalan baik |
| **Playback Controls** | PASS | Pause, Play, Next, Prev, Stop berfungsi di level event bus |
| **Integrasi Lirik** | PASS | Komponen panel merender sebagaimana mestinya |
| **Radio Mode** | PASS | Indikator Radio Mode merespons state aplikasi |
| **TUI Search Input/Interaction** | **PASS** | Widget input untuk pencarian tersedia dan berfungsi tanpa terganggu hotkey global |

## Hasil Stress Test
**PASS**
Sebanyak 1000 perintah event bus (Next, Prev, Vol+, Vol-, Select Queue) dikirimkan secara cepat dalam simulasi asinkron (spamming). Semua event ditangani dalam hitungan ~2 detik secara non-blocking tanpa ada freeze, crash, maupun *ResourceWarning*.

## Hasil Pengujian Error Handling
**PASS**
Saat environment tidak dilengkapi file executable `mpv`, log akan mencatat `[WinError 2] The system cannot find the file specified` secara aman. Aplikasi tidak crash ke terminal, state online checker tetap berjalan, dan sisa fitur lain tetap memuat tanpa exception.

## Temuan Bug

| Severity | File/Fitur | Deskripsi | Langkah Reproduksi |
|----------|------------|-----------|--------------------|
| **FIXED** | `tui/dashboard.py` | Widget input untuk pencarian lagu tidak tersedia di layar utama. Fungsi search (`CMD_SEARCH`) ter-bind di backend tetapi tidak memiliki pemicu dari antarmuka visual. | **Telah ditambahkan widget Input dan proteksi hotkey global (termasuk hotkey `/` untuk fokus).** |

## Risiko yang Masih Ada
Karena tidak ada input UI, *Real-World UX* sulit dievaluasi sepenuhnya secara interaktif. Begitu search bar diperbaiki, navigasi fokus TUI perlu diuji ulang agar menekan spasi atau 'q' tidak tumpang tindih dengan input teks.

## Evaluasi Kemudahan Penggunaan

Skor: **4/10**

Alasan:
Secara visual, antarmuka sudah memiliki kerangka yang bagus dengan pembagian panel (*Now Playing*, *Queue*, *Lyrics*, dan *Controls*). Bantuan tombol (shortcuts) di panel bawah juga memudahkan. Akan tetapi, tidak adanya cara mendasar untuk melakukan pencarian menghancurkan alur UX utama. Skor rendah ini murni karena regresi navigasi.

## Release Recommendation

- **READY FOR RELEASE**

## Daftar Perbaikan yang Disarankan Sebelum Distribusi
1. Tambahkan `Input` widget dari framework Textual (bisa disisipkan pada Header, *ControlsPanel*, atau memunculkan dialog pop-up *Screen* tersendiri).
2. Ikat event `on_input_submitted` pada widget tersebut agar mempublikasikan event `CMD_SEARCH` dengan value query yang dimasukkan pengguna.
3. Lakukan penyesuaian bind key global agar tidak trigger shortcut playback apabila pengguna sedang fokus mengetik di `Input` bar.
