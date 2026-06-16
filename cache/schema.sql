PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS tracks (
    video_id     TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    artist       TEXT,
    duration     INTEGER,
    view_count   INTEGER,
    thumbnail    TEXT,
    local_path   TEXT,           -- NULL if not downloaded
    stream_url   TEXT,           -- cached URL, can expire
    stream_url_ts INTEGER,       -- Unix timestamp when URL was fetched
    play_count   INTEGER DEFAULT 0,
    last_played  INTEGER,        -- Unix timestamp
    created_at   INTEGER DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_local_path ON tracks(local_path) WHERE local_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_last_played ON tracks(last_played DESC);
