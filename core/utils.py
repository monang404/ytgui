import re
from pathlib import Path
from config import BASE_DIR

def user_download_path(artist: str, title: str) -> Path:
    safe_artist = re.sub(r'[\\/*?:"<>|]', "", artist)
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    return BASE_DIR / "downloads" / f"{safe_artist} - {safe_title}.mp3"
