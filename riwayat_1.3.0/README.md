# Jago Prompt · Rekonstruksi Sales Page 1.3.0

**Ini paket website hasil implementasi, bukan paket audit saja.**

## Mulai

Buka `website/index.html` untuk melihat halaman. Untuk pratinjau lokal dengan dukungan seek video, jalankan dari folder paket:

```bash
python pratinjau_lokal.py
```

Buka alamat lokal yang dicetak script. Tidak diperlukan `npm install` atau proses build untuk memakai website.

## Isi paket

| Folder | Isi | Dipublikasikan? |
|---|---|---|
| `website/` | Homepage, halaman akses, 404, CSS, JS, gambar, font sumber, poster, dan video | Hanya folder ini untuk pratinjau publik setelah menilai batas rilis |
| `laporan/` | Perubahan, rekonsiliasi 73 komponen, atlas final, peta aset, hasil uji, batas rilis | Tidak |
| `dokumentasi_internal/` | Materi penggunaan yang dikeluarkan dari homepage | Tidak; belum terautentikasi |
| `konfigurasi/` dan `tools/` | Konfigurasi serta helper penghubung layanan akun resmi | Tidak |
| `qa/` | Script, hasil, dan screenshot final | Tidak |
| `bukti/` | Instruksi pemilik, inventaris sumber, checksum, provenance media | Tidak |

## Yang sudah diubah

Dua canon persis, hasil foto dan video lebih dahulu, 31 gambar dalam dua seri, empat video affiliate, kartu manfaat, FAQ, persona tanpa testimoni palsu, dan CTA yang konsisten. Stylesheet dasar investor tidak diubah. Materi teknis dipisahkan.

## Batas yang penting

**Pendaftaran/login dan mesin produk tidak ada dalam source unggahan.** Halaman `daftar.html` menunjukkan keadaan belum dibuka secara jujur; tidak membuat akun palsu. Jangan menyatakan paket ini sebagai layanan SaaS end-to-end yang sudah aktif.

`konfigurasi/rilis.json` masih tanpa URL akun/domain. `noindex` dipertahankan pada pratinjau. Baca `laporan/06_BATAS_RILIS_DAN_AKSES.md` sebelum publikasi komersial.

Daftar checksum final ada di `SHA256SUMS.txt`. Hasil uji berada di `laporan/05_HASIL_PENGUJIAN.md` dan `qa/hasil/`.
