# UI Rebuild Plan v2 — Pemetaan Literal Mockup → Textual

Status: draft siap eksekusi, pengganti `ui_rebuild.md` (v1)
Sumber kebenaran visual: `preview-termux.html` (mockup yang sudah disetujui)
Target: `tui/dashboard.py`, `tui/panels/*.py`, `tui/theme.py` (baru)

## Mengapa dokumen ini dibuat ulang, bukan revisi dari v1

Implementasi v1 oleh Gemini menghasilkan bug nyata di device (ruang kosong raksasa, Now Playing hilang, tab Lirik hilang — lihat screenshot yang dilaporkan sebelumnya). Akar masalah yang paling mungkin: CSS v1 banyak memakai `1fr` dan `auto` bertingkat tanpa nilai cell pasti di level mana pun, sehingga saat satu link di rantai (`Screen` → `#main_grid` → `#side_panel`) gagal mendapat tinggi tegas, seluruh turunannya collapse ke nol. Dokumen ini memperbaiki pendekatan itu dengan aturan tegas: **setiap container yang punya anak dengan `1fr` WAJIB memiliki tinggi tegas sendiri (baik lewat angka cell langsung, atau lewat `height: 100%` dari parent yang sudah pasti)**. Tidak ada `1fr` yang bergantung pada `1fr` lain tanpa root yang fixed.

Catatan jujur soal keterbatasan: saya tidak punya akses untuk menjalankan Textual secara live di sandbox ini (tidak ada jaringan untuk instalasi paket). Plan ini ditulis berdasarkan pembacaan literal CSS mockup yang sudah disetujui dan pengetahuan tentang Textual CSS, bukan hasil uji coba langsung. Tahap 7 di bawah (verifikasi visual bertahap) karena itu menjadi tahap **wajib**, bukan opsional — setiap tahap harus di-screenshot di Termux asli sebelum lanjut ke tahap berikutnya, supaya kalau ada bug seperti kemarin, ketahuan di tahap mana persisnya, bukan di akhir setelah semua berubah sekaligus.

---

## Tabel Pemetaan: Elemen Mockup → Widget Textual

| Elemen di `preview-termux.html` | Widget Textual | ID yang dipakai | Catatan tinggi/lebar |
|---|---|---|---|
| `.term-header` | `Header` (bawaan, atau `Static` custom) | `#term_header` | height: 1 (baris tunggal cukup di terminal, beda dari mockup web yang px-based) |
| `.top-bar` (search + online dot) | `Horizontal` membungkus `Input` + `Static` | `#top_bar` | height: 3 (border tall butuh 3 baris: atas, isi, bawah) |
| `.search-box` | `Input` | `#search_input` | width: 1fr di dalam `#top_bar` |
| `.online-dot` | `Static("●")` | `#online_indicator` | width: 3 (cukup untuk titik + padding) |
| `.main-grid` | `Vertical` (portrait) / `Horizontal` (landscape) — class di-toggle | `#main_grid` | height: 1fr — **tapi root Screen harus eksplisit fixed dulu, lihat Tahap 1** |
| `.now-playing` | `NowPlayingPanel(Widget)` | `#now_playing` | **height: 13** (fixed, bukan `1fr`/`auto` — lihat justifikasi di Tahap 2) |
| `.np-title`, `.np-artist`, `.np-meta` | `Static` tunggal (digabung jadi satu blok teks multi-baris, seperti kode asli) | `#np_info` | bagian dari `#now_playing`, height: auto di dalam parent fixed |
| `.eq-row` | `Static` (render karakter bar `▁▂▃▄▅▆▇█`, sudah ada di kode asli) | `#np_equalizer` | height: 1 baris |
| `.progress-line` + `.progress-bar` | `ClickableProgressBar(Static)` (sudah ada, dipertahankan) | `#np_progress` | height: 1 baris |
| `.np-status` | `Static` baru (lihat v1 Tahap 5, dipertahankan di plan ini) | `#np_status` | height: 1 baris, kosong jika tidak ada pesan |
| `.side-panel` | `Vertical` membungkus tab bar + content | `#side_panel` | **height: 1fr — sah karena parent (`#main_grid`) sudah fixed lewat Tahap 1** |
| `.tab-bar` + `.tab-btn` ×2 | `Horizontal` membungkus dua `Button` | `#tab_bar` | height: 3 (tombol butuh border) |
| `.panel-content` (queue) | `OptionList` (sudah ada, dipertahankan) | `#queue_list` | height: 1fr di dalam `#side_panel` |
| `.panel-content` (lyrics) | `Static` (sudah ada, dipertahankan) | `#lyrics_content` | height: 1fr di dalam `#side_panel`, toggle display dengan queue |
| `.controls` (3 baris) | `Vertical` membungkus 3 `Horizontal`/`Grid` | `#controls` | **height: 11 (fixed, lihat Tahap 4)** |
| `.ctrl-primary-row` | `Horizontal` (Prev, Play/Pause, Next) | `#controls_primary` | height: 3 |
| `.ctrl-secondary-row` | `Grid` 6 kolom (Stop, Vol-, Vol+, Radio, Lirik, DL) | `#controls_secondary` | height: 3 |
| `.ctrl-danger-row` | `Horizontal` align kanan (Keluar) | `#controls_danger` | height: 3 |
| `.term-footer` | `Footer` (bawaan Textual, sudah ada) | — | height: 1 |

Total tinggi minimum portrait yang dibutuhkan: `1 (header) + 3 (top_bar) + 13 (now_playing) + sisanya untuk side_panel + 11 (controls) + 1 (footer)` = minimal **29 baris** sebelum `side_panel` dapat ruang. Ini penting dicatat karena terminal Termux umum di HP kecil cuma 20-30 baris — di Tahap 2 ada strategi mitigasi untuk ini.

---

## Tahap 0 — Token desain terpusat (tetap dari v1, tidak berubah)

File `tui/theme.py` seperti di v1, ditambah satu konstanta baru yang hilang di v1:

```python
# tui/theme.py
BG_VOID      = "#0D0D0D"
BG_PANEL     = "#141420"
BG_ELEVATED  = "#1E1E30"
BORDER       = "#2a2a45"
BORDER_FOCUS = "#FFC107"
ACCENT_FIRE  = "#FF6B35"
ACCENT_GOLD  = "#FFC107"
TEXT_PRIMARY = "#E8E8FF"
TEXT_MUTED   = "#A0A0C0"
TEXT_DIM     = "#555580"
STATUS_OK    = "#4ade80"
STATUS_ERR   = "#ef4444"

BREAKPOINT_LANDSCAPE = 80

# BARU — tinggi fixed tiap region, dipakai literal di CSS, supaya
# satu sumber kebenaran angka magic number tidak tersebar di banyak file
HEIGHT_TOP_BAR          = 3
HEIGHT_NOW_PLAYING      = 13
HEIGHT_TAB_BAR          = 3
HEIGHT_CONTROLS_ROW     = 3
HEIGHT_CONTROLS_TOTAL   = 11   # 3 baris tombol + 2 margin antar grup
MIN_SIDE_PANEL_HEIGHT   = 6    # ambang minimum sebelum masuk mode compact (Tahap 2)
```

**Definisi selesai:** `grep -rn "height:" tui/*.py tui/panels/*.py` semua nilai tinggi merujuk konstanta ini lewat f-string CSS, tidak ada angka tertulis langsung di luar `theme.py`.

---

## Tahap 1 — Root Screen harus punya tinggi tegas sebelum anak manapun pakai `1fr`

**File:** `tui/dashboard.py`

Ini bagian yang hilang di v1 dan kemungkinan besar jadi akar bug collapse. Textual `Screen` secara default sudah punya tinggi penuh viewport terminal (`100vh` setara), tapi masalahnya bukan di situ — masalahnya di rantai container turunan yang dibungkus `Vertical` polos tanpa `height: 1fr` di setiap link rantai. Aturan tegas untuk plan ini:

```css
Screen {
    background: $bg-void;   /* via theme token */
    layout: vertical;
    height: 100%;            /* WAJIB eksplisit, jangan andalkan default */
}

#main_grid {
    height: 1fr;              /* sah: parent Screen sudah height:100% pasti */
    width: 100%;
}
```

Dan **setiap** container yang jadi anak langsung dari sesuatu yang punya `1fr`, kalau dia sendiri ingin anaknya juga pakai `1fr`, dia HARUS dideklarasikan `height: 1fr` juga secara eksplisit di selectornya sendiri — tidak cukup mengandalkan "auto akan membesar". Ini berbeda dari v1 yang menulis `#side_panel { height: 1fr }` tapi tidak memverifikasi bahwa `#main_grid` (parent langsungnya) sungguh-sungguh resolve ke tinggi pasti dulu.

**Definisi selesai:** buat skrip kecil `debug_layout.py` yang load `Dashboard` dengan `HeadlessDriver`, lalu print `self.query_one("#main_grid").size` dan `self.query_one("#side_panel").size` — kedua nilai height harus lebih dari 0 sebelum lanjut ke tahap berikutnya. Ini test otomatis sederhana yang langsung mendeteksi bug collapse v1 tanpa perlu screenshot device dulu.

---

## Tahap 2 — Now Playing fixed height 13, dengan strategi compact untuk terminal pendek

**File:** `tui/panels/now_playing.py`, `tui/dashboard.py`

Sesuai tabel pemetaan, `#now_playing` di mockup punya tinggi tetap (168px web ≈ 13 baris terminal, dihitung dari: title 1 + artist 1 + meta 1 + spasi 1 + equalizer 1 + spasi 1 + progress 1 + status 1 + padding atas-bawah panel 2 + border atas-bawah 2 = 12-13).

```css
#now_playing {
    height: 13;
    border: tall $border;
    background: $bg-panel;
    padding: 1 2;
}
```

**Masalah yang harus diantisipasi (tidak ada di mockup HTML karena web punya scroll, terminal tidak):** kalau total terminal cuma 22 baris, dan header+topbar+now_playing+controls+footer sudah makan `1+3+13+11+1=29` baris, maka `side_panel` akan dapat tinggi *negatif* secara matematis — Textual akan clamp ke 0, persis seperti bug kemarin tapi dengan sebab berbeda (bukan CSS salah, tapi memang tidak cukup ruang).

Mitigasi: tambahkan logic di `on_resize` (Tahap 1 dashboard) untuk mode "compact" tambahan:

```python
def on_resize(self, event) -> None:
    is_landscape = self.size.width >= BREAKPOINT_LANDSCAPE
    is_short = self.size.height < 26   # ambang: total minimum 29 dirapikan ke 26 dengan now_playing compact
    self.screen.set_class(is_landscape, "-landscape")
    self.screen.set_class(not is_landscape, "-portrait")
    self.screen.set_class(is_short, "-compact")
```

```css
Screen.-compact #now_playing {
    height: 8;   /* drop meta+status line, equalizer tetap ada karena itu elemen "hidup" yang penting */
}
```

`NowPlayingPanel.update_state()` mengecek `self.size.height` saat render: kalau ≤ 8, skip baris `.np-meta` dan `.np-status` dari output (bukan dihapus widget-nya, cukup tidak ditulis ke string Rich markup).

**Definisi selesai:** resize terminal manual ke tinggi 20 baris (`tmux resize-pane -y 20`), pastikan `#now_playing` tetap menunjukkan title+artist+equalizer+progress (4 elemen minimum vital), dan `#side_panel` tidak collapse ke 0 (dicek pakai skrip `debug_layout.py` dari Tahap 1).

---

## Tahap 3 — Tab bar dua tombol bersisian, lebar eksplisit (bukan auto)

**File:** `tui/dashboard.py`

Bug tab Lirik hilang di v1 kemungkinan dari `Horizontal` tanpa lebar eksplisit per child. Plan v2 mengunci lebar:

```python
def _build_tab_bar(self) -> ComposeResult:
    with Horizontal(id="tab_bar"):
        yield Button("Antrean", id="tab_btn_queue", classes="tab-btn -active")
        yield Button("Lirik", id="tab_btn_lyrics", classes="tab-btn")
```

```css
#tab_bar {
    height: 3;
    width: 100%;
}
.tab-btn {
    width: 1fr;   /* dua tombol, masing-masing setengah lebar #tab_bar yang sudah fixed width:100% */
    min-width: 10;  /* cegah collapse di lebar sangat kecil */
}
.tab-btn.-active {
    background: $bg-panel;
    color: $gold;
    border: tall $gold;
}
```

Berbeda dari v1 yang tidak mendeklarasikan `width` sama sekali pada `.tab-btn` (mengandalkan default Textual Button yang auto-size ke teks) — di plan v2, `width: 1fr` dipasang eksplisit dengan parent (`#tab_bar`) yang `width: 100%` pasti, jadi resolve-nya selalu dua tombol sama lebar mengisi penuh, sama seperti mockup HTML (`display: flex; gap: 4px`).

**Definisi selesai:** kedua tombol tab terlihat bersisian dengan lebar sama persis (visual cek lebar border kiri-kanan keduanya identik), klik salah satu tombol toggle `display` panel di bawahnya tanpa membuat tombol yang lain hilang.

---

## Tahap 4 — Controls 3 baris dengan tinggi total terkunci 11

**File:** `tui/panels/controls.py`

```python
def compose(self) -> ComposeResult:
    with Vertical(id="controls"):
        with Horizontal(id="controls_primary"):
            yield Button("⏮", id="btn_prev", classes="ctrl-sm")
            yield Button("⏯ PLAY/PAUSE", id="btn_pause", classes="ctrl-primary")
            yield Button("⏭", id="btn_next", classes="ctrl-sm")
        with Grid(id="controls_secondary"):
            yield Button("⏹ Stop", id="btn_stop")
            yield Button("🔉", id="btn_voldown")
            yield Button("🔊", id="btn_volup")
            yield Button("📻 Radio", id="btn_radio")
            yield Button("📝 Lirik", id="btn_lyrics")
            yield Button("⬇ DL", id="btn_dl")
        with Horizontal(id="controls_danger"):
            yield Button("🚪 Keluar", id="btn_quit", variant="error")
```

```css
#controls {
    height: 11;     /* fixed, bukan auto — supaya #side_panel di atasnya tidak ikut menebak-nebak sisa ruang */
}
#controls_primary {
    height: 3;
    margin-bottom: 1;
}
#btn_prev, #btn_next { width: 20%; }
#btn_pause { width: 1fr; background: $fire; }

#controls_secondary {
    layout: grid;
    grid-size: 6;
    grid-gutter: 1;
    height: 3;
    margin-bottom: 1;
}

#controls_danger {
    height: 3;
    align: right middle;
}
#btn_quit { width: 16; border: tall #3a1a1a; color: $status-err; }
```

Perhitungan tinggi: `3 (primary) + 1 (margin) + 3 (secondary) + 1 (margin) + 3 (danger) = 11`, cocok dengan konstanta `HEIGHT_CONTROLS_TOTAL` di `theme.py`.

**Definisi selesai:** ketiga baris kontrol terlihat sebagai grup terpisah dengan jarak vertikal jelas; tombol Play/Pause terlihat jauh lebih lebar dari Prev/Next dalam baris yang sama; tombol Keluar sendirian di baris bawah rata kanan.

---

## Tahap 5 — Status line & online indicator (sama seperti v1, posisinya dikonfirmasi ulang sesuai mockup)

**File:** `tui/panels/now_playing.py`, `tui/dashboard.py`

Sesuai tabel pemetaan, `.np-status` ada di dalam `.now-playing` (bukan di Controls), dan `.online-dot` ada di `.top-bar` sejajar search box. Implementasi identik dengan v1 Tahap 5 — tidak diulang detailnya di sini, cukup ditegaskan posisinya dipertahankan karena mockup HTML mengonfirmasi penempatan itu benar.

**Definisi selesai:** sama seperti v1 Tahap 5.

---

## Tahap 6 — Kontras border (sama seperti v1 Tahap 6, dipertahankan)

Tidak berubah dari v1 — ganti semua border dekat-invisible (`#1E1E30` di atas `#141420`) ke `$border` (`#2a2a45`), border focus jadi `$border-focus` (`#FFC107`). Tidak diulang detailnya di sini.

---

## Tahap 7 — Verifikasi visual bertahap (WAJIB, beda dari v1 yang menjadikan ini opsional di akhir)

Ini perubahan proses terbesar dari v1. Karena saya tidak bisa menjalankan Textual langsung untuk validasi, dan implementasi v1 yang "ditulis sekali lalu dicek di akhir" sudah terbukti menghasilkan bug yang baru ketemu setelah seluruh kode jadi — plan v2 mewajibkan checkpoint screenshot di **setiap tahap**, bukan di akhir saja:

| Setelah Tahap | Yang harus di-screenshot di Termux asli | Kegagalan yang harus dicek |
|---|---|---|
| 1 | Layar kosong/skeleton, hanya border kontainer kosong terlihat | `#main_grid` dan `#side_panel` punya tinggi >0 (cek juga lewat `debug_layout.py`) |
| 2 | Now Playing terisi penuh dengan data dummy | Title, artist, equalizer, progress semua terlihat; tidak collapse di terminal 20 baris |
| 3 | Tab bar dua tombol | Kedua tombol terlihat, klik salah satu tidak menghilangkan yang lain |
| 4 | Baris kontrol lengkap | Play/Pause jelas lebih besar dari Prev/Next; 3 grup baris terpisah jelas |
| 5 | Status message muncul saat search | Pesan tampil di bawah progress bar, hilang otomatis 5 detik |
| 6 | Seluruh UI gabungan | Border antar panel terlihat jelas, tidak menyatu dengan background |

Kalau di tahap manapun screenshot menunjukkan area kosong tak terduga (seperti bug kemarin), **stop, jangan lanjut ke tahap berikutnya** — debug di tahap itu dulu, karena kemungkinan besar sebabnya ada di CSS tahap tersebut, bukan tahap-tahap sebelumnya yang sudah divalidasi.

---

## Yang sengaja tidak diubah

Sama seperti v1: `engine/`, `cache/`, `core/event_bus.py`, `core/state.py`, `integrations/` tidak disentuh. `AutoplayEngine` dan `SponsorBlockHandler` tidak butuh hook baru.

## Yang berbeda dari v1 secara prinsip

v1 menulis layout dengan banyak `1fr`/`auto` berasumsi Textual akan "menyesuaikan otomatis", dan validasinya ditaruh di akhir semua tahap. v2 mengunci tinggi tiap region dengan angka cell pasti (kecuali satu titik `1fr` yang sudah dipastikan parent-nya fixed di Tahap 1), dan mewajibkan screenshot per tahap supaya bug seperti kemarin — ruang kosong raksasa karena rantai `1fr` putus di tengah — ketahuan di tahap pertama kali muncul, bukan di akhir setelah lima tahap lain ikut menumpuk di atasnya.
