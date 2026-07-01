#!/usr/bin/env bash
# ============================================================================
# patch.sh — ytgui: fix 3 bug Android Chrome / Termux (radio + discover autoplay)
#
#  1. Idle-view & status player desync (data-player-state cuma direfresh
#     kadang-kadang -> tombol play & progress bar bisa "hidup" padahal
#     player sebenarnya idle, atau sebaliknya idle-view nyangkut).
#  2. enqueue_artist_songs (klik artist di Discover) nge-null current_track
#     + set IDLE sesaat sebelum track baru siap -> flash "Belum ada lagu"
#     terutama kerasa di device lambat (Termux/Android).
#  3. Autoplay browser yang di-block (Chrome Android) bikin retry loop diam2
#     tiap detik tanpa feedback -> UI bilang PLAYING padahal suara nggak
#     keluar. Sekarang ada fallback tombol "tap to play" + retry dihentikan.
#
# Jalankan dari root project ytgui (folder yang berisi main.py).
# Aman dijalankan berkali-kali (idempotent) — kalau sudah dipatch, di-skip.
# ============================================================================
set -euo pipefail

MARKER="PATCH-ANDROID-AUDIO-01"

# ---------------------------------------------------------------------------
# 0. Validasi lokasi & dependency
# ---------------------------------------------------------------------------
if [[ ! -f "main.py" || ! -d "web/static/js" || ! -d "engine" ]]; then
    echo "[ERROR] Jalankan script ini dari root folder project ytgui (folder yang ada main.py)." >&2
    exit 1
fi

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"; else echo "[ERROR] python3 tidak ditemukan, dibutuhkan untuk patch ini." >&2; exit 1; fi

WS_PY="server/handlers/websocket.py"
NOWPLAYING_JS="web/static/js/render/now-playing.js"
PLAYER_JS="web/static/js/render/player.js"
WS_JS="web/static/js/ws.js"
AUDIO_JS="web/static/js/audio.js"

for f in "$WS_PY" "$NOWPLAYING_JS" "$PLAYER_JS" "$WS_JS" "$AUDIO_JS"; do
    if [[ ! -f "$f" ]]; then
        echo "[ERROR] File tidak ditemukan: $f (struktur project beda dari yang diharapkan)" >&2
        exit 1
    fi
done

if grep -q "$MARKER" "$AUDIO_JS" 2>/dev/null; then
    echo "[SKIP] Patch sudah pernah diterapkan sebelumnya (marker $MARKER ditemukan). Tidak ada yang dilakukan."
    exit 0
fi

# ---------------------------------------------------------------------------
# 1. Backup
# ---------------------------------------------------------------------------
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".patch_backup_${TS}"
mkdir -p "$BACKUP_DIR"
for f in "$WS_PY" "$NOWPLAYING_JS" "$PLAYER_JS" "$WS_JS" "$AUDIO_JS"; do
    mkdir -p "$BACKUP_DIR/$(dirname "$f")"
    cp "$f" "$BACKUP_DIR/$f"
done
echo "[INFO] Backup file asli disimpan di: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# 2. Apply patch lewat python (exact string replace, gagal kalau pattern
#    tidak ketemu persis sekali -> mencegah patch "nyasar" kalau source
#    sudah beda dari yang diharapkan)
# ---------------------------------------------------------------------------
"$PY" - "$WS_PY" "$NOWPLAYING_JS" "$PLAYER_JS" "$WS_JS" "$AUDIO_JS" "$MARKER" <<'PYEOF'
import sys, re

ws_py, nowplaying_js, player_js, ws_js, audio_js, MARKER = sys.argv[1:7]

def M(s):
    """Ganti placeholder __MARKER__ dengan nilai MARKER asli (hindari f-string
    di dalam blok kode JS/Python yang penuh kurung kurawal)."""
    return s.replace("__MARKER__", MARKER)


def replace_exact(path, old, new, label):
    old = M(old)
    new = M(new)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    count = content.count(old)
    if count != 1:
        print("[ERROR] %s: pola yang dicari ditemukan %dx di %s (harus tepat 1x). "
              "File mungkin sudah berubah dari versi yang diharapkan — patch dibatalkan."
              % (label, count, path), file=sys.stderr)
        sys.exit(1)
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("[OK] %s -> %s" % (label, path))


# ============================================================================
# FIX #2 (server): enqueue_artist_songs — jangan CMD_SET_MODE+null dulu,
# pakai CMD_PLAY_TRACK utk lagu pertama (pola yg sama dgn play_track action,
# yang sudah terbukti bisa keluar dari RADIO tanpa nge-null current_track).
# ============================================================================
old_ws = '''        elif action == "enqueue_artist_songs":
            artist_name = data.get("artist")
            if artist_name:
                songs = await db.get_artist_songs_strict(artist=artist_name, limit=10)
                if songs:
                    await db.increment_artist_click(artist_name)
                    
                    await command_bus.execute(CMD_SET_MODE, PlaybackMode.QUEUE)
                    state.queue.clear()
                    
                    for track in songs:
                        await command_bus.execute(CMD_QUEUE_ADD, track)
                        
                    await command_bus.execute(CMD_QUEUE_SELECT, 0)
'''

new_ws = '''        elif action == "enqueue_artist_songs":
            # __MARKER__: jangan CMD_SET_MODE dulu (itu nge-null current_track
            # + set IDLE secara instan -> flash "Belum ada lagu" sebelum
            # track baru siap, kerasa banget di device lambat spt Termux).
            # Pakai CMD_PLAY_TRACK utk lagu pertama: path yg sama dgn klik
            # search result, sudah handle keluar dari RADIO tanpa nge-null
            # track lama. Sisanya masuk antrean seperti biasa.
            artist_name = data.get("artist")
            if artist_name:
                songs = await db.get_artist_songs_strict(artist=artist_name, limit=10)
                if songs:
                    await db.increment_artist_click(artist_name)

                    state.queue.clear()
                    first_track, rest_tracks = songs[0], songs[1:]

                    for track in rest_tracks:
                        await command_bus.execute(CMD_QUEUE_ADD, track)

                    await command_bus.execute(CMD_PLAY_TRACK, first_track)
'''

replace_exact(ws_py, old_ws, new_ws, "Fix #2 (enqueue_artist_songs no idle-flash)")


# ============================================================================
# FIX #1a (JS): now-playing.js — ekstrak logic IDLE jadi fungsi terpisah
# yang bisa dipanggil dari file lain & dari progress-tick.
# ============================================================================
old_np = '''    if (!t || (!t.video_id && store.status !== "LOADING")) {
        document.body.setAttribute("data-player-state", "IDLE");
    } else {
        document.body.setAttribute("data-player-state", store.status);
    }
'''

new_np = '''    // __MARKER__: satu-satunya tempat yang nentuin data-player-state,
    // dipanggil juga dari player.js & ws.js (progress tick) supaya nggak
    // ada dua sumber kebenaran yang bisa desync.
    syncPlayerStateAttr();
'''

replace_exact(nowplaying_js, old_np, new_np, "Fix #1a (extract syncPlayerStateAttr)")

# tambahkan definisi fungsi syncPlayerStateAttr() di akhir file
with open(nowplaying_js, "r", encoding="utf-8") as fh:
    np_content = fh.read()

func_marker = "function syncPlayerStateAttr("
if func_marker not in np_content:
    np_content = np_content.rstrip() + M('''

// __MARKER__
function syncPlayerStateAttr() {
    const t = store.current_track;
    if (!t || (!t.video_id && store.status !== "LOADING")) {
        document.body.setAttribute("data-player-state", "IDLE");
    } else {
        document.body.setAttribute("data-player-state", store.status);
    }
}
''')
    with open(nowplaying_js, "w", encoding="utf-8") as fh:
        fh.write(np_content)
    print(f"[OK] Fix #1a (define syncPlayerStateAttr) -> {nowplaying_js}")
else:
    print(f"[ERROR] {nowplaying_js} sudah punya fungsi syncPlayerStateAttr — kemungkinan sudah dipatch sebagian. Dibatalkan.", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# FIX #1b (JS): player.js — jangan timpa data-player-state sendiri, pakai
# fungsi bersama supaya konsisten dengan now-playing.js.
# ============================================================================
old_pb = '''function renderPlayerBar() {
    document.body.dataset.playerState = store.status || "IDLE";
    const t = store.current_track;
'''

new_pb = '''function renderPlayerBar() {
    // __MARKER__: dulu baris ini menimpa data-player-state dengan logic
    // berbeda dari now-playing.js (cuma cek store.status, gak cek track),
    // bikin idle-view bisa nyangkut salah. Sekarang pakai fungsi bersama.
    if (typeof syncPlayerStateAttr === "function") syncPlayerStateAttr();
    const t = store.current_track;
'''

replace_exact(player_js, old_pb, new_pb, "Fix #1b (player.js shared state attr)")


# ============================================================================
# FIX #1c (JS): ws.js — refresh data-player-state tiap progress tick, bukan
# cuma saat statusChanged, supaya idle-view selalu sinkron sama kondisi asli.
# Sekalian: hentikan retry-resume tiap detik kalau sudah ketauan diblock
# browser (lihat Fix #3), nunggu user tap manual.
# ============================================================================
old_progress = '''            renderProgress();

            renderPlayBtn();
            if (statusChanged) {
                if (typeof renderNowPlaying === "function") renderNowPlaying();
                if (typeof renderQueue === "function") renderQueue();
                if (typeof renderRadio === "function") renderRadio();
                if (typeof updateSearchPlayingState === "function") updateSearchPlayingState();
                if (typeof updateDiscoverPlayingState === "function") updateDiscoverPlayingState();
            }
            syncBrowserAudio();'''

new_progress = '''            renderProgress();

            renderPlayBtn();
            // __MARKER__: dipanggil tiap tick (bukan cuma saat statusChanged)
            // supaya data-player-state / idle-view selalu sinkron dgn
            // store.status & store.current_track yang sebenarnya.
            if (typeof syncPlayerStateAttr === "function") syncPlayerStateAttr();
            if (statusChanged) {
                if (typeof renderNowPlaying === "function") renderNowPlaying();
                if (typeof renderQueue === "function") renderQueue();
                if (typeof renderRadio === "function") renderRadio();
                if (typeof updateSearchPlayingState === "function") updateSearchPlayingState();
                if (typeof updateDiscoverPlayingState === "function") updateDiscoverPlayingState();
            }
            syncBrowserAudio();'''

replace_exact(ws_js, old_progress, new_progress, "Fix #1c (refresh state attr every tick)")

old_retry = '''                } else if (audio.paused && audio.src && !audio.src.startsWith("data:") && audio.readyState >= 2) {
                    // FIX-RADIO-08: Audio stuck paused padahal status PLAYING.
                    // Terjadi saat AudioContext suspended (radio auto-switch tanpa user interaction).
                    // Coba resume AudioContext + play ulang tanpa menunggu user klik.
                    // audio.readyState >= 2 = HAVE_CURRENT_DATA — audio sudah ter-load, aman di-play.
                    if (typeof _resumeAndPlay === "function") {
                        _resumeAndPlay(audio);
                    }
                }'''

new_retry = '''                } else if (audio.paused && audio.src && !audio.src.startsWith("data:") && audio.readyState >= 2) {
                    // FIX-RADIO-08: Audio stuck paused padahal status PLAYING.
                    // Terjadi saat AudioContext suspended (radio auto-switch tanpa user interaction).
                    // Coba resume AudioContext + play ulang tanpa menunggu user klik.
                    // audio.readyState >= 2 = HAVE_CURRENT_DATA — audio sudah ter-load, aman di-play.
                    // __MARKER__: kalau sebelumnya sudah ketauan diblock browser,
                    // jangan retry diam2 tiap detik (spam gagal) — tunggu user
                    // tap tombol "tap to play" (lihat audio.js), itu pasti lolos
                    // autoplay policy krn ada user gesture beneran.
                    if (!window.audioBlocked && typeof _resumeAndPlay === "function") {
                        _resumeAndPlay(audio);
                    }
                }'''

replace_exact(ws_js, old_retry, new_retry, "Fix #3a (stop silent retry loop)")


# ============================================================================
# FIX #3 (JS): audio.js — tandai kalau autoplay di-block, tampilkan tombol
# "tap to play" supaya user bisa kasih gesture manual (pasti lolos autoplay
# policy Android Chrome), alih-alih diam2 gagal terus tiap detik.
# ============================================================================
old_resume = '''async function _resumeAndPlay(audio) {
    if (audioCtx && audioCtx.state === 'suspended') {
        try { await audioCtx.resume(); } catch (e) { console.warn("[audio] ctx resume failed:", e); }
    }
    try {
        await audio.play();
        console.log("[audio] play() OK");
        startFakeBeatLoop();
    } catch (e) {
        console.warn("[audio] play() blocked:", e.name, e.message);
    }
}'''

new_resume = '''// __MARKER__
window.audioBlocked = false;

function _showTapToPlayBanner() {
    let el = document.getElementById('audio-unlock-banner');
    if (!el) {
        el = document.createElement('button');
        el.id = 'audio-unlock-banner';
        el.type = 'button';
        el.textContent = '\\ud83d\\udd0a Tap untuk lanjut memutar';
        el.style.cssText = 'position:fixed;left:50%;bottom:90px;transform:translateX(-50%);' +
            'z-index:9999;padding:10px 18px;border-radius:999px;border:none;' +
            'background:var(--accent,#1db954);color:#fff;font-weight:600;font-size:14px;' +
            'box-shadow:0 4px 16px rgba(0,0,0,.35);cursor:pointer;';
        el.addEventListener('click', () => {
            _hideTapToPlayBanner();
            if (typeof unlockBrowserAudio === "function") unlockBrowserAudio();
            const audio = getOrInitAudio();
            if (audio && audio.src && !audio.src.startsWith('data:')) {
                _resumeAndPlay(audio);
            } else if (typeof syncBrowserAudio === "function") {
                syncBrowserAudio();
            }
        });
        document.body.appendChild(el);
    }
    el.style.display = 'block';
}

function _hideTapToPlayBanner() {
    const el = document.getElementById('audio-unlock-banner');
    if (el) el.style.display = 'none';
}

async function _resumeAndPlay(audio) {
    if (audioCtx && audioCtx.state === 'suspended') {
        try { await audioCtx.resume(); } catch (e) { console.warn("[audio] ctx resume failed:", e); }
    }
    try {
        await audio.play();
        console.log("[audio] play() OK");
        window.audioBlocked = false;
        _hideTapToPlayBanner();
        startFakeBeatLoop();
    } catch (e) {
        console.warn("[audio] play() blocked:", e.name, e.message);
        window.audioBlocked = true;
        _showTapToPlayBanner();
    }
}'''

replace_exact(audio_js, old_resume, new_resume, "Fix #3b (tap-to-play fallback)")

old_sync_new_track = '''    if (_lastLoadedVideoId !== track.video_id) {
        _lastLoadedVideoId = track.video_id;
        audio.src = expectedSrc;'''

new_sync_new_track = '''    if (_lastLoadedVideoId !== track.video_id) {
        _lastLoadedVideoId = track.video_id;
        // __MARKER__: track baru -> reset status block, kasih kesempatan baru
        // buat autoplay (banner lama kalau ada juga disembunyikan dulu).
        window.audioBlocked = false;
        if (typeof _hideTapToPlayBanner === "function") _hideTapToPlayBanner();
        audio.src = expectedSrc;'''

replace_exact(audio_js, old_sync_new_track, new_sync_new_track, "Fix #3c (reset block flag on new track)")

print("[DONE] Semua patch berhasil diterapkan.")
PYEOF

# ---------------------------------------------------------------------------
# 3. Verifikasi syntax
# ---------------------------------------------------------------------------
echo "[INFO] Verifikasi syntax..."

"$PY" -m py_compile "$WS_PY"
echo "[OK] Syntax valid: $WS_PY"

if command -v node >/dev/null 2>&1; then
    for f in "$NOWPLAYING_JS" "$PLAYER_JS" "$WS_JS" "$AUDIO_JS"; do
        node --check "$f"
        echo "[OK] Syntax valid: $f"
    done
else
    echo "[WARN] 'node' tidak ditemukan di sistem ini, syntax JS tidak diverifikasi otomatis. Cek manual kalau perlu."
fi

# ---------------------------------------------------------------------------
# 4. Verifikasi marker tertanam (anti-patch-ganda di masa depan)
# ---------------------------------------------------------------------------
for f in "$WS_PY" "$NOWPLAYING_JS" "$PLAYER_JS" "$WS_JS" "$AUDIO_JS"; do
    if ! grep -q "$MARKER" "$f"; then
        echo "[ERROR] Marker tidak ditemukan di $f setelah patch — sesuatu salah." >&2
        exit 1
    fi
done

echo ""
echo "============================================================"
echo " Patch berhasil diterapkan & terverifikasi:"
echo "   - $WS_PY"
echo "   - $NOWPLAYING_JS"
echo "   - $PLAYER_JS"
echo "   - $WS_JS"
echo "   - $AUDIO_JS"
echo ""
echo " Backup file asli ada di: $BACKUP_DIR"
echo " Restart server (python main.py / start.sh) lalu hard-refresh browser"
echo " (clear cache / ctrl+shift+r) supaya JS baru ke-load."
echo "============================================================"
