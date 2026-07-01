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
        if (store.status !== 'PLAYING') {
            if (dom.tabHome) {
                dom.tabHome.style.removeProperty('--beat-glow-opacity');
                dom.tabHome.style.removeProperty('--beat-bg-brightness');
                dom.tabHome.style.removeProperty('--beat-glow-transition');
            }
            if (_fakeBeatRaf) {
                cancelAnimationFrame(_fakeBeatRaf);
                _fakeBeatRaf = null;
            }
            return;
        }
        _fakeBeatRaf = requestAnimationFrame(tick);
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

// PATCH-ANDROID-AUDIO-01
window.audioBlocked = false;

function _showTapToPlayBanner() {
    let el = document.getElementById('audio-unlock-banner');
    if (!el) {
        el = document.createElement('button');
        el.id = 'audio-unlock-banner';
        el.type = 'button';
        el.textContent = '\ud83d\udd0a Tap untuk lanjut memutar';
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

function unlockBrowserAudio(forcePlay) {
    if (audioUnlocked || _unlocking) {
        // PATCH-AUDIO-UNLOCK-RACE-01: kalau sudah unlocked sebelumnya tapi dipanggil lagi
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
}

function syncBrowserAudio(forcePlay) {
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
        // PATCH-ANDROID-AUDIO-01: track baru -> reset status block, kasih kesempatan baru
        // buat autoplay (banner lama kalau ada juga disembunyikan dulu).
        window.audioBlocked = false;
        if (typeof _hideTapToPlayBanner === "function") _hideTapToPlayBanner();
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
            // PATCH-AUDIO-UNLOCK-RACE-01: dulu cuma cek store.status === "PLAYING". Tapi
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
}

function initAudio() {
    document.addEventListener("click", unlockBrowserAudio);
}