# Kegagalan pada putaran awal dan tindak lanjutnya

Dicatat agar hasil akhir tidak menutupi prosesnya. "Situs" berarti source diubah; "Harness" berarti skrip ujinya yang keliru.

| Putaran | Kegagalan | Jenis | Tindak lanjut |
|---|---|---|---|
| Sistem rilis #1 | 4 galat: pembantu fixture menerima argumen ganda; hash folder berubah karena `__pycache__` | Harness | Pembantu diperbaiki; subprocess dijalankan dengan `-B`. Kode alat rilis tidak diubah. |
| Browser #1 | Penanda menu aktif menunjuk "Manfaat" di "Visual Brand" | **Situs** (ada sejak 1.3.0) | `main.js`: pilih section berdasarkan posisi halaman. |
| Browser #1 | CLS 0,14 pada 1440 × 900 | **Situs** (ada sejak 1.3.0; diukur ulang pada 1.3.0 untuk memastikan) | Font cadangan bermetrik selaras di `sales.css`. CLS 0,00. |
| Browser #1 | `wait_for_function` gagal dengan EvalError | Harness | Fungsi itu memakai `eval` di halaman dan diblokir CSP situs, sesuai tujuan CSP. Diganti polling dari luar. CSP tidak dilonggarkan. |
| Browser #1 | Locator CTA cocok dengan dua elemen | Harness | Selektor dipersempit ke `#beranda`. |
| Browser #2 | Permintaan MP4 "gagal" saat seek | Harness | Chromium membatalkan unduhan awal ketika beralih ke Range; pembatalan media itu dikecualikan hanya pada uji video. |
| Browser #2–#4 | Galat sintaks/tanda tangan fungsi | Harness | Akibat penggantian teks massal saya sendiri pada skrip uji; diperbaiki. |
| Browser #5 | Status video dianggap tidak kosong | Harness | Elemen berisi spasi dari perapian HTML; pembanding memakai `trim()`. Kotak status tetap tersembunyi sebelum ada galat. |
| Visual #1 | Selisih piksel 1–6% pada section yang tidak diubah | Metode | Ditelusuri: anti-alias teks pada posisi sub-piksel; kotak elemen 0 px. Ditambah perbandingan kotak layout. Font cadangan juga dibatasi ke huruf Latin dasar agar simbol tetap memakai font sistem. |

Tidak ada assertion yang dihapus atau dilonggarkan untuk meluluskan hasil. Ambang "gambar hero terlihat" pada 844 × 390 tidak diwajibkan (bukan ukuran target), dan itu dinyatakan di laporan.
