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
    }
    return localAudio;
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
            syncBrowserAudio(); 
        });
    } else {
        audioUnlocked = true;
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
