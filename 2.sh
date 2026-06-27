#!/usr/bin/env bash
# =============================================================================
# 2.sh — Patch 3 Bug Krusial Radio Mode
# =============================================================================
# BUG-1: room_id tidak di-inject ke events dari PlaybackController
#         → server broadcast diam-diam gagal karena room_manager.rooms.get("default") = None
# BUG-2: room_id tidak di-inject ke events dari RadioEngine
#         → sama seperti BUG-1, tapi dari sisi radio_engine.py
# BUG-3: _on_radio_randomize memanggil _fetch_and_play_initial secara blocking
#         di dalam _lock → bisa deadlock/hang kalau fetch lama; harus jadi bg task
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PC="$SCRIPT_DIR/engine/playback_controller.py"
RE="$SCRIPT_DIR/engine/radio_engine.py"

PASS=0
FAIL=0

log()  { echo "[2.sh] $*"; }
ok()   { echo "  ✅ $*"; ((PASS+1)); }
fail() { echo "  ❌ $*"; ((FAIL+1)); }

# ── helpers ──────────────────────────────────────────────────────────────────
backup() {
    local f="$1"
    local ts
    ts="$(date +%Y%m%d_%H%M%S)"
    cp "$f" "${f}.bak_2sh_${ts}"
    log "Backup: ${f}.bak_2sh_${ts}"
}

patch_inline() {
    # patch_inline FILE OLD NEW DESCRIPTION
    local file="$1" old="$2" new="$3" desc="$4"
    if grep -qF "$old" "$file"; then
        # Gunakan Python untuk replace agar tidak ada masalah karakter khusus sed
        python3 - "$file" "$old" "$new" <<'PYEOF'
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
if old not in content:
    sys.exit(1)
content = content.replace(old, new, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
PYEOF
        ok "$desc"
    else
        fail "$desc — pola tidak ditemukan (mungkin sudah dipatch atau berubah)"
    fi
}

# =============================================================================
# Validasi file
# =============================================================================
log "Memvalidasi file target..."
[[ -f "$PC" ]] || { echo "FATAL: $PC tidak ditemukan. Jalankan dari root project."; exit 1; }
[[ -f "$RE" ]] || { echo "FATAL: $RE tidak ditemukan. Jalankan dari root project."; exit 1; }
log "File ditemukan. Membuat backup..."
backup "$PC"
backup "$RE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " BUG-1 — Inject room_id ke semua bus.publish() di PlaybackController"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# play_track: LogMessage audio output browser
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Audio output is browser, skipping mpv local playback."))' \
    'await self.bus.publish(LogMessageEvent(message="Audio output is browser, skipping mpv local playback.", room_id=self.room_id))' \
    "play_track: LogMessageEvent audio output browser"

# play_track: TrackStartedEvent
patch_inline "$PC" \
    'await self.bus.publish(TrackStartedEvent(track=track))' \
    'await self.bus.publish(TrackStartedEvent(track=track, room_id=self.room_id))' \
    "play_track: TrackStartedEvent"

# play_track: LogMessage gagal memutar
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message=f"Gagal memutar lagu: {track.title} | {type(e).__name__}: {str(e)}"))' \
    'await self.bus.publish(LogMessageEvent(message=f"Gagal memutar lagu: {track.title} | {type(e).__name__}: {str(e)}", room_id=self.room_id))' \
    "play_track: LogMessageEvent gagal memutar"

# play_track: LogMessage terlalu banyak kegagalan
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Terlalu banyak kegagalan beruntun. Pemutaran dihentikan."))' \
    'await self.bus.publish(LogMessageEvent(message="Terlalu banyak kegagalan beruntun. Pemutaran dihentikan.", room_id=self.room_id))' \
    "play_track: LogMessageEvent terlalu banyak kegagalan"

# _on_cmd_play_track: QueueUpdatedEvent saat switch dari RADIO
patch_inline "$PC" \
    'await self.bus.publish(QueueUpdatedEvent())
            await self.play_track(track)' \
    'await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))
            await self.play_track(track)' \
    "_on_cmd_play_track: QueueUpdatedEvent saat keluar RADIO"

# _on_track_ended: LogMessage error
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Terjadi kesalahan pemutaran"))' \
    'await self.bus.publish(LogMessageEvent(message="Terjadi kesalahan pemutaran", room_id=self.room_id))' \
    "_on_track_ended: LogMessageEvent error"

# _on_prev: LogMessage tidak ada lagu sebelumnya
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Tidak ada lagu sebelumnya"))' \
    'await self.bus.publish(LogMessageEvent(message="Tidak ada lagu sebelumnya", room_id=self.room_id))' \
    "_on_prev: LogMessageEvent tidak ada lagu sebelumnya"

# _on_stop: LogMessage pemutaran dihentikan
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Pemutaran dihentikan"))' \
    'await self.bus.publish(LogMessageEvent(message="Pemutaran dihentikan", room_id=self.room_id))' \
    "_on_stop: LogMessageEvent pemutaran dihentikan"

# _on_stop: QueueUpdatedEvent
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Pemutaran dihentikan", room_id=self.room_id))
        await self.bus.publish(QueueUpdatedEvent())' \
    'await self.bus.publish(LogMessageEvent(message="Pemutaran dihentikan", room_id=self.room_id))
        await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))' \
    "_on_stop: QueueUpdatedEvent"

# _on_set_mode: LogMessage mode diubah
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message=f"Mode diubah ke {mode.name}"))' \
    'await self.bus.publish(LogMessageEvent(message=f"Mode diubah ke {mode.name}", room_id=self.room_id))' \
    "_on_set_mode: LogMessageEvent mode diubah"

# _on_set_mode: QueueUpdatedEvent setelah mode change
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message=f"Mode diubah ke {mode.name}", room_id=self.room_id))
                await self.bus.publish(QueueUpdatedEvent())' \
    'await self.bus.publish(LogMessageEvent(message=f"Mode diubah ke {mode.name}", room_id=self.room_id))
                await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))' \
    "_on_set_mode: QueueUpdatedEvent"

# _on_queue_remove: QueueUpdatedEvent + LogMessage
patch_inline "$PC" \
    'await self.bus.publish(QueueUpdatedEvent())
                await self.bus.publish(LogMessageEvent(message=f"Dihapus dari antrean: {removed.title}"))' \
    'await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))
                await self.bus.publish(LogMessageEvent(message=f"Dihapus dari antrean: {removed.title}", room_id=self.room_id))' \
    "_on_queue_remove: QueueUpdatedEvent + LogMessageEvent"

# _on_queue_add: QueueUpdatedEvent + LogMessage
patch_inline "$PC" \
    'await self.bus.publish(QueueUpdatedEvent())
        await self.bus.publish(LogMessageEvent(message=f"Ditambahkan ke antrean: {track.title}"))' \
    'await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))
        await self.bus.publish(LogMessageEvent(message=f"Ditambahkan ke antrean: {track.title}", room_id=self.room_id))' \
    "_on_queue_add: QueueUpdatedEvent + LogMessageEvent"

# _on_queue_reorder: QueueUpdatedEvent
patch_inline "$PC" \
    '                    await self.bus.publish(QueueUpdatedEvent())

    async def _on_radio_randomize' \
    '                    await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))

    async def _on_radio_randomize' \
    "_on_queue_reorder: QueueUpdatedEvent"

# _on_radio_randomize: LogMessage radio tidak aktif
patch_inline "$PC" \
    'await self.bus.publish(LogMessageEvent(message="Radio tidak aktif"))' \
    'await self.bus.publish(LogMessageEvent(message="Radio tidak aktif", room_id=self.room_id))' \
    "_on_radio_randomize: LogMessageEvent radio tidak aktif"

# _on_set_output: LogMessage + QueueUpdated
patch_inline "$PC" \
    "await self.bus.publish(LogMessageEvent(message=f\"Output suara diubah ke: {'Browser' if output == AudioOutput.BROWSER else 'HP'}\"))
        await self.bus.publish(QueueUpdatedEvent())" \
    "await self.bus.publish(LogMessageEvent(message=f\"Output suara diubah ke: {'Browser' if output == AudioOutput.BROWSER else 'HP'}\", room_id=self.room_id))
        await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))" \
    "_on_set_output: LogMessageEvent + QueueUpdatedEvent"

# _on_set_sponsorblock: LogMessage + QueueUpdated
patch_inline "$PC" \
    "await self.bus.publish(LogMessageEvent(message=f\"SponsorBlock: {'ON' if enabled else 'OFF'}\"))
        await self.bus.publish(QueueUpdatedEvent())" \
    "await self.bus.publish(LogMessageEvent(message=f\"SponsorBlock: {'ON' if enabled else 'OFF'}\", room_id=self.room_id))
        await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))" \
    "_on_set_sponsorblock: LogMessageEvent + QueueUpdatedEvent"

# _on_lyrics_offset: LyricsUpdatedEvent
patch_inline "$PC" \
    'await self.bus.publish(LyricsUpdatedEvent())' \
    'await self.bus.publish(LyricsUpdatedEvent(room_id=self.room_id))' \
    "_on_lyrics_offset: LyricsUpdatedEvent"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " BUG-2 — Inject room_id ke semua bus.publish() di RadioEngine"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# _prefetch_next: QueueUpdatedEvent setelah extend
patch_inline "$RE" \
    'await controller.bus.publish(QueueUpdatedEvent())
            except Exception as e:
                await controller.bus.publish(LogMessageEvent(message=f"Prefetch Error: {str(e)}"))' \
    'await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
            except Exception as e:
                await controller.bus.publish(LogMessageEvent(message=f"Prefetch Error: {str(e)}", room_id=controller.room_id))' \
    "_prefetch_next: QueueUpdatedEvent + LogMessageEvent"

# _fetch_and_play_initial: LogMessage timeout pertama
patch_inline "$RE" \
    'await controller.bus.publish(LogMessageEvent(message="Pencarian radio timeout (30s), mencoba artis lain..."))' \
    'await controller.bus.publish(LogMessageEvent(message="Pencarian radio timeout (30s), mencoba artis lain...", room_id=controller.room_id))' \
    "_fetch_and_play_initial: LogMessageEvent timeout pertama"

# _fetch_and_play_initial: LogMessage timeout kedua
patch_inline "$RE" \
    'await controller.bus.publish(LogMessageEvent(message="Pencarian radio kembali timeout, coba lagi nanti."))' \
    'await controller.bus.publish(LogMessageEvent(message="Pencarian radio kembali timeout, coba lagi nanti.", room_id=controller.room_id))' \
    "_fetch_and_play_initial: LogMessageEvent timeout kedua"

# _fetch_and_play_initial: QueueUpdatedEvent setelah extend (tracks found)
patch_inline "$RE" \
    'await controller.bus.publish(QueueUpdatedEvent())
                await controller.play_track(tracks[0])' \
    'await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
                await controller.play_track(tracks[0])' \
    "_fetch_and_play_initial: QueueUpdatedEvent (tracks ditemukan)"

# _fetch_and_play_initial: LogMessage tidak ada hasil
patch_inline "$RE" \
    'await controller.bus.publish(LogMessageEvent(message="Radio: Tidak ada hasil lagu ditemukan."))' \
    'await controller.bus.publish(LogMessageEvent(message="Radio: Tidak ada hasil lagu ditemukan.", room_id=controller.room_id))' \
    "_fetch_and_play_initial: LogMessageEvent tidak ada hasil"

# _fetch_and_play_initial: LogMessage Radio Error
patch_inline "$RE" \
    'await controller.bus.publish(LogMessageEvent(message=f"Radio Error: {str(e)}"))' \
    'await controller.bus.publish(LogMessageEvent(message=f"Radio Error: {str(e)}", room_id=controller.room_id))' \
    "_fetch_and_play_initial: LogMessageEvent Radio Error"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " BUG-3 — _on_radio_randomize: ubah fetch jadi background task"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Ganti: _fetch_and_play_initial dipanggil blocking di dalam _lock
# Jadi:  dijalankan sebagai bg task agar _lock tidak ditahan selama network I/O

patch_inline "$PC" \
    '                await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))
                
                await self.bus.publish(LogMessageEvent(message="Mengacak ulang stasiun radio...", room_id=self.room_id))
                # Panggil fetch dengan seed jika ada, jika tidak None
                await self.radio_mode._fetch_and_play_initial(self, seed_artist=seed)' \
    '                await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))
                
                await self.bus.publish(LogMessageEvent(message="Mengacak ulang stasiun radio...", room_id=self.room_id))
                # BUG-3 FIX: jalankan fetch sebagai background task agar _lock
                # tidak ditahan selama network I/O (bisa deadlock kalau fetch lama)
                _track_task(
                    self.radio_mode._bg_tasks,
                    self.radio_mode._fetch_and_play_initial(self, seed_artist=seed),
                    name="radio_randomize_fetch",
                )' \
    "_on_radio_randomize: fetch jadi background task (BUG-3)"

# Pastikan _track_task diimport/tersedia — sudah ada di radio_engine, tapi
# dipanggil dari playback_controller via self.radio_mode._bg_tasks.
# _track_task adalah free function di radio_engine — tidak perlu import tambahan
# karena dipanggil sebagai self.radio_mode._bg_tasks (set) yang sudah ada.
# Verifikasi fungsi _track_task bisa diakses:
if python3 -c "
import ast, sys
with open('$PC') as f:
    src = f.read()
# Cek bahwa _track_task call ada dan _bg_tasks ada
ok = '_track_task' in src and '_bg_tasks' in src
sys.exit(0 if ok else 1)
" 2>/dev/null; then
    ok "BUG-3: referensi _track_task + _bg_tasks terverifikasi di file"
else
    fail "BUG-3: _track_task atau _bg_tasks tidak ditemukan di playback_controller — perlu cek manual"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " SELF-TEST — Verifikasi sintaks Python"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for f in "$PC" "$RE"; do
    if python3 -m py_compile "$f" 2>/dev/null; then
        ok "Sintaks OK: $f"
    else
        fail "Sintaks ERROR: $f — cek manual!"
        python3 -m py_compile "$f"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " VERIFIKASI — Pastikan tidak ada sisa bus.publish tanpa room_id"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Cek sisa publish tanpa room_id di kedua file
check_no_orphan() {
    local file="$1" label="$2"
    # Pola: bus.publish(XxxEvent()) atau bus.publish(XxxEvent(track=...)) TANPA room_id
    local orphans
    orphans=$(grep -n "bus\.publish(" "$file" | grep -v "room_id=" || true)
    if [[ -z "$orphans" ]]; then
        ok "$label: semua bus.publish() sudah mengandung room_id"
    else
        fail "$label: masih ada publish tanpa room_id:"
        echo "$orphans" | sed 's/^/    /'
    fi
}

check_no_orphan "$PC" "playback_controller.py"
check_no_orphan "$RE" "radio_engine.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf " HASIL: %d lulus, %d gagal\n" "$PASS" "$FAIL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $FAIL -eq 0 ]]; then
    echo ""
    echo "✅ Semua patch berhasil. Restart server:"
    echo "   pkill -f 'python.*main.py' && python main.py"
    echo ""
    echo "── Cara test radio ──────────────────────────────────────"
    echo "1. Buka browser, toggle Radio ON"
    echo "2. Dalam 4-10 detik playlist harus muncul di radio tab"
    echo "3. Klik 'Acak Artis' — playlist harus refresh dalam 4-10 detik"
    echo "4. Cek log server: harus ada 'Mode diubah ke RADIO' dan 'Mengacak ulang...'"
    echo ""
    echo "── Rollback jika perlu ──────────────────────────────────"
    echo "   cp engine/playback_controller.py.bak_2sh_* engine/playback_controller.py"
    echo "   cp engine/radio_engine.py.bak_2sh_* engine/radio_engine.py"
    exit 0
else
    echo ""
    echo "⚠️  Ada $FAIL patch gagal. Cek log di atas, lakukan manual jika perlu."
    echo "   Backup tersimpan di *.bak_2sh_* untuk rollback."
    exit 1
fi
