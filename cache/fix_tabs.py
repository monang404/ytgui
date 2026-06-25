with open('web/static/js/render/tabs.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
# Remove the broken function
content = re.sub(r'function renderRecentRow\(\) \{.*', '', content, flags=re.DOTALL)

func_code = """
function renderRecentRow() {
    const container = document.getElementById('home-recent-list');
    if (!container) return;

    const items = store.discover_recent || [];
    if (items.length === 0) {
        container.innerHTML = '<div style="padding:24px 20px; color:var(--text-3); font-size:14px; text-align:center;">Belum ada riwayat putar</div>';
        return;
    }

    const currentId = store.current_track && store.current_track.video_id;
    container.innerHTML = items.slice(0, 8).map(track => {
        const title = typeof cleanTrackTitle === 'function' ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
        const thumb = track.thumbnail
            ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
            : '<i class="ti ti-music-note"></i>';
        const isCurrent = track.video_id && track.video_id === currentId;
        return `
        <div class="home-recent-item${isCurrent ? ' current' : ''}" data-vid="${escapeHtml(track.video_id || '')}">
            <div class="home-recent-thumb">${thumb}</div>
            <div class="home-recent-info">
                <div class="home-recent-title">${title}</div>
                <div class="home-recent-artist">${escapeHtml(track.artist || '')}</div>
            </div>
            <button class="home-recent-more" data-track='${JSON.stringify(track).replace(/'/g, "&apos;")}' aria-label="More">
                <i class="ti ti-dots-vertical"></i>
            </button>
        </div>`;
    }).join('');

    /* Click handlers */
    container.querySelectorAll('.home-recent-item').forEach(el => {
        el.addEventListener('click', (e) => {
            if (e.target.closest('.home-recent-more')) return;
            if (store.userRole !== 'admin') return;
            const vid = el.dataset.vid;
            if (!vid) return;
            const track = (store.discover_recent || []).find(t => t.video_id === vid);
            if (track) wsSend('play_track', track);
        });
    });

    container.querySelectorAll('.home-recent-more').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            try {
                const track = JSON.parse(btn.dataset.track);
                if (typeof showActionModal === 'function') showActionModal(track);
            } catch(_) {}
        });
    });
}
"""

with open('web/static/js/render/tabs.js', 'w', encoding='utf-8') as f:
    f.write(content.strip() + '\n\n' + func_code.strip() + '\n')

print('tabs.js fixed!')
