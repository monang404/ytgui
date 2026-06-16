Ini codebase yang sama (TUI, bukan web GUI seperti namanya). Mari saya baca file-file rendering utamanya untuk audit tata letak yang akurat.Penting — ini sudah dimigrasi ke **Textual**, bukan Rich biasa lagi. Mari lihat semua panel komponennya untuk audit yang akurat.Sekarang saya punya gambaran lengkap. Mari saya petakan masalah tata letak dan hirarki secara konkret sebelum menulis rencana.Tidak ada network. Tidak masalah — saya sudah cukup familiar dengan Textual API untuk menyusun rencana yang valid. Berikut audit dan rencana refaktornya.

---

## Audit Tata Letak Saat Ini

Masalah konkret di `dashboard.py` dan panel-panelnya:

**Susunan vertikal kaku tanpa hierarki ruang.** Search input, Now Playing, Lyrics, Queue, Controls semua di-`yield` berurutan secara vertikal penuh lebar. Di layar Termux (umumnya 40–60 kolom lebar, tinggi 20–30 baris), ini berarti lima blok bersaing untuk tinggi yang sama-sama terbatas — padahal kontennya punya kepentingan visual yang berbeda. Now Playing seharusnya dominan (ini fokus utama), tapi sekarang setara dengan Lyrics dan Queue.

**Now Playing dan Queue/Lyrics tidak pernah didampingkan.** Karena semua `Vertical`, di layar landscape Termux yang lebih lebar dari tinggi (misalnya split keyboard kebuka, atau HP horizontal), ruang horizontal terbuang — padahal cukup lebar untuk Now Playing di kiri dan Queue/Lyrics di kanan, seperti versi web yang sudah dibuat sebelumnya.

**Grid controls 4 kolom tidak proporsional dengan teks tombol.** `grid-size: 4` dipaksa untuk 10 tombol dengan label seperti `⏮ Prev`, `⏯ Play/Pause`, `📝 Lyrics` — di lebar 40 kolom, setiap kolom dapat ~10 karakter, sehingga teks terpotong atau wrap secara tidak terduga. Tombol `Play/Pause` jadi tombol terpanjang tapi tidak diberi bobot visual lebih (padahal ini aksi paling sering dipakai).

**Tidak ada batas tinggi untuk Lyrics dan Queue saat keduanya `1fr` bersamaan.** `min-height: 5` untuk dua panel yang sama beratnya berarti di terminal 24 baris, sisa tinggi setelah Header+Search+NowPlaying+Controls+Footer bisa cuma 6–8 baris dibagi dua — masing-masing dapat 3–4 baris. Lyrics dengan window 4 baris ke atas+bawah jadi tidak kebaca, Queue cuma muat 2-3 track.

**Status message dan online indicator bercampur dalam satu string** (`status_text = f"{online_str} {self._status_msg}"`), ditaruh di `ControlsPanel` bagian paling bawah — jauh dari titik perhatian user (Now Playing), padahal ini info penting (gagal search, gagal download, dll).

**Tidak ada visual depth/separator yang konsisten.** Semua panel pakai `border: tall #1E1E30` dengan warna nyaris sama dengan background (`#0D0D0D` vs `#141420` vs `#1E1E30` — selisihnya tipis), sehingga di layar OLED kecil Termux, batas antar panel kabur dan keseluruhan terlihat seperti satu blok teks panjang.

---

## Rencana Refactor

### 1. Restrukturisasi layout jadi 2 mode responsif lewat CSS query, bukan logic Python

Textual mendukung `@media` lewat container query atau breakpoint manual. Saya akan pakai pendekatan paling stabil untuk versi Textual yang dipakai di sini: deteksi lebar lewat `on_resize` lalu toggle CSS class `-portrait` / `-landscape` di root `Screen`, dengan dua definisi grid di CSS.

```
Mode Portrait (width < 80 col) — khas Termux HP tegak:
┌─────────────────────────┐
│ Header                  │
├─────────────────────────┤
│ Search (collapsible)    │
├─────────────────────────┤
│ NOW PLAYING (tinggi=8)  │  ← dominan, fixed height
├─────────────────────────┤
│ [Queue] [Lyrics] tabs   │  ← satu area, bukan stacked
│  konten tab aktif       │  ← 1fr, ambil sisa ruang
├─────────────────────────┤
│ Controls (2 baris x 5)  │  ← grid 5 kolom, bukan 4
├─────────────────────────┤
│ Footer (key hints)      │
└─────────────────────────┘

Mode Landscape (width ≥ 80 col) — HP horizontal/tablet:
┌─────────────────────────────────────┐
│ Header                               │
├──────────────┬────────────────────────┤
│ Search        (lebar penuh, 1 baris) │
├──────────────┬────────────────────────┤
│ NOW PLAYING  │ [Queue] [Lyrics] tabs  │
│ (35% lebar)  │ konten (65% lebar)     │
│              │                        │
├──────────────┴────────────────────────┤
│ Controls (1 baris, semua tombol)      │
└─────────────────────────────────────┘
```

Alasan tab Queue/Lyrics digabung jadi satu (bukan stacked terus-terusan): keduanya adalah info sekunder yang user lihat sekilas, jarang dua-duanya dibutuhkan bersamaan dalam satu momen. Daripada membelah ruang vertikal jadi dua yang sama-sama sempit, lebih baik satu ruang penuh yang bisa di-switch — `L` tetap jadi shortcut untuk lompat ke tab Lyrics.

### 2. Hierarki visual lewat tipografi terminal, bukan warna semata

Saat ini differensiasi cuma lewat warna teks (`bold white`, `dim`, `#FF6B35`). Tambahkan:
- Title track: `bold` + warna terang penuh, ukuran "berat" lewat padding atas-bawah (bukan literal font size, tapi spasi vertikal yang memberi nafas)
- Artist: `dim`, tanpa bold — satu tingkat di bawah
- Metadata (durasi, views, via): `dim` + lebih kecil secara persepsi lewat penempatan di baris terpisah dengan indent konsisten
- Equalizer: warna aksen (`#FF6B35`) sebagai satu-satunya elemen "hidup", supaya mata otomatis tertarik ke sana saat audio berjalan — ini sudah benar di kode, dipertahankan

### 3. Status/error message dipindah ke dekat Now Playing, bukan di Controls

Buat `Static` kecil di bawah progress bar dalam `NowPlayingPanel`, muncul-hilang dengan animasi fade sederhana (toggle visibility), bukan menumpuk jadi satu baris panjang dengan online indicator. Online indicator pindah ke `Header` sebagai custom widget di kanan atas (titik hijau/merah kecil), karena itu status sistem permanen, bukan pesan sementara.

### 4. Reorganisasi grid Controls jadi prioritas-berbasis-ukuran

```
Baris 1 (aksi primer, tombol lebih besar):
[ ⏮ ]  [ ⏯ PLAY/PAUSE ]  [ ⏭ ]     ← 3 kolom, tombol tengah 2x lebar

Baris 2 (aksi sekunder, lebih kecil & padat):
[Stop] [Vol-] [Vol+] [Radio] [Lyr] [DL]  ← 6 kolom rapat

Baris 3 (destruktif, terpisah):
[Quit]  ← align kanan, warna merah redup, butuh sedikit jarak ekstra dari yang lain
```

Pemisahan ini eksplisit lewat `Grid` bertingkat (`Vertical` membungkus tiga `Horizontal`/`Grid` kecil), bukan satu `Grid` 4 kolom rata yang menyamakan bobot semua tombol.

### 5. Kontras warna dinaikkan untuk keterbacaan di layar HP kecil

Border antar panel naik dari `#1E1E30` (terlalu mirip background) ke kombinasi: background panel tetap `#141420`, tapi border pakai `#2a2a45` dengan border-style berbeda untuk panel aktif/focused (`#FFC107` saat fokus, sudah ada di search — diterapkan konsisten ke Queue OptionList juga).

---

### Urutan eksekusi

1. Refactor `dashboard.py`: tambah `on_resize` handler + CSS dua mode, restruktur `compose()` jadi nested containers sesuai diagram di atas
2. Gabung `QueuePanel` + `LyricsPanel` jadi satu `TabbedContent` (Textual punya widget built-in ini) — perlu sedikit adaptasi `update_state()` masing-masing supaya tetap dipanggil meski tab nonaktif
3. Pecah `ControlsPanel` grid jadi 3 grup baris sesuai prioritas
4. Tambah status widget kecil di `NowPlayingPanel`, hapus status text dari `ControlsPanel`
5. Buat custom `Header` widget kecil untuk online indicator (atau modifikasi `Header` default Textual lewat slot)
6. Test di lebar kolom sempit (40, 60, 80, 100) pakai `tmux resize-window` atau Textual devtools (`textual run --dev`) untuk validasi breakpoint

Mau saya langsung eksekusi jadi kode (mulai dari `dashboard.py` dan gabung Queue+Lyrics jadi tab), atau ada bagian rencana yang mau didiskusikan/diubah dulu?