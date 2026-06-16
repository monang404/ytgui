Berikut adalah dokumen **Product Requirement Document (PRD)** untuk rencana *refactor* besar `ytcli` guna mengintegrasikan dukungan mouse pada *environment* Termux, dengan tetap mempertahankan arsitektur *event-driven* yang sudah ada.

---

# Product Requirement Document (PRD): Migrasi `ytcli` ke *Clickable TUI*

## 1. Pendahuluan

Dokumen ini merinci rencana *refactor* aplikasi `ytcli` dari penggunaan `rich` ke framework `Textual`. Tujuan utamanya adalah mengaktifkan interaksi sentuh (*mouse input*) pada Termux tanpa mengorbankan performa aplikasi CLI yang ringan.

## 2. Sasaran Utama

* **Interaktivitas**: Mengubah antarmuka dari *keyboard-only* menjadi *touch-friendly*.


* **Efisiensi Kode**: Memanfaatkan struktur `EventBus` yang sudah ada untuk sinkronisasi antarmuka dan logika.


* **Kompatibilitas**: Memastikan aplikasi berjalan stabil di Termux dengan dukungan *mouse reporting*.



## 3. Scope Perubahan (Refactor)

### A. Transisi Framework

* **Pindah dari `rich` ke `Textual**`: `Textual` akan bertindak sebagai *layer* utama untuk menangani *event* terminal.


* **Component Wrapping**: Mengonversi komponen `rich` yang ada (Panel, List, Static) menjadi `Textual Widget`.



### B. Implementasi Fitur Mouse

* **Clickable Buttons**: Panel kontrol (`ytcli-090a8c9f4d0c14d155992f7be0aa0e2b6a57b499/tui/panels/controls.py`) akan diubah menjadi *widget* yang merespons `on_click`.


* **Interactive Progress Bar**: *Progress bar* akan mendukung *event* klik untuk menentukan koordinat $(x)$ dan menghitung persentase *seek* lagu secara instan.


* **List Interaction**: *Queue panel* akan diubah menjadi *selectable list* di mana klik pada item lagu langsung memicu `CMD_PLAY_TRACK`.



## 4. Arsitektur Teknis

* **Event Bus Integration**: Tetap menggunakan `EventBus` yang sudah ada untuk menangani logika bisnis. Saat widget mendeteksi *click*, ia akan mengirimkan *event* ke *bus* yang kemudian ditangkap oleh `engine`.


* **State Management**: Mempertahankan `State` aplikasi untuk sinkronisasi *UI* dengan *player status*.



## 5. Roadmap Implementasi

| Fase | Fokus | Deliverables |
| --- | --- | --- |
| **Fase 1** | *Skeleton Migration* | Instalasi `Textual` dan migrasi `main.py` agar berjalan sebagai aplikasi `Textual`.

 |
| **Fase 2** | *Widget Conversion* | Mengonversi panel yang sudah ada menjadi `Textual Widget` yang kompatibel.

 |
| **Fase 3** | *Mouse Logic* | Menambahkan *event listener* pada komponen kontrol dan *progress bar*.

 |
| **Fase 4** | *Testing* | Uji coba *touch feedback* dan responsivitas di Termux.

 |

## 6. Pertimbangan Khusus (Termux & Mobile)

* **Hitbox Size**: Karena ini berjalan di layar sentuh, ukuran tombol akan diatur minimal setinggi 1 *cell* terminal dengan lebar yang cukup untuk mencegah *misclick*.


* **Keyboard Fallback**: Semua fungsi klik *wajib* memiliki padanan *keyboard shortcut* agar tetap bisa diakses oleh *power user*.



## 7. Metrik Keberhasilan

* Aplikasi berhasil berjalan dengan *mouse reporting* di Termux.


* Tidak ada penurunan performa (latensi) saat perpindahan lagu melalui klik.


* *Queue* dan *Progress Bar* dapat dioperasikan dengan satu sentuhan jari.



---

**Catatan:** Refactor ini bersifat *backward compatible* terhadap logika `engine` Anda, sehingga Anda hanya perlu fokus pada pembaruan lapisan `tui`. Apakah Anda ingin saya membantu membuat contoh kode untuk *widget* kontrol pertama?