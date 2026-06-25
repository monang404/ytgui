function formatTime(secs) {
    if (!secs || secs < 0) return "00:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
}

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
    const cached = localStorage.getItem(cacheKey);
    if (cached) return cached;
    
    const ytFallback = `https://i.ytimg.com/vi/${track.video_id}/hqdefault.jpg`;
    
    if (!track.title || !track.artist) {
        return track.thumbnail || ytFallback;
    }
    
    try {
        const cleanTitle = window.cleanTrackTitle(track.title);
        const query = encodeURIComponent(track.artist + " " + cleanTitle);
        const res = await fetch(`https://itunes.apple.com/search?term=${query}&media=music&limit=1`);
        if (!res.ok) throw new Error("iTunes API failed");
        
        const data = await res.json();
        if (data.results && data.results.length > 0) {
            let artworkUrl = data.results[0].artworkUrl100;
            if (artworkUrl) {
                artworkUrl = artworkUrl.replace("100x100bb", "600x600bb");
                localStorage.setItem(cacheKey, artworkUrl);
                return artworkUrl;
            }
        }
    } catch (e) {
        console.warn("Cover fetch error for", track.title, e);
    }
    
    localStorage.setItem(cacheKey, ytFallback);
    return ytFallback;
};

window.loadLazyCovers = function() {
    const images = document.querySelectorAll('img.lazy-cover:not(.loaded)');
    images.forEach(async (img) => {
        img.classList.add('loaded');
        const vid = img.getAttribute('data-vid');
        const title = img.getAttribute('data-title');
        const artist = img.getAttribute('data-artist');
        const defaultThumb = img.getAttribute('data-thumb');
        
        if (!vid) return;
        
        const track = { video_id: vid, title: title, artist: artist, thumbnail: defaultThumb };
        const coverUrl = await window.getCoverArt(track);
        if (coverUrl) {
            img.src = coverUrl;
        }
    });
};

window.extractDominantColor = function(imgEl, callback) {
    if (!imgEl.complete || imgEl.naturalWidth === 0) {
        imgEl.addEventListener('load', () => window.extractDominantColor(imgEl, callback), { once: true });
        return;
    }
    
    try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = 50;
        canvas.height = 50;
        ctx.drawImage(imgEl, 0, 0, 50, 50);
        
        const data = ctx.getImageData(0, 0, 50, 50).data;
        let r = 0, g = 0, b = 0, count = 0;
        
        for (let i = 0; i < data.length; i += 16) {
            r += data[i];
            g += data[i+1];
            b += data[i+2];
            count++;
        }
        
        r = Math.floor(r / count);
        g = Math.floor(g / count);
        b = Math.floor(b / count);
        
        console.log("Cover Color Extracted:", r, g, b);
        if (callback) callback({r, g, b});
    } catch (e) {
        console.warn("Color extraction failed:", e);
        if (callback) callback("var(--bg-elevated)");
    }
};
