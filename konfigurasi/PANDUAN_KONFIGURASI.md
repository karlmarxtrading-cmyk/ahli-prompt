# Panduan `konfigurasi/rilis.json`

| Kunci | Isi | Wajib untuk |
|---|---|---|
| `site_url` | Alamat publik homepage, HTTPS. Boleh memakai subfolder. | production |
| `registration_url` | Halaman pendaftaran pada layanan akun resmi, HTTPS. | staging, production |
| `login_url` | Halaman login, HTTPS. | bila `account_requires_login` = `true` |
| `account_requires_login` | `true` bila alur produk punya halaman login terpisah, `false` bila tidak. Harus diputuskan, tidak boleh `null`. | staging, production |
| `official_hosts` | Daftar host layanan akun yang dinyatakan resmi oleh pemilik, mis. host dari `registration_url`. URL di luar daftar ini ditolak. | staging, production |
| `gates.*` | `{status, evidence, verified_by, date}`. Lihat `bukti/rilis/README.md`. | production |

Yang ditolak: `http://`, kredensial dalam URL, fragment `#`, alamat IP, `localhost`, domain contoh (`example.com`), dan TLD cadangan (`.test`, `.invalid`, `.local`, …).

## Urutan kerja

```bash
python3 tools/gate_rilis.py                              # lihat apa yang masih kurang
python3 tools/bangun_rilis.py --profile staging          # dry-run, tidak menulis
python3 tools/bangun_rilis.py --profile staging --apply  # tulis dist/staging/
python3 tools/periksa_url.py                             # bukti keterjangkauan URL
python3 tools/bangun_rilis.py --profile production --apply
python3 tools/smoke_live.py --profile production         # sesudah diunggah
```

`website/` tidak pernah diubah oleh alat-alat ini. Rollback: `python3 tools/bangun_rilis.py --profile <profil> --rollback`, atau unggah ulang `website/` (keadaan pratinjau).

Jangan menaruh kata sandi, token, atau kunci API di berkas ini atau di `website/`. Konfigurasi ini hanya memuat alamat publik.
