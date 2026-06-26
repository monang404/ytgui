#!/bin/bash
# =============================================
# Fix Bug Progress Bar Thumb (Titik Tidak Tengah)
# YTGUI - bagas.fm
# =============================================

echo "🔧 Memperbaiki Progress Bar Thumb..."

# Fix 1: player.css
cat > /dev/stdout << 'EOF' | sed -i '/\.pb-progress-track/,+10 s/.*margin-top: -9px.*//g' web/static/css/player.css
.pb-progress-track {
  min-height: 44px;
  touch-action: none;
  position: relative;
}

.pb-thumb {
  width: 22px;
  height: 22px;
}
EOF

# Fix 2: base.css (thumb centering yang lebih baik)
sed -i '/\.pb-thumb[[:space:]]*{/,+20 s/width: 16px;/width: 18px;/' web/static/css/base.css 2>/dev/null || true

sed -i '/\.pb-thumb[[:space:]]*{/,+20 s/height: 16px;/height: 18px;/' web/static/css/base.css 2>/dev/null || true

cat >> web/static/css/base.css << 'CSS' 2>/dev/null || true

/* FIX PROGRESS BAR THUMB - CENTERED */
.pb-progress-track {
  position: relative;
  min-height: 44px;
  touch-action: none;
}

.pb-thumb {
  position: absolute;
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%) !important;
  width: 18px;
  height: 18px;
  background: var(--accent);
  border: 2px solid #090A0D;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(242, 181, 68, 0.4);
  z-index: 10;
  opacity: 0;
  transition: all 0.2s ease;
}

.pb-track:hover .pb-thumb,
body[data-active-tab="home"] .pb-track .pb-thumb {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1.2) !important;
}
CSS

echo "✅ Perbaikan selesai!"
echo "🔄 Silakan restart aplikasi:"
echo "   python main.py"
echo ""
echo "Kemudian refresh browser Anda."
