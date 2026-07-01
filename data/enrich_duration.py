import json
import time
from ytmusicapi import YTMusic
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_duration(yt, video_id):
    try:
        res = yt.get_song(video_id)
        if res and 'videoDetails' in res and 'lengthSeconds' in res['videoDetails']:
            return int(res['videoDetails']['lengthSeconds'])
    except Exception as e:
        print(f"Error fetching {video_id}: {e}")
    return None

def main():
    input_file = "artists_enriched.json"
    output_file = "artists_enriched.json"

    print(f"Membaca {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    yt = YTMusic()

    songs_to_fetch = []
    for artist in data['artists']:
        for song in artist.get('lagu_populer', []):
            if song.get('youtube_id') and 'durasi' not in song:
                songs_to_fetch.append(song)

    if not songs_to_fetch:
        print("Semua lagu sudah memiliki durasi.")
        return

    print(f"Memproses {len(songs_to_fetch)} lagu untuk mengambil durasi secara paralel...")

    def process_song(song):
        dur = fetch_duration(yt, song['youtube_id'])
        if dur is not None:
            m, s = divmod(dur, 60)
            song['durasi'] = f"{m}:{s:02d}"
            song['durasi_detik'] = dur
        return dur

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_song, song): song for song in songs_to_fetch}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                print(f"Progress: {completed}/{len(songs_to_fetch)} lagu selesai diproses...")
                if completed % 200 == 0:
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"Auto-saved at {completed} songs.")

    print(f"Menyimpan hasil akhir ke {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Selesai! Metadata durasi berhasil ditambahkan.")

if __name__ == "__main__":
    main()
