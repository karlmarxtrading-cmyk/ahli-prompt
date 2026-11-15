#!/usr/bin/env python3
"""Nama lama (1.3.0). Sekarang hanya meneruskan ke tools/bangun_rilis.py.

Versi 1.3.0 menulis langsung ke website/ dan dapat mengganti CTA serta menghapus catatan akses sebelum
seluruh gerbang terpenuhi. Perilaku itu dihapus:
  - website/ tidak pernah diubah; keluaran ditulis ke dist/<profil>/
  - kelayakan ditentukan oleh aturan yang sama dengan gate (tools/rilis_core.py)
  - tanpa --apply hanya dry-run

  python3 tools/aktifkan_rilis.py                     = bangun_rilis.py --profile production   (dry-run)
  python3 tools/aktifkan_rilis.py --apply             = bangun_rilis.py --profile production --apply
  python3 tools/aktifkan_rilis.py --profile staging --apply
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rilis_core import validate_url  # noqa: E402,F401  (diekspor ulang untuk kompatibilitas)
import bangun_rilis  # noqa: E402

if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--profile' not in argv:
        argv = ['--profile', 'production'] + argv
    raise SystemExit(bangun_rilis.main(argv))
