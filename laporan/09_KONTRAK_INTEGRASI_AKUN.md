# Kontrak integrasi akun dan produk

Kelima arsip hanya memuat website statis. Dokumen ini menyebut apa yang harus disediakan layanan akun agar homepage dapat dihubungkan, tanpa memilih penyedia atau arsitektur.

## Yang dibutuhkan homepage dari layanan akun

| Kebutuhan | Bentuk | Dipakai di |
|---|---|---|
| Halaman pendaftaran | Satu URL HTTPS yang dapat dibuka langsung | 7 CTA `data-register-link`, `daftar.html` |
| Halaman login (bila ada) | Satu URL HTTPS | `daftar.html` |
| Host resmi | Nama host layanan akun | `official_hosts` |
| Keputusan alur | Apakah login terpisah dari pendaftaran | `account_requires_login` |

Homepage tidak mengirim data apa pun ke layanan akun. Tidak ada form, cookie, atau penyimpanan lokal. CSP menetapkan `form-action 'none'` dan `connect-src 'none'`; bila kelak homepage perlu memanggil API, kebijakan itu harus diperbarui dengan sengaja.

## Yang harus dibuktikan pada layanan itu (gerbang `account_flow_verified`)

1. Pendaftaran dengan data sah berhasil.
2. Input salah atau tidak lengkap ditolak dengan pesan yang aman.
3. Login dan logout bekerja; sesi berakhir sesudah logout.
4. Account Page hanya terbuka dengan sesi sah; tanpa sesi diarahkan ke login atau ditolak.
5. Tidak ada secret pada frontend.

Pengujian ini dilakukan pada layanan tersebut, bukan disimpulkan dari HTML homepage.

## Yang harus dibuktikan pada produk (gerbang `product_claims_verified`)

- **Canon 01** ("…selalu konsisten"): skenario berulang yang menunjukkan DNA Brand tersimpan memengaruhi hasil. Kata "selalu" adalah keputusan komunikasi pemilik; uji terbatas tidak membuktikan hasil identik di semua platform, dan batas itu perlu dicatat bersama buktinya.
- **Canon 02** ("Cukup satu klik… prompt siap pakai"): satu tindakan menghasilkan prompt yang berubah mengikuti data produk dan karakter brand. Tombol yang hanya menyalin teks tetap bukan bukti.

## Materi internal

`dokumentasi_internal/panduan_account.html` adalah bahan untuk Account Page. Ia tidak berada di folder publik dan baru boleh ditayangkan di balik autentikasi nyata. Memindahkannya ke folder bernama `account` bukan autentikasi.

## Langkah setelah layanan tersedia

Isi `konfigurasi/rilis.json` → `bangun_rilis.py --profile staging --apply` → unggah `dist/staging/` ke alamat uji → jalankan lima pembuktian di atas → catat di `bukti/rilis/` → `periksa_url.py` → `bangun_rilis.py --profile production --apply` → unggah → `smoke_live.py`.
