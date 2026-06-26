#!/usr/bin/env python3
"""
patch_ytgui.py — Patch otomatis untuk ytgui-main / bagas.fm
Menerapkan semua fix dari ANALISIS_MENDALAM.md dalam satu run.
Setiap patch memiliki verify check sebelum dan sesudah apply.
"""

import pathlib
import sys
import datetime
import textwrap

BASE = pathlib.Path("/home/claude/ytgui-main")

# ── Warna terminal ───────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; W = "\033[0m"; BOLD = "\033[1m"

results = []

def patch(pid, desc, filepath, old, new, verify_after=None):
    """Apply single string-replace patch, verify before and after."""
    path = BASE / filepath
    text = path.read_text(encoding="utf-8")
    already = (verify_after or new) in text

    if already:
        results.append((pid, "SKIP", desc))
        print(f"  {Y}[SKIP]{W} [{pid}] {desc}")
        return True

    if old not in text:
        results.append((pid, "MISS", desc))
        print(f"  {R}[MISS]{W} [{pid}] {desc}  ← string target tidak ditemukan!")
        return False

    patched = text.replace(old, new, 1)
    path.write_text(patched, encoding="utf-8")

    check = verify_after or new
    if check in path.read_text(encoding="utf-8"):
        results.append((pid, "OK", desc))
        print(f"  {G}[ OK ]{W} [{pid}] {desc}")
        return True
    else:
        results.append((pid, "FAIL", desc))
        print(f"  {R}[FAIL]{W} [{pid}] {desc}  ← patch tidak terverifikasi!")
        return False


def patch_multi(pid, desc, filepath, replacements, verify_token):
    """Apply multiple replacements to one file, verify with a final token."""
    path = BASE / filepath
    text = path.read_text(encoding="utf-8")

    if verify_token in text:
        results.append((pid, "SKIP", desc))
        print(f"  {Y}[SKIP]{W} [{pid}] {desc}")
        return True

    for old, new in replacements:
        if old in text:
            text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")

    if verify_token in path.read_text(encoding="utf-8"):
        results.append((pid, "OK", desc))
        print(f"  {G}[ OK ]{W} [{pid}] {desc}")
        return True
    else:
        results.append((pid, "FAIL", desc))
        print(f"  {R}[FAIL]{W} [{pid}] {desc}  ← patch tidak terverifikasi!")
        return False


# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}{B}═══ YTGUI PATCH SUITE ═══{W}")
print(f"Target : {BASE}")
print(f"Waktu  : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ────────────────────────────────────────────────────────────────────────────
print(f"{BOLD}── BACKEND PATCHES ─────────────────────────────────────────────────{W}")

# ── B-01 · Eviction tidak proteksi favorit ──────────────────────────────────
patch(
    "B-01",
    "Eviction SQL: guard is_favorite",
    "cache/db.py",
    '"DELETE FROM tracks WHERE last_played < ? AND play_count = 0 AND local_path IS NULL",',
    '"DELETE FROM tracks WHERE last_played < ? AND play_count = 0 AND local_path IS NULL AND (is_favorite = 0 OR is_favorite IS NULL)",',
)

# ── B-11 · Handle reason="stop" di _on_track_ended ──────────────────────────
patch(
    "B-11",
    "PlaybackController: handle mpv 'stop' reason",
    "engine/playback_controller.py",
    '        if reason == "eof":\n            await self._on_next(next_data)\n        elif reason == "error":',
    '        if reason == "eof":\n            await self._on_next(next_data)\n        elif reason == "stop":\n            # Intentional stop — sync server state ke IDLE\n            if self.state.status not in (PlayerStatus.IDLE,):\n                self.state.status = PlayerStatus.IDLE\n        elif reason == "error":',
    'elif reason == "stop":',
)

# ── A-05 · play_track() race condition — tambah _play_lock ──────────────────
patch(
    "A-05",
    "PlaybackController: _play_lock untuk play_track()",
    "engine/playback_controller.py",
    '        self._lock = asyncio.Lock()\n        self._retry_count = 0',
    '        self._lock = asyncio.Lock()\n        self._play_lock = asyncio.Lock()  # A-05: proteksi race condition di play_track\n        self._retry_count = 0',
    "_play_lock = asyncio.Lock()",
)

patch(
    "A-05b",
    "PlaybackController: play_track() pakai _play_lock",
    "engine/playback_controller.py",
    '    async def play_track(self, track: TrackInfo):\n        # Push current to history if it exists\n        if self.state.current_track:',
    '    async def play_track(self, track: TrackInfo):\n        async with self._play_lock:  # A-05: cegah concurrent play_track race\n         # Push current to history if it exists\n         if self.state.current_track:',
    "async with self._play_lock:  # A-05",
)

# ── B-02 · _on_set_mode memanggil _advance_to_next saat keluar RADIO ─────────
patch(
    "B-02",
    "PlaybackController: hapus _advance_to_next() saat keluar RADIO mode",
    "engine/playback_controller.py",
    '                self.state.status = PlayerStatus.IDLE\n                    await self._advance_to_next()\n                    \n                if mode == PlaybackMode.RADIO:',
    '                self.state.status = PlayerStatus.IDLE\n                    # B-02: tidak auto-advance saat keluar RADIO — biarkan user mulai manual\n                    \n                if mode == PlaybackMode.RADIO:',
    "# B-02: tidak auto-advance",
)

# ── A-06 · _is_fetching di RadioMode bisa stuck — ganti ke asyncio.Lock ─────
patch(
    "A-06",
    "RadioEngine: ganti _is_fetching bool → asyncio.Lock (atomic, tidak stuck)",
    "engine/radio_engine.py",
    '        self._is_fetching = False\n        self._bg_tasks = set()',
    '        self._fetch_lock = asyncio.Lock()  # A-06: ganti _is_fetching bool — atomic, tidak bisa stuck\n        self._bg_tasks = set()',
    "self._fetch_lock = asyncio.Lock()",
)

patch(
    "A-06b",
    "RadioEngine: _prefetch_next pakai _fetch_lock",
    "engine/radio_engine.py",
    '    async def _prefetch_next(self, controller: "PlaybackController") -> None:\n        \"\"\"Ambil batch track berikutnya di background, taruh ke radio_queue\n        (bukan queue). Sama seperti _fetch_and_play_initial, batch ini\n        diambil dari beberapa artis sekaligus lalu di-interleave supaya\n        tidak monoton satu artis berturut-turut.\"\"\"\n        if self._is_fetching:\n            return\n        self._is_fetching = True\n        try:',
    '    async def _prefetch_next(self, controller: "PlaybackController") -> None:\n        \"\"\"Ambil batch track berikutnya di background, taruh ke radio_queue\n        (bukan queue). Sama seperti _fetch_and_play_initial, batch ini\n        diambil dari beberapa artis sekaligus lalu di-interleave supaya\n        tidak monoton satu artis berturut-turut.\"\"\"\n        if self._fetch_lock.locked():  # A-06: atomic check\n            return\n        async with self._fetch_lock:  # A-06: tidak bisa stuck di finally\n            try:',
    "async with self._fetch_lock:",
)

# ── A-03 · mpv tidak publish error saat disconnect ──────────────────────────
patch(
    "A-03",
    "MpvController: publish TrackEndedEvent(error) saat koneksi terputus",
    "engine/mpv_controller.py",
    '        finally:\n            self.is_connected = False\n            for fut in self._pending.values():\n                if not fut.done():\n                    fut.cancel()\n            self._pending.clear()\n            logger.warning("mpv observer loop ended — connection lost.")',
    '        finally:\n            self.is_connected = False\n            for fut in self._pending.values():\n                if not fut.done():\n                    fut.cancel()\n            self._pending.clear()\n            logger.warning("mpv observer loop ended — connection lost.")\n            # A-03: notify PlaybackController supaya tidak silent-dead\n            if not getattr(self, "_shutting_down", False):\n                from core.events import TrackEndedEvent\n                import asyncio as _aio\n                try:\n                    loop = _aio.get_running_loop()\n                    loop.create_task(self._bus.publish(TrackEndedEvent(reason="error")))\n                except RuntimeError:\n                    pass  # loop sudah stop, tidak perlu publish',
    "A-03: notify PlaybackController",
)

# Tambah _shutting_down flag ke MpvController.close()
patch(
    "A-03b",
    "MpvController: set _shutting_down=True di close() agar tidak publish saat shutdown",
    "engine/mpv_controller.py",
    '    async def close(self):\n        """Graceful cleanup."""\n        self.is_connected = False',
    '    async def close(self):\n        """Graceful cleanup."""\n        self._shutting_down = True  # A-03b: cegah reconnect-publish saat shutdown normal\n        self.is_connected = False',
    "_shutting_down = True",
)

# ── A-04 · Windows multi-room TCP port conflict ──────────────────────────────
patch(
    "A-04",
    "RoomManager: TCP port unik per room (Windows fix)",
    "core/room_manager.py",
    '        self.mpv = MpvController(\n            socket_path=f"/tmp/mpv-socket-{room_id}",\n            event_bus=self.event_bus  # TASK-3.3: inject per-room bus\n        )',
    '        # A-04: port unik per-room agar multi-room Windows tidak conflict\n        _win_port = str(12345 + (abs(hash(room_id)) % 800))\n        self.mpv = MpvController(\n            socket_path=f"/tmp/mpv-socket-{room_id}",\n            tcp_port=_win_port,\n            event_bus=self.event_bus  # TASK-3.3: inject per-room bus\n        )',
    "A-04: port unik per-room",
)

# ── B-03 · Prefetch stream URL untuk track berikutnya, bukan yang sedang main ─
patch(
    "B-03",
    "server/app.py: prefetch stream URL untuk track berikutnya, bukan current",
    "server/app.py",
    '        if track and track.video_id:\n            safe_create_task(_prefetch_stream_url(track.video_id), name=f"prefetch_{track.video_id}")',
    '        # B-03: prefetch URL untuk track BERIKUTNYA di queue, bukan track yang baru main\n        # (current track sudah di-resolve oleh CacheResolver sesaat sebelumnya)\n        if room.state.queue:\n            _next = room.state.queue[0]\n            if _next and _next.video_id:\n                safe_create_task(_prefetch_stream_url(_next.video_id), name=f"prefetch_next_{_next.video_id}")',
    "B-03: prefetch URL untuk track BERIKUTNYA",
)

# ── B-10 · Service Worker cache version hardcoded ────────────────────────────
_cache_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
patch(
    "B-10",
    f"ServiceWorker: update cache version ke bagas-fm-{_cache_ts}",
    "web/static/sw.js",
    "const CACHE_VERSION = 'bagas-fm-v6';",
    f"const CACHE_VERSION = 'bagas-fm-{_cache_ts}';  // B-10: auto-updated {_cache_ts}",
    f"bagas-fm-{_cache_ts}",
)

# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}── CSS / FRONTEND PATCHES ──────────────────────────────────────────{W}")

# ── C-01 · user-scalable=no — WCAG violation ─────────────────────────────────
patch(
    "C-01",
    "index.html: hapus user-scalable=no (WCAG 1.4.4)",
    "web/static/index.html",
    'content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"',
    'content="width=device-width, initial-scale=1.0"',
    'initial-scale=1.0"',
)

# ── C-04 · safe-area-inset-top untuk iPhone notch / Dynamic Island ───────────
patch(
    "C-04",
    "layout.css: tambah safe-area-inset-top untuk iPhone notch/Dynamic Island",
    "web/static/css/layout.css",
    "@supports (padding: env(safe-area-inset-bottom)) {",
    """@supports (padding: env(safe-area-inset-top)) {
  /* C-04: iPhone notch / Dynamic Island */
  #app-header {
    padding-top: calc(var(--s4) + env(safe-area-inset-top));
  }
}

@supports (padding: env(safe-area-inset-bottom)) {""",
    "C-04: iPhone notch",
)

# ── C-03 · Tablet landscape — nav bar hilang tanpa fallback ─────────────────
# Add a compact tab strip yang always visible di landscape tablet
patch(
    "C-03",
    "layout.css: tablet landscape — nav bar compact, tidak hilang total",
    "web/static/css/layout.css",
    "  /* Sembunyikan nav bar di tablet landscape — navigasi via swipe atau gesture */\n  #nav-bar {\n    display: none;\n  }",
    """  /* C-03: kompres nav bar — jangan sembunyikan total, tidak ada swipe gesture */
  #nav-bar {
    height: auto;
    min-height: 44px;
  }
  .nav-btn {
    flex-direction: row;
    gap: 6px;
    padding: 8px 12px;
    font-size: 12px;
  }
  .nav-btn .nav-icon { font-size: 14px; }
  .nav-btn span { font-size: 11px; }""",
    "C-03: kompres nav bar",
)

# ── C-04b · Tablet portrait — maksimalkan penggunaan lebar ───────────────────
patch(
    "C-02",
    "layout.css: tablet portrait max-width 768px (dari 600px)",
    "web/static/css/layout.css",
    "@media (min-width: 601px) {\n  #app {\n    max-width: 600px;\n    margin: 0 auto;\n    box-shadow: 0 0 40px rgba(0, 0, 0, 0.6);\n  }",
    """@media (min-width: 601px) {
  #app {
    /* C-02: gunakan lebih banyak ruang di tablet, bukan cuma 600px kolom sempit */
    max-width: 768px;
    margin: 0 auto;
    box-shadow: 0 0 40px rgba(0, 0, 0, 0.6);
  }""",
    "C-02: gunakan lebih banyak ruang",
)

# ── C-05 · Settings sheet rusak di desktop ───────────────────────────────────
# Add desktop override untuk settings sheet
_settings_desktop = """
/* C-05: Settings sheet pada desktop — anchored ke kanan bawah konten, bukan fixed ke viewport */
@media (min-width: 1024px) {
  .settings-sheet {
    position: absolute;
    bottom: 80px;
    right: 20px;
    left: auto;
    max-width: 400px;
    border-radius: var(--r-lg);
    margin: 0;
  }
  .settings-sheet.open {
    bottom: 80px;
  }
}
"""

layout_path = BASE / "web/static/css/layout.css"
layout_text = layout_path.read_text(encoding="utf-8")
if "C-05: Settings sheet" not in layout_text:
    layout_text += _settings_desktop
    layout_path.write_text(layout_text, encoding="utf-8")
    print(f"  {G}[ OK ]{W} [C-05] layout.css: settings sheet desktop fix")
    results.append(("C-05", "OK", "layout.css: settings sheet desktop fix"))
else:
    print(f"  {Y}[SKIP]{W} [C-05] layout.css: settings sheet desktop fix")
    results.append(("C-05", "SKIP", "layout.css: settings sheet desktop fix"))

# ── C-06 · Volume slider touch target terlalu kecil ─────────────────────────
patch(
    "C-06",
    "components.css: volume slider lebih lebar dan tinggi (touch target)",
    "web/static/css/components.css",
    ".vol-slider {\n  width: 70px;\n  height: 3px;\n  cursor: pointer;\n  accent-color: var(--accent);\n  border-radius: 2px;\n  outline: none;\n  background: var(--fm-border);\n}",
    """.vol-slider {
  width: 120px;  /* C-06: dari 70px → 120px, lebih mudah digeser */
  height: 6px;   /* C-06: dari 3px → 6px, touch target lebih besar */
  cursor: pointer;
  accent-color: var(--accent);
  border-radius: 3px;
  outline: none;
  background: var(--fm-border);
}""",
    "C-06: dari 70px",
)

# ── C-07 · Queue drag handle tidak terlihat di mobile ───────────────────────
# Tambah di akhir components.css
_drag_mobile = """
/* C-07: Queue drag handle — selalu visible di touchscreen (tidak ada :hover) */
@media (hover: none) {
  .qi-drag {
    opacity: 0.45 !important;
  }
}
"""
comp_path = BASE / "web/static/css/components.css"
comp_text = comp_path.read_text(encoding="utf-8")
if "C-07: Queue drag handle" not in comp_text:
    comp_text += _drag_mobile
    comp_path.write_text(comp_text, encoding="utf-8")
    print(f"  {G}[ OK ]{W} [C-07] components.css: queue drag handle visible di mobile")
    results.append(("C-07", "OK", "components.css: queue drag handle mobile"))
else:
    print(f"  {Y}[SKIP]{W} [C-07] components.css: queue drag handle visible di mobile")
    results.append(("C-07", "SKIP", "components.css: queue drag handle mobile"))

# ── C-08 · Lyrics height inline style → CSS var ─────────────────────────────
# Patch index.html lyrics container
patch(
    "C-08",
    "index.html: lyrics height 60vh → 60dvh (dynamic viewport, Safari-safe)",
    "web/static/index.html",
    'style="height: 60vh; overflow-y: auto;"',
    'style="height: 60dvh; overflow-y: auto;"',  # C-08: dvh lebih stabil di mobile
    "60dvh",
)

# ── C-12 · iOS Safari overflow hidden body scroll-bleed ─────────────────────
patch(
    "C-12",
    "base.css: tambah overscroll-behavior:none agar body tidak scroll-bleed di iOS",
    "web/static/css/base.css",
    "html, body {\n  background: var(--bg-primary);\n  min-height: 100dvh;\n  min-height: 100vh;\n  margin: 0; padding: 0;\n  font-family: var(--font);\n  color: var(--text-1);\n  overflow: hidden;\n  -webkit-font-smoothing: antialiased;\n}",
    """html, body {
  background: var(--bg-primary);
  min-height: 100dvh;
  min-height: 100vh;
  margin: 0; padding: 0;
  font-family: var(--font);
  color: var(--text-1);
  overflow: hidden;
  overscroll-behavior: none;  /* C-12: cegah scroll-bleed di iOS Safari */
  -webkit-font-smoothing: antialiased;
}""",
    "C-12: cegah scroll-bleed",
)

# ── C-14 · Google Fonts @import → preconnect + preload di HTML ───────────────
# Step 1: hapus @import dari base.css
patch(
    "C-14a",
    "base.css: hapus Google Fonts @import (render-blocking)",
    "web/static/css/base.css",
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');\n\n",
    "/* C-14: Google Fonts dipindah ke <link> di HTML head untuk non-blocking load */\n\n",
    "C-14: Google Fonts dipindah",
)

# Step 2: tambah preconnect + preload di HTML head
patch(
    "C-14b",
    "index.html: tambah Google Fonts preconnect + preload (non-blocking)",
    "web/static/index.html",
    '    <meta name="viewport"',
    """    <!-- C-14: non-blocking font load -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" onload="this.onload=null;this.rel='stylesheet'">
    <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"></noscript>
    <meta name="viewport\"""",
    "C-14: non-blocking font load",
)

# ════════════════════════════════════════════════════════════════════════════
print(f"\n{BOLD}── HASIL AKHIR ─────────────────────────────────────────────────────{W}")

ok   = [r for r in results if r[1] == "OK"]
skip = [r for r in results if r[1] == "SKIP"]
fail = [r for r in results if r[1] in ("FAIL", "MISS")]

print(f"\n  {G}✔ Berhasil diterapkan : {len(ok):2d}{W}")
print(f"  {Y}◌ Sudah ada (skip)    : {len(skip):2d}{W}")
print(f"  {R}✘ Gagal               : {len(fail):2d}{W}")
print(f"  ─ Total patch          : {len(results):2d}")

if fail:
    print(f"\n{R}Patch yang gagal:{W}")
    for pid, status, desc in fail:
        print(f"  [{pid}] {desc}")

sys.exit(1 if fail else 0)
