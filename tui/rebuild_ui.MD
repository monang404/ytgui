# UI Rebuild Plan — YT Termux Player Pro

Status: draft siap eksekusi
Target: `tui/dashboard.py`, `tui/panels/*.py`
Tidak menyentuh: `engine/`, `cache/`, `core/event_bus.py`, `core/state.py`, `integrations/`

Verifikasi yang sudah dilakukan sebelum menulis plan ini:
- `core/state.py` dibaca penuh — field yang dipakai plan ini (`is_radio_mode`, `next_uri_ready`, `lyrics_index`, `lyrics_lines`, `is_online`, `status`, `current_track`, `queue`, `volume`, `position`) semua ada dan strukturnya sesuai asumsi.
- `config.py` dibaca — tidak ada konstanta warna/ukuran terpisah. Semua warna saat ini hardcoded di CSS string `dashboard.py`. Plan ini akan memindahkan warna ke satu tempat (lihat Tahap 0).
- Versi `textual` belum bisa diverifikasi langsung di sandbox ini (tidak ada akses jaringan untuk install). Karena itu plan ini **tidak** memakai container query/`@media` Textual yang klaimnya belum terverifikasi, dan **tidak** memakai `TabbedContent` built-in tanpa fallback. Sebagai gantinya dipakai pendekatan yang pasti kompatibel di semua versi Textual 0.x ke atas: `on_resize` manual + CSS class toggle, dan tab buatan sendiri dari `Static` + `Button` (lihat Tahap 3). Ini sedikit lebih banyak kode tapi nol risiko incompatibility.

---

## Tahap 0 — Sentralisasi token desain

Sebelum ubah layout, pindahkan semua warna dari CSS string `dashboard.py` ke satu tempat agar tidak ada duplikasi warna tersebar di banyak file panel.

**File baru:** `tui/theme.py`

```python
# tui/theme.py
BG_VOID     = "#0D0D0D"
BG_PANEL    = "#141420"
BG_ELEVATED = "#1E1E30"
BORDER      = "#2a2a45"
BORDER_FOCUS = "#FFC107"
ACCENT_FIRE = "#FF6B35"
ACCENT_GOLD = "#FFC107"
TEXT_PRIMARY = "#E8E8FF"
TEXT_MUTED   = "#A0A0C0"
TEXT_DIM     = "#555580"
STATUS_OK    = "#4ade80"
STATUS_ERR   = "#ef4444"

# Breakpoint lebar kolom terminal — bukan device pixel, ini character columns
BREAKPOINT_LANDSCAPE = 80
```

Import token ini di `dashboard.py` dan setiap panel yang butuh warna untuk Rich markup (mis. `f"[{ACCENT_FIRE}]...[/]"`). Ini langkah murah tapi penting: kalau nanti ganti satu warna, cukup ubah di satu tempat, bukan grep lima file.

**Definisi selesai:** `theme.py` dibuat, semua hex color di `dashboard.py` CSS string dan ketiga panel diganti jadi referensi ke konstanta ini (CSS string Textual tetap harus literal string, jadi gunakan f-string atau `.format()` saat membangun `CSS` class attribute).

---

## Tahap 1 — Deteksi lebar terminal & mode responsif

**File:** `tui/dashboard.py`

Tambahkan di `Dashboard`:

```python
from tui.theme import BREAKPOINT_LANDSCAPE

class Dashboard(App):
    ...
    def on_resize(self, event) -> None:
        is_landscape = self.size.width >= BREAKPOINT_LANDSCAPE
        self.screen.set_class(is_landscape, "-landscape")
        self.screen.set_class(not is_landscape, "-portrait")
```

Textual App punya `on_resize` bawaan yang dipanggil tiap kali ukuran terminal berubah (termasuk saat Termux software keyboard buka/tutup, yang mengubah tinggi viewport). `set_class` adalah API DOM-style Textual yang sudah stabil sejak versi awal — ini metode paling defensif dibanding mengandalkan container query yang versinya belum terverifikasi.

CSS lalu punya dua varian definisi grid memakai selector class:

```css
Screen.-portrait #main_grid {
    layout: vertical;
}
Screen.-landscape #main_grid {
    layout: horizontal;
}
```

**Definisi selesai:** resize terminal dari 40 kolom ke 100 kolom (via `tmux resize-pane` atau jendela terminal) memicu perubahan class yang terlihat di devtools Textual (`textual run --dev main.py`), tanpa restart app.

---

## Tahap 2 — Restrukturisasi `compose()` jadi container bertingkat

**File:** `tui/dashboard.py`

Struktur baru, portrait dan landscape pakai DOM yang sama, hanya CSS layout-nya beda (lebih murah daripada compose dua versi berbeda):

```python
def compose(self) -> ComposeResult:
    yield Header(show_clock=True)
    yield Input(placeholder="Search... ('/' focus, 'ESC' unfocus)", id="search_input")

    with Vertical(id="main_grid"):
        self.now_playing = NowPlayingPanel(id="now_playing")
        yield self.now_playing

        with Vertical(id="side_panel"):
            yield self._build_tab_bar()
            self.queue_panel = QueuePanel(id="queue_panel")
            self.lyrics_panel = LyricsPanel(id="lyrics_panel")
            yield self.queue_panel
            yield self.lyrics_panel

    self.controls = ControlsPanel(id="controls")
    yield self.controls
    yield Footer()
```

CSS untuk `#main_grid`:

```css
#main_grid.-portrait { layout: vertical; height: 1fr; }
#main_grid.-landscape { layout: horizontal; height: 1fr; }

#now_playing {
    height: 12;            /* portrait: fixed height, bukan auto */
}
Screen.-landscape #now_playing {
    width: 38%;
    height: 1fr;            /* landscape: isi penuh tinggi kolom kiri */
}

#side_panel {
    height: 1fr;
    width: 100%;
}
Screen.-landscape #side_panel {
    width: 62%;
}
```

Alasan `height: 12` fixed di portrait untuk Now Playing (bukan `auto` seperti sekarang): supaya panel ini punya alokasi ruang predictable terlepas dari panjang judul track, dan sisa tinggi terminal yang variable (Termux 20–35 baris) konsisten dialokasikan ke `side_panel` lewat `1fr`.

**Definisi selesai:** di portrait, Now Playing selalu tinggi 12 baris pas; sisa ruang ke bawah (sebelum Controls) terisi penuh oleh `side_panel`. Di landscape, Now Playing dan side_panel sejajar horizontal dengan rasio 38:62.

---

## Tahap 3 — Tab manual Queue/Lyrics (bukan `TabbedContent`)

**File:** `tui/dashboard.py` (tab bar), `tui/panels/queue_panel.py`, `tui/panels/lyrics_panel.py`

Alasan tidak pakai `TabbedContent` bawaan Textual: belum bisa diverifikasi behavior mount/unmount child-nya kompatibel dengan pola `update_state()` manual yang sudah dipakai di seluruh codebase ini (dipanggil tiap 0.3s dari `refresh_ui`, bukan reactive watch). Daripada migrasi pola itu sekaligus ganti widget tab — dua risiko sekaligus — dipakai toggle visibility sederhana yang sudah terbukti jalan (pola yang sama dipakai untuk `lyrics_panel.display` saat ini).

```python
def _build_tab_bar(self) -> ComposeResult:
    with Horizontal(id="tab_bar"):
        yield Button("Antrean", id="tab_btn_queue", classes="tab-btn -active")
        yield Button("Lirik", id="tab_btn_lyrics", classes="tab-btn")

@on(Button.Pressed, "#tab_btn_queue")
def _show_queue_tab(self) -> None:
    self._active_tab = "queue"
    self._sync_tab_visibility()

@on(Button.Pressed, "#tab_btn_lyrics")
def _show_lyrics_tab(self) -> None:
    self._active_tab = "lyrics"
    self._sync_tab_visibility()

def _sync_tab_visibility(self) -> None:
    self.queue_panel.display = (self._active_tab == "queue")
    self.lyrics_panel.display = (self._active_tab == "lyrics")
    self.query_one("#tab_btn_queue").set_class(self._active_tab == "queue", "-active")
    self.query_one("#tab_btn_lyrics").set_class(self._active_tab == "lyrics", "-active")
```

`action_toggle_lyrics` (binding `L`) diubah supaya juga memanggil `_show_lyrics_tab()`, bukan hanya toggle `state.show_lyrics` seperti sekarang — biar shortcut keyboard dan klik tombol tab konsisten hasilnya.

`refresh_ui()` di `Dashboard` tetap memanggil `update_state()` di kedua panel setiap tick tanpa peduli mana yang `display=True` — ini murah (cuma update Rich markup string, tidak re-render kalau hidden) dan menghindari state basi saat user pindah tab.

**Definisi selesai:** klik tombol "Antrean"/"Lirik" switch konten tanpa membongkar widget tree; tekan `L` dari mana saja langsung pindah ke tab Lirik; data di tab yang sedang tidak aktif tetap ter-update di background (dicek dengan pindah tab lalu lihat lyrics index sudah lanjut, bukan reset ke awal).

---

## Tahap 4 — Pecah Controls jadi 3 grup prioritas

**File:** `tui/panels/controls.py`

```python
def compose(self) -> ComposeResult:
    with Vertical():
        with Horizontal(id="controls_primary"):
            yield Button("⏮", id="btn_prev", classes="ctrl-sm")
            yield Button("⏯  PLAY / PAUSE", id="btn_pause", classes="ctrl-primary")
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

CSS:

```css
#controls_primary {
    height: 3;
    align: center middle;
}
#btn_pause {
    width: 60%;
    background: ACCENT_FIRE;  /* via theme.py f-string */
}
#btn_prev, #btn_next {
    width: 20%;
}

#controls_secondary {
    layout: grid;
    grid-size: 6;
    grid-gutter: 1;
    height: 3;
    margin-top: 1;
}

#controls_danger {
    align: right middle;
    height: 3;
    margin-top: 1;
}
#btn_quit {
    width: 16;
}
```

Logic `on_button_pressed` tidak berubah sama sekali — cuma `id` yang dirujuk tetap sama, jadi event handler existing tetap valid.

**Definisi selesai:** tombol Play/Pause secara visual ~3x lebih lebar dari Prev/Next dalam baris yang sama; 6 tombol sekunder rapi dalam grid rata; tombol Keluar terpisah baris sendiri rata kanan dengan jarak (`margin-top: 1`) dari grup di atasnya.

---

## Tahap 5 — Pindahkan status/error message ke Now Playing, online indicator ke Header

**File:** `tui/panels/now_playing.py`, `tui/dashboard.py`, `tui/panels/controls.py`

Di `NowPlayingPanel`, tambah satu `Static` baru di bawah progress bar:

```python
def compose(self) -> ComposeResult:
    with Vertical():
        self.info_label = Static("", id="np_info")
        self.progress_bar = ClickableProgressBar("", id="np_progress")
        self.status_line = Static("", id="np_status")
        yield self.info_label
        yield self.progress_bar
        yield self.status_line
```

`Dashboard._on_log_message` yang sekarang menulis ke `self.controls.status_msg` diubah menjadi menulis ke `self.now_playing.status_line`:

```python
async def _on_log_message(self, msg: str) -> None:
    self._status_msg = str(msg)
    self._status_msg_time = time.time()
    self.now_playing.status_line.update(f"[{ACCENT_GOLD}]{escape(str(msg))}[/]")
```

Dan `refresh_ui` membersihkan baris itu setelah 5 detik (logic timeout yang sudah ada dipertahankan, hanya target widget-nya pindah):

```python
if self._status_msg and (time.time() - self._status_msg_time > 5.0):
    self._status_msg = ""
    self.now_playing.status_line.update("")
```

Online indicator dipindah keluar dari `ControlsPanel.status_msg` sepenuhnya. Opsi paling murah tanpa subclass `Header` Textual (yang internal-nya bisa berubah antar versi): taruh sebagai `Static` kecil melayang di kanan atas lewat CSS `dock: right` di dalam `Header` slot, atau lebih aman — taruh sebagai elemen kecil terpisah tepat di bawah `Header`, sejajar dengan `Input` search:

```python
with Horizontal(id="top_bar"):
    yield Input(placeholder="...", id="search_input")
    self.online_dot = Static("●", id="online_indicator")
    yield self.online_dot
```

```python
def refresh_ui(self) -> None:
    color = STATUS_OK if self.state.is_online else STATUS_ERR
    self.online_dot.update(f"[{color}]●[/]")
```

**Definisi selesai:** `ControlsPanel.status_msg` reactive dan `watch_status_msg` dihapus sepenuhnya dari `controls.py` — panel itu sekarang murni tombol, tidak ada teks status. Pesan log (mis. "Searching: ...", "No results found.") muncul tepat di bawah progress bar Now Playing dan hilang otomatis 5 detik. Titik online/offline terlihat di kanan search bar, berubah warna saat koneksi putus (bisa ditest dengan matikan wifi Termux, tunggu siklus `check_connectivity` 30 detik).

---

## Tahap 6 — Kontras border antar panel

**File:** semua panel + `dashboard.py` CSS

Ganti semua `border: tall #1E1E30` (border hampir invisible karena dekat dengan `BG_PANEL`) menjadi `border: tall {BORDER}` (`#2a2a45`, satu tingkat lebih terang). Tambahkan state focus eksplisit ke `QueuePanel` OptionList yang saat ini override jadi `border: blank` saat focus — ganti jadi:

```css
OptionList:focus {
    border: tall {BORDER_FOCUS};
}
```

Supaya konsisten dengan `#search_input:focus` yang sudah memakai pola border gold saat aktif.

**Definisi selesai:** screenshot terminal di lebar 50 kolom menunjukkan empat panel (Now Playing, Queue/Lyrics, Controls, Search) punya garis pemisah yang jelas terlihat tanpa perlu zoom, dan widget yang sedang fokus (search atau queue list) punya border emas yang jelas beda dari yang tidak fokus.

---

## Urutan eksekusi & verifikasi per tahap

| # | Tahap | File disentuh | Cara verifikasi |
|---|---|---|---|
| 0 | Sentralisasi token warna | `tui/theme.py` (baru) | `grep -r "#1E1E30\|#FF6B35\|#FFC107" tui/` hasilnya nol di luar `theme.py` |
| 1 | Deteksi resize | `dashboard.py` | `textual run --dev main.py`, resize jendela, lihat class di DevTools console |
| 2 | Restruktur compose | `dashboard.py` | Jalankan di 40 kolom dan 100 kolom, screenshot, bandingkan rasio Now Playing |
| 3 | Tab manual | `dashboard.py`, `queue_panel.py`, `lyrics_panel.py` | Pindah tab lewat klik dan keyboard `L`, pastikan data tetap update di tab nonaktif |
| 4 | Grup controls | `controls.py` | Visual cek lebar tombol Play/Pause vs Prev/Next |
| 5 | Pindah status & online dot | `now_playing.py`, `dashboard.py`, `controls.py` | Trigger search gagal (matikan koneksi), lihat pesan muncul di Now Playing bukan di Controls |
| 6 | Kontras border | semua panel | Visual cek di terminal Termux asli (warna terminal emulator bisa beda render dari devtools desktop) |

Setiap tahap independen secara file — bisa di-commit terpisah dan dites satu-satu tanpa menunggu tahap lain selesai, kecuali Tahap 3 yang sebaiknya setelah Tahap 2 (karena butuh `side_panel` container sudah ada).

---

## Yang sengaja tidak diubah

`engine/`, `cache/`, `core/event_bus.py`, `core/state.py`, `integrations/` — semua logic pemutaran, caching, dan state tidak disentuh sama sekali. Risiko regresi dibatasi murni ke layer presentasi.

`AutoplayEngine` dan `SponsorBlockHandler` tidak ada hook UI baru yang dibutuhkan dari mereka — keduanya sudah berkomunikasi lewat `event_bus` yang sama, tidak ada perubahan kontrak event di plan ini.