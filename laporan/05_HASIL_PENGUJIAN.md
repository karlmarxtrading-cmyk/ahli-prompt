# Hasil pengujian · 1.4.0

Dijalankan 15–16 November 2026 pada source final. Hash isi `website/`: `a7bf5a7dd8160bdfa4bd3ee8c51bf2a6ad3f23707eaf5e8776e49c592bc90002`. Bila source berubah, `tools/gate_rilis.py` otomatis menganggap hasil ini tidak berlaku.

## Lingkungan

- Chromium 153.0.8010.12, headless, Linux (kontainer). Node 22, Python 3.12, ffmpeg.
- Server: `pratinjau_lokal.py` pada loopback, header keamanan aktif. Browser **bernavigasi ke URL**; aset dimuat lewat HTTP, bukan ditanamkan.
- Ukuran ponsel dan tablet adalah emulasi viewport pada Chromium desktop.

## Ringkasan per rangkaian

Satuan tiap rangkaian berbeda dan tidak dijumlahkan menjadi skor kesiapan.

| Rangkaian | Lulus | Gagal | Satuan | Perintah |
|---|---:|---:|---|---|
| Statis · profil preview | 624 | 0 | atribut dan berkas `website/`, decode penuh media | `python3 qa/check_static.py --profile preview` |
| Sistem rilis | 38 | 0 | uji unit pada salinan sementara, host fixture `.test` | `python3 qa/test_rilis.py` |
| HTTP lokal | 273 | 0 | permintaan ke server pratinjau | `python3 qa/http_checks.py` |
| Uji mutasi | 12 | 0 | mutasi yang harus terdeteksi | `python3 qa/uji_mutasi.py` |
| Browser · profil preview | 50 | 0 | skenario Chromium lewat HTTP | `python3 qa/browser_checks.py --profile preview` |
| Statis · staging (fixture) | 606 | 0 | aturan profil pada build uji | `python3 qa/check_static.py --profile staging` |
| Browser · staging (fixture) | 2 | 0 | skenario status akses | `python3 qa/browser_checks.py --profile staging` |
| Statis · production (fixture) | 609 | 0 | aturan profil pada build uji | `python3 qa/check_static.py --profile production` |
| Browser · production (fixture) | 2 | 0 | skenario status akses | `python3 qa/browser_checks.py --profile production` |

Rangkaian *fixture* membangun staging dan production di folder sementara dengan host `.test`. Hasilnya membuktikan aturan profil bekerja; **bukan** bukti bahwa layanan akun atau rilis nyata ada.

## Cakupan uji browser (profil preview)

- **Delapan viewport:** layar awal dan halaman penuh; tanpa scroll horizontal, tanpa teks terpotong, tanpa respons 4xx, tanpa galat console, tanpa pelanggaran CSP; media tidak diminta sebelum Putar.
- **Anchor dan navigasi:** enam anchor dengan pointer dan keyboard pada dua ukuran; lima tautan header dengan penanda aktif; `#cara-kerja`.
- **Empat video, masing-masing:** Putar, Jeda, seek, Space, panah, suara, selesai tanpa loop, putar ulang, layar penuh lewat API; audio benar-benar ter-decode; rasio 480:854.
- **Caption:** dimuat, cue aktif pada waktunya, teks sama dengan narasi di halaman.
- **Kegagalan media:** 404, jaringan putus, berkas rusak; pesan hanya pada video terkait; pemulihan dengan keyboard; tautan alternatif menjawab 206.
- **Tanpa JavaScript** (dua ukuran), `main.js` gagal dimuat, reduced motion.
- **Keyboard:** skip link, 48 perhentian Tab mengikuti urutan baca, menu mobile (fokus, Escape, klik luar), FAQ, disclosure galeri; 31 gambar sumber termuat setelah galeri dibuka.
- **Aksesibilitas terukur:** kontras terendah 4.81:1 pada 214 simpul teks; target interaktif terendah 44 px.
- **Zoom 200%/400% dan teks 200%;** gambar gagal; font gagal; halaman 404 berstatus 404.
- **Keamanan:** header terpasang; skrip sisipan, skrip luar, dan gambar luar diblokir CSP.

## Hasil ukur layar awal

| Viewport | Gambar utama terlihat | Ukuran H1 |
|---|---:|---:|
| 1440 × 900 | 97% | 52 px |
| 1280 × 800 | 80% | 49 px |
| 1024 × 768 | 100% | 43 px |
| 768 × 1024 | 100% | 38 px |
| 390 × 844 | 100% | 30 px |
| 360 × 800 | 100% | 30 px |
| 320 × 568 | 55% | 30 px |
| 844 × 390 | 33% | 28 px |

Pada 320 × 568 dan landscape 844 × 390 teks tidak diperkecil untuk memaksa gambar naik.

## Performa (pengukuran lab, bukan data pengguna)

Pemuatan dingin lewat HTTP loopback. Throttling memakai emulasi DevTools: 1,6 Mbps turun, RTT 150 ms, CPU 4× lebih lambat. Tidak ada skor Lighthouse yang dijalankan.

| Kondisi | FCP | LCP | CLS | Muat awal | Permintaan |
|---|---:|---:|---:|---:|---:|
| 1440x900 · tanpa throttling | 148 ms | 148 ms | 0.00 | 0.61 MB | 20 |
| 1440x900 · throttling 1,6 Mbps / RTT 150 ms / CPU 4x | 1736 ms | 1736 ms | 0.00 | 0.50 MB | 18 |
| 390x844 · tanpa throttling | 172 ms | 172 ms | 0.00 | 0.47 MB | 18 |
| 390x844 · throttling 1,6 Mbps / RTT 150 ms / CPU 4x | 1600 ms | 1600 ms | 0.00 | 0.47 MB | 18 |

Elemen LCP adalah gambar hero. Video dan caption tidak dimuat pada pemuatan awal.

## Perbandingan visual dengan 1.3.0

2 dari 20 tangkapan section identik per piksel (hero, dua ukuran). 16 dari 20 memiliki kotak tata letak yang tidak bergeser lebih dari 1 px. Yang berubah: `#hasil-video` (baris narasi) dan footer (target 44 px). Selisih piksel kecil pada section lain berasal dari anti-alias teks pada posisi sub-piksel; kotak elemennya 0 px.

## Kegagalan pada putaran awal

Dicatat di `bukti/QA_KEGAGALAN_AWAL_1.4.0.md`. Tidak ada assertion yang dilonggarkan untuk meluluskan hasil.

## Yang tidak tercakup

| Hal | Status |
|---|---|
| Safari/iOS, Chrome Android pada perangkat, Firefox | BLOCKED: browser tidak dapat dipasang; tidak ada perangkat fisik |
| Pembaca layar | NOT VERIFIED |
| Caption dicocokkan pendengar manusia | NOT VERIFIED |
| Layanan akun, login, sesi, Account Page | BLOCKED: tidak ada dalam bahan |
| Hosting produksi, HTTPS, CDN, performa pengguna | BLOCKED: domain dan hosting belum ada |
