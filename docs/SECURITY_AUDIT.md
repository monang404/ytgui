# SECURITY AUDIT — bagas.fm / YTGUI

Severity scale: **Critical / High / Medium / Low**, assessed against the project's actual deployment model (self-hosted, single admin, LAN-exposed, optionally internet-exposed if the operator forwards the port — `WEB_HOST` defaults to `0.0.0.0`).

---

### SEC-01 — Secrets, session tokens, and developer PII are present in the delivered source bundle
- **Severity:** Critical
- **Files:**
  - `cache/admin_password.txt` — a live PBKDF2-hashed admin password
  - `data/ytgui.db` (244K) + `data/ytgui.db-wal` (2.0MB) — contains the `sessions` table (`token TEXT PRIMARY KEY, expires_at INTEGER`), i.e. **live/recent authentication bearer tokens**
  - `cache/library.db` + `-shm`/`-wal`
  - `ytplayer.log` (580K, 4095 lines) — structured JSON log containing real LAN IP addresses (e.g. `192.168.18.219`), full browser user-agent strings, and a Windows filesystem path that discloses the developer's full real name (`C:\Users\PUTRA JAYA LIMBANGAN\Documents\ytgui\ytgui-main\...`)
- **Root cause:** `.gitignore` correctly lists every one of these paths as excluded (`cache/*.db`, `cache/admin_password.txt`, `data/ytgui.db`, `*.log`), which proves the project author is aware these must never ship — but the zip archive audited here contains them anyway. This means whatever process produced this bundle (manual zip of the working directory, a backup tool, an IDE "export project" action) does not respect the same boundary as `git`.
- **Why it's a problem:** Anyone who receives this bundle — a collaborator, a contractor, this audit, a support ticket attachment, a public bug-report upload — receives a working (if hashed) admin credential artifact and, more seriously, **live session tokens** that, if not yet expired (`expires_at`, 24h TTL per `server/handlers/auth.py:53`), grant immediate authenticated admin access to whatever server instance issued them, with no further authentication required. It also leaks the operator's real identity and home network's internal IP range.
- **Recommendation:**
  1. Immediately rotate the admin password (delete `cache/admin_password.txt` and restart, or run the app's password-reset flow) and consider the exposed session tokens compromised.
  2. Audit however this zip was produced and fix it to respect `.gitignore` (e.g., use `git archive HEAD` instead of a raw directory zip/copy).
  3. Scrub `ytplayer.log` of the developer's real path before any future sharing; consider structured logging that never includes raw OS paths from the runtime environment, or at least strips the home-directory prefix.
- **Expected benefit:** Eliminates a live credential-exposure incident and a PII leak.

---

### SEC-02 — `start.py` invokes `shell=True` with f-string-interpolated values for port-conflict detection
- **Severity:** Low (exploitability is currently constrained, but the pattern itself is unsafe)
- **File:** `start.py:344,357,363,369`
```python
output = subprocess.check_output(f'lsof -t -i:{port}', shell=True, text=True)
...
output = subprocess.check_output(f'fuser {port}/tcp', shell=True, text=True)
...
output = subprocess.check_output(f'ss -lptn "sport = :{port}"', shell=True, text=True)
```
- **Root cause:** `port` originates from `self.server_port`, a `@property` (line 329-334) that does `int(self._port_var.get().strip())` with a `try/except ValueError` fallback to `8765` — so `port` is guaranteed to be an `int` by the time it reaches these f-strings, which is what keeps this from being directly exploitable today (an `int` cannot contain shell metacharacters).
- **Why it's still a problem:** This is a fragile safety guarantee that depends entirely on one upstream cast holding forever. If `server_port` is ever refactored, or a new caller passes a port value from a different, less-sanitized source (e.g., a future `--port` CLI flag, an environment variable read without casting), this becomes a straightforward command-injection vector via `shell=True`. `shell=True` should not be used for these commands regardless — none of them need shell features (pipes, globs, `&&`) that a plain argument list can't express.
- **Recommendation:** Rewrite using `subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True)` etc. (list form, `shell=False`), and keep the `netstat -aon` Windows call (line 344) as-is since it doesn't interpolate untrusted data, but still consider moving it to list-form for consistency.
- **Expected benefit:** Removes an entire class of injection risk regardless of future refactors; brings the code in line with the project's own security-conscious patterns used elsewhere (e.g., `engine/mpv_controller.py` and `plugins/notifications.py` correctly use `asyncio.create_subprocess_exec` with argument lists, not shells).

---

### SEC-03 — Admin password is printed to stdout in a stdout-is-logged environment
- **Severity:** Low-Medium
- **Files:** `config.py:68-72`, `main.py:161-162`
- **Root cause:** On first run / auto-generated password, the raw (unhashed) password is printed to the console so the operator can capture it once, by design (`# Harap simpan password ini! Tidak akan ditampilkan lagi.`). This is a legitimate and common bootstrap UX pattern.
- **Why it's still worth flagging:** This audit confirmed (`ytplayer.log`) that this application's stdout/stderr **is** persisted to a log file in at least one real run of this project (structlog JSON events appear in `ytplayer.log`). While the specific password-print statements use plain `print()` (not the `structlog` logger) and were not found verbatim in the sampled log, the general pattern — a secret written to stdout in an application whose stdout is known to be redirected to a persistent log file by the operator's own tooling (`start.py`'s `_pipe_stdout`) — is a latent risk. If an operator's shell/service wrapper redirects stdout to a file (a very common way to run a background service on Termux/Linux), the one-time password will be permanently retained in plaintext on disk.
- **Recommendation:** Consider writing the one-time password to a short-lived, restrictively-permissioned file only (the app already does this via `admin_password.txt`, but that stores the *hash*, not the raw password) and printing a reference to it, or explicitly document that operators should not redirect stdout to a persistent log when running this app for the first time.

---

### SEC-04 — Username comparison in auth is not constant-time
- **Severity:** Low (theoretical)
- **File:** `server/handlers/auth.py:53` — `if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD):`
- **Root cause:** `verify_password` correctly uses `secrets.compare_digest` (`core/security.py:16`) for the password comparison, but `username == ADMIN_USERNAME` is a standard `==` string comparison, which is not timing-attack-resistant.
- **Why it's low severity:** Usernames are not secret in this application's model (there is exactly one admin account, `ADMIN_USERNAME` defaults to the public string `"admin"`), so a timing side-channel on the username comparison discloses nothing of value — an attacker already knows the username. Documented for completeness/defense-in-depth only.
- **Recommendation:** Optional: `secrets.compare_digest(username.encode(), ADMIN_USERNAME.encode())` for consistency, but this is not a priority fix.

---

### SEC-05 — `serve_metrics` trusts `request.remote` for its localhost allow-list with no reverse-proxy awareness
- **Severity:** Low, contingent on deployment topology
- **File:** `server/handlers/http.py:143-158`
```python
client_ip = request.remote
_localhost_ips = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
...
is_local = client_ip in _localhost_ips
```
- **Root cause:** `request.remote` reflects the direct TCP peer, which is correct when aiohttp is the internet-facing listener, but if this app is ever run behind a reverse proxy (nginx, Caddy, a Tailscale/Cloudflare tunnel — all plausible for a self-hosted personal server meant to be reached remotely), `request.remote` will always be the proxy's address. If the proxy happens to run on the same host as this app (a common setup), `client_ip` would always read as `127.0.0.1`, meaning **every external visitor would appear "local" and bypass the metrics token requirement entirely.**
- **Why current risk is limited:** `/metrics` only exposes Prometheus counters/latencies (command counts, websocket counts) — no secrets, PII, or control surface — so the worst case today is information disclosure about usage patterns, not compromise. This is documented as a forward-looking risk given the project's stated intent to be reachable "dari jaringan WiFi yang sama" and potentially beyond.
- **Recommendation:** If a reverse-proxy deployment is ever supported, honor `X-Forwarded-For` **only** when the immediate peer is a explicitly-configured trusted proxy address, never unconditionally — the current code correctly does *not* trust `X-Forwarded-For` at all, which is the safe default; just be aware this means "local" detection silently breaks (fails open on same-host proxies) rather than fails closed under that topology.

---

### SEC-06 — `check_rate_limit` and login-attempt tracking key on raw client IP with no reverse-proxy consideration
- **Severity:** Low, same contingency as SEC-05
- **File:** `server/handlers/websocket.py::ws_handler` passes `request.remote` as `client_ip` into `handle_auth`/`check_rate_limit`.
- **Consequence:** Under a same-host reverse-proxy deployment, all clients would collapse to one IP for rate-limiting purposes, which could either (a) cause one legitimate heavy user to lock out all other users sharing the proxy, or (b) in the worst case, cause the 5-attempts/5-minute login lockout to apply globally across all users instead of per-attacker, which is a denial-of-service vector for legitimate admins if any single client trips it. Not currently exploitable in the default direct-listen deployment.
- **Recommendation:** Same as SEC-05 — out of scope for the current single-process deployment, but flag as a required fix before ever recommending a reverse-proxy topology in documentation.

---

## What Was Checked and Found Clean

- **SQL injection:** Every database call in `cache/db.py`, `services/discover_service.py`, and `data/export_to_sqlite.py` uses parameterized `?` placeholders for all user/track-derived values; the only string-interpolated pieces of any query are trusted, code-controlled placeholder-count strings (`','.join('?' for _ in exclude_ids)`), never data values. **No SQL injection found.**
- **Path traversal:** `server/handlers/http.py::serve_stream` validates `video_id` against `^[a-zA-Z0-9_-]{11}$` before touching the filesystem, and additionally verifies `cache_file.resolve().is_relative_to(CACHE_DIR.resolve())` as defense in depth. **No traversal found.**
- **SSRF:** The stream-proxy path (`serve_stream`) explicitly allow-lists scheme (`https` only) and domain suffix (`.googlevideo.com` / `.youtube.com`) on the *resolved* stream URL before either redirecting to it or proxying it — this correctly defends against yt-dlp ever being tricked into resolving to an internal/arbitrary URL. **Well implemented.**
- **Command injection (primary paths):** `engine/mpv_controller.py`, `plugins/notifications.py`, and `engine/ytdlp_client.py` all use `asyncio.create_subprocess_exec`/direct `yt_dlp` library calls with argument lists, never shell strings built from untrusted input. (The one exception, `start.py`, is SEC-02 above, and is not attacker-reachable data.)
- **Deserialization:** No `pickle`, `eval`, `exec`, or `yaml.load` usage found anywhere in the non-test codebase.
- **Authentication:** PBKDF2-SHA256 (100,000 iterations) with per-password random salt, constant-time comparison, explicit removal of a legacy plaintext-password fallback (`TASK-1.1` comment in `core/security.py`), session tokens generated via `secrets.token_hex(16)` (128 bits of entropy) — all sound choices.
- **Rate limiting:** Per-IP login attempt limiting (5 attempts / 5 min) and per-IP command rate limiting (30/min) both implemented with stale-entry pruning to avoid unbounded memory growth (`_prune_stale_ips`).
- **XSS:** Frontend consistently escapes track metadata (title/artist — the only genuinely "untrusted, attacker-influenceable" data flowing through the UI, since it originates from YouTube search results) via `escapeHtml()` before any `innerHTML` write. Reviewed every `innerHTML` call site in `web/static/js/`.
- **Secrets in source code (application logic itself, as opposed to the shipped data files covered in SEC-01):** No hardcoded API keys, tokens, or passwords found in any `.py` or `.js` file.

## Severity Summary

| ID | Severity | Area |
|---|---|---|
| SEC-01 | **Critical** | Secrets/PII in delivered bundle |
| SEC-02 | Low | `shell=True` in launcher (defense-in-depth) |
| SEC-03 | Low-Medium | Password printed to stdout |
| SEC-04 | Low | Non-constant-time username compare |
| SEC-05 | Low | Metrics localhost-check reverse-proxy blind spot |
| SEC-06 | Low | Rate-limit keying reverse-proxy blind spot |
