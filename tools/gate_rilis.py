#!/usr/bin/env python3
"""Gerbang rilis: melaporkan kelayakan tiap profil dan tiga lingkup kesiapan.

Memakai aturan yang sama dengan tools/bangun_rilis.py (tools/rilis_core.py), sehingga hasil gate dan
hasil build tidak dapat berbeda. Kode keluar 0 hanya bila profil production layak; selain itu 2.

  python3 tools/gate_rilis.py            ringkasan terbaca
  python3 tools/gate_rilis.py --json     JSON (juga ditulis ke qa/hasil/release-gate.json bila --write)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rilis_core as core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def report(root: Path, config: dict, allow_test_hosts: bool = False) -> dict:
    profiles = {p: core.assess(root, config, p, allow_test_hosts) for p in core.PROFILES}
    scopes = core.scopes(root, config)
    gates = {}
    for key, label in core.GATES.items():
        e = core.gate_entry(config, key)
        gates[key] = {'label': label, 'status': e.get('status') is True, 'evidence': e.get('evidence'), 'verified_by': e.get('verified_by'), 'date': e.get('date')}
    production = profiles['production']
    return {
        'version': core.VERSION,
        'status': 'READY_FOR_PUBLIC_RELEASE' if production['eligible'] else 'NOT_READY_FOR_PUBLIC_RELEASE',
        'scopes': scopes,
        'profiles': {p: {'eligible': v['eligible'], 'gaps': v['gaps']} for p, v in profiles.items()},
        'gates': gates,
        'gaps': [g['message'] for g in production['gaps']],
        'website_tree_sha256': core.tree_hash(root / 'website'),
    }


def assess(config: dict, root: Path = ROOT) -> dict:
    """Antarmuka 1.3.0 dipertahankan: {'status', 'gaps'}."""
    r = report(root, config)
    return {'status': r['status'], 'gaps': r['gaps']}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--write', action='store_true', help='Simpan juga ke qa/hasil/release-gate.json')
    ap.add_argument('--config', default=str(ROOT / 'konfigurasi' / 'rilis.json'))
    args = ap.parse_args(argv)
    try:
        result = report(ROOT, core.load_config(Path(args.config)))
    except core.ConfigError as exc:
        print('KONFIGURASI TIDAK SAH:', exc)
        return 1
    if args.write:
        out = ROOT / 'qa' / 'hasil'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'release-gate.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print(f'STATUS RILIS PUBLIK: {result["status"]}')
        for name, s in result['scopes'].items():
            print(f'  {name}: {"YA" if s["ready"] else "BELUM"} — {s["reason"]}')
        for p, v in result['profiles'].items():
            print(f'  profil {p}: {"layak dibangun" if v["eligible"] else "belum layak"}')
            for g in v['gaps']:
                print(f'      - [{g["code"]}] {g["message"]}')
    return 0 if result['status'] == 'READY_FOR_PUBLIC_RELEASE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
