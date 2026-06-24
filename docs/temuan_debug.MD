# Temuan Debug Manual (UI/UX)

Dokumen ini berisi daftar masalah (bug) yang ditemukan selama proses pengujian manual antarmuka (UI) dan perbaikan yang telah diimplementasikan:

1. **Hasil Pencarian Berantakan (Menyamping)**
   - **Masalah:** Hasil pencarian dirender berjajar ke samping secara horizontal hingga keluar batas layar, alih-alih menurun ke bawah seperti *list*. Hal ini disebabkan oleh `#search-results` yang hanya diatur sebagai `flex` tanpa spesifikasi arah, dan kesalahan penamaan kelas di Javascript (`search-result-item` padahal CSS yang tersedia adalah `.sr-item`).
   - **Solusi:** Menambahkan `flex-direction: column` pada `#search-results` di `base.css` dan memperbaiki nama kelas menjadi `.sr-item` di `search.js`.

2. **Ikon Tombol Play/Pause Kosong (Hanya Lingkaran Ungu)**
   - **Masalah:** Tombol utama Play/Pause di *player bar* hanya berupa lingkaran ungu kosong tanpa ikon. Ini terjadi karena sistem mencoba memanggil ikon versi *filled* (`ti-player-play-filled`), yang ternyata tidak tersedia di versi pustaka Tabler Icons yang dimuat.
   - **Solusi:** Mengganti pemanggilan kelas ikon menjadi versi reguler (`ti-player-play` dan `ti-player-pause`) di `index.html` dan `player.js`.

3. **Playbar Melompat Kembali (Snap-back) Saat Digeser**
   - **Masalah:** Saat *playbar* ditarik ke waktu tertentu dan dilepas, titiknya malah melompat kembali ke waktu awal. Hal ini terjadi karena ada jeda antara perintah pencarian ke server dan respons server. Di jeda tersebut, audio browser (yang masih berputar di waktu lama) mengirim laporan waktu (via *event* `timeupdate`) yang menimpa posisi *playbar* kembali ke asal.
   - **Solusi:** Menambahkan logika untuk langsung memperbarui `audio.currentTime` di pemutar lokal secara instan tepat pada saat geseran dilepas (*pointerup*), memutus jeda tunggu respons server.

4. **Perubahan Volume Tidak Terasa Saat Slider Digeser**
   - **Masalah:** Saat *slider* volume digeser, tidak ada perubahan tingkat suara yang terdengar. Suara baru berubah setelah jari dilepaskan dari *slider*. Ini terjadi karena *event* `input` (saat digeser) hanya mengubah angka persentase visual, tanpa mengubah volume *audio element* di browser.
   - **Solusi:** Menambahkan logika pembaruan `audio.volume` lokal ke dalam *event listener* `input`, sehingga suara seketika mengecil/membesar selaras dengan pergerakan *slider*.

5. **Tombol Play/Pause Delay dan Ikon Berkedip/Macet**
   - **Masalah:** Tombol Play/Pause terasa lambat/tidak responsif. Audio tidak langsung berhenti saat diklik, dan ikonnya sering berkedip kembali ke posisi semula. Hal ini disebabkan oleh *progress tick* (laporan rutin) dari server yang terus mem-nol-kan status UI sementara server belum selesai memproses perintah Pause.
   - **Solusi:** Menghentikan atau memutar ulang audio lokal seketika saat tombol diklik tanpa menunggu konfirmasi server. Selain itu, ditambahkan jeda pengabaian (1 detik) di mana *progress tick* dari server tidak akan menimpa status UI agar tidak terjadi *flickering*.

6. **Hasil Pencarian Tidak Merespons Saat Diklik**
   - **Masalah:** Tidak terjadi apa-apa ketika pengguna mengklik salah satu lagu dari hasil pencarian, padahal seharusnya muncul opsi "Putar" atau "Antrean". Masalah ini timbul karena sama sekali tidak ada pendeteksi klik (*event listener*) yang dipasang pada elemen daftar pencarian (`.sr-item`).
   - **Solusi:** Menambahkan logika *event delegation* pada kontainer `searchResults` di `events.js` yang akan menangkap klik dari `.sr-item` dan memanggil `showActionModal` untuk menampilkan *Action Sheet*.
