# Hasil pengujian final · 1.3.0

| Kelompok | Lulus | Gagal | Yang diuji |
|---|---:|---:|---|
| Pemeriksaan source/media/helper | 466 | 0 | Struktur, canon, referensi file, semua aset, decode penuh video/audio, dan aktivasi URL pada fixture |
| Skenario Chromium | 68 | 0 | Render 8 viewport, gambar awal, keyboard/menu, FAQ, galeri, 4 video native, seek/pause/end/replay, error/retry, no-JS, reduced motion, teks 200%, materi storyboard |
| HTTP server lokal | 155 | 0 | GET file byte-identik, respons Range 206/416, media hilang 404 |

Jumlah di atas berbeda unit: pemeriksaan atribut/path bukan skenario pengguna. Angka-angka ini tidak dijumlahkan menjadi skor kesiapan bisnis.

Browser: **Chromium 144.0.7559.96**, headless Linux. Viewport: 1440×900, 1280×800, 1024×768, 768×1024, 390×844, 360×800, 320×568, dan 844×390. Ada 31 screenshot final.

## Metode dan batas

Browser benar-benar merender dan menjalankan JavaScript serta decoder MP4 native. Karena navigasi URL diblokir kebijakan lingkungan, HTML/CSS/JS dan aset sumber final ditanamkan ke dokumen pengujian lewat `set_content`. Berkas distribusi tetap memakai referensi aset normal, bukan base64. Tidak ada kebijakan browser yang diubah.

HTTP lokal diuji terpisah dengan urllib. Jadi laporan ini **bukan** bukti bahwa browser sudah diuji pada domain produksi, bahwa registrasi server berfungsi, atau bahwa Safari/iPhone/Android nyata sudah lulus. Performa network lapangan dan semantic audio tidak dinilai.

## Temuan dan perbaikan nyata

Pada ukuran 390 px dan teks 200%, grid judul kampanye sempat memaksa lebar halaman menjadi 427 px. Perbaikan `min-width: 0` pada anak grid dan `overflow-wrap` pada heading membuat lebar dokumen kembali 390 px tanpa menyembunyikan overflow atau mengecilkan teks. Stylesheet dasar investor tetap identik.

Dua koreksi fixture dan penantian smooth scroll dijelaskan di `qa/README.md`. Hasil awal disimpan di `bukti/QA_ITERASI_PERTAMA.json`; hasil final dan verifikasi anchor berada di `qa/hasil/`. Tidak ada kasus gagal terbuka dalam lingkup uji final ini.

## Gerbang komersial

Status: **NOT_READY_FOR_PUBLIC_RELEASE**. Ini gerbang terpisah, tidak diubah menjadi PASS oleh hasil frontend.

- registration_url belum diisi. Gunakan URL layanan nyata; jangan gunakan placeholder.
- site_url belum diisi. Gunakan URL layanan nyata; jangan gunakan placeholder.
- Pendaftaran/login layanan nyata belum terverifikasi
- Isi audio dan kebutuhan caption empat video belum diverifikasi
- Izin publikasi media belum dicatat
- Klaim satu klik dan konsistensi hasil belum diuji pada produk nyata
- Persetujuan rilis publik belum dicatat

Rujukan lengkap: `06_BATAS_RILIS_DAN_AKSES.md`.
