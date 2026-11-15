#!/usr/bin/env python3
"""Smoke test hosting: membandingkan situs yang sudah diunggah dengan keluaran build.

Dijalankan SETELAH isi dist/<profil>/ diunggah. Memeriksa, lewat HTTP nyata:
  - setiap berkas pada manifest build terlayani 200 dan byte-identik
  - MIME html/css/js/webp/woff2/mp4/vtt
  - Range 206 dan 416 pada keempat video
  - path yang tidak ada → status 404 (bukan 200)
  - kebijakan indeks sesuai profil (meta robots dan header X-Robots-Tag)
  - header keamanan yang terpasang (dilaporkan; CSP juga tertanam di HTML)

  python3 tools/smoke_live.py --profile production                 memakai site_url pada konfigurasi
  python3 tools/smoke_live.py --profile staging --url https://...   URL staging diberikan langsung

Hasil ditulis ke bukti/rilis/live-smoke.json (production) atau live-smoke-staging.json.
Bukan uji pendaftaran/login, bukan uji perangkat, bukan pengukuran performa pengguna.
"""
import argparse
import hashlib
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
MIME = {'.html': 'text/html', '.css': 'text/css', '.js': 'javascript', '.webp': 'image/webp', '.woff2': 'font/woff2',
        '.mp4': 'video/mp4', '.vtt': 'text/vtt', '.png': 'image/png', '.jpg': 'image/jpeg', '.xml': 'xml', '.txt': 'text/plain'}


def http(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'JagoPrompt-Smoke/1.4', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context() if url.startswith('https') else None) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def run(base: str, manifest: dict, profile: str) -> dict:
    base = base.rstrip('/')
    rows = []

    def add(name, ok, detail=''):
        rows.append({'test': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})

    index_headers = {}
    for rel, sha in manifest['files'].items():
        status, headers, body = http(f'{base}/{rel}')
        same = hashlib.sha256(body).hexdigest() == sha
        add(f'GET {rel}', status == 200 and same, {'http': status, 'identik': same})
        want = MIME.get(Path(rel).suffix.lower())
        if want:
            ct = {k.lower(): v for k, v in headers.items()}.get('content-type', '')
            add(f'MIME {rel}', want in ct.lower(), ct)
        if rel == 'index.html':
            index_headers = {k.lower(): v for k, v in headers.items()}
    status, headers, body = http(base + '/')
    add('Root melayani index.html', status == 200 and hashlib.sha256(body).hexdigest() == manifest['files']['index.html'], status)
    for rel in sorted(r for r in manifest['files'] if r.endswith('.mp4')):
        status, headers, body = http(f'{base}/{rel}', {'Range': 'bytes=100-1099'})
        h = {k.lower(): v for k, v in headers.items()}
        add(f'Range 206 {rel}', status == 206 and len(body) == 1000 and h.get('content-range', '').startswith('bytes 100-1099/'), {'http': status, 'content-range': h.get('content-range')})
        status, _, _ = http(f'{base}/{rel}', {'Range': 'bytes=999999999-'})
        add(f'Range tidak valid 416 {rel}', status == 416, status)
    status, _, body = http(base + '/halaman-yang-tidak-ada-7f3a/')
    add('Path tidak ada → 404', status == 404, status)
    add('Halaman 404 khusus dilayani', b'Halaman ini belum ditemukan' in body)
    robots_header = index_headers.get('x-robots-tag', '')
    index_html = http(base + '/index.html')[2].decode('utf-8', 'replace')
    if profile == 'production':
        add('Produksi: beranda boleh diindeks', 'content="index, follow" name="robots"' in index_html and 'noindex' not in robots_header.lower(), robots_header)
        status, _, body = http(base + '/robots.txt')
        add('Produksi: robots.txt tersedia', status == 200 and b'Sitemap:' in body, status)
    else:
        add(f'{profile}: beranda tidak diindeks', 'content="noindex, follow" name="robots"' in index_html, robots_header)
    add(f'Penanda profil = {profile}', f'content="{profile}" name="jp-release-profile"' in index_html)
    security = {k: index_headers.get(k.lower()) for k in ('Content-Security-Policy', 'X-Content-Type-Options', 'Referrer-Policy', 'X-Frame-Options', 'Strict-Transport-Security')}
    add('Header X-Content-Type-Options: nosniff', (security['X-Content-Type-Options'] or '').lower() == 'nosniff', security['X-Content-Type-Options'])
    counts = {s: sum(r['status'] == s for r in rows) for s in ('PASS', 'FAIL')}
    return {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'site_url': base, 'profile': profile,
            'output_tree_sha256': manifest['output_tree_sha256'], 'ok': counts['FAIL'] == 0, 'counts': counts,
            'security_headers_seen': security, 'results': rows,
            'scope': 'HTTP nyata terhadap URL yang diberikan. Bukan uji akun, perangkat, atau performa pengguna.'}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profile', required=True, choices=core.PROFILES)
    ap.add_argument('--url', help='URL situs yang diuji. Bawaan: site_url pada konfigurasi (wajib untuk production).')
    ap.add_argument('--manifest', help='Bawaan: dist/<profil>.manifest.json')
    ap.add_argument('--allow-local-http', action='store_true', help='Hanya untuk menguji skrip ini terhadap pratinjau_lokal.py. Tidak menulis bukti rilis.')
    ap.add_argument('--out', help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        config = core.load_config(ROOT / 'konfigurasi' / 'rilis.json')
    except core.ConfigError as exc:
        print('KONFIGURASI TIDAK SAH:', exc)
        return 1
    url = args.url or config.get('site_url')
    local = bool(url) and urlsplit(url).hostname in ('127.0.0.1', 'localhost')
    if not url:
        print('Tidak ada URL: isi site_url pada konfigurasi atau berikan --url. Tidak ada yang diuji.')
        return 2
    if local and not args.allow_local_http:
        print('URL lokal ditolak. Smoke test hosting harus terhadap alamat publik (atau pakai --allow-local-http untuk menguji skrip).')
        return 2
    if not local:
        try:
            core.validate_url(url, 'url')
        except ValueError as exc:
            print('URL TIDAK SAH:', exc)
            return 2
        if args.profile == 'production' and url.rstrip('/') != (config.get('site_url') or '').rstrip('/'):
            print('Untuk production, URL harus sama dengan site_url pada konfigurasi.')
            return 2
    manifest_path = Path(args.manifest) if args.manifest else ROOT / 'dist' / f'{args.profile}.manifest.json'
    if not manifest_path.is_file():
        print(f'Manifest build tidak ditemukan: {manifest_path}. Bangun dulu dengan tools/bangun_rilis.py --profile {args.profile} --apply.')
        return 2
    result = run(url, json.loads(manifest_path.read_text(encoding='utf-8')), args.profile)
    result['local_script_test'] = local
    print(f'SMOKE {args.profile} {url}: {result["counts"]}')
    for r in result['results']:
        if r['status'] != 'PASS':
            print('  GAGAL', r['test'], r['detail'])
    if args.out:
        target = Path(args.out)
    elif local:
        target = None          # uji skrip lokal tidak pernah menjadi bukti rilis
    else:
        target = ROOT / core.EVIDENCE_DIR / ('live-smoke.json' if args.profile == 'production' else f'live-smoke-{args.profile}.json')
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('Hasil ditulis:', target)
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
