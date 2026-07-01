#!/usr/bin/env bash
# ============================================================================
# patch_radio_empty.sh — ytgui: fix idle-flash saat Radio queue habis & next
#
# Bug: RadioMode.next() (engine/radio_engine.py) — saat radio_queue kosong
# (misalnya user pencet "next" pas lagi mepet/kosong), kode cuma men-trigger
# _start() sebagai background task lalu langsung return, TANPA mengubah
# status/current_track ATAU broadcast QueueUpdatedEvent. _start() bisa makan
# waktu sampai ~20 detik (fetch DB + resolve yt-dlp) kalau standby belum
# siap. Selama window itu, server tidak pernah memberi tahu frontend apa-apa
# -> UI nyangkut di info lagu LAMA yang sudah selesai (kelihatan idle/stuck),
# baru tiba-tiba lompat begitu _start() selesai. Kalau user sempat klik
# "play" di tengah window itu, hasilnya nyangkut sebentar lalu balik idle
# lagi karena state belum benar-benar konsisten.
#
# Fix: set status = LOADING dan publish QueueUpdatedEvent() SEKARANG (bukan
# nanti), persis sebelum _start() di-trigger di background. Ini membuat UI
# langsung pindah ke tampilan "Memuat..." (bukan idle-text "Belum ada lagu")
# selama proses refill radio berjalan, lalu otomatis pindah ke PLAYING
# begitu _start() berhasil play_track().
#
# Catatan: ini BUG TERPISAH dari yang diperbaiki patch.sh sebelumnya
# (idle-flash saat ganti mode RADIO->QUEUE via klik artis Discover).
# Bug ini trigger-nya next-track DI DALAM mode radio itu sendiri, lewat
# code path yang berbeda (RadioMode.next(), bukan _on_set_mode()).
#
# Jalankan dari root project ytgui (folder yang berisi main.py).
# Aman dijalankan berkali-kali (idempotent).
# ============================================================================
set -euo pipefail

MARKER="PATCH-RADIO-EMPTY-QUEUE-01"

# ---------------------------------------------------------------------------
# 0. Validasi lokasi
# ---------------------------------------------------------------------------
if [[ ! -f "main.py" || ! -f "engine/radio_engine.py" ]]; then
    echo "[ERROR] Jalankan script ini dari root folder project ytgui (folder yang ada main.py)." >&2
    exit 1
fi

RADIO_PY="engine/radio_engine.py"

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"; else echo "[ERROR] python3 tidak ditemukan." >&2; exit 1; fi

if grep -q "$MARKER" "$RADIO_PY" 2>/dev/null; then
    echo "[SKIP] Patch sudah pernah diterapkan sebelumnya (marker $MARKER ditemukan). Tidak ada yang dilakukan."
    exit 0
fi

# ---------------------------------------------------------------------------
# 1. Backup
# ---------------------------------------------------------------------------
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".patch_radio_empty_backup_${TS}"
mkdir -p "$BACKUP_DIR/$(dirname "$RADIO_PY")"
cp "$RADIO_PY" "$BACKUP_DIR/$RADIO_PY"
echo "[INFO] Backup file asli disimpan di: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# 2. Apply patch
# ---------------------------------------------------------------------------
"$PY" - "$RADIO_PY" "$MARKER" <<'PYEOF'
import sys

radio_py, MARKER = sys.argv[1:3]

def M(s):
    return s.replace("__MARKER__", MARKER)

with open(radio_py, "r", encoding="utf-8") as fh:
    content = fh.read()

old = '''    async def next(self, controller: "PlaybackController") -> None:
        if self.state.radio_queue:
            track = self.state.radio_queue.popleft()
            # Kalau queue mulai tipis, pastikan standby sedang disiapkan
            if len(self.state.radio_queue) <= 5:
                _track_task(self._bg_tasks, self._ensure_standby(controller), name="radio_ensure_standby")
            await controller.play_track(track)
        else:
            # Queue habis — ambil dari standby atau fetch ulang
            _track_task(self._bg_tasks, self._start(controller), name="radio_refill")'''

new = M('''    async def next(self, controller: "PlaybackController") -> None:
        if self.state.radio_queue:
            track = self.state.radio_queue.popleft()
            # Kalau queue mulai tipis, pastikan standby sedang disiapkan
            if len(self.state.radio_queue) <= 5:
                _track_task(self._bg_tasks, self._ensure_standby(controller), name="radio_ensure_standby")
            await controller.play_track(track)
        else:
            # __MARKER__: Queue habis — _start() jalan di background (bisa
            # sampai ~20 detik kalau standby belum siap & harus fetch+resolve
            # ulang dari yt-dlp). Sebelumnya state (current_track/status)
            # dibiarkan apa adanya selama window itu -> frontend tidak
            # diberi tahu apa-apa, jadi UI nyangkut pada info lagu lama yang
            # sudah selesai (kelihatan idle/stuck), baru update mendadak
            # begitu _start() selesai. Sekarang: set status LOADING dan
            # broadcast QueueUpdatedEvent SEKARANG juga, supaya UI tahu
            # "lagi nyari lagu radio berikutnya" selama window itu, alih-alih
            # diam/stale.
            self.state.status = PlayerStatus.LOADING
            await controller.bus.publish(QueueUpdatedEvent())
            _track_task(self._bg_tasks, self._start(controller), name="radio_refill")''')

count = content.count(old)
if count != 1:
    print(f"[ERROR] Pola yang dicari ditemukan {count}x di {radio_py} (harus tepat 1x). "
          f"File mungkin sudah berubah dari versi yang diharapkan — patch dibatalkan.", file=sys.stderr)
    sys.exit(1)

content = content.replace(old, new)

with open(radio_py, "w", encoding="utf-8") as fh:
    fh.write(content)

print(f"[OK] Fix radio empty-queue idle-flash -> {radio_py}")
print("[DONE] Patch berhasil diterapkan.")
PYEOF

# ---------------------------------------------------------------------------
# 3. Verifikasi syntax
# ---------------------------------------------------------------------------
"$PY" -m py_compile "$RADIO_PY"
echo "[OK] Syntax valid: $RADIO_PY"

if ! grep -q "$MARKER" "$RADIO_PY"; then
    echo "[ERROR] Marker tidak ditemukan di $RADIO_PY setelah patch — sesuatu salah." >&2
    exit 1
fi
echo "[OK] Marker terverifikasi di $RADIO_PY"

echo ""
echo "============================================================"
echo " Patch berhasil diterapkan & terverifikasi: $RADIO_PY"
echo " Backup file asli ada di: $BACKUP_DIR"
echo ""
echo " Restart server (python main.py / start.sh)."
echo " Tidak perlu kill-switch lagi untuk patch ini karena yang"
echo " diubah murni file Python (server-side), bukan JS."
echo ""
echo " Yang berubah: saat radio_queue habis dan Radio harus fetch ulang"
echo " lagu (bisa beberapa detik di Termux), UI sekarang akan menampilkan"
echo " status 'Memuat...' alih-alih nyangkut di info lagu lama / idle text"
echo " yang membingungkan."
echo "============================================================"
