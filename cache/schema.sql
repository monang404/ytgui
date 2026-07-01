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
CREATE TABLE IF NOT EXISTS artists (
    id INTEGER PRIMARY KEY,
    nama TEXT NOT NULL,
    kategori TEXT,
    tahun_aktif TEXT
);

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_genre TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS artist_genres (
    artist_id INTEGER,
    genre_id INTEGER,
    PRIMARY KEY (artist_id, genre_id),
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_id INTEGER,
    judul TEXT NOT NULL,
    youtube_id TEXT UNIQUE NOT NULL,
    duration INTEGER DEFAULT 0,
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artists_kategori ON artists(kategori);
CREATE INDEX IF NOT EXISTS idx_songs_youtube_id ON songs(youtube_id);
CREATE INDEX IF NOT EXISTS idx_songs_artist_id ON songs(artist_id);
