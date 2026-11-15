# Bukti rilis

Folder ini menampung bukti yang dirujuk gerbang pada `konfigurasi/rilis.json`. Gerbang hanya dianggap terpenuhi bila:

1. `status` bernilai `true`,
2. `evidence` menunjuk berkas **di dalam folder ini** yang ada dan tidak kosong,
3. `verified_by` berisi nama penanggung jawab,
4. `date` berformat `YYYY-MM-DD`.

Mengubah `status` menjadi `true` tanpa berkas bukti akan ditolak oleh `tools/gate_rilis.py` dan `tools/bangun_rilis.py`.

| Gerbang | Isi bukti yang diharapkan | Nama berkas yang disarankan |
|---|---|---|
| `account_flow_verified` | Catatan uji pada layanan nyata: daftar berhasil, input salah ditolak dengan aman, login, logout, akses Account Page, akses tanpa sesi ditolak. Sertakan tanggal, lingkungan, dan tangkapan layar atau log. | `alur-akun.md` |
| `audio_review_completed` | Pernyataan bahwa empat video telah didengarkan dan caption dicocokkan; daftar koreksi bila ada. | `tinjauan-audio.md` |
| `media_publication_approved` | Dasar hak publikasi komersial: asal gambar/video, izin pemeran (termasuk anak pada video 2 dan 3), dan keputusan atas merek pihak ketiga pada kemasan serta narasi. | `izin-media.md` |
| `product_claims_verified` | Skenario yang dapat diulang pada produk nyata untuk Canon 01 (konsistensi) dan Canon 02 (satu klik → prompt), berikut hasil dan batasnya. | `uji-klaim-produk.md` |
| `public_release_approved` | Persetujuan pemilik untuk rilis publik versi ini. | `persetujuan-rilis.md` |

Dua berkas dibuat oleh alat, bukan ditulis tangan:

- `url-check.json` ← `python3 tools/periksa_url.py`
- `live-smoke.json` ← `python3 tools/smoke_live.py --profile production`

Saat paket 1.4.0 diserahkan, folder ini hanya berisi README ini. Tidak ada bukti yang dibuat-buat.
