#!/usr/bin/env python3
"""Pemeriksaan HTTP atas folder distribusi lewat pratinjau_lokal.py. Bukan uji deployment atau hosting.

  python3 qa/http_checks.py [--site website] 
Memeriksa: tiap berkas 200 dan byte-identik, MIME, Range 206/416 keempat video, 404 nyata + halaman 404 khusus,
header keamanan, dan bahwa permintaan di luar folder publik tidak terlayani.
"""
import argparse, hashlib, json, sys, threading, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
import pratinjau_lokal, rilis_core as core  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--site', default=str(ROOT / 'website')); ap.add_argument('--out', default=str(ROOT / 'qa/hasil/http-results.json'))
args = ap.parse_args(); WEB = Path(args.site)
server = pratinjau_lokal.make_server(str(WEB), 0, security_headers=True)
threading.Thread(target=server.serve_forever, daemon=True).start(); base = f'http://127.0.0.1:{server.server_address[1]}'
MIME = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.webp': 'image/webp', '.woff2': 'font/woff2', '.mp4': 'video/mp4', '.vtt': 'text/vtt', '.png': 'image/png', '.jpg': 'image/jpeg'}
rows = []


def add(name, ok, detail=''):
    rows.append({'test': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})


def get(path, headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers or {})) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


try:
    for path in sorted(p for p in WEB.rglob('*') if p.is_file()):
        rel = path.relative_to(WEB).as_posix()
        status, headers, data = get('/' + rel)
        add('GET ' + rel, status == 200 and hashlib.sha256(data).digest() == hashlib.sha256(path.read_bytes()).digest(), {'http': status, 'bytes': len(data)})
        want = MIME.get(path.suffix.lower())
        if want:
            add('MIME ' + rel, headers.get('content-type', '').startswith(want), headers.get('content-type'))
    for i in range(1, 5):
        url = f'/assets/media/affiliate-{i:02d}.mp4'; blob = (WEB / url.lstrip('/')).read_bytes()
        status, headers, data = get(url, {'Range': 'bytes=100-1099'})
        add(f'Range 206 video {i}', status == 206 and data == blob[100:1100] and headers.get('content-range') == f'bytes 100-1099/{len(blob)}', headers.get('content-range'))
        status, headers, data = get(url, {'Range': 'bytes=-500'})
        add(f'Range akhiran video {i}', status == 206 and data == blob[-500:], status)
        status, headers, data = get(url, {'Range': 'bytes=99999999-'})
        add(f'Range tidak valid 416 video {i}', status == 416, status)
        add(f'Accept-Ranges video {i}', get(url, {'Range': 'bytes=0-0'})[1].get('accept-ranges') == 'bytes')
    status, headers, data = get('/')
    add('Root melayani index.html', status == 200 and data == (WEB / 'index.html').read_bytes())
    for h in ('content-security-policy', 'x-content-type-options', 'referrer-policy', 'x-frame-options', 'permissions-policy'):
        add('Header keamanan ' + h, bool(headers.get(h)), headers.get(h))
    for missing in ('/tidak-ada.mp4', '/tidak/ada/halaman', '/assets/media/affiliate-05.mp4', '/assets/video/fashion-example.mp4'):
        status, headers, data = get(missing)
        add('404 nyata ' + missing, status == 404 and b'Halaman ini belum ditemukan' in data, status)
    for outside in ('/../konfigurasi/rilis.json', '/..%2fkonfigurasi%2frilis.json', '/%2e%2e/dokumentasi_internal/panduan_account.html', '/../qa/README.md'):
        status, headers, data = get(outside)
        add('Di luar folder publik tidak terlayani ' + outside, status in (400, 403, 404) and b'registration_url' not in data and b'Materi' not in data[:0], status)
finally:
    server.shutdown(); server.server_close()
counts = {s: sum(r['status'] == s for r in rows) for s in ('PASS', 'FAIL')}
Path(args.out).write_text(json.dumps({'scope': 'Server pratinjau lokal (pratinjau_lokal.py) lewat urllib. Membuktikan berkas distribusi dan perilaku server contoh; BUKAN hosting publik.',
    'site_tree_sha256': core.tree_hash(WEB), 'counts': counts, 'results': rows}, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print('HTTP', counts)
for r in rows:
    if r['status'] == 'FAIL': print('  FAIL', r['test'], r['detail'])
sys.exit(0 if not counts['FAIL'] else 1)
