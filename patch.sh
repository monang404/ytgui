#!/usr/bin/env bash
# ============================================================
# patch_ytgui.sh — Patch Radio Mode untuk ytgui-main
# Jalankan dari root folder project:
#   bash patch_ytgui.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!!]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

# ── Deteksi root project ──────────────────────────────────
if [ ! -f "engine/playback_controller.py" ]; then
    error "Jalankan script ini dari root folder ytgui-main (yang ada folder engine/, server/, dll)"
fi
info "Root project ditemukan: $(pwd)"

# ── Backup ───────────────────────────────────────────────
BACKUP_DIR=".patch_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp engine/playback_controller.py "$BACKUP_DIR/"
cp engine/radio_engine.py        "$BACKUP_DIR/"
cp server/app.py                 "$BACKUP_DIR/"
info "Backup disimpan di: $BACKUP_DIR/"

# ============================================================
# PATCH 1 — engine/playback_controller.py
# Tambah PlayerStatus.LOADING sebelum on_activated agar
# frontend tidak stuck di state kosong saat radio mulai fetch
# ============================================================
FILE="engine/playback_controller.py"
TARGET='                if mode == PlaybackMode.RADIO:
                    await self.radio_mode.on_activated(self)'
REPLACE='                if mode == PlaybackMode.RADIO:
                    self.state.status = PlayerStatus.LOADING  # B-FIX: signal ke frontend bahwa radio sedang fetch
                    await self.radio_mode.on_activated(self)'

if grep -qF "B-FIX: signal ke frontend" "$FILE"; then
    warn "PATCH 1 sudah diterapkan sebelumnya, dilewati."
elif grep -qF 'await self.radio_mode.on_activated(self)' "$FILE"; then
    python3 - "$FILE" "$TARGET" "$REPLACE" <<'PYEOF'
import sys, pathlib
f, target, replace = sys.argv[1], sys.argv[2], sys.argv[3]
content = pathlib.Path(f).read_text()
if target not in content:
    print(f"TARGET tidak ditemukan di {f}")
    sys.exit(1)
pathlib.Path(f).write_text(content.replace(target, replace, 1))
PYEOF
    info "PATCH 1 diterapkan → $FILE"
else
    error "PATCH 1: target string tidak ditemukan di $FILE. File mungkin sudah dimodifikasi."
fi

# ============================================================
# PATCH 2 — engine/radio_engine.py
# Tambah QueueUpdatedEvent broadcast saat _start gagal total
# agar frontend keluar dari status LOADING
# ============================================================
FILE="engine/radio_engine.py"
TARGET='        else:
            await controller.bus.publish(LogMessageEvent(
                message="Radio: Tidak ada hasil ditemukan.", room_id=controller.room_id
            ))'
REPLACE='        else:
            # Broadcast state ulang agar frontend tidak stuck di "loading" tanpa info
            await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
            await controller.bus.publish(LogMessageEvent(
                message="Radio: Tidak ada hasil ditemukan.", room_id=controller.room_id
            ))'

if grep -qF 'Broadcast state ulang agar frontend tidak stuck' "$FILE"; then
    warn "PATCH 2 sudah diterapkan sebelumnya, dilewati."
elif grep -qF 'message="Radio: Tidak ada hasil ditemukan."' "$FILE"; then
    python3 - "$FILE" "$TARGET" "$REPLACE" <<'PYEOF'
import sys, pathlib
f, target, replace = sys.argv[1], sys.argv[2], sys.argv[3]
content = pathlib.Path(f).read_text()
if target not in content:
    print(f"TARGET tidak ditemukan di {f}")
    sys.exit(1)
pathlib.Path(f).write_text(content.replace(target, replace, 1))
PYEOF
    info "PATCH 2 diterapkan → $FILE"
else
    error "PATCH 2: target string tidak ditemukan di $FILE. File mungkin sudah dimodifikasi."
fi

# ============================================================
# PATCH 3 — server/app.py
# Prefetch stream URL juga untuk radio_queue, bukan hanya queue
# ============================================================
FILE="server/app.py"
TARGET='        # B-03: prefetch URL untuk track BERIKUTNYA di queue, bukan track yang baru main
        # (current track sudah di-resolve oleh CacheResolver sesaat sebelumnya)
        if room.state.queue:
            _next = room.state.queue[0]
            if _next and _next.video_id:
                safe_create_task(_prefetch_stream_url(_next.video_id), name=f"prefetch_next_{_next.video_id}")'
REPLACE='        # B-03: prefetch URL untuk track BERIKUTNYA di queue atau radio_queue
        # (current track sudah di-resolve oleh CacheResolver sesaat sebelumnya)
        _next = None
        if room.state.queue:
            _next = room.state.queue[0]
        elif room.state.radio_queue:
            _next = room.state.radio_queue[0]
        if _next and _next.video_id:
            safe_create_task(_prefetch_stream_url(_next.video_id), name=f"prefetch_next_{_next.video_id}")'

if grep -qF 'elif room.state.radio_queue:' "$FILE"; then
    warn "PATCH 3 sudah diterapkan sebelumnya, dilewati."
elif grep -qF 'B-03: prefetch URL untuk track BERIKUTNYA di queue' "$FILE"; then
    python3 - "$FILE" "$TARGET" "$REPLACE" <<'PYEOF'
import sys, pathlib
f, target, replace = sys.argv[1], sys.argv[2], sys.argv[3]
content = pathlib.Path(f).read_text()
if target not in content:
    print(f"TARGET tidak ditemukan di {f}")
    sys.exit(1)
pathlib.Path(f).write_text(content.replace(target, replace, 1))
PYEOF
    info "PATCH 3 diterapkan → $FILE"
else
    error "PATCH 3: target string tidak ditemukan di $FILE. File mungkin sudah dimodifikasi."
fi

# ── Verifikasi ────────────────────────────────────────────
echo ""
echo "─── Verifikasi ───────────────────────────────────────"
grep -q "B-FIX: signal ke frontend"            engine/playback_controller.py \
    && info "✓ playback_controller.py — LOADING sebelum on_activated" \
    || error "✗ playback_controller.py — patch tidak ditemukan"

grep -q 'Broadcast state ulang agar frontend tidak stuck' engine/radio_engine.py \
    && info "✓ radio_engine.py — QueueUpdatedEvent saat gagal fetch" \
    || error "✗ radio_engine.py — patch tidak ditemukan"

grep -q 'elif room.state.radio_queue:'          server/app.py \
    && info "✓ server/app.py — prefetch juga radio_queue" \
    || error "✗ server/app.py — patch tidak ditemukan"

echo ""
info "Semua patch berhasil diterapkan."
echo -e "  Untuk rollback: ${YELLOW}cp $BACKUP_DIR/* engine/ && cp $BACKUP_DIR/app.py server/${NC}"
