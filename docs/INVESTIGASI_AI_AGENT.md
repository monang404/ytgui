# Investigasi Task yang Di-skip — bagas.fm Refactor
> Tujuan: memahami KENAPA task ini belum selesai, bukan langsung minta fix.
> Baca semua jawaban AI dulu sebelum memutuskan langkah berikutnya.

---

## Konteks untuk AI

Audit `docs/audit/IMPLEMENTASI_AUDIT.md` menandai semua task di Fase 0–4 sebagai `[x]` (selesai).
Tapi verifikasi langsung ke kodebase menemukan 8 item yang BELUM terimplementasi.

Sebelum kamu memperbaiki apapun, jawab pertanyaan di bawah ini satu per satu.
Jawab jujur — termasuk jika kamu tidak tahu, atau jika ada risiko dari fix itu.

---

## Pertanyaan 1 — TASK-2.2: Duplicate `http_session`

**Fakta yang ditemukan:**
```
main.py baris 57:      http_session = aiohttp.ClientSession()
server/app.py baris 31: app["http_session"] = aiohttp.ClientSession()
```
Kedua baris ini membuat session terpisah. IMPLEMENTASI_AUDIT.md menandai task ini `[x]`.

**Pertanyaan:**
1. Mengapa masih ada dua `ClientSession()`? Apakah ini disengaja (dua session punya tujuan berbeda) atau memang terlewat?
2. Session di `server/app.py` dipakai untuk apa saja? Apakah berbeda fungsinya dari session di `main.py`?
3. Jika digabung jadi satu session, adakah risiko breaking change ke fitur lain (stream proxy, lyrics fetch, sponsorblock)?
4. Apa yang akan terjadi jika session di `server/app.py` tidak pernah ditutup saat shutdown abnormal?

Verifikasi sebelum menjawab:
```bash
grep -n "http_session\|ClientSession" main.py server/app.py server/handlers/http.py
```

---

## Pertanyaan 2 — TASK-2.4: `db.conn` vs `db._conn`

**Fakta yang ditemukan:**
```python
# server/handlers/http.py baris 19
db_status = "connected" if db.conn else "disconnected"
```
`Database` class hanya punya `self._conn` (private). Attribute `conn` tidak ada.

**Pertanyaan:**
1. Kenapa ini belum diperbaiki? Apakah `Database` class punya property `conn` yang tidak terdeteksi?
2. Jalankan ini dan tunjukkan outputnya:
```bash
grep -n "def conn\|self\.conn\|self\._conn\|@property" cache/db.py
```
3. Apa dampak konkretnya? Apakah `/health` endpoint selalu mengembalikan `"disconnected"` meskipun DB berfungsi?
4. Fix yang paling aman: tambah property `conn` di `Database`, atau ganti `db.conn` di http.py dengan `getattr(db, '_conn', None)`? Apa trade-off-nya?

---

## Pertanyaan 3 — TASK-2.5: Script injection di `plugins/notifications.py`

**Fakta yang ditemukan:**
```python
# plugins/notifications.py baris 71-72
script_path.write_text(
    f"{_SHEBANG}\necho '{token}' > '{self._fifo_path}' 2>/dev/null\n"
)
```
Tidak ada `shlex.quote()` di sini.

**Pertanyaan:**
1. Comment di baris 67 bilang `"action string must be a single bare path, no quotes/redirects"`. Apakah ini justifikasi untuk tidak pakai `shlex.quote()`? Jelaskan reasoning-nya.
2. Dalam kondisi apa `self._fifo_path` bisa mengandung karakter berbahaya? Tunjukkan contoh konkret input yang bisa menyebabkan injeksi.
3. Apakah `token` (yang isinya `prev/toggle/next`) bisa dimanipulasi dari luar? Dari mana asalnya?
4. Jika `shlex.quote()` ditambahkan, apakah script-nya masih bekerja di Termux? Ada risiko behavior berubah?

Verifikasi:
```bash
grep -n "token\|_fifo_path\|shlex\|write_text" plugins/notifications.py
```

---

## Pertanyaan 4 — TASK-3.7: Global `bus` masih diimport

**Fakta yang ditemukan:**
```bash
# Masih ada import global bus di:
main.py baris 10:             from core.event_bus import bus
engine/radio_engine.py baris 15: from core.event_bus import bus
engine/queue_manager.py baris 7: from core.event_bus import bus
```
IMPLEMENTASI_AUDIT.md menandai TASK-3.7 sebagai `[x]`.

**Pertanyaan:**
1. Untuk apa `bus` global masih dipakai di masing-masing file itu? Tunjukkan baris spesifik yang menggunakannya.
2. Apakah ini memang sisa yang belum dibersihkan, atau ada alasan arsitektur kenapa masih perlu?
3. `MpvController` dan `LyricsFetcher` sudah punya fallback ke global bus jika `event_bus=None` tidak diinject. Apakah ada path eksekusi di mana ini terjadi? Kapan?
4. Jika global `bus` dihapus sekarang dari ketiga file itu, apa yang akan rusak? Tunjukkan dependency chain-nya.

Verifikasi:
```bash
grep -n "^from core.event_bus import bus\|^bus\." main.py engine/radio_engine.py engine/queue_manager.py
grep -n "event_bus is None\|_global_bus" engine/mpv_controller.py plugins/lyrics.py plugins/sponsorblock.py
```

---

## Pertanyaan 5 — TASK-1.5: Unauthenticated `next` bypass

**Fakta yang ditemukan:**
```bash
grep -n "is_valid_auto_skip\|auto_skip" server/handlers/websocket.py
# → tidak ada output
```
Tidak ada trace blok `is_valid_auto_skip` di websocket.py. Tapi tidak jelas apakah ini karena:
- (a) bloknya sudah dihapus dengan benar, atau
- (b) logika auth-nya direstrukturisasi ke tempat lain

**Pertanyaan:**
1. Jalankan ini dan tunjukkan outputnya lengkap:
```bash
grep -n "is_authenticated\|require_auth\|not.*auth\|action.*next\|\"next\"" server/handlers/websocket.py
```
2. Di mana sekarang pengecekan auth untuk command `next` dilakukan? Tunjukkan baris dan file-nya.
3. Apakah ada command yang masih bisa dieksekusi tanpa autentikasi? Tunjukkan alur kode dari WebSocket message masuk sampai command dieksekusi.
4. Test manual: buka koneksi WebSocket tanpa login, kirim `{"type":"cmd","action":"next","data":{"video_id":"test"}}`. Apa yang terjadi?

---

## Pertanyaan 6 — CSS Law 5: 123 hex color di luar `tokens.css`

**Fakta yang ditemukan:**
```bash
grep -h "#[0-9a-fA-F]{3,6}" web/static/css/{base,layout,player,components,tabs,portal}.css | wc -l
# → 123
```
Seharusnya 0 sesuai Law 5: *"Tidak ada hex color (#xxxxx) di file CSS lain. EVER."*

**Pertanyaan:**
1. Jalankan ini untuk lihat sample-nya:
```bash
grep -hn "#[0-9a-fA-F]\{6\}" web/static/css/base.css web/static/css/layout.css web/static/css/player.css | head -20
```
2. Apakah hex-hex ini adalah sisa dari style.css lama yang belum di-replace ke `var(--fm-*)`, atau ada yang memang disengaja tidak masuk token?
3. Ada berapa hex yang unik (warna yang tidak punya token padanan di `tokens.css`)? Itu perlu token baru atau inline ok?
4. Apakah proses replace variabel di Fase 1 (`sed -i 's/var(--accent-fire)/var(--fm-accent)/g' ...`) hanya mengganti variable lama, tapi hex hardcode yang sudah ada dari awal terlewat?

---

## Pertanyaan 7 — `main.py` masih 190 baris (target < 100)

**Fakta yang ditemukan:**
```bash
wc -l main.py
# → 190
```
Target di REFACTOR_PLAN_FINAL.md dan Law 4: `main.py < 100 baris, hanya wiring`.

**Pertanyaan:**
1. Jalankan ini:
```bash
cat -n main.py
```
2. Baris mana saja yang bukan "wiring"? (Definisi wiring: import + instantiate + connect + run — tidak ada business logic)
3. Apa yang ada di baris 100–190? Apakah itu memang business logic, atau itu termasuk shutdown cleanup yang wajar ada di main?
4. Apakah ada risiko jika logika di baris 100–190 dipindahkan? Ke mana seharusnya dipindahkan?

---

## Pertanyaan 8 — `docs/mockup` belum di-rename ke `docs/mockups`

**Fakta yang ditemukan:**
```bash
ls docs/mockup/
# → bagas_fm_ui_mockup.html, discover.png, player.png, queue.PNG, radio.PNG, search.PNG
```
Tiga file masih huruf besar (`.PNG`). Folder masih `mockup` bukan `mockups`.

**Pertanyaan:**
1. Ini tampaknya task kecil (rename folder + lowercase). Kenapa belum dikerjakan?
2. Apakah ada file lain (HTML, README, atau script) yang hardcode path `docs/mockup/` sehingga rename bisa breaking?
3. Verifikasi:
```bash
grep -rn "docs/mockup\b" --include="*.md" --include="*.html" --include="*.py" .
```
4. Apakah ini sengaja ditunda karena ada dependency, atau memang terlewat?

---

## Setelah menjawab semua pertanyaan di atas:

**Buat rangkuman dalam format ini:**

```
TASK-X.X | Status sebenarnya | Alasan skip/belum selesai | Risiko jika dibiarkan | Risiko jika di-fix | Rekomendasi
```

Jangan fix apapun dulu sebelum rangkuman ini disetujui.
```

---

*Dokumen ini dibuat dari hasil verifikasi codebase pada 2026-06-24.*
*Referensi: docs/audit/IMPLEMENTASI_AUDIT.md, docs/REFACTOR_PLAN_FINAL.md, docs/AI_AGENT_PLAYBOOK.md*
