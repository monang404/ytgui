# Walkthrough Sprint 6

## Pengerjaan Task S6-01
**Tujuan:** Memecah `render/tabs.js` (455 baris) menjadi sub-modul render independen untuk memisahkan domain komponen sehingga lebih mudah dikelola.

### Langkah-langkah:
1. Mengekstrak fungsi-fungsi dari `tabs.js` dan menyimpannya ke modul-modul berikut di direktori `web/static/js/render/`:
   - `now-playing.js`: Menangani logika `renderNowPlaying` untuk tab Now Playing, cover art, dan kontrol ambient UI.
   - `discover.js`: Menangani `renderDiscoverTab`, `updateDiscoverPlayingState`, `renderRadio` dan elemen UI lainnya seperti riwayat home (`renderRecentRow`).
   - `queue.js`: Menangani rendering manual/radio queue (`renderQueue`, `renderList`, `createQueueItemTemplate`, `updateQueueItem`) dengan `radio-queue-item`.
   - `favorites.js`: Menangani rendering favorit (placeholder jika ada ekspektasi struktur modul).

2. Menghapus script pemuatan `tabs.js` di `web/static/index.html`.
3. Menambahkan tag script untuk file baru tersebut (`now-playing.js`, `queue.js`, `discover.js`, `favorites.js`) ke dalam `index.html`.
4. Menghapus fisik file `web/static/js/render/tabs.js` dari proyek.
5. Memperbarui `CURRENT_TASK.md` untuk menandai bahwa status Task S6-01 sudah `Done` dan menggeser sprint pointer saat ini ke `Sprint 7` / Task `S7-01`.

### Hasil Validasi:
- `grep -rn "render/tabs.js" web/static/index.html` menunjukkan 0 hasil (sudah terhapus sempurna).
- File baru telah sukses dibuat di repositori.
- Class `radio-queue-item` yang dikerjakan pada S0-24 ada di dalam file `queue.js`.
- Perbaikan mood card dan tombol (seperti see-all/menu `...`) tersedia di dalam `discover.js`.

Sprint 6 sukses dieksekusi. Selanjutnya proyek sudah siap memasuki fase Sprint 7 untuk Backend Cleanup.
