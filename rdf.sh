#!/usr/bin/env bash
# radio_fix.sh — Patch radio mode: 3 bug fix + fitur seed lagu populer dari DB
# Usage: bash radio_fix.sh (dari root project ytgui-main)

set -e

PC="engine/playback_controller.py"
RE="engine/radio_engine.py"

echo "=== Cek file ==="
[ -f "$PC" ] || { echo "ERROR: $PC tidak ditemukan. Jalankan dari root project."; exit 1; }
[ -f "$RE" ] || { echo "ERROR: $RE tidak ditemukan. Jalankan dari root project."; exit 1; }

echo "=== Backup ==="
cp "$PC" "$PC.bak_radiofix"
cp "$RE" "$RE.bak_radiofix"
echo "Backup: $PC.bak_radiofix"
echo "Backup: $RE.bak_radiofix"

# ─────────────────────────────────────────────────────────────
# BUG 1 & 3 — playback_controller.py
# Fix: tambah room_id di QueueUpdatedEvent & LogMessageEvent,
#      dan reset _artist_rotation sebelum fetch ulang
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== [1/2] Patch $PC ==="

python3 - "$PC" <<'PYEOF'
import sys

path = sys.argv[1]
old = open(path).read()

OLD = (
    "                await self.bus.publish(QueueUpdatedEvent())\n"
    "                \n"
    "                await self.bus.publish(LogMessageEvent(message=\"Mengacak ulang stasiun radio...\"))\n"
    "                # Panggil fetch dengan seed jika ada, jika tidak None\n"
    "                await self.radio_mode._fetch_and_play_initial(self, seed_artist=seed)"
)

NEW = (
    "                await self.bus.publish(QueueUpdatedEvent(room_id=self.room_id))\n"
    "                \n"
    "                # Reset rotasi artis agar sesi acak benar-benar fresh\n"
    "                self.radio_mode._artist_rotation = []\n"
    "                \n"
    "                await self.bus.publish(LogMessageEvent(message=\"Mengacak ulang stasiun radio...\", room_id=self.room_id))\n"
    "                # Panggil fetch dengan seed jika ada, jika tidak None\n"
    "                await self.radio_mode._fetch_and_play_initial(self, seed_artist=seed)"
)

if OLD not in old:
    print("ERROR: Pola target tidak ditemukan di", path)
    print("Mungkin file sudah pernah di-patch atau berbeda versi.")
    sys.exit(1)

new = old.replace(OLD, NEW, 1)
open(path, "w").write(new)
print("OK: QueueUpdatedEvent & LogMessageEvent ditambah room_id, _artist_rotation direset")
PYEOF

# ─────────────────────────────────────────────────────────────
# BUG 2 + FITUR SEED — radio_engine.py
# Fix 1: reset _artist_rotation di on_activated
# Fix 2: _search_artist pakai lagu populer dari DB sebagai query,
#         fallback ke "{artist} music" kalau seed kosong
# ─────────────────────────────────────────────────────────────
echo ""
echo "=== [2/2] Patch $RE ==="

python3 - "$RE" <<'PYEOF'
import sys

path = sys.argv[1]
old = open(path).read()

# --- Patch A: reset _artist_rotation di on_activated ---
OLD_A = (
    "        await self._ensure_artists_loaded()\n"
    "        self.state.radio_queue.clear()\n"
    "        seed_artist = random.choice(self._seed_artists)\n"
    "        _track_task(self._bg_tasks, self._fetch_and_play_initial(controller, seed_artist), name=\"radio_initial\")"
)

NEW_A = (
    "        await self._ensure_artists_loaded()\n"
    "        self.state.radio_queue.clear()\n"
    "        # Reset deck rotasi agar tiap sesi baru benar-benar dikocok ulang\n"
    "        self._artist_rotation = []\n"
    "        seed_artist = random.choice(self._seed_artists)\n"
    "        _track_task(self._bg_tasks, self._fetch_and_play_initial(controller, seed_artist), name=\"radio_initial\")"
)

if OLD_A not in old:
    print("ERROR: Pola A (on_activated) tidak ditemukan di", path)
    sys.exit(1)

new = old.replace(OLD_A, NEW_A, 1)

# --- Patch B: ganti seluruh _search_artist dengan versi seed-aware ---
OLD_B = (
    "    async def _search_artist(self, artist: str) -> list:\n"
    "        \"\"\"Cari track untuk satu artis, filter durasi + exclusion, lalu\n"
    "        dedup berdasarkan judul yang dinormalisasi (biar 'Rasa Ini' versi\n"
    "        official video/lyric/audio tidak terhitung sebagai 3 lagu beda).\n"
    "        Mengembalikan sekitar TRACKS_PER_ARTIST_TARGET track unik\n"
    "        (bisa kurang kalau memang stoknya tipis).\"\"\"\n"
    "        async with _RADIO_SEARCH_SEM:\n"
    "            query = f\"{artist} music\"\n"
    "            results = await self.ytdlp.search(query, max_results=15)\n"
    "            existing = self._build_exclusion_set()\n"
    "\n"
    "        seen_titles: set[str] = set()\n"
    "        unique_tracks = []\n"
    "        for t in results:\n"
    "            if t.video_id in existing:\n"
    "                continue\n"
    "            if not (0 < t.duration < MAX_TRACK_DURATION):\n"
    "                continue\n"
    "            norm = _normalize_title(t.title)\n"
    "            if norm and norm in seen_titles:\n"
    "                continue\n"
    "            seen_titles.add(norm)\n"
    "            unique_tracks.append(t)\n"
    "\n"
    "        random.shuffle(unique_tracks)\n"
    "        return unique_tracks[:TRACKS_PER_ARTIST_TARGET]"
)

NEW_B = (
    "    async def _search_artist(self, artist: str) -> list:\n"
    "        \"\"\"Cari track untuk satu artis.\n"
    "        Strategi query (prioritas):\n"
    "        1. Jika DB punya lagu_populer untuk artis ini, cari tiap judul\n"
    "           secara individual: \"{judul} {artis}\" agar hasil lebih presisi.\n"
    "        2. Fallback ke query generik \"{artis} music\" kalau seed kosong.\n"
    "        \"\"\"\n"
    "        # Ambil seed judul dari DB\n"
    "        seed_titles: list[str] = []\n"
    "        if self.db and self.db.conn:\n"
    "            try:\n"
    "                seed_titles = await self.db.get_artist_seeds(artist, limit=TRACKS_PER_ARTIST_TARGET + 2)\n"
    "            except Exception:\n"
    "                pass\n"
    "\n"
    "        existing = self._build_exclusion_set()\n"
    "        seen_titles: set[str] = set()\n"
    "        unique_tracks: list = []\n"
    "\n"
    "        if seed_titles:\n"
    "            # Strategi 1: cari per judul populer secara paralel\n"
    "            async def _search_one(judul: str):\n"
    "                q = f\"{judul} {artist}\"\n"
    "                async with _RADIO_SEARCH_SEM:\n"
    "                    return await self.ytdlp.search(q, max_results=5)\n"
    "\n"
    "            results_nested = await asyncio.gather(\n"
    "                *[_search_one(j) for j in seed_titles],\n"
    "                return_exceptions=True,\n"
    "            )\n"
    "            candidate_lists: list[list] = [\n"
    "                r for r in results_nested if not isinstance(r, Exception)\n"
    "            ]\n"
    "            for i in range(max((len(lst) for lst in candidate_lists), default=0)):\n"
    "                for lst in candidate_lists:\n"
    "                    if i < len(lst):\n"
    "                        t = lst[i]\n"
    "                        if t.video_id in existing:\n"
    "                            continue\n"
    "                        if not (0 < t.duration < MAX_TRACK_DURATION):\n"
    "                            continue\n"
    "                        norm = _normalize_title(t.title)\n"
    "                        if norm and norm in seen_titles:\n"
    "                            continue\n"
    "                        seen_titles.add(norm)\n"
    "                        unique_tracks.append(t)\n"
    "                        if len(unique_tracks) >= TRACKS_PER_ARTIST_TARGET:\n"
    "                            break\n"
    "                if len(unique_tracks) >= TRACKS_PER_ARTIST_TARGET:\n"
    "                    break\n"
    "\n"
    "        if len(unique_tracks) < TRACKS_PER_ARTIST_TARGET:\n"
    "            # Strategi 2 (fallback): query generik\n"
    "            async with _RADIO_SEARCH_SEM:\n"
    "                fallback_results = await self.ytdlp.search(f\"{artist} music\", max_results=15)\n"
    "            for t in fallback_results:\n"
    "                if t.video_id in existing:\n"
    "                    continue\n"
    "                if not (0 < t.duration < MAX_TRACK_DURATION):\n"
    "                    continue\n"
    "                norm = _normalize_title(t.title)\n"
    "                if norm and norm in seen_titles:\n"
    "                    continue\n"
    "                seen_titles.add(norm)\n"
    "                unique_tracks.append(t)\n"
    "                if len(unique_tracks) >= TRACKS_PER_ARTIST_TARGET:\n"
    "                    break\n"
    "\n"
    "        # Tidak di-shuffle: urutan seed DB sudah bermakna (populer duluan)\n"
    "        return unique_tracks[:TRACKS_PER_ARTIST_TARGET]"
)

if OLD_B not in new:
    print("ERROR: Pola B (_search_artist) tidak ditemukan di", path)
    sys.exit(1)

new = new.replace(OLD_B, NEW_B, 1)
open(path, "w").write(new)
print("OK: _artist_rotation direset di on_activated")
print("OK: _search_artist pakai seed lagu populer dari DB + fallback")
PYEOF

echo ""
echo "=== Verifikasi syntax ==="
python3 -m py_compile "$PC" && echo "OK: $PC"
python3 -m py_compile "$RE" && echo "OK: $RE"

echo ""
echo "=== Selesai. Restart server untuk menerapkan perubahan. ==="
