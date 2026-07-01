#!/usr/bin/env bash
# ============================================================================
# patch_all_remaining.sh — ytgui: jalankan SEMUA patch yang masih tersisa
# dalam satu kali eksekusi:
#
#   1. SW Kill-switch     (PATCH-SW-KILLSWITCH-01)
#      Bersihkan Service Worker zombie yang nge-cache JS lama di browser.
#   2. Radio empty-queue  (PATCH-RADIO-EMPTY-QUEUE-01)
#      Fix idle-flash saat klik Next di Radio pas radio_queue lagi kosong.
#   3. yt-dlp timeout      (PATCH-YTDLP-RESOLVE-TIMEOUT-01)
#      Fix yt-dlp resolve yang bisa hang tanpa batas waktu (penyebab utama
#      "klik artis Discover sambil lagu lain main -> looping idle").
#
# PENTING: Jalankan dari root project ytgui ASLI di Termux (folder yang ada
# main.py), BUKAN dari folder hasil unzip/sandbox. Cek dulu dengan `pwd`
# dan `ls main.py` sebelum menjalankan kalau ragu.
#
# Aman dijalankan berkali-kali (masing-masing bagian idempotent, akan
# di-skip kalau sudah pernah dipatch sebelumnya).
# ============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Validasi lokasi (cek di awal, sebelum bagian manapun jalan)
# ---------------------------------------------------------------------------
if [[ ! -f "main.py" || ! -d "web/static" || ! -f "engine/radio_engine.py" || ! -f "config.py" ]]; then
    echo "[ERROR] Jalankan script ini dari root folder project ytgui (folder yang ada main.py)." >&2
    echo "[ERROR] Lokasi sekarang: $(pwd)" >&2
    exit 1
fi

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"; else echo "[ERROR] python3 tidak ditemukan." >&2; exit 1; fi

echo "============================================================"
echo " ytgui — patch_all_remaining.sh"
echo " Lokasi: $(pwd)"
echo "============================================================"
echo ""

# ============================================================================
# BAGIAN 1: SW Kill-switch
# ============================================================================
echo "── [1/3] SW Kill-switch ──────────────────────────────────"
MARKER1="PATCH-SW-KILLSWITCH-01"
INDEX_HTML="web/static/index.html"

if [[ ! -f "$INDEX_HTML" ]]; then
    echo "[ERROR] File tidak ditemukan: $INDEX_HTML" >&2
    exit 1
fi

if grep -q "$MARKER1" "$INDEX_HTML" 2>/dev/null; then
    echo "[SKIP] Sudah pernah dipasang sebelumnya (marker ditemukan)."
else
    TS="$(date +%Y%m%d_%H%M%S)"
    BACKUP_DIR=".patch_swkill_backup_${TS}"
    mkdir -p "$BACKUP_DIR/$(dirname "$INDEX_HTML")"
    cp "$INDEX_HTML" "$BACKUP_DIR/$INDEX_HTML"
    echo "[INFO] Backup: $BACKUP_DIR"

    "$PY" - "$INDEX_HTML" "$MARKER1" <<'PYEOF'
import sys
index_html, MARKER = sys.argv[1:3]
def M(s): return s.replace("__MARKER__", MARKER)

with open(index_html, "r", encoding="utf-8") as fh:
    content = fh.read()

anchor = '<script src="/static/js/config.js" defer></script>'
count = content.count(anchor)
if count != 1:
    print(f"[ERROR] Anchor tag config.js ditemukan {count}x (harus tepat 1x). Patch dibatalkan.", file=sys.stderr)
    sys.exit(1)

snippet = M('''<script>
    // __MARKER__: Service Worker registration sudah di-DISABLE di main.js,
    // tapi SW lama yang sempat ter-register di sesi sebelumnya tetap aktif
    // di browser dan terus melayani JS/CSS dari cache lamanya sendiri,
    // lepas dari perubahan apapun di server/disk. Jalankan SEKALI di awal
    // load: unregister semua SW yang nyangkut + hapus semua Cache Storage,
    // lalu kalau memang ada yang dihapus, force reload sekali.
    (function () {
        "use strict";
        if (!('serviceWorker' in navigator)) return;
        var didCleanup = false;

        var unregisterAll = navigator.serviceWorker.getRegistrations()
            .then(function (regs) {
                if (!regs.length) return;
                didCleanup = true;
                return Promise.all(regs.map(function (r) { return r.unregister(); }));
            })
            .catch(function (e) { console.warn('[sw-kill] unregister failed:', e); });

        var clearCaches = ('caches' in window)
            ? caches.keys().then(function (keys) {
                if (!keys.length) return;
                didCleanup = true;
                return Promise.all(keys.map(function (k) { return caches.delete(k); }));
            }).catch(function (e) { console.warn('[sw-kill] cache clear failed:', e); })
            : Promise.resolve();

        Promise.all([unregisterAll, clearCaches]).then(function () {
            if (didCleanup && !sessionStorage.getItem('sw_killswitch_reloaded')) {
                console.log('[sw-kill] stale service worker / cache dibersihkan, reload sekali...');
                sessionStorage.setItem('sw_killswitch_reloaded', '1');
                location.reload();
            } else if (didCleanup) {
                console.log('[sw-kill] dibersihkan (reload sudah pernah dilakukan sesi ini).');
            }
        });
    })();
    </script>

    ''') + anchor

content = content.replace(anchor, snippet)
with open(index_html, "w", encoding="utf-8") as fh:
    fh.write(content)
print(f"[OK] Kill-switch terpasang -> {index_html}")
PYEOF

    if ! grep -q "$MARKER1" "$INDEX_HTML"; then
        echo "[ERROR] Marker tidak ditemukan setelah patch — gagal." >&2
        exit 1
    fi
    echo "[OK] Bagian 1 selesai & terverifikasi."
fi
echo ""

# ============================================================================
# BAGIAN 2: Radio empty-queue fix
# ============================================================================
echo "── [2/3] Radio empty-queue fix ───────────────────────────"
MARKER2="PATCH-RADIO-EMPTY-QUEUE-01"
RADIO_PY="engine/radio_engine.py"

if grep -q "$MARKER2" "$RADIO_PY" 2>/dev/null; then
    echo "[SKIP] Sudah pernah dipasang sebelumnya (marker ditemukan)."
else
    TS="$(date +%Y%m%d_%H%M%S)"
    BACKUP_DIR=".patch_radio_empty_backup_${TS}"
    mkdir -p "$BACKUP_DIR/$(dirname "$RADIO_PY")"
    cp "$RADIO_PY" "$BACKUP_DIR/$RADIO_PY"
    echo "[INFO] Backup: $BACKUP_DIR"

    "$PY" - "$RADIO_PY" "$MARKER2" <<'PYEOF'
import sys
radio_py, MARKER = sys.argv[1:3]
def M(s): return s.replace("__MARKER__", MARKER)

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
            # sampai ~20 detik). Set status LOADING & broadcast SEKARANG
            # supaya UI tidak nyangkut di info lagu lama selama window itu.
            self.state.status = PlayerStatus.LOADING
            await controller.bus.publish(QueueUpdatedEvent())
            _track_task(self._bg_tasks, self._start(controller), name="radio_refill")''')

count = content.count(old)
if count != 1:
    print(f"[ERROR] Pola ditemukan {count}x (harus tepat 1x). Patch dibatalkan.", file=sys.stderr)
    sys.exit(1)

content = content.replace(old, new)
with open(radio_py, "w", encoding="utf-8") as fh:
    fh.write(content)
print(f"[OK] Fix radio empty-queue -> {radio_py}")
PYEOF

    "$PY" -m py_compile "$RADIO_PY"
    if ! grep -q "$MARKER2" "$RADIO_PY"; then
        echo "[ERROR] Marker tidak ditemukan setelah patch — gagal." >&2
        exit 1
    fi
    echo "[OK] Bagian 2 selesai, syntax valid & terverifikasi."
fi
echo ""

# ============================================================================
# BAGIAN 3: yt-dlp resolve timeout
# ============================================================================
echo "── [3/3] yt-dlp resolve timeout ──────────────────────────"
MARKER3="PATCH-YTDLP-RESOLVE-TIMEOUT-01"
CONFIG_PY="config.py"
YTDLP_PY="engine/ytdlp_client.py"

if grep -q "$MARKER3" "$YTDLP_PY" 2>/dev/null; then
    echo "[SKIP] Sudah pernah dipasang sebelumnya (marker ditemukan)."
else
    TS="$(date +%Y%m%d_%H%M%S)"
    BACKUP_DIR=".patch_ytdlp_timeout_backup_${TS}"
    for f in "$CONFIG_PY" "$YTDLP_PY"; do
        mkdir -p "$BACKUP_DIR/$(dirname "$f")"
        cp "$f" "$BACKUP_DIR/$f"
    done
    echo "[INFO] Backup: $BACKUP_DIR"

    "$PY" - "$CONFIG_PY" "$YTDLP_PY" "$MARKER3" <<'PYEOF'
import sys
config_py, ytdlp_py, MARKER = sys.argv[1:4]
def M(s): return s.replace("__MARKER__", MARKER)

def replace_exact(path, old, new, label):
    old = M(old); new = M(new)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    count = content.count(old)
    if count != 1:
        print(f"[ERROR] {label}: pola ditemukan {count}x di {path}. Patch dibatalkan.", file=sys.stderr)
        sys.exit(1)
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"[OK] {label} -> {path}")

old_cfg = "STREAM_URL_TTL_SEC = 21600"
new_cfg = M('''STREAM_URL_TTL_SEC = 21600
# __MARKER__: yt-dlp.get_stream_url() sebelumnya tidak punya batas waktu,
# bisa hang tanpa batas tanpa pernah throw -> play_track() nyangkut
# selamanya di LOADING. Timeout ini memaksa gagal cepat & jelas.
YTDLP_RESOLVE_TIMEOUT_SEC = 25''')
replace_exact(config_py, old_cfg, new_cfg, "Tambah YTDLP_RESOLVE_TIMEOUT_SEC")

old_import = "from config import CACHE_DIR"
new_import = "from config import CACHE_DIR, YTDLP_RESOLVE_TIMEOUT_SEC"
replace_exact(ytdlp_py, old_import, new_import, "Import YTDLP_RESOLVE_TIMEOUT_SEC")

old_resolve = '''        url = f"https://www.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(self._executor, self._extract_sync, url, opts)
            if info:
                stream_url = self._pick_audio_url(info)
                if stream_url:
                    return stream_url
            raise RuntimeError(f"yt-dlp returned no stream URL for {video_id}")
        except RuntimeError:
            raise
        except Exception as e:
            _log.error(f"get_stream_url failed for {video_id}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Gagal mengambil stream URL untuk {video_id}: {e}") from e'''

new_resolve = M('''        url = f"https://www.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        try:
            # __MARKER__: dibungkus timeout supaya hang network tidak
            # bikin play_track() nyangkut selamanya tanpa sinyal error.
            info = await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._extract_sync, url, opts),
                timeout=YTDLP_RESOLVE_TIMEOUT_SEC,
            )
            if info:
                stream_url = self._pick_audio_url(info)
                if stream_url:
                    return stream_url
            raise RuntimeError(f"yt-dlp returned no stream URL for {video_id}")
        except asyncio.TimeoutError:
            _log.error(f"get_stream_url timed out after {YTDLP_RESOLVE_TIMEOUT_SEC}s for {video_id}")
            raise RuntimeError(
                f"Timeout ({YTDLP_RESOLVE_TIMEOUT_SEC}s) saat mengambil stream URL untuk {video_id}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            _log.error(f"get_stream_url failed for {video_id}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Gagal mengambil stream URL untuk {video_id}: {e}") from e''')

replace_exact(ytdlp_py, old_resolve, new_resolve, "Bungkus get_stream_url dengan timeout")
print("[DONE] Bagian 3 selesai.")
PYEOF

    "$PY" -m py_compile "$CONFIG_PY" "$YTDLP_PY"
    for f in "$CONFIG_PY" "$YTDLP_PY"; do
        if ! grep -q "$MARKER3" "$f"; then
            echo "[ERROR] Marker tidak ditemukan di $f setelah patch — gagal." >&2
            exit 1
        fi
    done
    echo "[OK] Bagian 3 selesai, syntax valid & terverifikasi."
fi
echo ""

# ============================================================================
# Ringkasan akhir
# ============================================================================
echo "============================================================"
echo " SEMUA PATCH SELESAI DIPROSES."
echo ""
echo " Verifikasi marker di file live (bukan backup):"
for m in "$MARKER1" "$MARKER2" "$MARKER3"; do
    found=$(grep -rl "$m" --include="*.py" --include="*.js" --include="*.html" . 2>/dev/null | grep -v "_backup_" || true)
    if [[ -n "$found" ]]; then
        echo "   [OK] $m -> $found"
    else
        echo "   [MISSING] $m -> TIDAK DITEMUKAN, cek manual!"
    fi
done
echo ""
echo " Langkah selanjutnya:"
echo "   1. Restart server (python main.py / start.sh)"
echo "   2. Buka ytgui di Chrome Android SEKALI seperti biasa"
echo "      (kill-switch akan auto-bersihkan SW lama + reload sekali)"
echo "   3. Test ulang: Radio -> next saat queue mepet/kosong,"
echo "      Discover -> klik artis lain saat lagu lain masih main"
echo "============================================================"
