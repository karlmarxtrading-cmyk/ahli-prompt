#!/usr/bin/env python3
"""Hubungkan CTA ke layanan akun nyata; pustaka standar Python, tanpa paket tambahan.

Isi konfigurasi/rilis.json. Jalankan script untuk validasi/dry-run.
Gunakan --apply hanya sesudah URL akun dan domain telah benar-benar diverifikasi.
Script tidak membuat backend dan tidak menguji keberhasilan registrasi jarak jauh.
"""
from __future__ import annotations
import argparse, html, json, re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

def validate_url(value: str | None, label: str, required: bool = True) -> str | None:
    if not value:
        if required:
            raise ValueError(f'{label} belum diisi. Gunakan URL layanan nyata; jangan gunakan placeholder.')
        return None
    if not isinstance(value, str) or any(c in value for c in ['\r', '\n', '\t', '<', '>', '"', "'"]):
        raise ValueError(f'{label} bukan URL yang aman.')
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment:
        raise ValueError(f'{label} harus HTTPS, tanpa kredensial atau fragment.')
    if u.hostname in {'example.com','example.org','localhost','127.0.0.1'} or u.hostname.endswith('.invalid'):
        raise ValueError(f'{label} masih menggunakan host contoh/lokal.')
    return value

def set_href(tag: str, url: str) -> str:
    return re.sub(r'\bhref="[^"]*"', 'href="'+html.escape(url, quote=True)+'"', tag, count=1)

def apply(root: Path, config: dict, write: bool = False) -> list[str]:
    register=validate_url(config.get('registration_url'),'registration_url')
    login=validate_url(config.get('login_url'),'login_url',False)
    site=validate_url(config.get('site_url'),'site_url',False)
    approved=config.get('public_release_approved') is True
    if approved and not site:
        raise ValueError('Rilis publik memerlukan site_url yang benar.')
    if approved and config.get('account_flow_verified') is not True:
        raise ValueError('account_flow_verified harus true setelah alur akun diuji pada layanan nyata.')
    changes=[]
    for name in ['index.html','daftar.html']:
        p=root/'website'/name
        text=p.read_text(encoding='utf-8')
        text=re.sub(r'<a\b[^>]*\bdata-register-link(?:="[^"]*")?[^>]*>',lambda m:set_href(m.group(0),register),text)
        if name=='index.html':
            text=re.sub(r'<p\b[^>]*\bdata-access-note(?:="[^"]*")?[^>]*>.*?</p>','',text,flags=re.S)
        else:
            text=re.sub(r'<div\b[^>]*\bdata-registration-closed(?:="[^"]*")?[^>]*>',lambda m:re.sub(r'\s+hidden(?:="[^"]*")?','',m.group(0))[:-1]+' hidden>',text)
            text=re.sub(r'<div\b[^>]*\bdata-registration-open(?:="[^"]*")?[^>]*>',lambda m:re.sub(r'\s+hidden(?:="[^"]*")?','',m.group(0)),text)
            text=re.sub(r'<a\b[^>]*\bdata-registration-destination(?:="[^"]*")?[^>]*>',lambda m:set_href(m.group(0),register),text)
            if login:
                text=re.sub(r'<a\b[^>]*\bdata-login-link(?:="[^"]*")?[^>]*>',lambda m:set_href(re.sub(r'\s+hidden(?:="[^"]*")?','',m.group(0)),login),text)
        if site:
            base=site.rstrip('/')
            canonical=base+'/' if name=='index.html' else base+'/daftar.html'
            text=re.sub(r'<link\b[^>]*rel="canonical"[^>]*>\s*','',text)
            text=text.replace('</head>','<link rel="canonical" href="'+html.escape(canonical,quote=True)+'">\n</head>')
            text=re.sub(r'(<meta\b[^>]*property="og:image"[^>]*content=")[^"]*',lambda m:m.group(1)+base+'/assets/media/kosmetik-02-896.webp',text)
            # BeautifulSoup may serialize content before property, so support both orders.
            text=re.sub(r'<meta\b(?=[^>]*property="og:image")[^>]*>', '<meta property="og:image" content="'+html.escape(base,quote=True)+'/assets/media/kosmetik-02-896.webp">',text)
        if name=='index.html' and approved:
            text=re.sub(r'<meta\b(?=[^>]*name="robots")[^>]*>','<meta name="robots" content="index, follow">',text)
        if write:p.write_text(text,encoding='utf-8')
        changes.append(str(p.relative_to(root)))
    return changes

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply',action='store_true',help='Tulis perubahan; tanpa flag ini hanya validasi.')
    args=ap.parse_args()
    try:
        config=json.loads((ROOT/'konfigurasi/rilis.json').read_text(encoding='utf-8'))
        paths=apply(ROOT,config,args.apply)
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print('TIDAK DITERAPKAN:',exc)
        return 1
    print(('DITERAPKAN' if args.apply else 'DRY RUN — tidak ada file yang diubah')+': '+', '.join(paths))
    print('URL valid secara format bukan bukti bahwa layanan akun telah bekerja. Uji pendaftaran, login, dan akses akun di hosting nyata.')
    return 0
if __name__=='__main__':raise SystemExit(main())
