#!/usr/bin/env bash
# ============================================================================
# patch_ytdlp_timeout.sh — ytgui: tambah timeout ke yt-dlp resolve supaya
# tidak hang tanpa batas (penyebab "stuck idle/loop" tanpa pesan error jelas)
#
# Bug: engine/ytdlp_client.py -> get_stream_url() memanggil
# loop.run_in_executor(...) TANPA timeout sama sekali. Kalau network
# Termux/Android lambat atau flaky, panggilan yt-dlp ke YouTube bisa hang
# untuk waktu yang sangat lama (bahkan tanpa batas) TANPA PERNAH throw
# exception. Akibatnya play_track() di controller.py nyangkut selamanya di
# status LOADING — tidak ada sinyal error, tidak ada retry, tidak ada
# fallback ke idle yang jelas. User cuma lihat "macet" tanpa pesan apapun,
# sampai mereka sendiri melakukan aksi lain (klik stop/play) yang baru
# men-trigger reset state ke idle secara paksa — sementara proses yt-dlp
# yang hang itu masih jalan di background dan baru selesai belakangan
# (kadang sempat "flash" play sebentar sebelum di-override state lain).
#
# Fix: bungkus panggilan executor dengan asyncio.wait_for(timeout=25s).
# Kalau timeout, raise RuntimeError yang jelas -> ini akan masuk ke
# except-block yang SUDAH ADA di play_track() (controller.py), yang sudah
# benar menangani retry/backoff/advance-to-next. Jadi user akan lihat pesan
# error yang jelas + retry otomatis, bukan macet diam-diam tanpa batas waktu.
#
# CATATAN PENTING (keterbatasan, baca sebelum pakai):
# asyncio.wait_for() membatalkan SISI ASYNC yang menunggu, TAPI thread yang
# menjalankan yt-dlp di ThreadPoolExecutor (engine/ytdlp_client.py, hanya
# 2 worker) tetap berjalan di background sampai dia sendiri selesai/gagal
# — Python tidak bisa memaksa hentikan thread dari luar. Kalau hang
# berulang kali secara beruntun, ke-2 slot worker bisa penuh dan resolve
# berikutnya jadi antre. Patch ini menghilangkan gejala "UI macet diam-diam
# tanpa batas waktu" yang user alami, TAPI bukan solusi sempurna untuk
# kondisi network yang BURUK SECARA TERUS-MENERUS.
#
# Jalankan dari root project ytgui (folder yang berisi main.py).
# Aman dijalankan berkali-kali (idempotent).
# ============================================================================
set -euo pipefail

MARKER="PATCH-YTDLP-RESOLVE-TIMEOUT-01"

# ---------------------------------------------------------------------------
# 0. Validasi lokasi
# ---------------------------------------------------------------------------
if [[ ! -f "main.py" || ! -f "config.py" || ! -f "engine/ytdlp_client.py" ]]; then
    echo "[ERROR] Jalankan script ini dari root folder project ytgui (folder yang ada main.py)." >&2
    exit 1
fi

CONFIG_PY="config.py"
YTDLP_PY="engine/ytdlp_client.py"

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"; else echo "[ERROR] python3 tidak ditemukan." >&2; exit 1; fi

if grep -q "$MARKER" "$YTDLP_PY" 2>/dev/null; then
    echo "[SKIP] Patch sudah pernah diterapkan sebelumnya (marker $MARKER ditemukan). Tidak ada yang dilakukan."
    exit 0
fi

# ---------------------------------------------------------------------------
# 1. Backup
# ---------------------------------------------------------------------------
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".patch_ytdlp_timeout_backup_${TS}"
for f in "$CONFIG_PY" "$YTDLP_PY"; do
    mkdir -p "$BACKUP_DIR/$(dirname "$f")"
    cp "$f" "$BACKUP_DIR/$f"
done
echo "[INFO] Backup file asli disimpan di: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# 2. Apply patch
# ---------------------------------------------------------------------------
"$PY" - "$CONFIG_PY" "$YTDLP_PY" "$MARKER" <<'PYEOF'
import sys

config_py, ytdlp_py, MARKER = sys.argv[1:4]

def M(s):
    return s.replace("__MARKER__", MARKER)

def replace_exact(path, old, new, label):
    old = M(old)
    new = M(new)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    count = content.count(old)
    if count != 1:
        print(f"[ERROR] {label}: pola ditemukan {count}x di {path} (harus tepat 1x). "
              f"File mungkin sudah berubah dari versi yang diharapkan — patch dibatalkan.", file=sys.stderr)
        sys.exit(1)
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"[OK] {label} -> {path}")


# ============================================================================
# 1. config.py: tambah konstanta timeout
# ============================================================================
old_cfg = "STREAM_URL_TTL_SEC = 21600"
new_cfg = M('''STREAM_URL_TTL_SEC = 21600
# __MARKER__: yt-dlp.get_stream_url() sebelumnya tidak punya batas waktu
# sama sekali -> kalau network Termux lambat/flaky, proses bisa hang TANPA
# BATAS tanpa pernah throw exception, sehingga play_track() nyangkut
# selamanya di status LOADING tanpa ada sinyal error/idle ke UI (kelihatan
# seperti "stuck" tanpa pesan jelas). Timeout ini memaksa gagal cepat
# supaya error/retry-path yang sudah ada di play_track() bisa jalan.
YTDLP_RESOLVE_TIMEOUT_SEC = 25''')

replace_exact(config_py, old_cfg, new_cfg, "Tambah YTDLP_RESOLVE_TIMEOUT_SEC")

# ============================================================================
# 2. ytdlp_client.py: import konstanta
# ============================================================================
old_import = "from config import CACHE_DIR"
new_import = "from config import CACHE_DIR, YTDLP_RESOLVE_TIMEOUT_SEC"

replace_exact(ytdlp_py, old_import, new_import, "Import YTDLP_RESOLVE_TIMEOUT_SEC")

# ============================================================================
# 3. ytdlp_client.py: bungkus run_in_executor dengan wait_for(timeout=...)
# ============================================================================
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
            # __MARKER__: dulu run_in_executor() di sini tidak punya batas
            # waktu -> network lambat/flaky bisa bikin proses hang tanpa
            # batas tanpa pernah throw, jadi play_track() nyangkut selamanya
            # di status LOADING. Sekarang dibungkus asyncio.wait_for supaya
            # gagal cepat & jelas kalau kelamaan.
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

print("[DONE] Semua patch berhasil diterapkan.")
PYEOF

# ---------------------------------------------------------------------------
# 3. Verifikasi syntax
# ---------------------------------------------------------------------------
"$PY" -m py_compile "$CONFIG_PY" "$YTDLP_PY"
echo "[OK] Syntax valid: $CONFIG_PY, $YTDLP_PY"

for f in "$CONFIG_PY" "$YTDLP_PY"; do
    if ! grep -q "$MARKER" "$f"; then
        echo "[ERROR] Marker tidak ditemukan di $f setelah patch — sesuatu salah." >&2
        exit 1
    fi
done
echo "[OK] Marker terverifikasi di kedua file"

echo ""
echo "============================================================"
echo " Patch berhasil diterapkan & terverifikasi:"
echo "   - $CONFIG_PY"
echo "   - $YTDLP_PY"
echo " Backup file asli ada di: $BACKUP_DIR"
echo ""
echo " Restart server (python main.py / start.sh)."
echo ""
echo " Yang berubah: kalau resolve stream URL dari yt-dlp lebih lambat dari"
echo " 25 detik (biasanya tanda network bermasalah), proses akan gagal"
echo " dengan pesan error yang jelas dan otomatis masuk ke retry/advance"
echo " yang sudah ada, alih-alih nyangkut diam-diam tanpa batas waktu."
echo ""
echo " CATATAN: ini bukan solusi sempurna untuk network yang buruk terus-"
echo " menerus — ThreadPoolExecutor (cuma 2 worker) tidak bisa dipaksa"
echo " berhenti dari luar, jadi proses yang sudah telanjur hang tetap jalan"
echo " di background sampai dia sendiri selesai/gagal."
echo "============================================================"
