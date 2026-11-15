# Panduan menjalankan dan deploy

## 1. Melihat di komputer sendiri

```bash
python3 pratinjau_lokal.py            # http://127.0.0.1:8080/
```

Server ini mendukung geser-posisi video (Range), melayani `404.html`, dan mengirim MIME yang benar. Membuka `website/index.html` langsung juga bisa, tetapi caption video tidak dimuat lewat `file://` (pembatasan browser); teks narasi di bawah video tetap tampil.

## 2. Yang dipublikasikan dan yang tidak

| Folder | Dipublikasikan? |
|---|---|
| `website/` (pratinjau) atau `dist/<profil>/` (hasil build) | **Ya, hanya isi salah satu folder ini** |
| `dokumentasi_internal/` | Tidak. Hanya untuk Account Page yang benar-benar terproteksi |
| `konfigurasi/`, `tools/`, `qa/`, `bukti/`, `laporan/`, `arsip/`, `riwayat_1.3.0/` | Tidak |

Folder publik berisi 122 berkas, 15 MB, semuanya dirujuk halaman (kecuali lisensi font). Tidak ada proses build, tidak ada dependensi pengunjung.

## 3. Tiga keadaan

| Profil | Kapan | Perintah | Hasil |
|---|---|---|---|
| preview | Sekarang | tidak perlu; unggah `website/` | "Pendaftaran belum dibuka", tidak diindeks |
| staging | Sesudah ada URL layanan akun | `python3 tools/bangun_rilis.py --profile staging --apply` | CTA ke layanan akun, bertanda "Lingkungan uji", tidak diindeks |
| production | Sesudah semua gerbang berbukti | `python3 tools/bangun_rilis.py --profile production --apply` | CTA ke layanan akun, diindeks, canonical, sitemap |

Tanpa `--apply` perintah hanya melaporkan. Bila syarat kurang, tidak ada yang ditulis dan kekurangannya disebut satu per satu. Skema konfigurasi: `konfigurasi/PANDUAN_KONFIGURASI.md`.

## 4. Hosting

Hosting belum ditetapkan, jadi tidak ada penyedia yang dipilih. Website ini statis dan berjalan di hosting statis mana pun yang:

- melayani `404.html` dengan status 404,
- mendukung permintaan Range untuk `.mp4`,
- mengirim `text/vtt` untuk `.vtt`, `image/webp`, `font/woff2`.

Content-Security-Policy sudah tertanam di HTML. Header tambahan (nosniff, Referrer-Policy, HSTS, cache) ada sebagai contoh di `konfigurasi/hosting/` untuk tiga format; pakai yang sesuai hosting Anda. Untuk staging, tambahkan `X-Robots-Tag: noindex`.

## 5. Sesudah unggah

```bash
python3 tools/smoke_live.py --profile production          # memakai site_url pada konfigurasi
python3 tools/smoke_live.py --profile staging --url https://ALAMAT-STAGING-ANDA
```

Memeriksa tiap berkas byte demi byte, MIME, Range 206/416, 404, kebijakan indeks, dan header. Hasilnya menjadi dasar LIVE_DEPLOYMENT_VERIFIED. Lalu buka di iPhone dan ponsel Android nyata.

## 6. Rollback

- Hasil build: `python3 tools/bangun_rilis.py --profile <profil> --rollback` mengaktifkan generasi sebelumnya di `dist/`.
- Situs: unggah ulang folder sebelumnya. `website/` selalu merupakan keadaan pratinjau yang aman.

## 7. Mengulang QA

```bash
pip install -r qa/requirements.txt && playwright install chromium
python3 qa/jalankan_semua.py
python3 tools/gate_rilis.py
```
