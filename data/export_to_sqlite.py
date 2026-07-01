import json
import sqlite3
import os

def create_tables(cursor):
    cursor.execute('DROP TABLE IF EXISTS songs')
    cursor.execute('DROP TABLE IF EXISTS artist_genres')
    cursor.execute('DROP TABLE IF EXISTS genres')
    cursor.execute('DROP TABLE IF EXISTS artists')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artists (
        id INTEGER PRIMARY KEY,
        nama TEXT NOT NULL,
        kategori TEXT,
        tahun_aktif TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_genre TEXT UNIQUE NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artist_genres (
        artist_id INTEGER,
        genre_id INTEGER,
        PRIMARY KEY (artist_id, genre_id),
        FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE,
        FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_id INTEGER,
        judul TEXT NOT NULL,
        youtube_id TEXT UNIQUE NOT NULL,
        duration INTEGER DEFAULT 0,
        FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE
    )
    ''')

def main():
    json_file = 'artists_enriched.json'
    db_file = 'ytgui.db'

    if not os.path.exists(json_file):
        print(f"Error: File {json_file} tidak ditemukan!")
        return

    print(f"Membaca data dari {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Menghubungkan ke database {db_file}...")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    create_tables(cursor)

    total_artists = 0
    total_songs = 0
    total_genres = set()

    print("Mengekspor data ke SQLite, mohon tunggu sebentar...")

    for artist in data.get('artists', []):
        artist_id = artist['id']

        cursor.execute('''
        INSERT OR REPLACE INTO artists (id, nama, kategori, tahun_aktif)
        VALUES (?, ?, ?, ?)
        ''', (artist_id, artist['nama'], artist['kategori'], artist['tahun_aktif']))
        total_artists += 1

        for genre_name in artist.get('genre', []):
            total_genres.add(genre_name)
            cursor.execute('''
            INSERT OR IGNORE INTO genres (nama_genre)
            VALUES (?)
            ''', (genre_name,))

            cursor.execute('SELECT id FROM genres WHERE nama_genre = ?', (genre_name,))
            genre_id = cursor.fetchone()[0]

            cursor.execute('''
            INSERT OR IGNORE INTO artist_genres (artist_id, genre_id)
            VALUES (?, ?)
            ''', (artist_id, genre_id))

        for lagu in artist.get('lagu_populer', []):
            youtube_id = lagu.get('youtube_id')
            if youtube_id:
                duration = lagu.get('durasi_detik', 0)
                cursor.execute('''
                INSERT OR IGNORE INTO songs (artist_id, judul, youtube_id, duration)
                VALUES (?, ?, ?, ?)
                ''', (artist_id, lagu['judul'], youtube_id, duration))

                if cursor.rowcount > 0:
                    total_songs += 1
                else:
                    cursor.execute('''
                    UPDATE songs SET duration = ? WHERE youtube_id = ? AND duration = 0
                    ''', (duration, youtube_id))

    conn.commit()
    conn.close()

    print("\n" + "="*40)
    print("EKSPOR SELESAI!")
    print(f"Total Artis diekspor : {total_artists}")
    print(f"Total Genre unik     : {len(total_genres)}")
    print(f"Total Lagu diekspor  : {total_songs}")
    print("="*40)
    print(f"Database Anda telah siap di file '{db_file}'! ✨")

if __name__ == '__main__':
    main()
