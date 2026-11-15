#!/usr/bin/env python3
"""Periksa keterjangkauan URL pada konfigurasi/rilis.json dan simpan buktinya.

Validasi bentuk (HTTPS, bukan host contoh) tidak cukup: tujuan harus benar-benar merespons saat diuji dan
berada pada host yang dinyatakan resmi oleh pemilik (official_hosts). Skrip ini melakukan GET HTTPS ke
site_url, registration_url, dan login_url, mengikuti redirect, lalu menulis bukti/rilis/url-check.json.

  python3 tools/periksa_url.py            periksa dan tulis bukti
  python3 tools/periksa_url.py --dry-run  periksa tanpa menulis

Skrip ini TIDAK menguji pendaftaran, login, atau sesi. Itu dicatat terpisah pada gerbang account_flow_verified.
Kode keluar 0 bila semua URL yang diisi lulus; 2 bila ada yang gagal; 1 bila konfigurasi rusak.
"""
import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rilis_core as core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str, timeout: float = 20.0) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'JagoPrompt-ReleaseCheck/1.4'})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        return {'status': r.status, 'final_url': r.geturl(), 'content_type': r.headers.get('Content-Type', '')}


def check(config: dict, fetcher=fetch, allow_test_hosts: bool = False) -> dict:
    """`fetcher` dapat diganti pada pengujian; jalur produksi selalu memakai jaringan nyata."""
    official = {h.lower() for h in (config.get('official_hosts') or []) if isinstance(h, str)}
    site_host = (urlsplit(config.get('site_url') or '').hostname or '').lower()
    results = []
    for key in ('site_url', 'registration_url', 'login_url'):
        value = config.get(key)
        if not value:
            continue
        row = {'key': key, 'url': value, 'ok': False}
        try:
            core.validate_url(value, key, True, allow_test_hosts)
            got = fetcher(value)
            final_host = (urlsplit(got['final_url']).hostname or '').lower()
            allowed = official | ({site_host} if site_host else set())
            row.update(got)
            if not 200 <= got['status'] < 300:
                row['detail'] = f'status HTTP {got["status"]}'
            elif urlsplit(got['final_url']).scheme != 'https':
                row['detail'] = 'berakhir pada alamat non-HTTPS'
            elif final_host not in allowed:
                row['detail'] = f'redirect berakhir pada host yang tidak dinyatakan resmi ({final_host})'
            elif 'html' not in got.get('content_type', '').lower():
                row['detail'] = f'bukan halaman HTML ({got.get("content_type")})'
            else:
                row['ok'] = True
                row['detail'] = 'terjangkau'
        except ValueError as exc:
            row['detail'] = str(exc)
        except urllib.error.HTTPError as exc:
            row['detail'] = f'status HTTP {exc.code}'
        except Exception as exc:  # jaringan, TLS, DNS, timeout
            row['detail'] = f'{type(exc).__name__}: {exc}'[:200]
        results.append(row)
    return {
        'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'config_fingerprint': core.url_fingerprint(config),
        'scope': 'GET HTTPS + redirect + host resmi. Bukan uji pendaftaran/login.',
        'ok': bool(results) and all(r['ok'] for r in results),
        'results': results,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--config', default=str(ROOT / 'konfigurasi' / 'rilis.json'))
    args = ap.parse_args(argv)
    try:
        config = core.load_config(Path(args.config))
    except core.ConfigError as exc:
        print('KONFIGURASI TIDAK SAH:', exc)
        return 1
    result = check(config)
    if not result['results']:
        print('Tidak ada URL yang diisi pada konfigurasi. Tidak ada yang diperiksa dan tidak ada bukti yang ditulis.')
        return 2
    for r in result['results']:
        print(f'  {"OK " if r["ok"] else "GAGAL"} {r["key"]}: {r["url"]} — {r["detail"]}')
    if not args.dry_run:
        out = ROOT / core.EVIDENCE_DIR
        out.mkdir(parents=True, exist_ok=True)
        (out / 'url-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'Bukti ditulis: {core.EVIDENCE_DIR}/url-check.json')
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
