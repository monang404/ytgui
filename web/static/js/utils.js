function formatTime(seconds) {
    if (!seconds || seconds < 0) return "00:00";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return String(minutes).padStart(2, "0") + ":" + String(remainingSeconds).padStart(2, "0");
}

window.safeStorage = {
    get: function(key) {
        try { return localStorage.getItem(key); } catch(e) { return null; }
    },
    set: function(key, value) {
        try { localStorage.setItem(key, value); } catch(e) {}
    },
    remove: function(key) {
        try { localStorage.removeItem(key); } catch(e) {}
    }
};

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function showConnectionToast(text, type) {
    dom.connectionToast.textContent = text;
    dom.connectionToast.className = "active " + type;
}

function hideConnectionToast() {
    dom.connectionToast.className = "";
}

let logToastTimer = null;
function showLogToast(text) {
    dom.logToast.textContent = text;
    dom.logToast.classList.add("active");
    if (logToastTimer) clearTimeout(logToastTimer);
    logToastTimer = setTimeout(() => {
        dom.logToast.classList.remove("active");
    }, 3000);
}

window.cleanTrackTitle = function(title) {
    if (!title) return "";
    return title.replace(/[\[\(].*?(official|music video|lyric|audio|live|performance).*?[\]\)]/gi, '')
                .replace(/#\S+/g, '')
                .replace(/\s{2,}/g, ' ')
                .replace(/\s+-\s*$/, '')
                .trim();
};

window.getCoverArt = async function(track) {
    if (!track) return "";
    if (!track.video_id) return track.thumbnail || "";
    
    const cacheKey = "cover_" + track.video_id;
    const cachedStr = window.safeStorage.get(cacheKey);
    if (cachedStr) {
        try {
            if (cachedStr.startsWith("{")) {
                const cached = JSON.parse(cachedStr);
                if (Date.now() - cached.ts < 7 * 24 * 60 * 60 * 1000) {
                    return cached.url;
                }
            } else {
                return cachedStr;
            }
        } catch(e) {}
    }
    
    const ytFallback = `https://i.ytimg.com/vi/${track.video_id}/mqdefault.jpg`;
    
    if (!track.title || !track.artist) {
        let fallback = track.thumbnail || ytFallback;
        if (typeof fallback === "string") {
            fallback = fallback.replace("hqdefault.jpg", "mqdefault.jpg").replace("sddefault.jpg", "mqdefault.jpg");
        }
        return fallback;
    }
    
    const saveCache = (url) => {
        window.safeStorage.set(cacheKey, JSON.stringify({url: url, ts: Date.now()}));
        return url;
    };
    
    try {
        const cleanTitle = window.cleanTrackTitle(track.title);
        const query = encodeURIComponent(track.artist + " " + cleanTitle);
        const response = await fetch(`https://itunes.apple.com/search?term=${query}&media=music&limit=1`);
        if (!response.ok) throw new Error("iTunes API failed");
        
        const data = await response.json();
        if (data.results && data.results.length > 0) {
            let artworkUrl = data.results[0].artworkUrl100;
            if (artworkUrl) {
                artworkUrl = artworkUrl.replace("100x100bb", "600x600bb");
                return saveCache(artworkUrl);
            }
        }
    } catch (e) {
        console.warn("Cover fetch error for", track.title, e);
    }
    
    return saveCache(ytFallback);
};

let _lazyCoverObserver = null;

window.loadLazyCovers = function() {
    if (!_lazyCoverObserver) {
        _lazyCoverObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    observer.unobserve(img);
                    img.classList.add('loaded');
                    const videoId = img.getAttribute('data-vid');
                    const title = img.getAttribute('data-title');
                    const artist = img.getAttribute('data-artist');
                    const defaultThumb = img.getAttribute('data-thumb');
                    
                    if (!videoId) return;
                    
                    const track = { video_id: videoId, title: title, artist: artist, thumbnail: defaultThumb };
                    window.getCoverArt(track).then(coverUrl => {
                        if (coverUrl) {
                            img.src = coverUrl;
                        }
                    });
                }
            });
        }, { rootMargin: '200px' });
    }

    const images = document.querySelectorAll('img.lazy-cover:not(.observed)');
    images.forEach((img) => {
        img.classList.add('observed');
        _lazyCoverObserver.observe(img);
    });
};

window.extractDominantColor = function(imageElement, callback) {
    if (!imageElement.complete || imageElement.naturalWidth === 0) {
        imageElement.addEventListener('load', () => window.extractDominantColor(imageElement, callback), { once: true });
        return;
    }
    
    try {
        const canvas = document.createElement('canvas');
        const canvasContext = canvas.getContext('2d', { willReadFrequently: true });
        canvas.width = 50;
        canvas.height = 50;
        canvasContext.drawImage(imageElement, 0, 0, 50, 50);
        
        const data = canvasContext.getImageData(0, 0, 50, 50).data;
        let bestR = 0, bestG = 0, bestB = 0;
        let maxScore = -1;
        
        for (let i = 0; i < data.length; i += 16) {
            let r = data[i], g = data[i+1], b = data[i+2];
            let max = Math.max(r, g, b), min = Math.min(r, g, b);
            let l = (max + min) / 2;
            
            if (l < 20 || l > 240) continue;
            
            let s = 0;
            if (max !== min) {
                s = l > 127 ? (max - min) / (510 - max - min) : (max - min) / (max + min);
            }
            
            let score = s * 100;
            if (score > maxScore) {
                maxScore = score;
                bestR = r; bestG = g; bestB = b;
            }
        }
        
        if (maxScore === -1) {
            let r = 0, g = 0, b = 0, count = 0;
            for (let i = 0; i < data.length; i += 16) {
                r += data[i]; g += data[i+1]; b += data[i+2]; count++;
            }
            bestR = Math.floor(r / count);
            bestG = Math.floor(g / count);
            bestB = Math.floor(b / count);
        }
        
        console.log("Cover Color Extracted:", bestR, bestG, bestB);
        if (callback) callback({r: bestR, g: bestG, b: bestB});
    } catch (e) {
        console.warn("Color extraction failed:", e);
        if (callback) callback("var(--bg-elevated)");
    }
};
