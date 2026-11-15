#!/usr/bin/env python3
"""Bangun keluaran website per profil. Folder website/ TIDAK PERNAH diubah.

  python3 tools/bangun_rilis.py --profile preview                 dry-run (bawaan): menilai dan melaporkan, tanpa menulis
  python3 tools/bangun_rilis.py --profile staging --apply         tulis dist/staging/
  python3 tools/bangun_rilis.py --profile production --apply      tulis dist/production/ HANYA bila semua gerbang berbukti
  python3 tools/bangun_rilis.py --profile staging --rollback      kembali ke keluaran generasi sebelumnya

Kode keluar: 0 = layak/berhasil, 2 = syarat belum terpenuhi (tidak ada yang ditulis), 1 = konfigurasi rusak.
Aturan kelayakan berasal dari tools/rilis_core.py dan sama dengan yang dipakai tools/gate_rilis.py.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rilis_core as core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profile', required=True, choices=core.PROFILES)
    ap.add_argument('--apply', action='store_true', help='Tulis keluaran ke dist/<profil>/. Tanpa ini hanya dry-run.')
    ap.add_argument('--rollback', action='store_true', help='Aktifkan kembali keluaran generasi sebelumnya.')
    ap.add_argument('--config', default=str(ROOT / 'konfigurasi' / 'rilis.json'))
    ap.add_argument('--root', default=str(ROOT), help=argparse.SUPPRESS)
    ap.add_argument('--json', action='store_true', help='Cetak hasil sebagai JSON.')
    args = ap.parse_args(argv)
    root = Path(args.root)
    if args.rollback:
        result = core.rollback(root, args.profile)
        print(json.dumps(result, ensure_ascii=False, indent=1) if args.json else ('ROLLBACK: ' + ('berhasil' if result['rolled_back'] else result['reason'])))
        return 0 if result['rolled_back'] else 2
    try:
        config = core.load_config(Path(args.config))
        if args.apply:
            result = core.build(root, config, args.profile)
        else:
            p = core.plan(root, config, args.profile)
            result = {k: p[k] for k in ('profile', 'eligible', 'gaps', 'changed', 'added')}
            result['written'] = False
    except core.ConfigError as exc:
        print('KONFIGURASI TIDAK SAH:', exc)
        return 1
    if args.json:
        print(json.dumps({k: v for k, v in result.items() if k != 'manifest'}, ensure_ascii=False, indent=1))
    elif not result['eligible']:
        print(f'TIDAK DIBANGUN — profil {args.profile} belum memenuhi syarat. Tidak ada berkas yang dibuat atau diubah.')
        for g in result['gaps']:
            print(f'  - [{g["code"]}] {g["message"]}')
    elif args.apply:
        m = result['manifest']
        print(f'DIBANGUN: {result["out"]}  (profil {args.profile})')
        print(f'  halaman berubah: {", ".join(m["changed_pages"]) or "-"} · berkas tambahan: {", ".join(m["added_files"]) or "-"}')
        print(f'  hash keluaran: {m["output_tree_sha256"]}')
        if args.profile == 'staging':
            print('  Staging tetap noindex dan bertanda lingkungan uji. Uji alur akun di sini, lalu catat buktinya.')
        if args.profile == 'production':
            print('  Unggah isi folder ini, lalu jalankan tools/smoke_live.py terhadap site_url.')
    else:
        print(f'DRY-RUN — profil {args.profile} layak dibangun. Tidak ada berkas yang ditulis.')
        print(f'  akan berubah: {", ".join(result["changed"]) or "-"} · akan ditambah: {", ".join(result["added"]) or "-"}')
    return 0 if result['eligible'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
