# tui/theme.py
# Claude/Anthropic Brand Palette
BG_VOID      = "#141413"    # Dark
BG_PANEL     = "#1c1c1b"    # Dark + panel elevation
BG_ELEVATED  = "#242422"    # Dark + elevated surface
BORDER       = "#b0aea5"    # Mid Gray
BORDER_FOCUS = "#d97757"    # Orange (aksen utama)
ACCENT_FIRE  = "#d97757"    # Orange — aksen utama Claude
ACCENT_GOLD  = "#d97757"    # Orange — alias untuk backward compat
ACCENT_BLUE  = "#6a9bcc"    # Blue — aksen sekunder
ACCENT_GREEN = "#788c5d"    # Green — aksen tersier
TEXT_PRIMARY = "#faf9f5"    # Light
TEXT_MUTED   = "#b0aea5"    # Mid Gray
TEXT_DIM     = "#706f66"    # Dim variant
STATUS_OK    = "#788c5d"    # Green Claude
STATUS_ERR   = "#c45040"    # Warm red

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

# V2 additions
CARD_WIDTH          = 18
CARD_HEIGHT         = 3
CARD_BORDER         = "round"
ROW_GAP             = 1
SECTION_TITLE_MARGIN= 1

HEIGHT_NAV_BAR      = 3    # tinggi bottom navigation
NAV_ACTIVE_COLOR    = ACCENT_FIRE
NAV_INACTIVE_COLOR  = TEXT_DIM
TAB_HOME   = "home"
TAB_SEARCH = "search"
TAB_RADIO  = "radio"
TAB_QUEUE  = "queue"
