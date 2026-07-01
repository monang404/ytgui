#!/usr/bin/env bash
# ============================================================================
# patch_audio_unlock_race.sh — ytgui: fix race antara klik tombol Play dan
# proses unlock AudioContext browser, yang bikin audio gagal play TANPA
# pesan/banner apapun (gejala: progress bar jalan, ikon pause aktif, tapi
# suara tidak keluar; klik play malah balik ke idle).
#
# Root cause: web/static/js/events/player-events.js -> handler klik tombol
# Play melakukan flip OPTIMISTIK ke store.status SEBELUM memanggil
# unlockBrowserAudio() + syncBrowserAudio(). Tapi unlockBrowserAudio() bisa
# memicu proses ASYNC (AudioContext.resume() -> doUnlock() -> syncBrowserAudio()
# lagi, lalu audio.oncanplay nanti baru fire). Saat oncanplay akhirnya fire,
# kode lama membaca ULANG store.status untuk memutuskan apakah perlu
# _resumeAndPlay() — padahal klik yang SAMA sudah keburu mengubah
# store.status duluan, jadi bisa salah baca dan _resumeAndPlay() TIDAK
# PERNAH dipanggil. Akibatnya: tidak ada percobaan play() sama sekali, dan
# tidak ada banner "tap to play" pun (karena banner itu munculnya kalau
# _resumeAndPlay() gagal — kalau dia tidak pernah dipanggil, tidak ada
# sinyal apapun ke user).
#
# Fix: handler klik Play menyimpan intent (wantsPlay) SEBELUM mengubah
# store.status, lalu meneruskan intent itu secara eksplisit ke
# unlockBrowserAudio(forcePlay) dan syncBrowserAudio(forcePlay) — termasuk
# di sepanjang chain async unlock (doUnlock, catch handler, AC-unsupported
# fallback) — supaya keputusan play/tidak TIDAK bergantung lagi pada
# store.status yang sudah ke-mutasi oleh klik yang sama.
#
# Listener klik umum (document-wide, untuk unlock AudioContext di klik
# manapun) TIDAK diubah — tetap konservatif, tidak forcePlay.
#
# Jalankan dari root project ytgui (folder yang berisi main.py).
# Aman dijalankan berkali-kali (idempotent).
# ============================================================================
set -euo pipefail

MARKER="PATCH-AUDIO-UNLOCK-RACE-01"

# ---------------------------------------------------------------------------
# 0. Validasi lokasi
# ---------------------------------------------------------------------------
if [[ ! -f "main.py" || ! -f "web/static/js/audio.js" || ! -f "web/static/js/events/player-events.js" ]]; then
    echo "[ERROR] Jalankan script ini dari root folder project ytgui (folder yang ada main.py)." >&2
    echo "[ERROR] Lokasi sekarang: $(pwd)" >&2
    exit 1
fi

AUDIO_JS="web/static/js/audio.js"
PLAYER_EVENTS_JS="web/static/js/events/player-events.js"

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"; else echo "[ERROR] python3 tidak ditemukan." >&2; exit 1; fi

if grep -q "$MARKER" "$AUDIO_JS" 2>/dev/null; then
    echo "[SKIP] Patch sudah pernah diterapkan sebelumnya (marker $MARKER ditemukan). Tidak ada yang dilakukan."
    exit 0
fi

# ---------------------------------------------------------------------------
# 1. Backup
# ---------------------------------------------------------------------------
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".patch_audio_unlock_race_backup_${TS}"
for f in "$AUDIO_JS" "$PLAYER_EVENTS_JS"; do
    mkdir -p "$BACKUP_DIR/$(dirname "$f")"
    cp "$f" "$BACKUP_DIR/$f"
done
echo "[INFO] Backup file asli disimpan di: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# 2. Apply patch
# ---------------------------------------------------------------------------
"$PY" - "$AUDIO_JS" "$PLAYER_EVENTS_JS" "$MARKER" <<'PYEOF'
import sys

audio_js, player_events_js, MARKER = sys.argv[1:4]

def M(s):
    return s.replace("__MARKER__", MARKER)

def replace_exact(path, old, new, label):
    old = M(old); new = M(new)
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
# 1. audio.js: unlockBrowserAudio menerima & meneruskan forcePlay
# ============================================================================
old_unlock = '''function unlockBrowserAudio() {
    if (audioUnlocked || _unlocking) return;
    _unlocking = true;
    console.log("[audio] unlocking via AudioContext...");

    // Buat AudioContext sementara khusus untuk unlock jika belum ada
    // (initVisualizer belum dipanggil karena belum ada interaksi sebelumnya)
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) {
        // Browser tidak support AudioContext — mark unlocked dan coba play langsung
        audioUnlocked = true;
        _unlocking = false;
        _lastLoadedVideoId = null;
        syncBrowserAudio();
        return;
    }

    // Kalau audioCtx sudah ada (dari initVisualizer), pakai itu
    // Kalau belum, buat baru khusus untuk unlock
    const ctx = audioCtx || new AC();

    const doUnlock = () => {
        audioUnlocked = true;
        _unlocking = false;
        console.log("[audio] unlocked, syncing...");
        // Simpan ctx sebagai audioCtx global jika belum ada
        if (!audioCtx) {
            audioCtx = ctx;
        }
        // Inisialisasi visualizer lewat initVisualizer() — dia yang tahu
        // cara handle CORS dan perbedaan mobile/desktop
        initVisualizer();
        // Reset agar syncBrowserAudio load src nyata dengan oncanplay
        _lastLoadedVideoId = null;
        syncBrowserAudio();
    };

    if (ctx.state === 'suspended') {
        ctx.resume().then(doUnlock).catch((e) => {
            console.warn("[audio] AudioContext resume failed:", e);
            // Tetap mark unlocked — coba saja play, mungkin berhasil
            _unlocking = false;
            audioUnlocked = true;
            _lastLoadedVideoId = null;
            syncBrowserAudio();
        });
    } else {
        // ctx sudah running (bisa terjadi di desktop)
        doUnlock();
    }
}'''

new_unlock = M('''function unlockBrowserAudio(forcePlay) {
    if (audioUnlocked || _unlocking) {
        // __MARKER__: kalau sudah unlocked sebelumnya tapi dipanggil lagi
        // dengan forcePlay (dari klik tombol play), tetap teruskan intent
        // itu ke syncBrowserAudio supaya tidak bergantung pada store.status
        // yang mungkin sudah ke-flip duluan oleh klik yang sama.
        if (forcePlay && audioUnlocked) syncBrowserAudio(true);
        return;
    }
    _unlocking = true;
    console.log("[audio] unlocking via AudioContext...");

    // Buat AudioContext sementara khusus untuk unlock jika belum ada
    // (initVisualizer belum dipanggil karena belum ada interaksi sebelumnya)
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) {
        // Browser tidak support AudioContext — mark unlocked dan coba play langsung
        audioUnlocked = true;
        _unlocking = false;
        _lastLoadedVideoId = null;
        syncBrowserAudio(forcePlay);
        return;
    }

    // Kalau audioCtx sudah ada (dari initVisualizer), pakai itu
    // Kalau belum, buat baru khusus untuk unlock
    const ctx = audioCtx || new AC();

    const doUnlock = () => {
        audioUnlocked = true;
        _unlocking = false;
        console.log("[audio] unlocked, syncing...");
        // Simpan ctx sebagai audioCtx global jika belum ada
        if (!audioCtx) {
            audioCtx = ctx;
        }
        // Inisialisasi visualizer lewat initVisualizer() — dia yang tahu
        // cara handle CORS dan perbedaan mobile/desktop
        initVisualizer();
        // Reset agar syncBrowserAudio load src nyata dengan oncanplay
        _lastLoadedVideoId = null;
        syncBrowserAudio(forcePlay);
    };

    if (ctx.state === 'suspended') {
        ctx.resume().then(doUnlock).catch((e) => {
            console.warn("[audio] AudioContext resume failed:", e);
            // Tetap mark unlocked — coba saja play, mungkin berhasil
            _unlocking = false;
            audioUnlocked = true;
            _lastLoadedVideoId = null;
            syncBrowserAudio(forcePlay);
        });
    } else {
        // ctx sudah running (bisa terjadi di desktop)
        doUnlock();
    }
}''')

replace_exact(audio_js, old_unlock, new_unlock, "unlockBrowserAudio menerima forcePlay")


# ============================================================================
# 2. audio.js: syncBrowserAudio menerima forcePlay, dipakai di oncanplay
#    dan di branch "track sama" sebagai pengganti store.status yang racy
# ============================================================================
old_sync_sig = "function syncBrowserAudio() {"
new_sync_sig = "function syncBrowserAudio(forcePlay) {"
replace_exact(audio_js, old_sync_sig, new_sync_sig, "syncBrowserAudio menerima forcePlay")

old_oncanplay = '''        // Sudah unlock: load → oncanplay → play
        audio.oncanplay = () => {
            audio.oncanplay = null;
            if (store.position > 5 && Math.abs(audio.currentTime - store.position) > 5) {
                audio.currentTime = store.position;
            }
            if (store.status === "PLAYING") {
                console.log("[audio] canplay → play:", track.video_id);
                _resumeAndPlay(audio);
            }
        };
        audio.load();
        return;
    }

    // Track sama
    audio.volume = Math.max(0, Math.min(1, (store.volume || 80) / 100));
    if (store.status === "PLAYING") {
        if (audio.paused && audio.src && !audio.src.startsWith("data:") && audioUnlocked) {
            _resumeAndPlay(audio);
        }
    } else {
        if (!audio.paused) audio.pause();
    }
}'''

new_oncanplay = M('''        // Sudah unlock: load → oncanplay → play
        audio.oncanplay = () => {
            audio.oncanplay = null;
            if (store.position > 5 && Math.abs(audio.currentTime - store.position) > 5) {
                audio.currentTime = store.position;
            }
            // __MARKER__: dulu cuma cek store.status === "PLAYING". Tapi
            // store.status bisa keburu di-flip secara optimistik oleh klik
            // tombol play yang JUSTRU memicu unlockBrowserAudio() ->
            // syncBrowserAudio() ini sendiri. Akibatnya pas oncanplay fire,
            // store.status sudah salah, jadi _resumeAndPlay() tidak pernah
            // dipanggil -> audio diam, tidak ada banner pun. forcePlay=true
            // dipakai saat dipanggil dari user gesture asli (unlock), jadi
            // gesture itu sendiri sudah cukup sinyal untuk play.
            if (forcePlay || store.status === "PLAYING") {
                console.log("[audio] canplay → play:", track.video_id);
                _resumeAndPlay(audio);
            }
        };
        audio.load();
        return;
    }

    // Track sama
    audio.volume = Math.max(0, Math.min(1, (store.volume || 80) / 100));
    if (forcePlay || store.status === "PLAYING") {
        if (audio.paused && audio.src && !audio.src.startsWith("data:") && audioUnlocked) {
            _resumeAndPlay(audio);
        }
    } else {
        if (!audio.paused) audio.pause();
    }
}''')

replace_exact(audio_js, old_oncanplay, new_oncanplay, "oncanplay & track-sama pakai forcePlay")


# ============================================================================
# 3. player-events.js: simpan intent sebelum flip status, teruskan ke
#    unlockBrowserAudio()/syncBrowserAudio()
# ============================================================================
old_handler = '''    dom.btnPlay.addEventListener("click", () => {
        if (store.userRole === "admin") {
            store.status = store.status === "PLAYING" ? "PAUSED" : "PLAYING";
            window.lastToggleTime = Date.now();
            if (typeof renderPlayBtn === "function") renderPlayBtn();
            if (typeof renderNowPlaying === "function") renderNowPlaying();
            if (typeof renderQueue === "function") renderQueue();
            if (store.audio_output === "browser" && typeof syncBrowserAudio === "function") {
                unlockBrowserAudio();
                syncBrowserAudio();
            }
            wsSend("toggle_pause");
        }
    });'''

new_handler = M('''    dom.btnPlay.addEventListener("click", () => {
        if (store.userRole === "admin") {
            // __MARKER__: simpan intent SEBELUM store.status di-flip, supaya
            // syncBrowserAudio() di bawah tahu persis apa yang user maksud
            // (play/pause), bukan menebak ulang dari store.status yang baru
            // saja diubah oleh baris ini sendiri.
            const wantsPlay = store.status !== "PLAYING";
            store.status = wantsPlay ? "PLAYING" : "PAUSED";
            window.lastToggleTime = Date.now();
            if (typeof renderPlayBtn === "function") renderPlayBtn();
            if (typeof renderNowPlaying === "function") renderNowPlaying();
            if (typeof renderQueue === "function") renderQueue();
            if (store.audio_output === "browser" && typeof syncBrowserAudio === "function") {
                unlockBrowserAudio(wantsPlay);
                syncBrowserAudio(wantsPlay);
            }
            wsSend("toggle_pause");
        }
    });''')

replace_exact(player_events_js, old_handler, new_handler, "Play button handler simpan & teruskan intent")

print("[DONE] Semua patch berhasil diterapkan.")
PYEOF

# ---------------------------------------------------------------------------
# 3. Verifikasi syntax
# ---------------------------------------------------------------------------
if command -v node >/dev/null 2>&1; then
    node --check "$AUDIO_JS"
    echo "[OK] Syntax valid: $AUDIO_JS"
    node --check "$PLAYER_EVENTS_JS"
    echo "[OK] Syntax valid: $PLAYER_EVENTS_JS"
else
    echo "[WARN] 'node' tidak ditemukan, syntax JS tidak diverifikasi otomatis."
fi

for f in "$AUDIO_JS" "$PLAYER_EVENTS_JS"; do
    if ! grep -q "$MARKER" "$f"; then
        echo "[ERROR] Marker tidak ditemukan di $f setelah patch — sesuatu salah." >&2
        exit 1
    fi
done
echo "[OK] Marker terverifikasi di kedua file"

echo ""
echo "============================================================"
echo " Patch berhasil diterapkan & terverifikasi:"
echo "   - $AUDIO_JS"
echo "   - $PLAYER_EVENTS_JS"
echo " Backup file asli ada di: $BACKUP_DIR"
echo ""
echo " File JS ini perlu kill-switch Service Worker untuk benar-benar"
echo " ke-load di browser (lihat patch_swkill.sh / patch_all_remaining.sh"
echo " kalau belum pernah dipasang). Restart server lalu buka ytgui sekali"
echo " di Chrome Android."
echo "============================================================"
