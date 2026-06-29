PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS tracks (
    video_id     TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    artist       TEXT,
    duration     INTEGER,
    view_count   INTEGER,
    thumbnail    TEXT,
    local_path   TEXT,           -- NULL if not downloaded
    stream_url   VARCHAR(2048),  -- cached URL, can expire
    stream_url_ts INTEGER,       -- Unix timestamp when URL was fetched
    play_count   INTEGER DEFAULT 0,
    last_played  INTEGER,        -- Unix timestamp
    is_favorite  INTEGER DEFAULT 0, -- 1 if liked, 0 otherwise
    created_at   INTEGER DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_local_path ON tracks(local_path) WHERE local_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_last_played ON tracks(last_played DESC);
CREATE INDEX IF NOT EXISTS idx_play_count ON tracks(play_count DESC) WHERE play_count > 0;
CREATE INDEX IF NOT EXISTS idx_stream_url_ts ON tracks(stream_url_ts);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL
);

-- Artists untuk Radio Mode seed
-- Diisi via: python data/import_artists.py --db data/ytgui.db --json data/artists.json
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
    urutan     INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artists_kategori ON artists(kategori);
CREATE INDEX IF NOT EXISTS idx_genres_genre     ON artist_genres(genre);
CREATE INDEX IF NOT EXISTS idx_seeds_artist     ON artist_seeds(artist_id);
