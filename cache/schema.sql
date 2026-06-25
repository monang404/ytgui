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
