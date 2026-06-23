# AUDIT RINGKASAN EKSEKUTIF — YTGUI Phase 3 Security Cleanup

**Tanggal Audit:** 2026-06-23  
**Versi Codebase:** ytgui-patch-3-phase3-security-cleanup  
**Auditor:** Automated Deep Audit

---

## Executive Summary

YTGUI adalah aplikasi pemutar musik YouTube berbasis Python yang berjalan di Termux/Linux/Windows. Arsitektur menggunakan pola event-driven dengan EventBus + CommandBus, lapisan cache SQLite, MPV sebagai audio backend, dan web server aiohttp sebagai UI.

Codebase ini telah melalui beberapa iterasi perbaikan (patch 0.x, 1.x, 2.x, 3.x). Banyak bug kritis sebelumnya sudah ditangani — namun audit ini menemukan sejumlah **risiko residual yang nyata** terutama di lapisan keamanan, konkurensi, dan resource management.

---

## Score

| Dimensi | Score | Keterangan |
|---|---|---|
| **Overall Health** | **62 / 100** | Cukup stabil untuk personal use, belum production-ready |
| **Security** | **55 / 100** | Beberapa patch dilakukan, namun masih ada celah struktural |
| **Architecture** | **70 / 100** | Event-driven yang baik, ada beberapa pelanggaran layer |
| **Maintainability** | **65 / 100** | Bersih secara keseluruhan, ada duplikasi dan god-module |
| **Scalability** | **45 / 100** | Multi-room ada, namun global singleton bus membatasi skalabilitas |
| **Concurrency** | **58 / 100** | Beberapa race condition residual, task lifecycle tidak sempurna |

---

## Top 20 Risiko Terbesar

| # | Severity | Area | Masalah |
|---|---|---|---|
| 1 | 🔴 CRITICAL | Security | `verify_password()` fallback ke plaintext comparison (config.py & security.py) |
| 2 | 🔴 CRITICAL | Security | `admin` password mentah disimpan di file jika `YTGUI_ADMIN_PASS` di-set via ENV (config.py L46) |
| 3 | 🔴 CRITICAL | Concurrency | Global `bus` singleton dipakai semua room — event dari room A bisa ter-dispatch ke handler room B |
| 4 | 🔴 CRITICAL | Security | `/metrics` endpoint tanpa autentikasi — ekspos nama room, command history, event count |
| 5 | 🟠 HIGH | Security | `unauthenticated next` bypass: siapapun bisa mengirim `next` jika tahu `video_id` aktif |
| 6 | 🟠 HIGH | Concurrency | `_on_track_ended` tidak di-lock — dua event `eof` bersamaan bisa double-skip |
| 7 | 🟠 HIGH | Resource | `Database._conn` tidak thread-safe — aiosqlite connection shared tanpa serialisasi dari multiple coroutines |
| 8 | 🟠 HIGH | Architecture | `DownloadManager._on_download` signature tidak sesuai `CommandBus.execute()` convention — `room_id` diabaikan |
| 9 | 🟠 HIGH | Bug | MPV reconnect di `main.py` menggunakan `MPV_SOCKET` hardcode (bukan per-room socket) — semua room mencoba reconnect ke socket yang sama |
| 10 | 🟠 HIGH | Security | `room_id` dari WebSocket query param tidak divalidasi — bisa digunakan untuk room-enumeration/creation tanpa batas |
| 11 | 🟠 HIGH | Concurrency | `LyricsFetcher` subscribe ke global `bus.TrackProgressEvent` — semua room men-trigger `_on_progress` yang sama |
| 12 | 🟠 HIGH | Concurrency | `SponsorBlockHandler` sama — subscribe ke global `bus` bukan per-room event bus |
| 13 | 🟡 MEDIUM | Bug | `_retry_count` di `PlaybackController` tidak di-reset saat `_on_stop()` — retry state bocor antar lagu |
| 14 | 🟡 MEDIUM | Security | Session token tidak dirotasi setelah login — token 24-jam tidak bisa di-revoke selain dari DB |
| 15 | 🟡 MEDIUM | Bug | `DiscoverService` mengakses `self.db._conn` langsung (private attribute) — coupling fragile |
| 16 | 🟡 MEDIUM | Memory | `manager.login_attempts` dan `command_history` tidak pernah di-evict secara berkala — memory leak untuk server long-running |
| 17 | 🟡 MEDIUM | Resource | `http_session` dibuat dua kali: satu di `main.py` dan satu lagi di `create_app()` — salah satunya tidak pernah dipakai |
| 18 | 🟡 MEDIUM | Bug | `config.py`: ketika `YTGUI_ADMIN_PASS` di ENV, password disimpan as-is tanpa hashing — `verify_password` fallback plaintext adalah "fitur" yang tidak aman |
| 19 | 🟡 MEDIUM | Concurrency | `RadioMode._bg_tasks` set tidak dibersihkan saat `on_deactivated()` — task orphan potensial |
| 20 | 🟡 MEDIUM | Performance | `last_progress` throttle menggunakan dict global yang shared — semua room berbagi throttle yang sama |

---

## Prioritas Perbaikan

### 🔴 SEGERA (Security & Data Corruption Risk)

1. **Fix global bus cross-room contamination** — setiap Room harus punya EventBus sendiri
2. **Proteksi /metrics endpoint** — minimal IP whitelist atau basic auth
3. **Hapus plaintext fallback di verify_password** — setelah migrasi semua password ke pbkdf2
4. **Validasi room_id** — whitelist karakter, maksimum 64 char, reject unknown room creation dari publik
5. **Hash password ENV var** — jika YTGUI_ADMIN_PASS di-set, hash di startup sebelum dibandingkan

### 🟠 SEGERA (Reliability)

6. **Fix MPV reconnect** — gunakan per-room socket path, bukan MPV_SOCKET global
7. **Fix DownloadManager signature** — hormati room_id dari CommandBus
8. **Lock `_on_track_ended`** — cegah double-skip dari concurrent EOF events
9. **Reset `_retry_count` di `_on_stop()`**

### 🟡 JANGKA MENENGAH

10. **Eviction login_attempts dan command_history** — tambah background cleanup task
11. **Tutup duplicate http_session** — pilih satu, tutup yang lain
12. **Cleanup RadioMode._bg_tasks saat deactivated**
13. **Pisahkan per-room progress throttle**
