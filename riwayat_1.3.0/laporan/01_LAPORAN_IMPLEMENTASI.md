# Rekonstruksi homepage Jago Prompt · 1.3.0

15 November 2026 — implementasi langsung pada source 1.2.0.

## Hasil yang diserahkan

Homepage sudah diubah dari presentasi mekanisme/pembelajaran menjadi sales page. Folder `website/` berisi implementasi yang dapat dibuka dan dipratinjau, bukan wireframe atau rekomendasi saja. UI/UX investor dijadikan baseline: seluruh isi `css/styles.css`, logo, font sumber, token warna, dan bentuk komponen utama dipertahankan. Penyesuaian untuk konten baru berada dalam `css/sales.css`.

Tidak ada klaim bahwa desain baru telah disetujui ulang investor; yang dipertahankan adalah dasar desain yang menurut pemilik sudah disetujui.

## Baseline dan prioritas arahan

Paket audit yang diunggah ulang berisi baseline historis 1.1.0. Versi 1.2.0 masih tersedia dari unggahan sebelumnya dan merupakan versi yang telah dinyatakan disetujui desainnya. Karena itu rekonstruksi memakai 1.2.0, bukan mengulang pekerjaan dari versi lama. Semua 139 checksum utama versi 1.2.0 cocok. Checksum paket audit UI/UX (41) dan audit konten (34) juga cocok. ASET(1).zip identik byte dengan ASET.zip sebelumnya.

Master instruction terbaru mengatasi saran lama yang mendorong tutorial, prompt, label kursus, dan rincian operasional di homepage. Dua canon dipertahankan persis; tidak dilunakkan atau diganti tanpa persetujuan.

## Dua canon dan fungsi aset

**Canon 01:** “Kunci DNA Brand kamu untuk hasil generate yang selalu konsisten.”

Menjadi H1 hero. Hasil visual ditampilkan sebelum masalah: tiga foto kosmetik dalam satu seri menggantikan campuran serum, tas, dan makanan yang sebelumnya tidak membuktikan kesinambungan satu seri. Galeri memperlihatkan dua studi visual terpisah: kosmetik dan kuliner. Total 31 gambar terpasang, terdiri dari dua referensi produk dan 29 contoh visual. Galeri tambahan memakai disclosure native, bukan auto-carousel.

**Canon 02:** “Cukup satu klik: hasilkan estetika produk menjadi prompt siap pakai.”

Menjadi judul bagian video tepat setelah hero. Empat MP4 vertikal 480 × 854, masing-masing 10 detik, dipasang untuk memperlihatkan arah konten affiliate: dua kosmetik dan dua aksesori/helm anak. Video menunjukkan produk, pemakaian, dan keseharian; tidak disajikan sebagai tutorial atau rekaman fitur satu klik yang telah diuji.

MP4 identik dengan unggahan. Poster diambil dari frame, audio tidak dibuang, kontrol native tetap tersedia, tidak ada autoplay. Setiap pemutar punya deskripsi visual, tautan langsung, pesan kegagalan, dan tombol coba lagi sendiri. Memutar satu video menghentikan yang lain.

## Urutan sales page final

1. **Hero / #beranda:** Canon 01, contoh hasil, manfaat singkat, dan CTA akses.
2. **Video / #hasil-video:** Canon 02, empat contoh konten affiliate, relevansi penggunaan.
3. **Masalah / #ide:** konten yang berubah-ubah dapat melemahkan kesan identitas; hubungan dua contoh dijelaskan setelah hasil sudah terlihat.
4. **Manfaat / #fitur:** empat kartu yang tetap mengikuti bentuk lama; konsistensi, daya tarik, kemudahan affiliate, dan keluwesan konten.
5. **Seri brand / #arahan-foto:** kosmetik dan kuliner tidak digabung sebagai satu DNA. Konteks referensi dan variasi dijelaskan.
6. **Kampanye / #arahan-video:** area gelap lama tetap ada, tetapi isinya kebutuhan etalase, keseharian, sorotan produk, dan momen khusus—bukan storyboard teknis.
7. **FAQ / #pemula:** bukan kursus, siapa pengguna, konteks contoh foto/video, dan perbedaan karakter antarbrand. Anchor lama #cara-kerja tetap tersedia di area ini.
8. **Pengguna / #cerita:** tiga kartu kebutuhan pemilik brand, affiliate, dan tim konten; tanpa nama, kutipan, rating, atau testimoni buatan.
9. **CTA / #mulai:** alasan mulai dan jalur akses yang jelas, kemudian footer.

## Yang dipisahkan ke materi Account Page

Panduan warna/suasana/ciri khas, contoh prompt, editor simulasi, diagram cahaya, tutorial, langkah penggunaan, dan storyboard parfum lama disimpan dalam `dokumentasi_internal/panduan_account.html`. Fungsi tombol Putar storyboard lama dipertahankan.

Dokumen tersebut **bukan akun aktif** dan **tidak dilindungi autentikasi**. Folder tidak termasuk yang dipublikasikan. Dokumen disiapkan untuk dipindahkan ke Account Page terautentikasi pada produk asli, bukan disamarkan sebagai dashboard yang telah selesai.

Contoh prompt lama “no text or logo” di arsip materi diperbaiki menjadi arahan mempertahankan label/kemasan/logo produk, tanpa mengarang klaim baru. Perubahan ini tidak membangun atau membuktikan mesin AI.

## Jalur akses dan batas backend

Source 1.2.0 tidak memuat backend, pendaftaran, login, penyimpanan Brand DNA, atau mesin AI. Rekonstruksi konten tidak menciptakan server tersebut secara diam-diam.

Semua CTA utama menuju `daftar.html`, halaman akses yang sungguh ada. Keadaan belum terhubung ditampilkan dengan jelas: tidak ada form email, password, pembayaran, pesan sukses palsu, atau akun berbasis localStorage yang disamarkan sebagai akun server. Catatan ringkas akses yang belum dibuka juga terlihat pada CTA akhir homepage.

`konfigurasi/rilis.json` dan `tools/aktifkan_rilis.py` disediakan untuk menghubungkan tombol secara konsisten ke layanan akun resmi ketika URL nyata tersedia. Helper memvalidasi format URL HTTPS, tetapi bukan pengganti uji pendaftaran pada layanan nyata. Script mengubah HTML sehingga tautan tetap berfungsi tanpa JavaScript setelah diaktifkan. `tools/gate_rilis.py` sengaja menolak label siap rilis komersial ketika persyaratan belum lengkap.

## Pembuktian dan komunikasi yang tidak dicampur

Kesamaan warna, suasana, dan kemasan pada contoh adalah bukti visual atas aset yang disediakan—bukan pembuktian bahwa software dalam ZIP menghasilkan aset tersebut, menjaga semua detail produk identik, atau setara pada semua platform AI. Kalimat canon berasal dari arahan pemilik; keberadaan kalimat tersebut bukan hasil uji efektivitas produk.

Tidak ditambahkan statistik, jumlah pelanggan, rating Jago Prompt, testimoni, pendapatan affiliate, tarif, maupun jaminan penjualan. Klaim/teks yang tampak dalam foto referensi produk pihak lain tidak dipindahkan menjadi klaim Jago Prompt.

## Pengujian

Lihat `qa/hasil/` dan `laporan/05_HASIL_PENGUJIAN.md` untuk hasil final. Pengujian statis memeriksa source, aset, tautan, canon, dan helper konfigurasi. HTTP lokal memeriksa byte aset dan respons Range video. Chromium benar-benar merender HTML dan memutar byte MP4 asli, namun memakai sumber yang di-inline karena kebijakan lingkungan memblokir navigasi URL browser. Ini bukan bukti deployment atau tes perangkat ponsel nyata.

Masalah reflow pada pembesaran teks 200% ditemukan dan diperbaiki: judul pada grid kampanye tidak lagi memaksa lebar minimum di luar layar. Perbaikannya tidak mengganti token/stylesheet dasar investor.

## Status penyerahan

**Rekonstruksi homepage: terimplementasi.**

**Rilis layanan komersial end-to-end: belum terverifikasi dan belum boleh disebut selesai.** Kesenjangan akun, klaim produk nyata, audio/caption, domain, serta perangkat/hosting dijelaskan tanpa disembunyikan. Website hasil kerja tetap diserahkan lengkap untuk pratinjau dan integrasi, tidak ditahan sebagai audit saja.
