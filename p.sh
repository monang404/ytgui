#!/usr/bin/env bash
# ============================================================
# patch4_remove_hardcode.sh — Hapus hardcode fallback artis
# Jalankan dari root folder project:
#   bash patch4_remove_hardcode.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!!]${NC} $1"; }
error() { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

if [ ! -f "engine/radio_engine.py" ]; then
    error "Jalankan dari root folder ytgui-main"
fi

FILE="engine/radio_engine.py"

# Cek sudah dipatch belum
if ! grep -qF '_FALLBACK_ARTISTS' "$FILE"; then
    warn "Hardcode sudah dihapus sebelumnya, tidak ada yang perlu dilakukan."
    exit 0
fi

# Backup
cp "$FILE" "${FILE}.bak4"
info "Backup: ${FILE}.bak4"

python3 << PYEOF
import pathlib, re, sys

f = pathlib.Path("$FILE")
content = f.read_text()

# 1. Hapus baris konstanta _FALLBACK_ARTISTS
content = re.sub(
    r"^_FALLBACK_ARTISTS\s*=\s*\[.*?\]\n",
    "",
    content,
    flags=re.MULTILINE
)

# 2. Ganti blok fallback diam-diam dengan pesan error ke frontend
old = '''        if not self._seed_artists:
            import logging
            logging.getLogger(__name__).warning(
                "Tabel artists kosong. Jalankan import_artists.py"
            )
            self._seed_artists = list(_FALLBACK_ARTISTS)'''

new = '''        if not self._seed_artists:
            # Tidak ada fallback hardcode — DB harus diisi dulu
            # Error ini akan ditangkap oleh _start dan dikirim ke frontend
            raise RuntimeError(
                "Tabel artists kosong. Jalankan: python data/import_artists.py "
                "--db cache/library.db --json data/artists.json"
            )'''

if old not in content:
    print("ERROR: target string tidak ditemukan — file mungkin sudah dimodifikasi")
    sys.exit(1)

content = content.replace(old, new, 1)
f.write_text(content)
print("ok")
PYEOF

[ $? -ne 0 ] && error "Python patch gagal" || true

# 3. Patch _start agar tangkap RuntimeError dan kirim ke frontend
python3 << 'PYEOF'
import pathlib, sys

f = pathlib.Path("engine/radio_engine.py")
content = f.read_text()

old = '''        # Fetch cepat: ARTISTS_QUICK artis dulu, langsung putar
        try:
            quick_tracks = await asyncio.wait_for(
                self._gather_batch(max_artists=ARTISTS_QUICK),
                timeout=20.0
            )
        except (asyncio.TimeoutError, Exception):
            quick_tracks = []'''

new = '''        # Fetch cepat: ARTISTS_QUICK artis dulu, langsung putar
        try:
            quick_tracks = await asyncio.wait_for(
                self._gather_batch(max_artists=ARTISTS_QUICK),
                timeout=20.0
            )
        except RuntimeError as e:
            # DB artists kosong — kirim pesan jelas ke frontend
            await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
            await controller.bus.publish(LogMessageEvent(
                message=f"Radio: {e}", room_id=controller.room_id
            ))
            return
        except (asyncio.TimeoutError, Exception):
            quick_tracks = []'''

if old not in content:
    print("ERROR: target _start tidak ditemukan")
    sys.exit(1)

content = content.replace(old, new, 1)
f.write_text(content)
print("ok")
PYEOF

[ $? -ne 0 ] && error "Python patch _start gagal" || true

# Verifikasi
echo ""
echo "─── Verifikasi ───────────────────────────────────────"

grep -q '_FALLBACK_ARTISTS' "$FILE" \
    && error "✗ Hardcode masih ada!" \
    || info "✓ Hardcode _FALLBACK_ARTISTS sudah dihapus"

grep -q 'Tabel artists kosong. Jalankan:' "$FILE" \
    && info "✓ Error message proper sudah ada" \
    || error "✗ Error message tidak ditemukan"

grep -q 'except RuntimeError as e:' "$FILE" \
    && info "✓ RuntimeError handler di _start sudah ada" \
    || error "✗ RuntimeError handler tidak ditemukan"

echo ""
info "Patch 4 selesai."
echo ""
echo "Sekarang kalau artists DB kosong, frontend akan tampilkan pesan:"
echo -e "  ${YELLOW}Radio: Tabel artists kosong. Jalankan: python data/import_artists.py ...${NC}"
echo "Bukan diam-diam pakai Sheila On 7 lagi 😄"
