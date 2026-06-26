#!/bin/bash
set -e

echo "🚀 YTGUI Mobile Patch v2 - Fixed Version (No /tmp dependency)"

PROJECT_ROOT="$(pwd)"
if [ ! -f "$PROJECT_ROOT/main.py" ]; then
    echo "❌ Jalankan dari root ytgui-main/"
    exit 1
fi

WEB_JS="$PROJECT_ROOT/web/static/js"
WEB_CSS="$PROJECT_ROOT/web/static/css"

echo "Membersihkan perubahan lama yang bermasalah..."
sed -i '/safe-area-inset-top/d' "$WEB_JS/main.js" 2>/dev/null || true
sed -i '/--sat/d' "$WEB_JS/main.js" 2>/dev/null || true

echo "Menerapkan patch yang diperbaiki..."

# Bug 1: Visual Viewport + Safe Area (cleaner)
sed -i '/app.style.height = window.visualViewport.height + '\''px'\'';/a\
            document.documentElement.style.setProperty("--sat", "env(safe-area-inset-top)");\
            document.documentElement.style.setProperty("--sab", "env(safe-area-inset-bottom)");' "$WEB_JS/main.js"

# Bug 4 & 8: CSS improvements
cat >> "$WEB_CSS/player.css" << 'CSS1'
.pb-progress-track { min-height: 44px; touch-action: none; }
.pb-thumb { width: 22px; height: 22px; margin-top: -9px; }
CSS1

cat >> "$WEB_CSS/layout.css" << 'CSS2'
.nav-tabs { overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.nav-tabs::-webkit-scrollbar { display: none; }
CSS2

cat >> "$WEB_CSS/tabs.css" << 'CSS3'
@media (max-width: 480px) {
    .discover-section, .fav-card, .sr-item { flex: 1 1 100%; min-width: 0; }
}
CSS3

# Bug 7: Swipe gesture (clean)
if ! grep -q "touchStartX" "$WEB_JS/main.js"; then
    cat >> "$WEB_JS/main.js" << 'SWIPE'
    
// Mobile Swipe for Next/Prev
let touchStartX = 0;
document.addEventListener('touchstart', e => {
    if (e.touches.length === 1) touchStartX = e.touches[0].screenX;
});
document.addEventListener('touchend', e => {
    if (e.changedTouches.length === 1) {
        const touchEndX = e.changedTouches[0].screenX;
        if (Math.abs(touchEndX - touchStartX) > 80) {
            if (touchEndX < touchStartX) cmd('next');
            else cmd('prev');
        }
    }
});
SWIPE
fi

echo "✅ Patch v2 Fixed selesai dijalankan."
echo "🔄 Silakan restart aplikasi:"
echo "   python main.py"
