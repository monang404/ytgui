# 🎨 DESIGN DOCUMENT — YT Termux Player Pro v1.0

**Tipe Dokumen:** TUI/UX Design Specification  
**Audience:** Developer yang implement layer TUI

---

## FILOSOFI DESAIN

> "Terminal bukan kekurangan — terminal adalah fitur."

YT Termux Player Pro dirancang untuk membuktikan bahwa pengalaman mendengarkan musik kelas premium bisa dicapai tanpa GUI. Desain mengutamakan:

1. **Information Density** — Setiap karakter di layar harus bermakna
2. **Glanceability** — Status terpenting terbaca dalam < 1 detik
3. **Keyboard-First** — Semua aksi dapat dilakukan tanpa mengangkat tangan dari keyboard
4. **Resilient Layout** — Tetap fungsional di terminal 80×24 hingga full HD

---

## TERMINAL REQUIREMENTS

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Lebar | 80 karakter | 120+ karakter |
| Tinggi | 24 baris | 36+ baris |
| Color depth | 8-color | 256-color / Truecolor |
| Font | Monospace | Nerd Font (ikon Unicode) |
| Encoding | UTF-8 | UTF-8 |

**Deteksi terminal:**
```python
import shutil, os

cols, rows = shutil.get_terminal_size(fallback=(80, 24))
has_truecolor = os.environ.get("COLORTERM") in ("truecolor", "24bit")
has_256color = "256color" in os.environ.get("TERM", "")
```

---

## COLOR PALETTE

```python
# Semua warna didefinisikan di satu tempat — JANGAN hardcode inline

COLORS = {
    # Primary
    "accent":       "#FF6B35",   # Orange — Now Playing highlight
    "accent_dim":   "#8B3A1E",   # Orange gelap — secondary accent

    # Status
    "online":       "#4CAF50",   # Hijau — ONLINE status
    "offline":      "#F44336",   # Merah — OFFLINE / ERROR
    "buffering":    "#FFC107",   # Kuning — LOADING / BUFFERING
    "paused":       "#9C27B0",   # Ungu — PAUSED state

    # Text hierarchy
    "text_primary":   "#FFFFFF",   # Judul, info penting
    "text_secondary": "#AAAAAA",   # Metadata (artis, durasi)
    "text_muted":     "#555555",   # Placeholder, non-aktif
    "text_lyric_active": "#FF6B35", # Baris lirik aktif
    "text_lyric_prev":   "#888888", # Baris lirik sebelumnya
    "text_lyric_next":   "#CCCCCC", # Baris lirik berikutnya

    # Background
    "bg_panel":     "#0D0D0D",   # Panel background
    "bg_header":    "#1A1A2E",   # Header background
    "bg_progress":  "#2D2D2D",   # Progress bar track

    # Queue
    "queue_active": "#FF6B35",   # Item yang sedang diputar
    "queue_next":   "#FFFFFF",   # Item berikutnya
    "queue_rest":   "#777777",   # Item sisa
}
```

---

## LAYOUT SPECIFICATION

### Grid System

```
Terminal (80–120 cols × 24–36 rows)
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER (3 rows fixed)                                                       │
├─────────────────────────────────┬───────────────────────────────────────────┤
│                                 │                                           │
│  LEFT PANEL                     │  RIGHT TOP PANEL                         │
│  NOW PLAYING                    │  QUEUE & AUTOPLAY                        │
│  (50% width, dynamic height)    │  (50% width, ~40% height)               │
│                                 │                                           │
│                                 ├───────────────────────────────────────────┤
│                                 │                                           │
│                                 │  RIGHT BOTTOM PANEL                      │
│                                 │  SYNCHRONIZED LYRICS                     │
│                                 │  (50% width, ~60% height)               │
│                                 │                                           │
├─────────────────────────────────┴───────────────────────────────────────────┤
│ FOOTER (5 rows fixed)                                                       │
│  - Keyboard controls (2 rows)                                               │
│  - Search input (1 row)                                                     │
│  - Status messages (1 row)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rich Layout Code

```python
from rich.layout import Layout

def build_layout() -> Layout:
    layout = Layout(name="root")

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=6),
    )

    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1),
    )

    layout["right"].split_column(
        Layout(name="queue", ratio=2),
        Layout(name="lyrics", ratio=3),
    )

    return layout
```

---

## PANEL SPECIFICATIONS

### Panel 1: Header

```
╔════════════════════════════════════════════════════════════════════════════╗
║ 🎵 YT TERMUX PLAYER PRO v1.0          ⚡ ONLINE  🔋 87%  📶 WiFi  22:47 ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Elemen:**
- Logo + versi (kiri)
- Status koneksi: `⚡ ONLINE` (hijau) / `📵 OFFLINE` (merah)
- Baterai termux-battery-status via `termux-battery-status` (JSON)
- Jam sistem

```python
from rich.panel import Panel
from rich.text import Text
import subprocess, json, datetime

def render_header(state: AppState) -> Panel:
    # Battery info
    try:
        bat = json.loads(subprocess.check_output(["termux-battery-status"], timeout=0.5))
        battery = f"🔋 {bat['percentage']}%"
    except Exception:
        battery = ""

    clock = datetime.datetime.now().strftime("%H:%M")
    status_color = "green" if state.is_online else "red"
    status_text = "⚡ ONLINE" if state.is_online else "📵 OFFLINE"

    left = Text("🎵 YT TERMUX PLAYER PRO v1.0", style="bold white")
    right = Text(f"{status_text}  {battery}  {clock}",
                 style=f"bold {status_color}")

    # Gabung dengan padding
    header_text = Text.assemble(left, "  " + " " * 30 + "  ", right)
    return Panel(header_text, style="on #1A1A2E", padding=(0, 1))
```

---

### Panel 2: Now Playing (Kiri)

```
╔═══════════════════════════════════╗
║ [ NOW PLAYING ]                   ║
║                                   ║
║  ♪  Nasi Goreng Song              ║
║     The Wok Masters               ║
║     👁 1.2M views  ⏱ 3:40        ║
║     Via: 💾 Local Cache           ║
║                                   ║
║  ▁▃▅▇█▇▅▃▁ ▂▄▆█▇▅▃▁ ▃▅▇█▆▄▂     ║
║                                   ║
║  ██████████░░░░░░░░░░░░░░░░░░     ║
║  01:15 ────────────────── 03:40   ║
║                                   ║
║  🔊 80%  ⏩ Gapless: ON           ║
║  🚫 SponsorBlock: 2 segs skipped  ║
╚═══════════════════════════════════╝
```

**Spesifikasi Equalizer:**

Gunakan 16 bar dengan 3 sine wave berlapis berbeda frekuensi:

```python
import math, time

BARS = "▁▂▃▄▅▆▇█"

def render_equalizer(n_bars: int = 16) -> str:
    t = time.time()
    result = []
    for i in range(n_bars):
        # 3 oscillator dengan frekuensi berbeda untuk naturalisme
        v1 = math.sin(t * 2.3 + i * 0.7)
        v2 = math.sin(t * 5.1 + i * 1.4) * 0.6
        v3 = math.sin(t * 8.7 + i * 0.3) * 0.3
        combined = (v1 + v2 + v3) / 1.9       # normalize ~(-1, 1)
        bar_idx = int((combined + 1) / 2 * 7) # 0–7
        result.append(BARS[max(0, min(7, bar_idx))])
        if (i + 1) % 4 == 0:
            result.append(" ")
    return "".join(result)
```

**Spesifikasi Progress Bar:**

```python
from rich.progress import BarColumn, TextColumn, Progress

def render_progress(position: float, duration: float) -> str:
    if duration <= 0:
        return ""
    pct = position / duration
    bar_width = 30
    filled = int(pct * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    pos_str = f"{int(position//60):02d}:{int(position%60):02d}"
    dur_str = f"{int(duration//60):02d}:{int(duration%60):02d}"
    return f"[dim]{pos_str}[/] {bar} [dim]{dur_str}[/]"
```

---

### Panel 3: Queue & Autoplay (Kanan Atas)

```
╔═══════════════════════════════════════╗
║ [ QUEUE & AUTOPLAY ]  3 lagu         ║
║                                       ║
║  ▶ 1. Nasi Goreng Song  [NOW]        ║
║    2. Sate Madura Vibes   3:22       ║
║    3. Martabak Manis Lofi 4:15       ║
║    ─────────────────────────────      ║
║    4. (Radio) Rendang Rock  ~4:00    ║
║    5. (Radio) Opor Ambient  ~3:30   ║
║                                       ║
║  📻 Radio Mode: ON                   ║
╚═══════════════════════════════════════╝
```

**Aturan display:**
- Item aktif: warna accent + prefix `▶`
- Item manual: warna putih + nomor
- Item radio/autoplay: warna muted + prefix `(Radio)` + durasi dengan `~` (estimasi)
- Jika queue > 8 item: tampilkan 3 sebelum dan 3 sesudah current, sisanya `... +N lagu`

---

### Panel 4: Synchronized Lyrics (Kanan Bawah)

```
╔═══════════════════════════════════════╗
║ [ SYNCHRONIZED LYRICS ]              ║
║                                       ║
║  Mengaduk bumbu di atas wajan...      ║  ← 2 baris sebelumnya (muted)
║  Aroma harum mulai menggoda...        ║
║                                       ║
║▶ Nasi goreng spesial siap dihidang   ║  ← BARIS AKTIF (accent, bold)
║                                       ║
║  Ditaburi bawang goreng renyah        ║  ← 2 baris berikutnya (dim)
║  Dan telur mata sapi sempurna         ║
║                                       ║
║  [Instrumen]                          ║  ← Segment non-vokal
╚═══════════════════════════════════════╝
```

**Logika sinkronisasi:**

```python
def find_active_lyric_index(lyrics: list[tuple[float, str]], position: float) -> int:
    """Return index baris yang sedang aktif berdasarkan posisi."""
    active = 0
    for i, (timestamp, _) in enumerate(lyrics):
        if timestamp <= position:
            active = i
        else:
            break
    return active

def render_lyrics_window(lyrics, active_idx, window=2) -> list[tuple[str, str]]:
    """Return list of (style, text) untuk window di sekitar baris aktif."""
    result = []
    for i in range(active_idx - window, active_idx + window + 1):
        if i < 0 or i >= len(lyrics):
            result.append(("dim", ""))
            continue
        _, text = lyrics[i]
        if i == active_idx:
            result.append(("bold #FF6B35", f"▶ {text}"))
        elif i < active_idx:
            style = "dim" if active_idx - i > 1 else "#888888"
            result.append((style, f"  {text}"))
        else:
            style = "dim" if i - active_idx > 1 else "#CCCCCC"
            result.append((style, f"  {text}"))
    return result
```

---

### Panel 5: Footer — Controls & Input

```
╔═════════════════════════════════════════════════════════════════════════════╗
║ ─────────────────────────── KONTROL ──────────────────────────────────────║
║  [P] Pause/Play  [N] Next  [B] Prev  [S] Stop  [U] Vol+  [D] Vol-         ║
║  [M] Download & Cache   [R] Radio Mode   [L] Toggle Lyrics   [Q] Quit     ║
║ ─────────────────────────────────────────────────────────────────────────  ║
║  ❯ _                                                                       ║
╚═════════════════════════════════════════════════════════════════════════════╝
```

---

## KEYBOARD MAP LENGKAP

| Key | Aksi | Event yang dipublish |
|-----|------|---------------------|
| `P` | Toggle pause/play | `CMD_TOGGLE_PAUSE` |
| `N` | Next track | `CMD_NEXT` |
| `B` | Previous track | `CMD_PREV` |
| `S` | Stop & clear queue | `CMD_STOP` |
| `U` | Volume +5 | `VOLUME_CHANGED` |
| `D` | Volume -5 | `VOLUME_CHANGED` |
| `M` | Download current track | `CMD_DOWNLOAD` |
| `R` | Toggle radio mode | `CMD_TOGGLE_RADIO` |
| `L` | Toggle lyrics panel | `CMD_TOGGLE_LYRICS` |
| `Q` | Quit / hide ke background | `CMD_QUIT` |
| `1`–`9` | Pilih lagu dari queue | `CMD_QUEUE_SELECT` |
| `Enter` | Submit search query | `CMD_SEARCH` |
| `/` | Focus ke search input | `CMD_FOCUS_SEARCH` |
| `Esc` | Cancel / unfocus search | `CMD_UNFOCUS` |

**Implementasi non-blocking keyboard:**

```python
# tui/input_handler.py
import asyncio, sys, tty, termios

async def read_key() -> str:
    """Baca satu keystroke secara async tanpa blocking event loop."""
    loop = asyncio.get_event_loop()
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = await loop.run_in_executor(None, sys.stdin.read, 1)
        return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
```

---

## SEARCH INPUT UX

Saat user mengetik di footer search:

1. **Typing mode** diaktifkan saat `❯` di-focus
2. Karakter muncul real-time di input field
3. Saat `Enter` → trigger search, tampilkan `Searching...` di footer
4. Hasil muncul sebagai **overlay** di atas queue panel:

```
╔═══════════════════════════════════════╗
║ [ HASIL PENCARIAN: "nasi goreng" ]   ║
║                                       ║
║  1. Nasi Goreng Song - Wok Masters   ║
║  2. Nasi Goreng Beat - DJ Dapur      ║
║  3. Nasi Goreng Anthem - Fried Rice  ║
║                                       ║
║  Tekan [1-9] untuk pilih, [Esc] batal║
╚═══════════════════════════════════════╝
```

---

## STATE VISUAL MAPPING

| AppState | Visual Indicator |
|----------|-----------------|
| `IDLE` | Header: abu-abu. Equalizer: flat |
| `LOADING` | Header: kuning berkedip. Footer: "⟳ Loading..." |
| `PLAYING` | Equalizer: animasi. Progress bar: bergerak |
| `PAUSED` | Equalizer: static (frozen frame). `⏸` di header |
| `BUFFERING` | Progress bar: spinner. Footer: "⟳ Buffering..." |
| `ERROR` | Header: merah. Footer: pesan error. Log ke file |

---

## RESPONSIVE BEHAVIOR

### Narrow Terminal (80–99 cols)
- Lyrics panel disembunyikan otomatis
- Queue hanya tampilkan 5 item
- Equalizer dikurangi jadi 8 bar

### Wide Terminal (120+ cols)
- Semua panel penuh
- Lyrics tampil dengan margin lebih lebar
- Tambahkan album art ASCII (opsional, fase 5)

```python
def adapt_layout(cols: int, rows: int, layout: Layout):
    if cols < 100:
        layout["lyrics"].visible = False
    if rows < 28:
        # Kurangi baris equalizer
        pass
```

---

## ANIMASI & TIMING

| Elemen | Refresh | Catatan |
|--------|---------|---------|
| Equalizer | 250ms (4fps) | Lebih cepat = boros CPU di HP entry-level |
| Progress bar | 500ms | Sync dengan mpv IPC polling |
| Lyrics highlight | On event | Dipicu LYRICS_UPDATED, bukan polling |
| Status messages | 100ms | Untuk animasi spinner loading |
| Header clock | 1000ms | Tidak perlu lebih cepat |

**Rule of thumb:** Gunakan `asyncio.sleep()` untuk timing, bukan `time.sleep()`. `time.sleep()` akan memblokir event loop.

---

## TERMUX WIDGET DESIGN

File shortcut di `~/.shortcuts/`:

```
~/.shortcuts/
├── ▶⏸ Play Pause.sh
├── ⏭ Next Track.sh
├── ⏮ Prev Track.sh
├── 🔊 Volume Up.sh
└── 🔇 Volume Down.sh
```

Nama file dengan emoji/space agar tampil cantik di widget Android.

```bash
# ▶⏸ Play Pause.sh
#!/data/data/com.termux/files/usr/bin/bash
SOCK="/tmp/mpv-yt-player.sock"

if [ -S "$SOCK" ]; then
    echo '{"command":["cycle","pause"]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
    termux-notification --title "YT Player" --content "▶/⏸ toggled"
else
    termux-notification --title "YT Player" --content "⚠️ Player tidak berjalan"
fi
```
