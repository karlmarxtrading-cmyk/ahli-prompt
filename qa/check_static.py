#!/usr/bin/env python3
"""Pemeriksaan source/keluaran per PROFIL RILIS. Tidak menyimpulkan kemampuan backend dari HTML.

  python3 qa/check_static.py --profile preview                         memeriksa website/
  python3 qa/check_static.py --profile staging    --site dist/staging
  python3 qa/check_static.py --profile production --site dist/production

Kriteria yang tidak bergantung profil (canon, struktur, aset, video, keamanan) berlaku di semua profil.
Kriteria status akses berbeda per profil dan TIDAK saling menggantikan:
  preview     harus jujur "belum dibuka", CTA ke daftar.html, noindex
  staging     CTA ke layanan akun resmi, tetap bertanda lingkungan uji, noindex
  production  CTA ke layanan akun resmi, tanpa status pratinjau, indeks + canonical + sitemap

--fixture menandai pemeriksaan atas build uji (host .test). Hasilnya membuktikan bahwa ATURAN profil bekerja,
bukan bahwa rilis nyata sudah ada.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rilis_core as core  # noqa: E402

CANON_01 = 'Kunci DNA Brand kamu untuk hasil generate yang selalu konsisten.'
CANON_02 = 'Cukup satu klik: hasilkan estetika produk menjadi prompt siap pakai.'
SECTION_ORDER = ['beranda', 'hasil-video', 'ide', 'fitur', 'arahan-foto', 'arahan-video', 'pemula', 'cerita', 'mulai']
ALLOWED_UNREFERENCED = {'assets/fonts/OFL-LICENSE.txt', 'robots.txt', 'sitemap.xml'}
CSP_REQUIRED = ["default-src 'self'", "script-src 'self'", "style-src 'self'", "object-src 'none'", "base-uri 'self'", "form-action 'none'"]

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--profile', required=True, choices=core.PROFILES)
ap.add_argument('--site', help='Folder yang diperiksa. Bawaan: website/ untuk preview, dist/<profil>/ selain itu.')
ap.add_argument('--config', default=str(ROOT / 'konfigurasi' / 'rilis.json'))
ap.add_argument('--fixture', action='store_true')
ap.add_argument('--out')
args = ap.parse_args()
PROFILE = args.profile
WEB = Path(args.site) if args.site else (ROOT / 'website' if PROFILE == 'preview' else ROOT / 'dist' / PROFILE)
CONFIG = core.load_config(Path(args.config))
results = []


def check(name, condition, detail='', old_id=None):
    results.append({'test': name, 'status': 'PASS' if condition else 'FAIL', 'detail': detail if isinstance(detail, (str, int, float, list, dict)) else str(detail), **({'replaces': old_id} if old_id else {})})


def norm(s):
    return ' '.join(s.split())


def read(p):
    return Path(p).read_text(encoding='utf-8')


if not WEB.is_dir():
    print(f'Folder {WEB} tidak ada. Bangun dulu: python3 tools/bangun_rilis.py --profile {PROFILE} --apply')
    sys.exit(2)

s = BeautifulSoup(read(WEB / 'index.html'), 'html.parser')
entry = BeautifulSoup(read(WEB / 'daftar.html'), 'html.parser')
nf = BeautifulSoup(read(WEB / '404.html'), 'html.parser')
pages = {'index.html': s, 'daftar.html': entry, '404.html': nf}
main_text = norm(s.main.get_text(' ', strip=True))
JS = read(WEB / 'js/main.js')

# ------------------------------------------------------------------ canon dan identitas
check('Canon 01 persis pada H1', norm(s.h1.get_text(' ', strip=True)) == CANON_01, norm(s.h1.get_text(' ', strip=True)))
check('Canon 02 persis pada #video-title', norm(s.select_one('#video-title').get_text(' ', strip=True)) == CANON_02)
check('Canon 01 hanya muncul sebagai H1 dan Canon 02 berada di #hasil-video', s.select_one('#beranda h1') is not None and s.select_one('#hasil-video #video-title') is not None)
check('Satu H1', len(s.find_all('h1')) == 1)
check('Bahasa Indonesia', s.html.get('lang') == 'id')
check('Nama brand tetap Jago Prompt', 'Jago Prompt' in s.title.get_text() and s.find('meta', attrs={'property': 'og:site_name'})['content'] == 'Jago Prompt')
check('Urutan section sales page terkunci', [x.get('id') for x in s.select('main > section')] == SECTION_ORDER, [x.get('id') for x in s.select('main > section')])
check('Anchor kompatibilitas #cara-kerja tetap ada', s.find(id='cara-kerja') is not None)
check('Navigasi header menuju section yang ada', [a['href'] for a in s.select('.nav-link')] == ['#beranda', '#arahan-foto', '#hasil-video', '#fitur', '#pemula'])

# ------------------------------------------------------------------ sales page, bukan manual/akun
check('Tidak ada contoh kode/prompt di homepage', not s.main.select('code, pre, .editor, .learn-illustration, .guide-illustration, .sv-prompt'))
check('Tidak ada tutorial operasional', all(x not in main_text.lower() for x in ['three-quarter', 'key fill rim', 'langkah 3 dari 6', 'no text or logo', 'kamera 45°', 'belajar sambil membuat']))
check('Tidak ada testimonial palsu', not s.main.select('blockquote'))
check('Tidak ada form, input, atau penyimpanan akun palsu', not any(p.select('form, input, select, textarea') for p in pages.values()) and not re.search(r'localStorage|sessionStorage|indexedDB|document\.cookie', JS))
check('Tidak ada tautan mati href="#" atau javascript:', not any(a.get('href', '').strip() in ('#', '') or a.get('href', '').lower().startswith('javascript:') for p in pages.values() for a in p.find_all('a')))
banned = ['pasti laku', 'omzet naik', 'penjualan naik', 'dijamin', 'ribuan pengguna', 'ratusan brand', 'terbukti meningkatkan', 'mitra resmi', 'partner resmi', 'penghasilan affiliate', 'komisi']
hit = [b for b in banned if b in main_text.lower()]
check('Tidak ada janji pendapatan, jumlah pengguna, atau kemitraan', not hit, hit)
check('Kartu pengguna menjelaskan kebutuhan, bukan kutipan', len(s.select('.persona-grid .testimonial-card')) == 3 and not s.select('.persona-grid q, .persona-grid cite'))
check('FAQ menjawab keraguan (4 butir native details)', len(s.select('.faq-list details > summary')) == 4)
check('Disclaimer merek/kemasan dan narasi video tersedia', 'tidak menyatakan kerja sama' in main_text and 'bukan pernyataan, penawaran, atau kerja sama dari Jago Prompt' in main_text)
check('Hero tanpa form, input, atau langkah wajib sebelum hasil', not s.select('#beranda form, #beranda input, #beranda button') and s.select_one('#beranda .hero-shot-main img[fetchpriority=high][loading=eager]') is not None)

# ------------------------------------------------------------------ aset gambar
manifest = json.loads(read(ROOT / 'bukti/ASET_MANIFEST.json'))
check('Manifest memuat 31 gambar dan 4 video', len(manifest['images']) == 31 and len(manifest['videos']) == 4)
check('Dua seri aset terpisah', bool(s.select_one('#case-kosmetik') and s.select_one('#case-kuliner')))
used = {t.get('src') for t in s.select('img')}
for r in manifest['images']:
    check(f'Gambar sumber {r["id"]:02d} terpakai', r['variants'][-1]['url'] in used, r['variants'][-1]['url'])
    for v in r['variants']:
        p = WEB / v['url']
        check(f'Varian gambar utuh {v["url"]}', p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == v['sha256'])
refs = [t for t in s.select('.case-reference img')]
check('Dua referensi produk dibedakan dari 29 contoh visual', len(refs) == 2 and all('referensi' in t['alt'].lower() for t in refs) and all('Referensi produk' in f.get_text() for f in s.select('.case-reference figcaption')))
kos = {t['src'] for t in s.select('article[aria-labelledby=case-kosmetik] img')}
kul = {t['src'] for t in s.select('article[aria-labelledby=case-kuliner] img')}
check('Seri kosmetik dan kuliner tidak bercampur', all('kosmetik-' in x for x in kos) and all('kuliner-' in x for x in kul) and len(kos) == 15 and len(kul) == 16, {'kosmetik': len(kos), 'kuliner': len(kul)})
check('Tidak ada gambar stok/placeholder dari luar aset proyek', all(x.startswith(('assets/media/', 'assets/brand/')) for x in used), sorted(x for x in used if not x.startswith(('assets/media/', 'assets/brand/'))))

# ------------------------------------------------------------------ video, caption, narasi
videos = s.find_all('video')
check('Tepat empat video baru (tanpa pemutar kelima)', len(videos) == 4 and sorted(v.source['src'] for v in videos) == [f'assets/media/affiliate-0{i}.mp4' for i in range(1, 5)])
check('Video fashion historis tidak dipublikasikan', not (WEB / 'assets/video').exists() and 'fashion-example' not in read(WEB / 'index.html'))
cues_ref = json.loads(read(ROOT / 'bukti/audio/caption_cues.json'))
for v in videos:
    vid = v['id']
    n = vid.split('-')[1]
    check(f'Kontrol native {vid}', v.has_attr('controls') and v.has_attr('playsinline') and v.get('preload') == 'none' and not any(v.has_attr(a) for a in ('autoplay', 'loop', 'muted')))
    check(f'Dimensi intrinsik dan poster {vid}', v.get('width') == '480' and v.get('height') == '854' and (WEB / v.get('poster', 'x')).is_file())
    check(f'Deskripsi video {vid}', s.find(id=v.get('aria-describedby')) is not None)
    check(f'Tautan alternatif di luar pemutar {vid}', any(a.find_parent('video') is None for a in s.find_all('a', href=v.source['src'])))
    unit = v.find_parent(attrs={'data-media-unit': True})
    check(f'Pesan gagal dan tombol coba lagi {vid}', unit is not None and unit.select_one('[data-video-status][role=status]') is not None and unit.select_one('button[data-video-retry][hidden]') is not None)
    tr = v.find('track')
    ok_track = tr is not None and tr.get('kind') == 'captions' and tr.get('srclang') == 'id' and (WEB / tr.get('src', 'x')).is_file()
    check(f'Caption Indonesia terpasang {vid}', ok_track)
    if ok_track:
        vtt = read(WEB / tr['src'])
        cues = re.findall(r'(\d\d):(\d\d):(\d\d\.\d{3}) --> (\d\d):(\d\d):(\d\d\.\d{3})\n(.+)', vtt)
        times = [(int(a) * 3600 + int(b) * 60 + float(c), int(d) * 3600 + int(e) * 60 + float(f)) for a, b, c, d, e, f, _ in cues]
        mono = all(st < en for st, en in times) and all(times[i][1] <= times[i + 1][0] + 1e-6 for i in range(len(times) - 1))
        check(f'WebVTT sah dan berurutan {vid}', vtt.startswith('WEBVTT') and len(cues) >= 4 and mono and times[-1][1] <= 10.0, len(cues))
        text = ' '.join(c[6].strip() for c in cues)
        check(f'Caption sama dengan transkrip yang ditinjau {vid}', text == ' '.join(c['text'] for c in cues_ref[n]))
        tp = unit.select_one('details.media-transcript p') if unit else None
        check(f'Teks narasi tersedia tanpa JS dan sama dengan caption {vid}', tp is not None and norm(tp.get_text()) == text)
for m in manifest['videos']:
    p = WEB / m['website_url']
    check(f'Video identik sumber {m["id"]}', hashlib.sha256(p.read_bytes()).hexdigest() == m['sha256'])
    done = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'null', '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check(f'Decode penuh audio/video {m["id"]}', done.returncode == 0 and not done.stderr.strip(), done.stderr.decode()[:300])
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'json', str(p)], stdout=subprocess.PIPE).stdout)
    check(f'Track audio dipertahankan {m["id"]}', sorted(x['codec_type'] for x in probe['streams']) == ['audio', 'video'])
check('Satu video berjalan pada satu waktu (jeda video lain)', 'other.pause()' in JS and 'addEventListener("playing"' in JS)
check('Tidak ada autoplay/loop dari skrip', not re.search(r'\.autoplay\s*=|\.loop\s*=|\.muted\s*=', JS))

# ------------------------------------------------------------------ desain investor
check('CSS dasar investor tidak berubah', (WEB / 'css/styles.css').read_bytes() == (ROOT / 'bukti/source_sebelum/css/styles.css').read_bytes())
check('Perubahan CSS dipisahkan di sales.css', (WEB / 'css/sales.css').is_file() and [l['href'] for l in s.select('link[rel=stylesheet]')] == ['css/styles.css', 'css/sales.css'])
check('Font dan logo sumber dipakai', (WEB / 'assets/fonts/plus-jakarta-sans-latin-800-normal.woff2').is_file() and s.select_one('.brand img')['src'] == 'assets/brand/logo-jago-prompt-96.png')

# ------------------------------------------------------------------ keamanan frontend dan folder publik
for name, page in pages.items():
    csp = page.find('meta', attrs={'http-equiv': 'Content-Security-Policy'})
    check(f'CSP tertanam: {name}', csp is not None and all(d in csp['content'] for d in CSP_REQUIRED), csp['content'] if csp else '')
    inline = [t for t in page.find_all('script') if not t.get('src') and t.get('type') != 'application/ld+json']
    check(f'Tanpa script inline: {name}', not inline)
    handlers = [(t.name, a) for t in page.find_all(True) for a in t.attrs if a.lower().startswith('on')]
    check(f'Tanpa event handler inline: {name}', not handlers, handlers[:3])
    check(f'Tanpa atribut style atau <style>: {name}', not page.find_all(style=True) and not page.find_all('style'))
    ext = [t.get(a) for t in page.find_all(['script', 'link', 'img', 'video', 'source', 'track', 'iframe']) for a in ('src', 'href', 'poster') if t.get(a, '').startswith(('http:', 'https:', '//')) and not (t.name == 'link' and 'canonical' in (t.get('rel') or []))]
    check(f'Tanpa sumber daya pihak ketiga: {name}', not ext, ext)
    for block in page.find_all('script', type='application/ld+json'):
        try:
            json.loads(block.string)
            ok = True
        except Exception:
            ok = False
        check(f'JSON-LD sah: {name}', ok)
    check(f'Penanda profil = {PROFILE}: {name}', (page.find('meta', attrs={'name': 'jp-release-profile'}) or {}).get('content') == PROFILE)
    check(f'Versi 1.4.0 tercatat: {name}', (page.find('meta', attrs={'name': 'jp-version'}) or {}).get('content') == core.VERSION)
check('flag.js menandai JS dan mencabutnya bila main.js gagal', 'classList.add("js")' in read(WEB / 'js/flag.js') and 'classList.remove("js")' in read(WEB / 'js/flag.js'))
all_files = {p.relative_to(WEB).as_posix() for p in WEB.rglob('*') if p.is_file()}
bad_types = sorted(f for f in all_files if Path(f).suffix.lower() in ('.py', '.md', '.json', '.csv', '.zip', '.map', '.log', '.env', '.pdf') or Path(f).name.startswith('.'))
check('Folder publik tanpa laporan, konfigurasi, skrip, atau berkas tersembunyi', not bad_types, bad_types)
check('Materi internal tidak ikut dipublikasikan', not any('dokumentasi' in f or 'panduan_account' in f for f in all_files) and 'panduan_account' not in read(WEB / 'index.html'))
secret = [f for f in all_files if Path(f).suffix in ('.html', '.js', '.css') and re.search(r'(api[_-]?key|secret|password|token)\s*[:=]\s*["\'][^"\']{8,}', read(WEB / f), re.I)]
check('Tidak ada secret pada frontend', not secret, secret)

# ------------------------------------------------------------------ referensi berkas, ID, anchor, alt
referenced = set()
for name, page in pages.items():
    ids = [t['id'] for t in page.find_all(id=True)]
    check(f'ID unik: {name}', len(ids) == len(set(ids)))
    check(f'H1 tunggal: {name}', len(page.find_all('h1')) == 1)
    for t in page.find_all(True):
        for attr in ('src', 'href', 'poster'):
            url = t.get(attr)
            if not url or url.startswith(('http:', 'https:', 'data:', 'mailto:', 'tel:')):
                continue
            if url.startswith('#'):
                check(f'Anchor {name}{url}', url[1:] in ids)
                continue
            part = url.split('#')[0]
            if part in ('', '/'):
                continue
            p = WEB / part.lstrip('/')
            check(f'Resource {name} -> {url}', p.is_file())
            referenced.add(part.lstrip('/'))
            if '#' in url and part.endswith('.html') and p.is_file():
                target_ids = {x['id'] for x in BeautifulSoup(read(p), 'html.parser').find_all(id=True)}
                check(f'Anchor lintas halaman {name} -> {url}', url.split('#')[1] in target_ids)
    for t in page.select('img'):
        check(f'Alt dan dimensi gambar {name}: {t.get("src", "")[-28:]}', bool(t.get('alt')) and t.get('width', '').isdigit() and t.get('height', '').isdigit())
    for t in page.find_all(srcset=True) + page.find_all(imagesrcset=True):
        for item in (t.get('srcset') or t.get('imagesrcset')).split(','):
            rel = item.strip().split()[0]
            check(f'Srcset {rel}', (WEB / rel).is_file())
            referenced.add(rel)
    for meta in page.find_all('meta', attrs={'property': 'og:image'}):
        if not meta['content'].startswith('http'):
            referenced.add(meta['content'])
for css in (WEB / 'css').glob('*.css'):
    for u in re.findall(r'url\(["\']?([^)"\']+)', read(css)):
        p = (css.parent / u).resolve()
        check(f'Resource CSS {css.name} -> {u}', p.is_file())
        if p.is_file():
            referenced.add(p.relative_to(WEB.resolve()).as_posix())
orphans = sorted(all_files - referenced - set(pages) - ALLOWED_UNREFERENCED)
check('Tidak ada berkas publik yang tidak dipakai', not orphans, orphans)
pre = s.select_one('link[rel=preload][as=image]')
first = s.select_one('.hero-shot-main img')
check('Preload gambar sama dengan gambar hero pertama', pre is not None and pre['href'] == first['src'] and pre.get('imagesrcset') == first.get('srcset'))
check('Semua berkas di bawah 25 MiB', all((WEB / f).stat().st_size < 25 * 1024 * 1024 for f in all_files))
check('JS syntax main.js', subprocess.run(['node', '--check', str(WEB / 'js/main.js')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0)
check('JS syntax flag.js', subprocess.run(['node', '--check', str(WEB / 'js/flag.js')], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0)

# ------------------------------------------------------------------ status akses PER PROFIL
register_links = s.select('[data-register-link]')
robots = {n: (p.find('meta', attrs={'name': 'robots'}) or {}).get('content') for n, p in pages.items()}
closed, opened = entry.select_one('[data-registration-closed]'), entry.select_one('[data-registration-open]')
check('Tujuh CTA daftar konsisten', len(register_links) == 7 and len({a['href'] for a in register_links}) == 1, [a['href'] for a in register_links])
check('daftar.html dan 404.html tidak pernah diindeks', robots['daftar.html'] == 'noindex, follow' and robots['404.html'] == 'noindex, follow', robots)

if PROFILE == 'preview':
    check('[preview] CTA menuju halaman akses yang ada', all(a['href'] == 'daftar.html' for a in register_links), old_id='1.3.0: CTA menuju halaman akses yang ada')
    check('[preview] Halaman akses jujur: belum dibuka', not closed.has_attr('hidden') and opened.has_attr('hidden') and 'belum dibuka' in closed.get_text(), old_id='1.3.0: Halaman akses jujur')
    check('[preview] Status akun terlihat di homepage', 'akses akun segera hadir' in main_text.lower(), old_id='1.3.0: Status akun terlihat di homepage')
    check('[preview] Beranda tidak diindeks', robots['index.html'] == 'noindex, follow', old_id='1.3.0: Pratinjau tidak diindeks sebelum rilis')
    check('[preview] Tanpa canonical, robots.txt, sitemap', not any(p.select('link[rel=canonical]') for p in pages.values()) and not (WEB / 'robots.txt').exists() and not (WEB / 'sitemap.xml').exists())
    check('[preview] Tidak ada URL absolut layanan akun', not re.search(r'href="https?://', read(WEB / 'index.html') + read(WEB / 'daftar.html')))
    check('[preview] Tanda lingkungan uji tersembunyi', entry.select_one('[data-staging-note]').has_attr('hidden'))
else:
    reg, login, site = CONFIG.get('registration_url'), CONFIG.get('login_url'), (CONFIG.get('site_url') or '').rstrip('/')
    official = {h.lower() for h in CONFIG.get('official_hosts') or []}
    check(f'[{PROFILE}] Konfigurasi memuat tujuan akun', bool(reg))
    check(f'[{PROFILE}] CTA menuju layanan akun pada konfigurasi', bool(reg) and all(a['href'] == reg for a in register_links), old_id='1.3.0: CTA menuju halaman akses yang ada (diganti: tujuan akun nyata)')
    check(f'[{PROFILE}] Tujuan akun HTTPS dan pada host resmi', bool(reg) and urlsplit(reg).scheme == 'https' and urlsplit(reg).hostname in official)
    check(f'[{PROFILE}] Halaman akses menampilkan tujuan resmi, bukan "belum dibuka"', closed.has_attr('hidden') and not opened.has_attr('hidden') and entry.select_one('[data-registration-destination]')['href'] == reg, old_id='1.3.0: Halaman akses jujur (diganti: status akses sesuai profil)')
    link = entry.select_one('[data-login-link]')
    check(f'[{PROFILE}] Tautan login sesuai keputusan alur', (link['href'] == login and not link.has_attr('hidden')) if login else link.has_attr('hidden'))
    hosts = set(re.findall(r'https?://([A-Za-z0-9.\-]+)', ''.join(read(WEB / n) for n in pages))) - {'schema.org'}
    leaked = sorted(h for h in hosts if core.host_is_reserved(h))
    if args.fixture:
        check(f'[{PROFILE}] (fixture) host uji hanya .test', all(h.endswith('.test') for h in leaked), leaked)
    else:
        check(f'[{PROFILE}] Tidak ada host contoh/uji pada keluaran', not leaked, leaked)
    if PROFILE == 'staging':
        check('[staging] Tetap bertanda lingkungan uji di homepage', 'Lingkungan uji' in (s.select_one('[data-access-note]').get_text() if s.select_one('[data-access-note]') else ''), old_id='1.3.0: Status akun terlihat di homepage (diganti: tanda staging)')
        check('[staging] Tanda lingkungan uji di halaman akses', not entry.select_one('[data-staging-note]').has_attr('hidden'))
        check('[staging] Tidak diindeks', robots['index.html'] == 'noindex, follow', old_id='1.3.0: Pratinjau tidak diindeks sebelum rilis')
        check('[staging] Tanpa canonical, robots.txt, sitemap', not any(p.select('link[rel=canonical]') for p in pages.values()) and not (WEB / 'robots.txt').exists())
    if PROFILE == 'production':
        check('[production] Tanpa status pratinjau/staging', s.select_one('[data-access-note]') is None and 'segera hadir' not in main_text.lower() and 'Lingkungan uji' not in main_text and entry.select_one('[data-staging-note]').has_attr('hidden'), old_id='1.3.0: Status akun terlihat di homepage (diganti: status akses produksi)')
        check('[production] Beranda boleh diindeks', robots['index.html'] == 'index, follow', old_id='1.3.0: Pratinjau tidak diindeks sebelum rilis (diganti: indeks hanya pada rilis sah)')
        can = s.select_one('link[rel=canonical]')
        check('[production] Canonical dan og:url = site_url', bool(site) and can is not None and can['href'] == site + '/' and s.find('meta', attrs={'property': 'og:url'})['content'] == site + '/')
        og = s.find('meta', attrs={'property': 'og:image'})['content']
        check('[production] og:image absolut pada site_url dan berkasnya ada', og.startswith(site + '/') and (WEB / og[len(site) + 1:]).is_file(), og)
        check('[production] JSON-LD memuat url situs', json.loads(s.find('script', type='application/ld+json').string).get('url') == site + '/')
        check('[production] robots.txt dan sitemap.xml', (WEB / 'robots.txt').is_file() and f'Sitemap: {site}/sitemap.xml' in read(WEB / 'robots.txt') and f'<loc>{site}/</loc>' in read(WEB / 'sitemap.xml'))
        check('[production] site_url HTTPS', urlsplit(site).scheme == 'https')
        if not args.fixture:
            gate = core.assess(ROOT, CONFIG, 'production')
            check('[production] Gate rilis memenuhi syarat dengan bukti', gate['eligible'], [g['message'] for g in gate['gaps']], old_id='1.3.0: Gerbang rilis tidak PASS palsu (diganti: gate harus terbukti)')

# ------------------------------------------------------------------ konsistensi sistem rilis (hanya pada paket nyata)
if not args.fixture:
    for script in ['tools/rilis_core.py', 'tools/bangun_rilis.py', 'tools/gate_rilis.py', 'tools/aktifkan_rilis.py', 'tools/periksa_url.py', 'tools/smoke_live.py', 'pratinjau_lokal.py']:
        check('Python compile ' + script, subprocess.run([sys.executable, '-B', '-c', f'import ast,sys;ast.parse(open(r"{ROOT / script}",encoding="utf-8").read())']).returncode == 0)
    real = core.load_config(ROOT / 'konfigurasi/rilis.json')
    flags_true = [k for k in core.GATES if core.gate_entry(real, k).get('status') is True]
    gate = core.assess(ROOT, real, 'production')
    check('Gerbang rilis tidak PASS palsu: tiap gerbang true memiliki bukti yang sah', gate['eligible'] or not any(g['code'] in flags_true and 'Belum terpenuhi' not in g['message'] for g in gate['gaps']) , flags_true, old_id='1.3.0: Gerbang rilis tidak PASS palsu')
    check('Konfigurasi paket tidak memuat host contoh/uji', not any(core.host_is_reserved(urlsplit(real.get(k) or 'https://x.y').hostname) for k in ('site_url', 'registration_url', 'login_url') if real.get(k)))
    if PROFILE == 'preview':
        check('website/ adalah keadaan preview (build preview identik)', core.plan(ROOT, real, 'preview')['changed'] == [])
        for doc in sorted((ROOT / 'dokumentasi_internal').glob('*.html')):
            d = BeautifulSoup(read(doc), 'html.parser')
            missing = [t.get(at) for t in d.find_all(True) for at in ('src', 'href', 'poster') if t.get(at) and not t.get(at).startswith(('http', '#', 'data:', 'mailto:')) and not (doc.parent / t.get(at).split('#')[0]).exists()]
            check(f'Materi internal utuh dan di luar folder publik: {doc.name}', not missing and ROOT / 'website' not in doc.parents, missing)
            check(f'Materi internal bertanda tidak diindeks: {doc.name}', 'noindex' in ((d.find('meta', attrs={'name': 'robots'}) or {}).get('content') or ''))

counts = {k: sum(r['status'] == k for r in results) for k in ('PASS', 'FAIL')}
out = Path(args.out) if args.out else ROOT / 'qa' / 'hasil' / f'static-{PROFILE}{"-fixture" if args.fixture else ""}.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({
    'profile': PROFILE, 'fixture': args.fixture, 'site': str(WEB.relative_to(ROOT)) if WEB.is_relative_to(ROOT) else 'folder sementara (build fixture)',
    'scope': 'Pemeriksaan statis berkas distribusi dan decode penuh media. Bukan uji browser, akun, atau hosting.' + (' BUILD FIXTURE dengan host .test: membuktikan aturan profil, bukan rilis nyata.' if args.fixture else ''),
    'site_tree_sha256': core.tree_hash(WEB), 'counts': counts, 'results': results}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'STATIC[{PROFILE}{" fixture" if args.fixture else ""}]', counts)
for r in results:
    if r['status'] == 'FAIL':
        print('  FAIL', r['test'], '|', str(r['detail'])[:300])
sys.exit(0 if counts['FAIL'] == 0 else 1)
