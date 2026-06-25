let localAudio = null;
let audioUnlocked = false;
let _lastLoadedVideoId = null;

function getOrInitAudio() {
    if (!localAudio) {
        localAudio = new Audio();
        localAudio.preload = "auto";
        localAudio.crossOrigin = "anonymous";
        localAudio.onerror = (e) => {
            const err = localAudio.error;
            if (!err) return;
            if (err.code === 1) return; // MEDIA_ERR_ABORTED (e.g. changing src quickly)
            if (err.code === 4 && localAudio.src.includes("data:audio")) return; // Ignore dummy audio error

            const errMsg = err.message || ("code " + err.code);
            if (errMsg.includes("Empty src") || !localAudio.getAttribute("src")) {
                return;
            }
            console.warn("Browser audio error:", err.code, errMsg);
            // Hanya tampilkan toast jika bukan dummy
            showLogToast("⚠️ Audio stream info: " + errMsg);
        };
        localAudio.addEventListener("timeupdate", () => {
            if (store.userRole === "client" || store.audio_output === "browser") {
                if (!window.isDraggingPb) {
                    store.position = localAudio.currentTime;
                    renderProgress();
                    renderPlayerBar();
                }
                if (typeof syncLocalLyrics === "function") {
                    syncLocalLyrics();
                }
            }
        });
    }
    return localAudio;
}

let audioCtx = null;
let analyser = null;
let dataArray = null;

function initVisualizer() {
    if (audioCtx || !localAudio) return;
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioContext();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        
        const source = audioCtx.createMediaElementSource(localAudio);
        source.connect(analyser);
        analyser.connect(audioCtx.destination);
        
        dataArray = new Uint8Array(analyser.frequencyBinCount);
        startVisualizerLoop();
    } catch (e) {
        console.warn("Visualizer init failed:", e);
    }
}

function startVisualizerLoop() {
    if (!analyser || !dom.vinylRecord) return;
    requestAnimationFrame(startVisualizerLoop);
    
    const isBrowser = store.userRole === "client" || store.audio_output === "browser";
    if (!isBrowser || store.status !== "PLAYING") {
        if (dom.tabHome) {
            dom.tabHome.style.removeProperty('--beat-glow-opacity');
            dom.tabHome.style.removeProperty('--beat-bg-brightness');
            dom.tabHome.style.removeProperty('--beat-glow-transition');
        }
        return;
    }
    
    analyser.getByteFrequencyData(dataArray);
    
    let bassSum = 0;
    for (let i = 0; i < 10; i++) {
        bassSum += dataArray[i];
    }
    const bassAvg = bassSum / 10;
    const ratio = bassAvg / 255;
    
    const glowOpacity = 0.4 + (ratio * 0.2);
    const bgBrightness = 0.2 + (ratio * 0.1);
    const transitionTime = ratio > 0.4 ? '0.2s' : '0.4s';
    
    if (dom.tabHome) {
        dom.tabHome.style.setProperty('--beat-glow-opacity', glowOpacity.toFixed(3));
        dom.tabHome.style.setProperty('--beat-bg-brightness', bgBrightness.toFixed(3));
        dom.tabHome.style.setProperty('--beat-glow-transition', transitionTime);
    }
}

function unlockBrowserAudio() {
    if (audioUnlocked) return;
    const audio = getOrInitAudio();
    
    if (!audio.src || audio.src === window.location.href || audio.src === window.location.origin + "/") {
        audio.src = "data:audio/mpeg;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU5LjI3LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAEAAABIAD+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+/v7+AAAAAExhdmM1OS4zNy4xMDBHAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0gAAAAARTmZ//MUZAYAAAGkAAAAAAAAA0gAAAAARTmZ//MUZAwAAAGkAAAAAAAAA0gAAAAARTmZ";
    }
    
    audio.volume = 0;
    const p = audio.play();
    if (p !== undefined) {
        p.catch((err) => {
            console.warn("Unlock play failed:", err);
        }).finally(() => {
            audioUnlocked = true;
            initVisualizer();
            if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
            syncBrowserAudio(); 
        });
    } else {
        audioUnlocked = true;
        initVisualizer();
        if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
        syncBrowserAudio();
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
        
        audio.oncanplay = () => {
            if (store.position > 2 && Math.abs(audio.currentTime - store.position) > 2) {
                audio.currentTime = store.position;
            }
            audio.oncanplay = null;
        };
        
        audio.onended = () => {
            console.log("Browser audio ended, requesting next track");
            if (store.audio_output === "browser") {
                wsSend("next", { video_id: track.video_id });
            }
        };
        
        audio.load();
    }

    audio.volume = Math.max(0, Math.min(1, (store.volume || 80) / 100));

    if (store.status === "PLAYING") {
        if (audio.paused && audio.src) {
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(err => console.warn("Autoplay prevented:", err));
            }
        }
    } else {
        if (!audio.paused) {
            audio.pause();
        }
    }
}

function initAudio() {
    document.addEventListener("click", unlockBrowserAudio, { once: true });
    document.addEventListener("touchstart", unlockBrowserAudio, { once: true });
}
