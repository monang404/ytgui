# PERFORMANCE AUDIT — bagas.fm / YTGUI

Findings are ranked by estimated real-world impact given the project's actual deployment target (single Python process, SQLite on local disk, a handful of concurrent LAN clients). Impact estimates are qualitative, based on reading the algorithms and query plans — no profiler was run against a live instance.

---

## Ranked Findings

### PERF-01 — Unbounded local disk growth: cleanup routines exist but are never scheduled
- **Impact:** High (long-running-install correctness/disk usage), Low (CPU)
- **Location:** `cache/db.py::evict_stale_tracks()` (56-80), `cache/db.py::cleanup_sessions()` (229-232); neither is called from `main.py`, `start.py`, or any `engine/` background task.
- **Root cause:** The cleanup logic was written and covered by tests but never wired into a periodic task, unlike other background work in the same codebase (`main.py` already runs `check_connectivity()` and `mpv_reconnect_checker()` via `safe_create_task` on a loop — the same pattern was simply never applied here).
- **Consequence:** `cache/mp3/` and the `tracks` table grow without bound for the lifetime of an installation; `sessions` rows for expired tokens accumulate forever (low absolute cost per row, but still dead weight on every `verify_session` query as the table grows).
- **Recommendation:** Add a `safe_create_task(periodic_cleanup(), name="db_cleanup")` in `main.py` that calls both methods on a daily interval (e.g., `asyncio.sleep(86400)` loop), following the exact pattern already used for `mpv_reconnect_checker`.
- **Expected benefit:** Bounded disk usage and query table sizes indefinitely, with no architecture change required — the fix is purely "call the function that already exists."

---

### PERF-02 — Missing index on `songs.artist_id` used in every radio/genre join
- **Impact:** Medium at current dataset size, growing linearly with catalog size
- **Location:** `cache/schema.sql` — `songs` table has `youtube_id` indexed (`idx_songs_youtube_id`) but **no index on `artist_id`**, despite `cache/db.py::get_random_songs` (263-303), `get_artist_songs_strict` (305-326), and `get_genre_songs` (328-357) all `JOIN songs s ON s.artist_id = a.id` (or via `artist_genres`) as their primary access pattern, combined with a window function (`ROW_NUMBER() OVER (PARTITION BY s.artist_id ...)`) that also benefits directly from an index on that column.
- **Root cause:** `artist_id` is a `FOREIGN KEY` in the schema but SQLite does not automatically index foreign keys (unlike some other RDBMSs), and no explicit `CREATE INDEX` was added for it.
- **Recommendation:** `CREATE INDEX IF NOT EXISTS idx_songs_artist_id ON songs(artist_id);`
- **Expected benefit:** At current data volumes (the shipped `data/artists.json` suggests a few hundred artists / low thousands of songs) this is a minor win; but Radio Mode's `_gather_batch` runs on essentially every track transition, so the win compounds over the life of a long listening session, and becomes significant if the artist catalog grows 10-100x.

---

### PERF-03 — `search()` always fetches exactly 10 results from yt-dlp regardless of the requested `max_results`
- **Impact:** Low-Medium (network + yt-dlp extraction cost)
- **Location:** `engine/ytdlp_client.py:37-40` — `url = f"ytsearch10:{query}"` is hardcoded; the `max_results` parameter is only used afterward to `break` out of the local result-filtering loop (line 64), not to size the actual yt-dlp search.
- **Root cause:** The `ytsearchN:` prefix was hardcoded rather than built from `max_results`.
- **Consequence:** Every search call pays the full cost of extracting metadata for 10 YouTube results even if the caller only wanted (or the UI only shows) fewer — and if a caller ever legitimately requests more than 10 (`max_results=15` is the type hint's own default in `core/ports.py::MediaExtractorPort.search`), it will silently receive at most 10, which is a **functional** bug as well as a performance one.
- **Recommendation:** `url = f"ytsearch{max_results}:{query}"`.
- **Expected benefit:** Correct behavior when `max_results != 10`; avoids wasted extraction work when fewer results are needed.

---

### PERF-04 — WebSocket broadcast sends to all connections sequentially, one `await` at a time
- **Impact:** Low today (few LAN clients), becomes linear-latency-per-client if listener count grows
- **Location:** `server/handlers/websocket.py::ConnectionManager.broadcast()` (45-54)
```python
for ws in self.active_connections:
    try:
        await ws.send_str(data)
    except Exception:
        dead.append(ws)
```
- **Root cause:** Sends are awaited one after another rather than concurrently.
- **Consequence:** With N connected clients, a broadcast (which happens on every state change — track start, progress tick, queue update) takes roughly N × (per-send latency) instead of max(per-send latency). For a handful of LAN clients this is sub-millisecond and invisible; it would only matter if the "client mode / listen-only" audience the README describes (multiple household members listening passively) grew into the dozens.
- **Recommendation:** `await asyncio.gather(*(ws.send_str(data) for ws in self.active_connections), return_exceptions=True)`, then filter failures from the results instead of via try/except per iteration.
- **Expected benefit:** Broadcast latency becomes constant instead of linear in listener count; not urgent at current scale but cheap to fix now.

---

### PERF-05 — `DiscoverService` performs five independent sequential queries per call, on the hot path of two different websocket actions
- **Impact:** Low-Medium
- **Location:** `services/discover_service.py` — `get_recent`, `get_favorites`, `get_cached`, `get_featured_artists`, `get_featured_genres` are each separate `await self.db._conn.execute(...)` calls, and `server/handlers/websocket.py`'s `discover`, `toggle_favorite`, and `delete_download` handlers all `await` them one after another (see CQ-04 in `CODE_QUALITY_REPORT.md` for the duplication angle on the same code).
- **Root cause:** No use of `asyncio.gather` to parallelize independent read queries against the same (single, shared) SQLite connection.
- **Consequence:** Each of these three actions pays the sum of five query latencies instead of their max. Because `aiosqlite` serializes all operations on a single background thread, true parallel execution across the *same connection* is not actually available here — `asyncio.gather` would only help if there is meaningful "wait" time interleaved (e.g., row iteration) rather than pure CPU-bound SQLite work, so the realistic win is smaller than it would be with a true async driver, but still non-zero for the I/O-bound portions.
- **Recommendation:** Low priority given the single-connection constraint; if this becomes a bottleneck, the more effective fix is a connection pool (see `ARCHITECTURE_AUDIT.md` note on `Database._conn`) rather than just `gather`-ing on one connection.

---

### PERF-06 — Frontend: `discover.js` fully replaces `innerHTML` on every update instead of reusing DOM nodes
- **Impact:** Low-Medium (perceived UI smoothness on lower-end phones, the primary target device per the README)
- **Location:** `web/static/js/render/discover.js::renderDiscoverTab()` — every section (`discFavorites`, `discRecent`, `discArtists`, `discGenres`, `discCached`) does `container.innerHTML = items.map(...).join('')` on every `discover_data` websocket push.
- **Contrast:** `web/static/js/render/queue.js::renderList()` (lines 20-51) deliberately reuses existing DOM nodes (`existing[i]`, only creating/removing the delta) specifically to avoid this cost.
- **Consequence:** Every discover-tab update destroys and recreates every card's DOM subtree, forcing full layout/paint of that section, discarding any transient state (scroll position within the section, the `.observed`/`.loaded` classes used by the `IntersectionObserver`-based lazy cover loader in `utils.js`, meaning **already-loaded cover art thumbnails get reset and re-fetched** from the iTunes API / re-observed on every discover-tab refresh). This is a real, if modest, source of both wasted network calls (repeat iTunes lookups already cached in `localStorage` are still cheap, but the re-observe/re-render churn is not free) and visual "flicker" on data refresh.
- **Recommendation:** Apply the same reuse-existing-elements pattern already implemented in `queue.js::renderList` to `discover.js`.
- **Expected benefit:** Smoother discover-tab updates, fewer redundant lazy-cover re-triggers, consistent rendering strategy across the frontend (also a code-quality win — currently two different rendering philosophies coexist in the same app).

---

### PERF-07 — `_pick_audio_url` iterates every format on every stream resolution with no caching of format-selection outcome across the reversed list scan
- **Impact:** Negligible
- **Location:** `engine/ytdlp_client.py:139-144` — `for format_info in reversed(formats): ...` is O(formats), typically tens of entries; this is not a real bottleneck, noted only because it's the kind of thing that looks worse than it is — the actual expensive operation is the preceding network/extraction call (already correctly given a 25s timeout via `YTDLP_RESOLVE_TIMEOUT_SEC`), not this loop.
- **Recommendation:** No action needed; included here only to document that it was checked and is not a concern.

---

## Summary Table

| ID | Area | Impact | Effort to Fix |
|---|---|---|---|
| PERF-01 | Backend / disk | High (correctness over time) | Small |
| PERF-02 | Database | Medium, scales with catalog | Small |
| PERF-03 | yt-dlp integration | Low-Medium, also a correctness bug | Small |
| PERF-04 | WebSocket broadcast | Low today, scales with listeners | Small |
| PERF-05 | Discover queries | Low-Medium | Medium (needs connection-pool discussion) |
| PERF-06 | Frontend rendering | Low-Medium (UX smoothness) | Medium |
| PERF-07 | yt-dlp format pick | Negligible | N/A |
