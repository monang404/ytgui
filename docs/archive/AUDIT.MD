# PROMPT UNTUK CLAUDE — AUDIT MENYELURUH APLIKASI

Anda adalah kombinasi dari beberapa peran berikut sekaligus:

* Principal UX Researcher (10+ tahun pengalaman)
* Senior UI/Interaction Designer
* Principal Backend Engineer
* Software Architect
* Security Reviewer
* DevOps & Reliability Engineer
* Technical Writer

Saya akan memberikan source code aplikasi dalam bentuk ZIP. Tugas Anda adalah melakukan audit menyeluruh terhadap aplikasi tersebut seolah-olah Anda sedang melakukan technical due diligence untuk produk yang akan masuk tahap produksi.

## KONTEKS

Aplikasi ini merupakan platform radio/music player berbasis Termux dengan beberapa komponen seperti:

* Terminal UI (TUI)
* Web UI
* Mode Client dan Admin
* Event-driven architecture
* Integrasi MPV sebagai audio engine
* WebSocket untuk komunikasi realtime
* Cache management
* Playlist dan queue management
* Lyrics support
* Sinkronisasi state antar client

Lakukan audit berdasarkan implementasi aktual pada source code, bukan asumsi.

---

# OUTPUT YANG WAJIB DIHASILKAN

Buat laporan lengkap dalam file Markdown bernama:

audit.md

Gunakan struktur berikut.

# EXECUTIVE SUMMARY

Berikan ringkasan singkat:

* Tujuan aplikasi
* Tingkat kematangan produk
* Kesiapan produksi
* Kelebihan utama
* Risiko terbesar

Berikan skor:

* UX: x/10
* UI: x/10
* Backend: x/10
* Security: x/10
* Scalability: x/10
* Maintainability: x/10
* Overall: x/10

---

# 1. PROJECT UNDERSTANDING

Jelaskan:

* Fungsi utama aplikasi
* Alur pengguna
* Komponen utama
* Dependency penting
* Gambaran arsitektur yang ditemukan

Jika memungkinkan, buat diagram arsitektur dalam Mermaid.

---

# 2. UX AUDIT

Lakukan heuristic evaluation menggunakan Nielsen's 10 Usability Heuristics.

Untuk setiap heuristik:

## Nama Heuristik

### Temuan

* ...

### Dampak

* Low / Medium / High / Critical

### Bukti Implementasi

* File terkait
* Potongan kode relevan

### Rekomendasi

* ...

Berikan skor UX keseluruhan.

Identifikasi:

* Friction points
* Dead-end flows
* Cognitive load
* Discoverability issue
* Empty-state issue
* Error handling issue
* Onboarding issue

---

# 3. UI AUDIT

Analisis:

* Visual hierarchy
* Konsistensi desain
* Typography
* Layout
* Responsiveness
* Mobile usability
* Desktop usability
* Accessibility
* Feedback/loading state
* Color usage
* Iconography

Jika terdapat CSS/design system:

Evaluasi:

* Reusability
* Token consistency
* Component architecture

Berikan skor UI.

---

# 4. ACCESSIBILITY AUDIT (WCAG 2.2)

Audit berdasarkan WCAG:

* Perceivable
* Operable
* Understandable
* Robust

Identifikasi:

* Missing labels
* Keyboard navigation issue
* Focus state issue
* Contrast issue
* Screen reader issue

Beri severity:

* Minor
* Major
* Critical

Sertakan rekomendasi.

---

# 5. BACKEND AUDIT

Analisis:

## Arsitektur

* Layering
* Separation of concerns
* Modularitas
* Dependency coupling
* Cohesion

## Data Flow

Jelaskan alur data.

Jika memungkinkan buat sequence diagram Mermaid.

## Event System

Evaluasi:

* Event bus
* Event listener
* Race condition risk
* Event explosion risk
* Memory leak risk

## API

Audit:

* REST/WebSocket design
* Payload consistency
* Error contract
* Response pattern

## Cache

Evaluasi:

* Invalidasi
* Konsistensi
* Potensi stale data

## MPV Integration

Audit:

* Fault tolerance
* Recovery
* Timeout
* State synchronization

## Queue/Playlist

Evaluasi:

* Konsistensi state
* Edge case
* Concurrent access

Berikan skor backend.

---

# 6. SECURITY AUDIT

Identifikasi:

* Hardcoded secret
* Credential exposure
* Missing authentication
* Missing authorization
* Input validation issue
* Injection risk
* Path traversal
* Command injection
* WebSocket abuse
* CSRF risk
* XSS risk
* DOS risk
* Sensitive logging

Buat tabel:

| Temuan | Severity | Lokasi | Risiko | Solusi |

Severity:

* Low
* Medium
* High
* Critical

Berikan skor security.

---

# 7. PERFORMANCE AUDIT

Analisis:

* Startup performance
* Runtime performance
* Memory usage
* CPU usage
* I/O bottleneck
* WebSocket efficiency
* Cache efficiency
* MPV interaction efficiency

Berikan:

Quick Wins dan Long-Term Improvements.

---

# 8. MAINTAINABILITY AUDIT

Evaluasi:

* Struktur folder
* Naming convention
* Code duplication
* Dead code
* Technical debt
* Testability
* Documentation quality
* Readability

Berikan skor maintainability.

---

# 9. TESTING AUDIT

Identifikasi:

* Unit test coverage
* Integration test coverage
* End-to-end test coverage
* Missing test scenario

Buat daftar prioritas test yang harus dibuat.

---

# 10. DEVOPS & OBSERVABILITY AUDIT

Evaluasi:

* Logging
* Monitoring
* Metrics
* Health checks
* Graceful shutdown
* Recovery strategy
* Deployment readiness
* Environment management

Berikan rekomendasi.

---

# 11. TECHNICAL DEBT

Daftar:

* Debt item
* Dampak
* Prioritas
* Estimasi effort

Format tabel.

---

# 12. ROADMAP

Buat roadmap:

## 30 Hari

Perbaikan kritis.

## 60 Hari

Perbaikan menengah.

## 90 Hari

Peningkatan lanjutan.

Kelompokkan berdasarkan:

* UX
* UI
* Backend
* Security
* DevOps

---

# 13. TOP 10 PRIORITAS

Urutkan 10 tindakan paling penting yang harus dilakukan tim.

Format:

1. ...

   * Dampak:
   * Estimasi usaha:
   * Prioritas:

---

# 14. KESIMPULAN

Berikan jawaban akhir:

* Apakah aplikasi siap production?
* Apa risiko terbesarnya?
* Apa kekuatan terbesarnya?
* Jika Anda menjadi CTO proyek ini, apa 5 keputusan pertama yang akan Anda ambil?

---

# ATURAN AUDIT

* Audit HARUS berdasarkan source code nyata.
* Jangan membuat asumsi tanpa bukti.
* Sebutkan file yang menjadi dasar temuan.
* Kutip potongan kode yang relevan bila diperlukan.
* Jika ada ketidakpastian, tulis "Tidak ditemukan bukti yang cukup".
* Fokus pada temuan yang actionable.
* Bersikap kritis tetapi konstruktif.
* Berikan severity dan prioritas yang jelas.
* Gunakan Markdown yang rapi.
* Gunakan Mermaid untuk diagram jika memungkinkan.
* Targetkan laporan minimal setara audit teknis profesional 20–40 halaman.
* Output akhir HARUS berupa isi lengkap file `audit.md`.
