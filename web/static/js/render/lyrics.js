function renderLyrics() {
    if (!dom.lyricsPanel.classList.contains("active")) return;

    const lines = store.lyrics_lines;
    const idx = store.lyrics_index;

    if (!lines || lines.length === 0) {
        dom.lyricsContent.innerHTML = '<div style="color:var(--fm-text-5)">Tidak ada lirik tersedia</div>';
        return;
    }

    const start = Math.max(0, idx - 5);
    const end = Math.min(lines.length, idx + 6);

    let html = "";
    for (let i = start; i < end; i++) {
        const text = escapeHtml(lines[i]);
        if (i === idx) {
            html += '<div class="lyric-line active">▶ ' + text + " ◀</div>";
        } else if (i < idx) {
            html += '<div class="lyric-line past">' + text + "</div>";
        } else {
            html += '<div class="lyric-line future">' + text + "</div>";
        }
    }
    dom.lyricsContent.innerHTML = html;

    const activeLine = dom.lyricsContent.querySelector(".lyric-line.active");
    if (activeLine) {
        activeLine.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function updateOffsetDisplay() {
    if (!dom.lyricOffsetDisplay) return;
    const val = store.lyrics_offset || 0;
    const sign = val >= 0 ? '+' : '';
    dom.lyricOffsetDisplay.textContent = sign + val.toFixed(1) + 's';
}
