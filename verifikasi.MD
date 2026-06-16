# VERIFIKASI.md

# Final Pre-Release Verification

## Objective

Lakukan verifikasi menyeluruh terhadap aplikasi sebelum distribusi publik.

Fokus utama:

* memastikan fitur utama berjalan sesuai harapan;
* mendeteksi bug runtime;
* memverifikasi stabilitas;
* memeriksa usability;
* memastikan tidak ada regresi yang jelas;
* memastikan aplikasi layak digunakan pengguna akhir.

Audit ini **harus berbasis eksekusi nyata**, bukan hanya analisis kode.

---

# Rules

* Jalankan aplikasi.
* Jalankan seluruh fitur utama.
* Dokumentasikan setiap kegagalan.
* Jangan menganggap suatu fitur benar hanya karena berhasil dikompilasi.
* Jangan menghasilkan kesimpulan "tidak ada bug" tanpa bukti pengujian.

---

# Phase 1 – Build Verification

Verifikasi bahwa:

* project dapat di-install dari awal;
* dependency berhasil dipasang;
* tidak ada dependency yang hilang;
* startup berhasil tanpa error;
* shutdown berjalan bersih;
* tidak ada traceback saat startup maupun exit.

---

# Phase 2 – Runtime Smoke Test

Pastikan:

* aplikasi dapat dibuka;
* UI muncul dengan benar;
* tidak terjadi crash dalam 5 menit penggunaan normal;
* tidak ada freeze;
* tidak ada deadlock;
* tidak ada exception yang muncul di console.

---

# Phase 3 – Feature Verification

Uji seluruh fitur utama, termasuk:

* pencarian lagu;
* pencarian playlist;
* pemuatan hasil;
* pemilihan item;
* pemutaran audio;
* pause;
* resume;
* stop;
* next;
* previous;
* seek;
* volume;
* repeat;
* shuffle;
* queue management;
* history;
* cache;
* lyrics;
* sponsorblock (jika ada);
* persistence;
* restore state.

Untuk setiap fitur:

* PASS
* FAIL
* Catatan

---

# Phase 4 – Error Handling

Uji kondisi berikut:

* internet mati;
* timeout jaringan;
* URL tidak valid;
* video dihapus;
* playlist kosong;
* hasil pencarian kosong;
* database rusak;
* cache rusak;
* file konfigurasi hilang;
* mpv tidak tersedia;
* yt-dlp gagal.

Pastikan aplikasi:

* tidak crash;
* memberikan pesan yang jelas;
* dapat pulih atau keluar secara aman.

---

# Phase 5 – Stress Test

Uji dengan:

* ratusan item dalam queue;
* operasi next/previous berulang;
* pencarian berulang;
* pergantian lagu cepat;
* buka/tutup aplikasi berkali-kali.

Amati:

* penggunaan memori;
* CPU;
* respons UI;
* kebocoran resource.

---

# Phase 6 – Async & Concurrency

Periksa:

* task yatim (orphan tasks);
* coroutine yang tidak pernah selesai;
* race condition;
* event bus yang macet;
* deadlock;
* blocking call pada event loop.

---

# Phase 7 – Resource Cleanup

Pastikan setelah aplikasi ditutup:

* proses mpv berhenti;
* socket IPC dibersihkan;
* koneksi database ditutup;
* ClientSession ditutup;
* thread executor berhenti;
* file handle dilepas.

---

# Phase 8 – Logging

Periksa:

* tidak ada traceback yang disembunyikan;
* error penting tercatat;
* log tidak membocorkan informasi sensitif;
* level log sesuai.

---

# Phase 9 – UX Verification

Evaluasi dari sudut pandang pengguna baru:

* instalasi mudah;
* aplikasi mudah dipahami;
* navigasi jelas;
* pesan error membantu;
* loading memiliki indikator;
* shortcut konsisten;
* dokumentasi cukup untuk mulai menggunakan aplikasi.

Berikan skor 1–10 beserta alasan.

---

# Phase 10 – Release Readiness Checklist

Verifikasi:

* [ ] Tidak ada crash yang diketahui.
* [ ] Tidak ada bug kritis yang dapat direproduksi.
* [ ] Tidak ada kebocoran resource yang jelas.
* [ ] Startup dan shutdown stabil.
* [ ] Seluruh fitur inti berfungsi.
* [ ] Error handling memadai.
* [ ] Tidak ada exception berulang di log.
* [ ] Dokumentasi instalasi akurat.
* [ ] README sesuai implementasi.
* [ ] Konfigurasi default dapat digunakan.
* [ ] Dependensi penting tersedia.
* [ ] Performa dapat diterima untuk penggunaan normal.

---

# Deliverable

Buat file `HASIL_VERIFIKASI.md` dengan format berikut:

```markdown
# HASIL VERIFIKASI

## Executive Summary

## Environment

## Hasil Smoke Test

## Hasil Pengujian Fitur

| Fitur | Status | Catatan |
|--------|--------|----------|

## Hasil Stress Test

## Hasil Pengujian Error Handling

## Temuan Bug

| Severity | File/Fitur | Deskripsi | Langkah Reproduksi |

## Risiko yang Masih Ada

## Evaluasi Kemudahan Penggunaan

Skor: X/10

Alasan:

...

## Release Recommendation

- READY FOR RELEASE
atau
- READY WITH MINOR ISSUES
atau
- NOT READY

## Daftar Perbaikan yang Disarankan Sebelum Distribusi
```

## Kriteria Kelulusan

Hanya rekomendasikan **READY FOR RELEASE** apabila:

* tidak ditemukan bug kritis;
* seluruh fitur inti lulus pengujian;
* tidak ada crash yang dapat direproduksi;
* cleanup resource berjalan benar;
* startup dan shutdown stabil;
* pengalaman pengguna dasar dinilai baik.

Jika salah satu kondisi tersebut tidak terpenuhi, gunakan status yang lebih konservatif dan jelaskan alasannya.
