# AGENT_CONTEXT.md

## Purpose

Dokumen ini adalah titik masuk utama untuk seluruh AI Agent.

Baca dokumen ini terlebih dahulu sebelum membaca dokumen lain.

Dokumen ini menjelaskan:

* identitas proyek
* batasan proyek
* prioritas proyek
* urutan dokumen
* lokasi informasi penting

---

# Project Identity

Nama:
bagas.fm

Jenis:
Personal Music Player

Platform:

* Android Phone
* Android Tablet
* iPad / Safari
* Desktop Browser

Deployment:

* Termux
* windows 10
* Localhost

Audience:

* Pemilik aplikasi

Bukan:

* SaaS
* Multi-user platform
* Public streaming service
* Enterprise application

---

# Product Goal

Membangun music player personal dengan kualitas UX setara aplikasi modern.

Target:

* cepat
* ringan
* stabil
* nyaman digunakan setiap hari

Inspirasi UX:

* Spotify
* YouTube Music
* Apple Music

Tanpa menyalin seluruh fitur mereka.

---

# Device Strategy

Pendekatan:

Mobile-first

Target resmi:

1. Android Phone
2. Android Tablet
3. iPad Safari
4. Desktop Browser

Semua fitur inti harus berjalan pada seluruh kategori perangkat.

Jika terjadi konflik UX:

Android Phone menjadi prioritas utama.

---

# Technical Stack

Backend:

* Python
* aiohttp
* WebSocket
* Event Bus

Frontend:

* Vanilla JavaScript
* CSS
* HTML

Deployment:

* Termux Android

Build Tools:

* None

Framework:

* None

---

# Hard Constraints

Jangan menambahkan:

* React
* Vue
* Angular
* Svelte
* Tailwind
* Vite
* Webpack
* Redux
* Zustand
* TypeScript

kecuali diminta eksplisit.

---

# Engineering Philosophy

Selalu pilih:

* perubahan kecil
* patch lokal
* solusi sederhana

Hindari:

* rewrite
* refactor besar
* migrasi framework
* perubahan arsitektur tanpa alasan kuat

Jika bug dapat diperbaiki secara lokal:

jangan redesign sistem.

---

# AI Agent Operating Rules

1. Kerjakan satu task.
2. Jangan lompat fase.
3. Jangan membuat task baru.
4. Jangan memperluas scope.
5. Jangan melakukan refactor besar.
6. Verifikasi hasil.
7. STOP setelah task selesai.

Jika ragu:

STOP dan minta keputusan manusia.

---

# Document Hierarchy

Prioritas dokumen:

1. Human Instruction
2. /docs/playbook.md
3. /docs/audit.md
4. /docs/agent_konteks.md

Jika terjadi konflik:

Human Instruction menang.

Playbook menang atas Audit.

Audit adalah referensi.
Playbook adalah instruksi eksekusi.

---

# Project Knowledge Index

## PROJECT OVERVIEW

Baca dokumen ini:

AGENT_CONTEXT.md

---

## PROJECT AUDIT

Baca:

/docs/audit.md

Berisi:

* Executive Summary
* Scoring
* UI Analysis
* UX Analysis
* Architecture Analysis
* Accessibility Analysis
* Performance Analysis
* Spotify-Class Blueprint
* Roadmap

Gunakan untuk memahami:

* kondisi saat ini
* masalah
* target state

Jangan gunakan sebagai task list.

---

## EXECUTION PLAN

Baca:

/docs/playbook.md

Berisi:

* phase roadmap
* task breakdown
* implementation guide
* verification procedure
* rollback strategy
* regression prevention

Gunakan untuk:

* menentukan task aktif
* menentukan urutan kerja
* menentukan verifikasi

---

# Navigation Guide

Jika ingin memahami aplikasi:

→ baca AGENT_CONTEXT

Jika ingin memahami masalah:

→ baca AUDIT

Jika ingin mengerjakan pekerjaan:

→ baca PLAYBOOK

Jika ingin menentukan task aktif:

→ baca PLAYBOOK Phase List

Jika ingin memverifikasi hasil:

→ baca PLAYBOOK Verification Section

---

# Success Criteria

Perubahan dianggap berhasil jika:

* task selesai
* verification PASS
* tidak ada regression
* scope tetap terkendali

Lebih baik menyelesaikan satu task dengan aman
daripada sepuluh task sekaligus.
