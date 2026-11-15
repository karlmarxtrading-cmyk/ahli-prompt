# QA · 1.4.0

`python3 qa/jalankan_semua.py` menjalankan semuanya dan menulis `hasil/ringkasan.json`, yang terikat pada hash isi `website/`.

| Skrip | Hasil | Sifat |
|---|---|---|
| `check_static.py --profile <p>` | `static-<p>.json` | Statis per profil rilis; decode penuh media |
| `test_rilis.py` | `release-system-results.json` | Sistem rilis, kasus positif dan negatif, salinan sementara |
| `http_checks.py` | `http-results.json` | Server pratinjau lokal |
| `uji_mutasi.py` | `mutation-results.json` | Membuktikan pemeriksaan statis dapat gagal |
| `browser_checks.py --profile <p>` | `browser-<p>.json`, `screenshot/` | Chromium bernavigasi lewat HTTP |
| `visual_compare.py --baseline <folder>` | `visual-compare.json`, `screenshot/banding_*` | Perbandingan dengan 1.3.0 |
| `audio_transkripsi.py`, `audio_segmentasi.py` | `bukti/audio/` | Rekaman metode; memerlukan model yang diunduh terpisah |

Berkas `*-fixture.json` berasal dari build staging/production dengan host `.test` di folder sementara. Itu bukti aturan profil, bukan bukti rilis nyata.

Screenshot disimpan sebagai JPEG (kualitas 80) dari tangkapan PNG; menjalankan ulang skrip menghasilkan PNG.

Batas: satu mesin browser (Chromium desktop headless), viewport ponsel diemulasi, tanpa pembaca layar, tanpa hosting produksi.
