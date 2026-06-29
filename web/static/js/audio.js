let localAudio = null;
let audioUnlocked = false;
let _unlocking = false; // guard agar tidak double-call saat masih proses
let _lastLoadedVideoId = null;

function getOrInitAudio() {
    if (!localAudio) {
        localAudio = new Audio();
        localAudio.preload = "auto";
        localAudio.onerror = (e) => {
            const err = localAudio.error;
            if (!err) return;
            if (err.code === 1) return;
            if (err.code === 4 && localAudio.src.includes("data:audio")) return;
            const errMsg = err.message || ("code " + err.code);
            if (errMsg.includes("Empty src") || !localAudio.getAttribute("src")) return;
            console.warn("Browser audio error:", err.code, errMsg);
            showLogToast("⚠️ Audio stream info: " + errMsg);
        };
        localAudio.addEventListener("timeupdate", () => {
            if (store.userRole === "client" || store.audio_output === "browser") {
                if (!window.isDraggingPb) {
                    store.position = localAudio.currentTime;
                    renderProgress();
                }
                if (typeof syncLocalLyrics === "function") syncLocalLyrics();
            }
        });
    }
    return localAudio;
}

let audioCtx = null;
let analyser = null;
let dataArray = null;

function initVisualizer() {
    // Semua platform pakai fake beat.
    // createMediaElementSource di-skip karena /api/stream/ tidak ada CORS header
    // -> browser silence audio jika di-connect ke AudioContext (CORS zeroes bug).
    startFakeBeatLoop();
}

let _fakeBeatRaf = null;
function startFakeBeatLoop() {
    if (_fakeBeatRaf) return;
    const BASE_INTERVAL = 500;
    let lastBeat = 0;
    function tick(ts) {
        _fakeBeatRaf = requestAnimationFrame(tick);
        if (store.status !== 'PLAYING') {
            if (dom.tabHome) {
                dom.tabHome.style.removeProperty('--beat-glow-opacity');
                dom.tabHome.style.removeProperty('--beat-bg-brightness');
                dom.tabHome.style.removeProperty('--beat-glow-transition');
            }
            return;
        }
        const elapsed = ts - lastBeat;
        if (elapsed < BASE_INTERVAL) return;
        lastBeat = ts;
        if (!dom.tabHome) return;
        dom.tabHome.style.setProperty('--beat-glow-opacity', '0.5');
        dom.tabHome.style.setProperty('--beat-bg-brightness', '0.28');
        dom.tabHome.style.setProperty('--beat-glow-transition', '0.15s');
        setTimeout(() => {
            if (!dom.tabHome) return;
            dom.tabHome.style.setProperty('--beat-glow-opacity', '0.4');
            dom.tabHome.style.setProperty('--beat-bg-brightness', '0.22');
            dom.tabHome.style.setProperty('--beat-glow-transition', '0.4s');
        }, 150);
    }
    _fakeBeatRaf = requestAnimationFrame(tick);
}

let _vizRafId = null;
function startVisualizerLoop() {
    if (!analyser || !dom.vinylRecord) return;
    const isBrowser = store.userRole === "client" || store.audio_output === "browser";
    if (!isBrowser || store.status !== "PLAYING") {
        if (dom.tabHome) {
            dom.tabHome.style.removeProperty('--beat-glow-opacity');
            dom.tabHome.style.removeProperty('--beat-bg-brightness');
            dom.tabHome.style.removeProperty('--beat-glow-transition');
        }
        _vizRafId = null;
        return;
    }
    analyser.getByteFrequencyData(dataArray);
    let bassSum = 0;
    for (let i = 0; i < 10; i++) bassSum += dataArray[i];
    const ratio = (bassSum / 10) / 255;
    if (dom.tabHome) {
        dom.tabHome.style.setProperty('--beat-glow-opacity', (0.4 + ratio * 0.2).toFixed(3));
        dom.tabHome.style.setProperty('--beat-bg-brightness', (0.2 + ratio * 0.1).toFixed(3));
        dom.tabHome.style.setProperty('--beat-glow-transition', ratio > 0.4 ? '0.2s' : '0.4s');
    }
    _vizRafId = requestAnimationFrame(startVisualizerLoop);
}

function resumeVisualizerLoop() {
    if (!_vizRafId && analyser) startVisualizerLoop();
}

async function _resumeAndPlay(audio) {
    if (audioCtx && audioCtx.state === 'suspended') {
        try { await audioCtx.resume(); } catch (e) { console.warn("[audio] ctx resume failed:", e); }
    }
    try {
        await audio.play();
        console.log("[audio] play() OK");
    } catch (e) {
        console.warn("[audio] play() blocked:", e.name, e.message);
    }
}

document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume().catch(() => {});
        const isBrowser = store && (store.userRole === "client" || store.audio_output === "browser");
        if (isBrowser && store.status === "PLAYING") {
            const audio = getOrInitAudio();
            if (audio.paused && audio.src && !audio.src.startsWith("data:")) {
                _resumeAndPlay(audio);
            }
        }
    }
});

// ─────────────────────────────────────────────────────────────────────────────
// UNLOCK STRATEGY
//
// Masalah dummy audio base64: beberapa browser/OS tidak support format itu,
// throw NotSupportedError → unlock gagal selamanya.
//
// Solusi: pakai AudioContext (Web Audio API) sebagai unlock mechanism,
// bukan Audio element. AudioContext.resume() dalam gesture context cukup
// untuk memberi "autoplay allowance" ke Audio element di halaman yang sama.
//
// Setelah AudioContext di-resume dalam gesture → audioUnlocked=true →
// syncBrowserAudio() load src nyata → oncanplay → audio.play() diizinkan.
// ─────────────────────────────────────────────────────────────────────────────

function unlockBrowserAudio() {
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
}

function syncBrowserAudio() {
    const isBrowser = store.userRole === "client" || store.audio_output === "browser";
    const audio = getOrInitAudio();

    if (!isBrowser) {
        if (!audio.paused) audio.pause();
        return;
    }

    const track = store.current_track;
    if (!track) {
        if (!audio.paused) audio.pause();
        if (audio.hasAttribute("src") && audio.src && !audio.src.startsWith("data:")) {
            audio.removeAttribute("src");
            audio.load();
        }
        _lastLoadedVideoId = null;
        return;
    }

    const expectedSrc = window.location.origin + `/api/stream/${track.video_id}`;

    if (_lastLoadedVideoId !== track.video_id) {
        _lastLoadedVideoId = track.video_id;
        audio.src = expectedSrc;
        audio.volume = Math.max(0, Math.min(1, (store.volume || 80) / 100));

        audio.onended = () => {
            console.log("[radio] track ended, requesting next...");
            if (store.audio_output === "browser") {
                wsSend("next", { video_id: track.video_id });
            }
        };

        if (!audioUnlocked) {
            // Belum unlock: buffer saja, jangan play
            // unlockBrowserAudio() akan reset dan sync ulang setelah user klik
            audio.oncanplay = null;
            audio.load();
            console.log("[audio] buffering, waiting for user gesture:", track.video_id);
            return;
        }

        // Sudah unlock: load → oncanplay → play
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
}

function initAudio() {
    document.addEventListener("click", unlockBrowserAudio);
    document.addEventListener("touchstart", unlockBrowserAudio, { passive: true });
}