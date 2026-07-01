"""
import_artists.py
----------------
Import artists.json ke SQLite database.

Usage:
    python import_artists.py                        # default: ytgui.db
    python import_artists.py --db path/to/your.db  # custom db path
    python import_artists.py --reset               # drop & recreate tables dulu

Schema:
    artists        — data utama artis
    artist_genres  — relasi artis <-> genre (many-to-many friendly)
    artist_seeds   — lagu populer per artis (buat seed yt-dlp)
"""

import sqlite3, json, argparse, os, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--db",    default="ytgui.db",   help="Path ke SQLite DB")
parser.add_argument("--json",  default="artists.json", help="Path ke artists.json")
parser.add_argument("--reset", action="store_true",  help="Drop tables sebelum import")
args = parser.parse_args()

json_path = Path(args.json)
if not json_path.exists():
    sys.exit(f"[ERROR] File tidak ditemukan: {json_path}")

con = sqlite3.connect(args.db)
cur = con.cursor()
cur.execute("PRAGMA journal_mode=WAL")
cur.execute("PRAGMA foreign_keys=ON")

if args.reset:
    cur.executescript("""
        DROP TABLE IF EXISTS artist_seeds;
        DROP TABLE IF EXISTS artist_genres;
        DROP TABLE IF EXISTS artists;
    """)
    print("[reset] Tables dropped.")

cur.executescript("""
    CREATE TABLE IF NOT EXISTS artists (
        id           INTEGER PRIMARY KEY,
        nama         TEXT    NOT NULL,
        kategori     TEXT    CHECK(kategori IN ('individu','band')),
        tahun_aktif  TEXT,
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS artist_genres (
        artist_id  INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
        genre      TEXT    NOT NULL,
        PRIMARY KEY (artist_id, genre)
    );

    CREATE TABLE IF NOT EXISTS artist_seeds (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_id  INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
        judul      TEXT    NOT NULL,
        urutan     INTEGER NOT NULL   -- urutan dari list lagu_populer
    );

    -- Index untuk radio mode (random pick by kategori/genre)
    CREATE INDEX IF NOT EXISTS idx_artists_kategori ON artists(kategori);
    CREATE INDEX IF NOT EXISTS idx_genres_genre     ON artist_genres(genre);
    CREATE INDEX IF NOT EXISTS idx_seeds_artist     ON artist_seeds(artist_id);
""")

data = json.loads(json_path.read_text(encoding="utf-8"))
artists = data["artists"]

inserted = 0
skipped  = 0

for a in artists:
    existing = cur.execute("SELECT id FROM artists WHERE id=?", (a["id"],)).fetchone()
    if existing and not args.reset:
        skipped += 1
        continue

    cur.execute("""
        INSERT OR REPLACE INTO artists (id, nama, kategori, tahun_aktif)
        VALUES (?, ?, ?, ?)
    """, (a["id"], a["nama"], a["kategori"], a["tahun_aktif"]))

    cur.execute("DELETE FROM artist_genres WHERE artist_id=?", (a["id"],))
    for genre in a["genre"]:
        cur.execute("INSERT OR IGNORE INTO artist_genres (artist_id, genre) VALUES (?,?)",
                    (a["id"], genre))

    cur.execute("DELETE FROM artist_seeds WHERE artist_id=?", (a["id"],))
    for urutan, judul in enumerate(a["lagu_populer"], 1):
        cur.execute("INSERT INTO artist_seeds (artist_id, judul, urutan) VALUES (?,?,?)",
                    (a["id"], judul, urutan))

    inserted += 1

con.commit()
con.close()

print(f"[done] Inserted: {inserted}, Skipped (already exist): {skipped}")
print(f"[db]   {os.path.abspath(args.db)}")
print()
print("Contoh query radio mode:")
print("  SELECT a.nama, s.judul FROM artists a")
print("  JOIN artist_seeds s ON s.artist_id = a.id AND s.urutan = 1")
print("  ORDER BY RANDOM() LIMIT 5;")
