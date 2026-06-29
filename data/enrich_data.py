import json
import time
import random
import re
import os
from ytmusicapi import YTMusic

def clean_title(title, artist_name):
    # Hapus isi dalam kurung () atau [] seperti (Official Music Video), [Lyrics], dll
    t = re.sub(r'[\(\[].*?[\)\]]', '', title).lower()
    # Hapus nama artis jika terselip di judul (contoh: "Mahalini - Sial")
    t = t.replace(artist_name.lower(), '')
    # Hapus kata-kata umum yang sering mengganggu
    for word in ['official', 'music', 'video', 'lyric', 'lyrics', 'audio', 'live', '-', 'ft', 'feat', '.', ',']:
        t = t.replace(word, '')
    # Hapus semua karakter kecuali huruf dan angka untuk pencocokan yang sangat ketat
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def deduplicate_songs(song_list, artist_name, max_items=10):
    unique_songs = []
    seen_ids = set()
    seen_titles = set()
    
    for song in song_list:
        if len(unique_songs) >= max_items:
            break
            
        vid_id = song.get('videoId')
        raw_title = song.get('title', '')
        duration = song.get('duration_seconds', 0)
        
        # Bersihkan judul untuk pengecekan anti duplikasi yang lebih cerdas
        base_title = clean_title(raw_title, artist_name)
        
        # Simpan jika ID dan Title dasarnya belum pernah ada
        if vid_id and vid_id not in seen_ids and base_title not in seen_titles and base_title != "":
            # Tetap simpan judul aslinya, bukan yang sudah dibersihkan
            unique_songs.append({"judul": raw_title, "youtube_id": vid_id, "duration": duration})
            seen_ids.add(vid_id)
            seen_titles.add(base_title)
            
    return unique_songs

def get_artist_songs(ytmusic, artist_name):
    print(f"Mencari lagu untuk: {artist_name}...")
    all_raw_songs = []
    
    try:
        # Coba cari artisnya dulu untuk hasil yang lebih akurat (Top Songs dari Profil Artis)
        artists = ytmusic.search(artist_name, filter="artists")
        if artists and 'browseId' in artists[0]:
            artist_id = artists[0]['browseId']
            artist_info = ytmusic.get_artist(artist_id)
            
            # Cek apakah bagian 'songs' ada di dalam info artis
            if 'songs' in artist_info and 'results' in artist_info['songs']:
                top_songs = artist_info['songs']['results']
                if top_songs:
                    all_raw_songs.extend(top_songs)
    except Exception as e:
        print(f"  [-] Gagal dari profil artis ({e}), mencoba fallback...")
        
    current_unique = deduplicate_songs(all_raw_songs, artist_name, max_items=10)
    
    # Jika hasil pencarian profil artis kurang dari 10, tambahkan pencarian lagu
    if len(current_unique) < 10:
        try:
            print(f"  [*] Baru dapat {len(current_unique)} lagu unik, melakukan pencarian tambahan...")
            # Limit besar agar setelah diduplikasi tetap bisa dapat banyak
            songs = ytmusic.search(artist_name, filter="songs", limit=40)
            all_raw_songs.extend(songs)
        except Exception as e:
            print(f"  [-] Error mencari lagu tambahan: {e}")
            
    # Kembalikan hasil gabungan
    return deduplicate_songs(all_raw_songs, artist_name, max_items=10)

def main():
    input_file = "artists.json"
    output_file = "artists_enriched.json"
    
    print("Inisialisasi YTMusic...")
    ytmusic = YTMusic()

    # Cek apakah file progress (enriched) sudah ada agar bisa lanjut dari progress sebelumnya
    if os.path.exists(output_file):
        print(f"Melanjutkan progress dari {output_file}...")
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"Membaca {input_file}...")
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    total = len(data['artists'])
    
    for i, artist in enumerate(data['artists']):
        # Cek apakah artis ini sudah diproses dan lagunya sudah lengkap 10
        lagu = artist.get('lagu_populer', [])
        if lagu and isinstance(lagu[0], dict) and 'youtube_id' in lagu[0]:
            if len(lagu) >= 10:
                print(f"Progress: {i+1}/{total} | Melewati {artist['nama']} (Sudah lengkap 10 lagu).")
                continue
            else:
                print(f"Progress: {i+1}/{total} | Melengkapi {artist['nama']} (Baru punya {len(lagu)} lagu unik).")

        # Jeda acak (2 hingga 5 detik) untuk mencegah rate limit / IP Ban dari YouTube
        delay = random.uniform(2, 5)
        print(f"\nMenunggu {delay:.1f} detik sebelum request selanjutnya...")
        time.sleep(delay)
        
        songs = get_artist_songs(ytmusic, artist['nama'])
        
        # Format ke array of object
        if songs:
            artist['lagu_populer'] = songs
            print(f"  [+] Ditemukan {len(songs)} lagu untuk {artist['nama']}.")
        else:
            # Jika gagal, konversi lagu populer lama (array string) ke format baru tanpa ID
            lama = artist.get('lagu_populer', [])
            print(f"  [-] Tidak ditemukan lagu di YouTube untuk {artist['nama']}. Menggunakan data lama.")
            artist['lagu_populer'] = [{"judul": judul, "youtube_id": None} for judul in lama]
            
        print(f"Progress: {i+1}/{total}\n")

        # Simpan progress sementara setiap kelipatan 5 atau jika ini adalah artis terakhir
        if (i + 1) % 5 == 0 or (i + 1) == total:
            print(f"  [!] Auto-save: Menyimpan progress ke {output_file}...\n")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Menyimpan ke {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Selesai! Data berhasil disimpan.")

if __name__ == "__main__":
    main()
