# AUDIT SECURITY — YTGUI Phase 3

Metodologi: OWASP Top 10 + manual code review

---

## Ringkasan Temuan

| Severity | Jumlah |
|---|---|
| 🔴 CRITICAL | 3 |
| 🟠 HIGH | 5 |
| 🟡 MEDIUM | 4 |
| 🟢 LOW | 3 |

---

## Tabel Temuan

| Severity | File | Line | Vulnerability | Fix |
|---|---|---|---|---|
| 🔴 CRITICAL | `core/security.py` | 14 | Plaintext password fallback | Hapus fallback, wajibkan pbkdf2 |
| 🔴 CRITICAL | `config.py` | 46 | ENV password tidak di-hash | Hash saat startup |
| 🔴 CRITICAL | `web/server.py` | ~310 | `/metrics` tanpa auth | Tambah IP whitelist atau token |
| 🟠 HIGH | `web/server.py` | ~246 | Unauthenticated `next` bypass | Hapus atau batasi lebih ketat |
| 🟠 HIGH | `web/server.py` | ~175 | `room_id` tidak divalidasi | Whitelist karakter, max length |
| 🟠 HIGH | `core/room_manager.py` | 30 | `get_or_create_room` tanpa batas | Rate limit / limit jumlah room |
| 🟠 HIGH | `web/server.py` | ~118 | Session tidak dirotasi | Tambah token rotation |
| 🟠 HIGH | `integrations/termux_notification.py` | 63 | Script injection via track title | Sanitize title sebelum masuk script |
| 🟡 MEDIUM | `web/server.py` | ~233 | Rate limit berbasis IP — bypass mudah | Tambah user-agent fingerprint |
| 🟡 MEDIUM | `engine/ytdlp_client.py` | 47 | `search` query tidak di-sanitasi ke yt-dlp | Sudah aman (yt-dlp handle) tapi log query ke strukturlog |
| 🟡 MEDIUM | `cache/db.py` | semua | Tidak ada prepared statement verification | Sudah pakai parameterized query — OK |
| 🟡 MEDIUM | `web/server.py` | ~370 | Error message bocorkan internal exception detail | Sanitasi error response |
| 🟢 LOW | `config.py` | 68 | Password file chmod tidak di-set | Tambah `chmod 600` pada password file |
| 🟢 LOW | `web/server.py` | semua | Tidak ada CORS policy proper | Tambah explicit CORS header |
| 🟢 LOW | `web/server.py` | semua | Tidak ada CSRF protection | Tambah CSRF token untuk web form |

---

## Detail Temuan Kritis

### 🔴 CRITICAL-SEC-01: Plaintext Password Fallback

**File:** `core/security.py` baris 14–16  
**Root Cause:**
```python
def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password.startswith("pbkdf2:sha256:"):
        # Fallback to plaintext for backwards compatibility or ENV vars
        return password == hashed_password  # ← BAHAYA: timing-safe tapi plaintext comparison
```

**Impact:** Jika `YTGUI_ADMIN_PASS` di-set via environment variable dengan nilai plaintext (misalnya `admin123`), password tersebut **tidak pernah di-hash**. `verify_password` akan melakukan perbandingan plaintext, dan password mentah tersimpan di process environment, log, dan `/proc/self/environ`.

**Exploitability:** Siapapun dengan akses shell ke server bisa baca env var. Jika env var bocor melalui `/health` atau error response, password langsung terbaca.

**Fix:**
```python
# Di config.py startup
if "YTGUI_ADMIN_PASS" in os.environ:
    from core.security import hash_password
    raw = os.environ["YTGUI_ADMIN_PASS"]
    ADMIN_PASSWORD = hash_password(raw)  # Hash dulu

# Di core/security.py — HAPUS plaintext fallback
def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password.startswith("pbkdf2:sha256:"):
        raise ValueError("Password hash format tidak valid. Jalankan ulang untuk regenerate.")
    # ... lanjut logika pbkdf2
```

---

### 🔴 CRITICAL-SEC-02: `/metrics` Endpoint Tanpa Autentikasi

**File:** `web/server.py` baris ~308–314  
**Root Cause:**
```python
async def handle_metrics(request):
    content, content_type = get_metrics_content()
    return web.Response(body=content, content_type=ct)

app.router.add_get("/metrics", handle_metrics)  # publik!
```

**Impact:** Endpoint ini mengekspos:
- Jumlah room yang aktif (`room_id` label)
- Nama command yang dieksekusi
- Jumlah event per type
- Jumlah WebSocket connection per room

Informasi ini memungkinkan attacker untuk **enumerate room**, memahami command flow, dan memantau aktivitas user tanpa login.

**Fix:**
```python
async def handle_metrics(request):
    # Cek token atau batasi ke localhost
    if request.remote not in ("127.0.0.1", "::1"):
        metrics_token = os.environ.get("YTGUI_METRICS_TOKEN")
        if not metrics_token or request.headers.get("X-Metrics-Token") != metrics_token:
            return web.HTTPForbidden()
    content, content_type = get_metrics_content()
    return web.Response(body=content, content_type=ct)
```

---

### 🟠 HIGH-SEC-03: Unauthenticated `next` Bypass

**File:** `web/server.py` baris ~246–255  
**Root Cause:**
```python
if not is_authenticated:
    is_valid_auto_skip = (
        action == "next" 
        and isinstance(data, dict) 
        and data.get("video_id") == getattr(state.current_track, "video_id", None)
    )
    if not is_valid_auto_skip:
        # reject
        return
    # LANJUT TANPA AUTH → siapapun bisa skip lagu!
```

**Impact:** Siapapun yang mengetahui `video_id` track yang sedang diputar (ekspos via `/api/stream/{video_id}` atau state broadcast) bisa mengirim `next` command dan skip lagu tanpa login.

**Exploitability:** `video_id` YouTube bersifat publik. Attacker cukup monitor WebSocket state broadcast untuk mendapatkan `video_id` aktif, lalu kirim `{"type":"cmd","action":"next","data":{"video_id":"..."}}`

**Fix:**
```python
# Opsi 1: Hapus pengecualian ini sama sekali — semua command butuh auth
if not is_authenticated:
    await ws.send_str(json.dumps({"type": "error", "data": "Akses ditolak."}))
    return

# Opsi 2: Jika perlu auto-skip dari browser, gunakan event khusus yang diverifikasi berbeda
```

---

### 🟠 HIGH-SEC-04: Termux Notification Script Injection

**File:** `integrations/termux_notification.py` baris 63–67  
**Root Cause:**
```python
script_path.write_text(
    f"{_SHEBANG}\necho '{token}' > '{self._fifo_path}' 2>/dev/null\n"
)
```

Variable `token` di sini aman (hardcoded `prev/toggle/next`), tapi `self._fifo_path` berasal dari `BASE_DIR / "cache" / "sockets" / "nowplaying.fifo"`. Jika `BASE_DIR` dimanipulasi (via `YT_PLAYER_BASE` env var dengan karakter khusus), script bisa mengandung injeksi.

Lebih berbahaya: jika ada titik lain yang menulis judul lagu ke script (future change), title bisa mengandung `'; rm -rf /data '`.

**Fix:**
```python
import shlex
script_path.write_text(
    f"{_SHEBANG}\necho {shlex.quote(token)} > {shlex.quote(str(self._fifo_path))} 2>/dev/null\n"
)
```

---

### 🟠 HIGH-SEC-05: `room_id` Tanpa Validasi

**File:** `web/server.py` baris ~175  
```python
room_id = request.query.get("room", "default")
room = await room_manager.get_or_create_room(room_id)
```

**Impact:**
- Attacker bisa membuat ribuan room (`/ws?room=room1`, `/ws?room=room2`, ...) → memory exhaustion
- `room_id` dipakai sebagai label di Prometheus → label cardinality explosion
- `room_id` dipakai dalam `socket_path = f"/tmp/mpv-socket-{room_id}"` → path traversal jika room_id mengandung `../`

**Exploitability:**
```
GET /ws?room=../../etc/passwd
GET /ws?room=AAAA...AAA  (10000 karakter)
GET /ws?room=1, /ws?room=2, ... (loop)
```

**Fix:**
```python
import re
room_id = request.query.get("room", "default")
if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', room_id):
    return web.HTTPBadRequest(text="Invalid room_id")

# Tambah limit jumlah room
if room_id not in room_manager.rooms and len(room_manager.rooms) >= MAX_ROOMS:
    return web.HTTPTooManyRequests(text="Room limit exceeded")
```

---

## OWASP Top 10 Mapping

| OWASP | Status | Detail |
|---|---|---|
| A01 Broken Access Control | ⚠️ Partial | Unauthenticated `next` bypass, `/metrics` publik |
| A02 Cryptographic Failures | ⚠️ Partial | Plaintext fallback di verify_password |
| A03 Injection | ✅ Mitigated | SQL: parameterized queries. Shell: termux script perlu shlex |
| A04 Insecure Design | ⚠️ | Room creation tanpa batas, session tidak revocable |
| A05 Security Misconfiguration | ⚠️ | CORS wildcard, metrics tanpa auth |
| A06 Vulnerable Components | ℹ️ | Bergantung pada yt-dlp, aiohttp, syncedlyrics — perlu audit dependensi |
| A07 Auth/Identification Failures | ⚠️ | Plaintext password fallback, session tidak dirotasi |
| A08 Software Integrity | ✅ | Tidak ada dynamic code eval yang berbahaya |
| A09 Logging Failures | ✅ | structlog + rotating file handler ada |
| A10 SSRF | ✅ Mitigated | PATCH-1-08 sudah ada domain whitelist di handle_stream |
