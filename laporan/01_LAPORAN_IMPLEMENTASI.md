# Laporan implementasi · Jago Prompt 1.4.0

16 November 2026 · baseline: `JAGO_PROMPT_REKONSTRUKSI_SALES_1.3.0_20261115.zip` (SHA-256 `517b588c…f79a`, checksum internal cocok)

## Hasil dalam satu paragraf

Frontend selesai dan teruji lewat navigasi HTTP nyata. Sistem rilis (konfigurasi, build, gate) kini satu aturan dan tidak dapat diaktifkan tanpa bukti. Isi audio keempat video teridentifikasi dan diberi caption. Rilis publik **belum** dapat dinyatakan siap: tidak ada layanan akun, mesin produk, domain, atau hosting di dalam bahan, dan izin publikasi media belum dicatat. Paket ini kandidat rilis, bukan PRODUCTION_READY.

| Lingkup | Status | Dasar |
|---|---|---|
| FRONTEND_READY | **Ya** (Chromium desktop + emulasi viewport) | `qa/hasil/ringkasan.json`, terikat hash `website/` |
| ACCOUNT_PRODUCT_E2E_READY | **Belum** (BLOCKED) | Tidak ada URL, backend, atau mesin produk dalam kelima arsip |
| LIVE_DEPLOYMENT_VERIFIED | **Belum** (BLOCKED) | Domain dan hosting belum ditetapkan; tidak ada deployment |

## 1. Yang dipertahankan

- Dua canon, persis: H1 `#beranda` dan judul `#hasil-video`.
- Urutan sales page, anchor `#cara-kerja`, 31 gambar (2 referensi + 29 contoh, dua seri terpisah), 4 video baru.
- `css/styles.css` identik byte demi byte dengan dasar investor. Semua penyesuaian tetap di `css/sales.css`.
- Keadaan pratinjau yang jujur di `website/`: CTA ke `daftar.html`, "pendaftaran belum dibuka", `noindex`.
- 112 dari 122 berkas `website/` identik dengan 1.3.0.

## 2. Yang diperbaiki

### 2.1 Konfigurasi, helper aktivasi, dan gate

Cabang yang diminta diverifikasi memang ada pada 1.3.0: `aktifkan_rilis.py --apply` hanya memeriksa bentuk URL, lalu menulis langsung ke `website/`, mengganti tujuh CTA dan **menghapus catatan akses** walau gerbang lain belum terpenuhi. Hanya perubahan `robots` yang menunggu gate.

Sekarang:

- **Satu aturan.** `tools/rilis_core.py` menentukan kelayakan. `bangun_rilis.py` dan `gate_rilis.py` memanggil fungsi yang sama; uji memastikan keduanya selalu sepakat.
- **Tiga profil.** `preview` (sama dengan `website/`), `staging` (CTA ke layanan akun untuk diuji, tetap bertanda "Lingkungan uji" dan `noindex`), `production` (hanya bila semua syarat berbukti).
- **Source tidak pernah diubah.** Keluaran ditulis ke `dist/<profil>/` secara atomik. Syarat kurang berarti tidak ada berkas yang dibuat.
- **Dry-run bawaan**, `--apply` untuk menulis, `--rollback` untuk kembali satu generasi.
- **Gerbang berbukti.** `true` hanya berlaku bila menunjuk berkas nyata di `bukti/rilis/`, dengan penanggung jawab dan tanggal. Boolean datar gaya 1.3.0 ditolak.
- **URL.** Selain bentuk: host harus ada di `official_hosts`, dan `tools/periksa_url.py` harus mencatat URL itu terjangkau. Mengganti URL sesudah diperiksa membatalkan buktinya.
- **Fixture tidak bocor.** Uji memakai host `.test`; jalur CLI menolaknya, dan keluaran dipindai sebelum disahkan.
- `aktifkan_rilis.py` dipertahankan namanya, tetapi hanya meneruskan ke `bangun_rilis.py`.

### 2.2 Audio dan caption

Keempat video berisi narasi penjualan berbahasa Indonesia. Rincian metode dan transkrip: `bukti/audio/TINJAUAN_AUDIO.md`.

- Caption WebVTT Indonesia pada tiap video, tidak aktif otomatis, tidak dimuat sebelum pengguna memutar.
- Teks narasi yang sama di bawah tiap video, terbaca tanpa JavaScript.
- Penafian di bawah kelompok video diperluas: narasi, penyebutan merek, klaim produk, dan ajakan membeli adalah bagian dari contoh konten, bukan pernyataan Jago Prompt.
- Video 4 menyebut "Maybelline Lifter Gloss". Itu saya tulis apa adanya pada caption dan saya catat sebagai blocker publikasi.

### 2.3 Cacat 1.3.0 yang ditemukan uji browser lewat HTTP

| Temuan | Dampak | Perbaikan |
|---|---|---|
| Penanda menu aktif memakai urutan tautan, padahal urutan menu berbeda dari urutan section | Di "Visual Brand", menu menandai "Manfaat" | `main.js`: pilih section terdekat di atas ambang berdasarkan posisi |
| Pergeseran layout desktop saat font selesai dimuat (CLS 0,14) | Judul hero pindah baris, isi hero naik | `sales.css`: font cadangan bermetrik selaras; tampilan akhir tidak berubah. CLS terukur 0,00 |
| Tautan footer setinggi 40 px | Di bawah 44 px | 44 px |
| Meta description `404.html` menyalin deskripsi halaman akses | Deskripsi salah | Diperbaiki |
| Server pratinjau mengembalikan halaman galat bawaan Python untuk 404, tanpa MIME `.vtt` | Tidak meniru hosting statis | `pratinjau_lokal.py` melayani `404.html` berstatus 404 dan MIME eksplisit |

### 2.4 Folder publik dan keamanan

- 29 berkas (5,7 MB) tidak dirujuk halaman mana pun, termasuk `assets/video/fashion-example.mp4`. Lima yang dipakai materi internal pindah ke `dokumentasi_internal/assets/`; sisanya ke `arsip/aset_tidak_dipakai/`. Daftar dan hash: `bukti/BERKAS_DIKELUARKAN_DARI_PUBLIK.json`.
- Content-Security-Policy tertanam sebagai `<meta>` di ketiga halaman, sehingga berlaku di hosting apa pun. Untuk itu script inline dipindah ke `js/flag.js` dan atribut `onerror` dihapus. Uji browser membuktikan skrip sisipan, skrip luar, dan gambar luar diblokir, tanpa pelanggaran pada pemakaian normal.
- Contoh header untuk tiga jenis server ada di `konfigurasi/hosting/`, dibangkitkan dari satu sumber. Tidak ada penyedia yang dipilih.

### 2.5 QA

- `check_static.py` berprofil. Kriteria pratinjau tetap ada untuk `preview`; `staging` dan `production` punya kriteria pengganti yang diuji pada build fixture. Pemetaan ID lama: `07_PEMETAAN_KRITERIA_LAMA.csv`.
- `browser_checks.py` bernavigasi ke server HTTP yang melayani berkas distribusi, menggantikan `set_content` dengan aset ditanamkan.
- `test_rilis.py`: 38 uji, termasuk penolakan untuk tiap gerbang yang belum terpenuhi.
- `uji_mutasi.py`: 12 mutasi (canon diubah, indeks dibuka, form palsu, dan lain-lain) semuanya terdeteksi.

## 3. Perbandingan visual dengan 1.3.0

Hero identik per piksel pada 1440 dan 390. Pada section lain, kotak tata letak setiap elemen tidak bergeser (0 px). Dua pengecualian yang disengaja: `#hasil-video` bertambah tinggi karena baris "Baca narasi video" (155 px desktop, 381 px ponsel), dan footer berubah 4–8 px. Rincian: `qa/hasil/visual-compare.json`, gambar `qa/screenshot/banding_*.jpg`.

**Perubahan yang terlihat ini belum ditinjau investor.** Persetujuan investor atas 1.3.0 tidak saya anggap mencakupnya.

## 4. Yang tidak dikerjakan, dan alasannya

- **Akun, login, Account Page, penyimpanan Brand DNA, mesin prompt.** Saya memeriksa kelima arsip: tidak ada endpoint, konfigurasi, atau spesifikasi integrasi. Membangunnya berarti memilih penyedia, model data, dan biaya atas nama Anda. Yang disiapkan: kontrak kebutuhan (`09_KONTRAK_INTEGRASI_AKUN.md`) dan perangkat aktivasi yang sudah teruji.
- **Deployment.** Tidak ada domain, akses hosting, atau otorisasi. `tools/smoke_live.py` siap dipakai sesudah unggah; skripnya diuji terhadap server lokal dan menolak URL lokal sebagai bukti.
- **Firefox, Safari/WebKit.** Tidak dapat dipasang di lingkungan kerja.
