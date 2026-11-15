# Batas rilis dan penyambungan akun

## Status saat diserahkan

Homepage telah direkonstruksi dan file nyata telah tersedia. Tetapi **belum siap untuk dinyatakan sebagai produk komersial end-to-end yang menerima pendaftaran**.

| Gerbang | Status | Alasan dan tindakan |
|---|---|---|
| Layanan pendaftaran/login | BLOCKED — tidak tersedia dalam source | Hubungkan URL resmi; uji pendaftaran, email bila relevan, login, kegagalan input, dan masuk ke Account Page. Tidak ada formulir palsu dalam paket. |
| Mesin Brand DNA / prompt satu klik | NOT VERIFIED | Dua canon adalah arahan komunikasi pemilik, bukan pembuktian implementasi layanan. Uji pada produk nyata; gambar/video bukan rekaman pengoperasian. |
| Isi audio empat video / caption | NOT VERIFIED | Track AAC tetap utuh dan decode penuh diuji. Tidak dilakukan pemeriksaan semantik melalui pendengaran. Caption tidak dikarang. Periksa seluruh audio; buat caption yang tepat bila ada ucapan/suara bermakna. |
| Publikasi media | OWNER REVIEW | Bahan disediakan untuk proyek; tidak ada dokumen izin media/kemitraan yang diverifikasi. Teks tidak mengklaim merek/pemeran mendukung Jago Prompt. |
| Safari iOS, Android nyata, Firefox, pembaca layar | NOT VERIFIED | Viewport Chromium bukan perangkat nyata. Perlu uji kontrol, suara, fokus, fullscreen dan pembaca layar pada target. |
| Navigasi browser ke URL hosting | BLOCKED dalam lingkungan audit | Kebijakan browser URLBlocklist berlaku. Render/interaksi diperiksa dari source inlined; HTTP lokal diperiksa terpisah. Tidak ada pengubahan kebijakan tersebut. |
| Domain, metadata absolut, indeks pencarian | BELUM DIISI | Domain tidak dikarang. Pratinjau noindex. Isi URL resmi lalu terapkan helper bila sudah diverifikasi. |
| Performa lapangan | NOT VERIFIED | Tidak ada angka LCP/CLS/lighthouse produksi yang dibuat dari render dengan aset tertanam. |

## Hubungkan layanan nyata

Edit `konfigurasi/rilis.json` menggunakan alamat HTTPS yang benar. Field `registration_url` dan `login_url` harus menunjuk layanan akun resmi milik proyek. `site_url` adalah domain publik homepage. Jangan memakai domain contoh yang diberikan sebagai format.

Dari folder paket:

```bash
python tools/aktifkan_rilis.py
python tools/aktifkan_rilis.py --apply
python tools/gate_rilis.py
```

Tanpa `--apply`, helper hanya memvalidasi. Helper tidak membuat backend, tidak menghubungi layanan, dan tidak mengubah kegagalan registrasi menjadi keberhasilan. Setelah penerapan, uji semua jalur di layanan nyata dan jalankan ulang QA. Perbarui checksum sebelum membuat paket rilis baru.

`public_release_approved`, `account_flow_verified`, `audio_review_completed`, `media_publication_approved`, dan `product_claims_verified` bukan tombol untuk melewati pekerjaan. Ubah menjadi true hanya setelah ada bukti yang sesuai. Gate sengaja tetap gagal pada paket yang belum memenuhi syarat.

## Materi Account Page

`dokumentasi_internal/panduan_account.html` hanya bahan migrasi. Bukan dashboard terautentikasi. Tidak boleh dipublikasikan bersama folder website. Integrasi materi tersebut ke halaman akun yang benar merupakan pekerjaan pada produk/backend yang tidak disertakan dalam ZIP sumber.
