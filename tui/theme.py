# tui/theme.py
BG_VOID     = "#0D0D0D"
BG_PANEL    = "#141420"
BG_ELEVATED = "#1E1E30"
BORDER      = "#2a2a45"
BORDER_FOCUS = "#FFC107"
ACCENT_FIRE = "#FF6B35"
ACCENT_GOLD = "#FFC107"
TEXT_PRIMARY = "#E8E8FF"
TEXT_MUTED   = "#A0A0C0"
TEXT_DIM     = "#555580"
STATUS_OK    = "#4ade80"
STATUS_ERR   = "#ef4444"

# Breakpoint lebar kolom terminal — bukan device pixel, ini character columns
BREAKPOINT_LANDSCAPE = 80

# BARU — tinggi fixed tiap region, dipakai literal di CSS, supaya
# satu sumber kebenaran angka magic number tidak tersebar di banyak file
HEIGHT_TOP_BAR          = 3
HEIGHT_NOW_PLAYING      = 13
HEIGHT_TAB_BAR          = 3
HEIGHT_CONTROLS_ROW     = 3
HEIGHT_CONTROLS_TOTAL   = 11   # 3 baris tombol + 2 margin antar grup
MIN_SIDE_PANEL_HEIGHT   = 6    # ambang minimum sebelum masuk mode compact (Tahap 2)
