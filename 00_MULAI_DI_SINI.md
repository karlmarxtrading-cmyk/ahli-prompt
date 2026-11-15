# Jago Prompt 1.4.0 · kandidat rilis

16 November 2026 · lanjutan dari 1.3.0

## Status

| Lingkup | Status |
|---|---|
| FRONTEND_READY | **Ya.** Teruji di Chromium lewat HTTP; ponsel/tablet berupa emulasi. |
| ACCOUNT_PRODUCT_E2E_READY | **Belum.** Tidak ada layanan akun atau mesin produk dalam bahan. |
| LIVE_DEPLOYMENT_VERIFIED | **Belum.** Domain dan hosting belum ditetapkan. |

Status rilis publik: `NOT_READY_FOR_PUBLIC_RELEASE`. Tujuh butir yang tersisa beserta penanggung jawab dan langkahnya ada di `BLOCKERS.json`.

## Lihat sekarang

```bash
python3 pratinjau_lokal.py     # http://127.0.0.1:8080/
python3 tools/gate_rilis.py    # apa yang masih kurang untuk rilis
```

## Peta paket

| Lokasi | Isi |
|---|---|
| `website/` | **Folder siap unggah** (keadaan pratinjau yang jujur). 122 berkas, 15 MB. |
| `tools/` | `bangun_rilis.py`, `gate_rilis.py`, `periksa_url.py`, `smoke_live.py`, `rilis_core.py` |
| `konfigurasi/` | `rilis.json` (tanpa secret), panduan, contoh header hosting |
| `laporan/` | Implementasi, ledger, perubahan, peta media, hasil uji, matriks, panduan deploy, kontrak akun |
| `qa/` | Skrip uji, `hasil/` (JSON), `screenshot/` (72 gambar dari source final) |
| `bukti/` | Manifest aset, tinjauan audio, bukti rilis (masih kosong), instruksi pemilik |
| `dokumentasi_internal/` | Materi Account Page. **Tidak dipublikasikan.** |
| `arsip/` | Aset lama yang dikeluarkan dari folder publik |
| `riwayat_1.3.0/` | Laporan, konfigurasi, dan skrip 1.3.0 yang digantikan |
| `BLOCKERS.json`, `CHECKPOINT.json`, `SHA256SUMS.txt` | Status, titik lanjut, checksum |

Urutan baca: `laporan/01_LAPORAN_IMPLEMENTASI.md` → `BLOCKERS.json` → `laporan/08_PANDUAN_JALANKAN_DAN_DEPLOY.md`.
