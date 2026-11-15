# Tinjauan isi audio empat video · 1.4.0

**Metode: transkripsi mesin, bukan pendengaran manusia.** Saya (Claude) tidak dapat mendengar audio. Audio tiap video diekstrak (mono 16 kHz) lalu ditranskripsikan dengan dua model Whisper yang berbeda ukuran (small dan medium, lewat sherpa-onnx). Bahasa terdeteksi otomatis: Indonesia, pada keempat berkas. Kedua model menghasilkan isi yang sama; perbedaannya hanya ejaan.

Temuan 1.3.0 "isi audio belum diverifikasi" kini terjawab: **keempat video berisi narasi penjualan berbahasa Indonesia.** Tingkat suara rata-rata −17 sampai −19 dB, puncak sekitar −1 dB.

## Transkrip yang dipakai sebagai caption

| Video | Berkas | Narasi |
|---|---|---|
| 1 | `affiliate-01.mp4` | Makeup udah rapi, tapi bibirnya flat banget? Layer di atas lipstikmu. Langsung plumpy, nggak lengket, warnanya intense. Cocok semua tone kulit. Shade incaran keburu habis, amankan sekarang! |
| 2 | `affiliate-02.mp4` | Anak ogah pakai helm? Coba yang ini. Gayanya retro, busanya empuk, kacanya bening full. Usia 4–12 tahun. Warna krem incaran, checkout sebelum kehabisan. |
| 3 | `affiliate-03.mp4` | Telat sekolah gara-gara drama helm? Stop! Helm retro krem bikin anak semangat berangkat. Busa plus, usia 4–12 tahun. Warna incaran, checkout sebelum kehabisan. |
| 4 | `affiliate-04.mp4` | Bibir kering pas difoto? Tahan! Ini Maybelline Lifter Gloss, ada hyaluronic acid. Sekali oles terasa lembap dan glossy. Ada 6 shade. Checkout sebelum shade incaranmu kehabisan. |

Ejaan dinormalkan dari keluaran mesin (mis. "plampi/plumpy" → plumpy, "olez" → oles, "in caran" → incaran, "hellem" → helm, "retro-creme" → retro krem). Keluaran mentah kedua model: `transkrip_whisper_small.json`, `transkrip_whisper_medium.json`.

## Kata yang perlu dipastikan pendengar manusia

| Video | Kata pada caption | Catatan |
|---|---|---|
| 1 | "Layer" | small menulis "layar", medium "Layer". |
| 2 | "full" | Muncul di kedua model sesudah "kacanya bening". |
| 3 | "Busa plus" | Kedua model menulis "Busa plus/Plus". Bisa juga kata lain yang mirip bunyinya. |
| 4 | "Maybelline Lifter Gloss" | Nama merek pihak ketiga; kedua model sama. Lihat `BLOCKERS.json` butir media. |

## Pewaktuan

Batas cue diambil dari lembah energi audio dan jeda senyap (`segmen_pewaktuan.json`), lalu teks transkrip penuh dipetakan ke rentang itu. Ketelitian diperkirakan ±0,3 detik. Uji browser memastikan cue kedua aktif pada waktunya dan teks caption sama dengan teks narasi di halaman; uji itu tidak menilai kecocokan dengan suara.

## Keputusan

- Caption WebVTT berbahasa Indonesia dipasang pada keempat video (`assets/media/affiliate-0N.id.vtt`), tidak aktif otomatis.
- Teks narasi yang sama tersedia di bawah tiap video (`Baca narasi video N`), terbaca tanpa JavaScript.
- Audio tidak diubah atau dibuang.
- Halaman menyatakan bahwa narasi, penyebutan merek, klaim produk, dan ajakan membeli adalah bagian dari contoh konten, bukan pernyataan Jago Prompt.

## Status

Identifikasi isi audio dan penyediaan caption: selesai dengan metode mesin.
**Koreksi oleh pendengar manusia: belum dilakukan.** Gerbang `audio_review_completed` tetap `false`. Untuk menutupnya: putar keempat video (40 detik), cocokkan dengan tabel di atas, perbaiki `.vtt` dan teks narasi bila ada yang berbeda, lalu catat di `bukti/rilis/` (lihat `bukti/rilis/README.md`).
