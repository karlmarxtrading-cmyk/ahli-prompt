#!/usr/bin/env python3
"""Inti sistem rilis Jago Prompt — satu sumber aturan untuk konfigurasi, build, dan gate.

Dipakai bersama oleh:
  tools/bangun_rilis.py   membangun keluaran per profil ke dist/<profil>/ (website/ tidak pernah diubah)
  tools/gate_rilis.py     melaporkan kelayakan tiap profil dan tiga lingkup kesiapan
  tools/aktifkan_rilis.py nama lama; sekarang hanya meneruskan ke bangun_rilis.py
  qa/                     pengujian memanggil fungsi yang sama, bukan salinan aturannya

Hanya pustaka standar Python 3. Tidak menghubungi jaringan (lihat tools/periksa_url.py dan tools/smoke_live.py).

Tiga profil:
  preview     Keadaan jujur "pendaftaran belum dibuka". Sama persis dengan folder website/. Tidak diindeks.
  staging     CTA menuju layanan akun resmi untuk DIUJI. Tetap tidak diindeks dan tetap diberi tanda lingkungan uji.
  production  Rilis publik. Hanya dapat dibangun bila SEMUA gerbang punya bukti.
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

VERSION = '1.4.0'
PROFILES = ('preview', 'staging', 'production')
PAGES = ('index.html', 'daftar.html', '404.html')
EVIDENCE_DIR = 'bukti/rilis'

# Gerbang yang harus disertai bukti. Persetujuan desain investor BUKAN salah satunya.
GATES = {
    'account_flow_verified': 'Alur akun pada layanan nyata (daftar, kegagalan input, login/logout, akses Account Page, penolakan tanpa sesi)',
    'audio_review_completed': 'Isi audio empat video dan caption telah diperiksa pendengar manusia',
    'media_publication_approved': 'Hak publikasi komersial media (pemeran, merek pada kemasan dan narasi) dicatat',
    'product_claims_verified': 'Klaim dua canon diuji pada produk nyata dengan skenario yang dapat diulang',
    'public_release_approved': 'Persetujuan pemilik untuk rilis publik dicatat',
}

RESERVED_TLDS = ('.test', '.example', '.invalid', '.localhost', '.local', '.internal', '.lan')
RESERVED_HOSTS = {'example.com', 'example.org', 'example.net', 'localhost'}
STAGING_NOTE = 'Lingkungan uji. Alur akun sedang diverifikasi dan belum dibuka untuk umum.'


class ConfigError(ValueError):
    """Konfigurasi tidak dapat dibaca atau bentuknya salah."""


# ---------------------------------------------------------------- konfigurasi
def load_config(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except OSError as exc:
        raise ConfigError(f'Konfigurasi tidak dapat dibaca: {exc}') from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f'Konfigurasi bukan JSON yang sah: {exc}') from exc
    if not isinstance(data, dict):
        raise ConfigError('Konfigurasi harus berupa objek JSON.')
    return data


def gate_entry(config: dict, key: str) -> dict:
    """Bentuk 1.4.0: gates.<key> = {status, evidence, verified_by, date}.
    Bentuk 1.3.0 (boolean datar) tetap dibaca, tetapi `true` tanpa bukti tidak pernah lulus."""
    gates = config.get('gates')
    if isinstance(gates, dict) and isinstance(gates.get(key), dict):
        return gates[key]
    if key in config:
        return {'status': config.get(key), 'evidence': None, 'verified_by': None, 'date': None, '_legacy': True}
    return {'status': False, 'evidence': None, 'verified_by': None, 'date': None}


# ---------------------------------------------------------------- URL
def host_is_reserved(host: str) -> bool:
    host = (host or '').lower().rstrip('.')
    if host in RESERVED_HOSTS or any(host.endswith(t) for t in RESERVED_TLDS):
        return True
    if any(host == h or host.endswith('.' + h) for h in RESERVED_HOSTS):
        return True
    try:
        ipaddress.ip_address(host.strip('[]'))
        return True          # alamat IP bukan domain layanan resmi
    except ValueError:
        return False


def validate_url(value, label: str, required: bool = True, allow_test_hosts: bool = False):
    """Validasi BENTUK saja. Lulus di sini bukan bukti bahwa tujuan resmi, benar, atau dapat dijangkau."""
    if value is None or value == '':
        if required:
            raise ValueError(f'{label} belum diisi. Gunakan URL layanan nyata; jangan gunakan placeholder.')
        return None
    if not isinstance(value, str) or any(c in value for c in '\r\n\t<>"\' \\') or any(ord(c) < 32 for c in value):
        raise ValueError(f'{label} bukan URL yang aman.')
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment:
        raise ValueError(f'{label} harus HTTPS, tanpa kredensial atau fragment.')
    try:
        _ = u.port
    except ValueError:
        raise ValueError(f'{label} memiliki port yang tidak sah.')
    if '.' not in u.hostname and not allow_test_hosts:
        raise ValueError(f'{label} harus memakai nama domain lengkap.')
    if host_is_reserved(u.hostname) and not (allow_test_hosts and u.hostname.endswith('.test')):
        raise ValueError(f'{label} masih menggunakan host contoh, lokal, atau cadangan ({u.hostname}).')
    return value


def url_fingerprint(config: dict) -> str:
    urls = {k: config.get(k) for k in ('site_url', 'registration_url', 'login_url')}
    return hashlib.sha256(json.dumps(urls, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------- hash
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def tree_hash(directory: Path) -> str:
    """Hash deterministik isi sebuah folder (path relatif + isi berkas)."""
    directory = Path(directory)
    h = hashlib.sha256()
    for p in sorted(q for q in directory.rglob('*') if q.is_file()):
        h.update(p.relative_to(directory).as_posix().encode())
        h.update(b'\0')
        h.update(bytes.fromhex(sha256_file(p)))
    return h.hexdigest()


# ---------------------------------------------------------------- penilaian
def _gap(code: str, message: str) -> dict:
    return {'code': code, 'message': message}


def _account_gaps(config: dict, allow_test_hosts: bool) -> list:
    gaps = []
    hosts = config.get('official_hosts')
    if not isinstance(hosts, list) or not all(isinstance(h, str) and h for h in (hosts or [])):
        hosts = []
    official = {h.lower() for h in hosts}
    try:
        reg = validate_url(config.get('registration_url'), 'registration_url', True, allow_test_hosts)
    except ValueError as exc:
        gaps.append(_gap('registration_url', str(exc)))
        reg = None
    needs_login = config.get('account_requires_login')
    if needs_login not in (True, False):
        gaps.append(_gap('account_requires_login', 'account_requires_login belum diputuskan (true/false). Tentukan apakah alur produk memerlukan halaman login terpisah.'))
    try:
        login = validate_url(config.get('login_url'), 'login_url', needs_login is True, allow_test_hosts)
    except ValueError as exc:
        gaps.append(_gap('login_url', str(exc)))
        login = None
    for label, value in (('registration_url', reg), ('login_url', login)):
        if value and urlsplit(value).hostname.lower() not in official:
            gaps.append(_gap('official_hosts', f'Host {label} ({urlsplit(value).hostname}) tidak tercantum dalam official_hosts. Pemilik harus menyatakan host resmi secara eksplisit.'))
    return gaps


def _evidence_gaps(root: Path, config: dict) -> list:
    gaps = []
    base = (Path(root) / EVIDENCE_DIR).resolve()
    for key, label in GATES.items():
        entry = gate_entry(config, key)
        if entry.get('status') is not True:
            gaps.append(_gap(key, f'Belum terpenuhi: {label}.'))
            continue
        evidence = entry.get('evidence')
        if not evidence or not isinstance(evidence, str):
            gaps.append(_gap(key, f'{key} bernilai true tanpa bukti. Isi "evidence" dengan berkas di {EVIDENCE_DIR}/.'))
            continue
        target = (Path(root) / evidence).resolve()
        if base not in target.parents:
            gaps.append(_gap(key, f'Bukti {key} harus berada di dalam {EVIDENCE_DIR}/ (ditemukan: {evidence}).'))
            continue
        if not target.is_file() or target.stat().st_size == 0:
            gaps.append(_gap(key, f'Berkas bukti {key} tidak ada atau kosong: {evidence}.'))
            continue
        if not (isinstance(entry.get('verified_by'), str) and entry['verified_by'].strip()):
            gaps.append(_gap(key, f'{key}: "verified_by" (nama penanggung jawab) belum diisi.'))
        try:
            date.fromisoformat(str(entry.get('date')))
        except ValueError:
            gaps.append(_gap(key, f'{key}: "date" harus berformat YYYY-MM-DD.'))
    return gaps


def _url_check_gaps(root: Path, config: dict) -> list:
    """Bukti keterjangkauan dibuat oleh tools/periksa_url.py dan terikat pada URL yang sedang dikonfigurasi."""
    path = Path(root) / EVIDENCE_DIR / 'url-check.json'
    if not path.is_file():
        return [_gap('url_check', f'Keterjangkauan URL belum diperiksa. Jalankan tools/periksa_url.py (menghasilkan {EVIDENCE_DIR}/url-check.json).')]
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return [_gap('url_check', 'url-check.json tidak dapat dibaca.')]
    if data.get('config_fingerprint') != url_fingerprint(config):
        return [_gap('url_check', 'url-check.json dibuat untuk URL yang berbeda dari konfigurasi saat ini. Jalankan ulang tools/periksa_url.py.')]
    gaps = []
    results = {r.get('key'): r for r in data.get('results', [])}
    for key in ('site_url', 'registration_url', 'login_url'):
        if not config.get(key):
            continue
        r = results.get(key)
        if not r or r.get('ok') is not True:
            gaps.append(_gap('url_check', f'{key} tidak terjangkau atau tidak sesuai saat diperiksa: {(r or {}).get("detail", "tidak ada hasil")}.'))
    return gaps


def frontend_evidence(root: Path) -> dict:
    """FRONTEND_READY hanya sah bila ringkasan QA dibuat dari isi website/ yang sekarang dan tanpa kegagalan."""
    path = Path(root) / 'qa' / 'hasil' / 'ringkasan.json'
    current = tree_hash(Path(root) / 'website')
    if not path.is_file():
        return {'ready': False, 'reason': 'qa/hasil/ringkasan.json belum ada. Jalankan qa/jalankan_semua.py.', 'website_tree_sha256': current}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'ready': False, 'reason': 'ringkasan QA tidak dapat dibaca.', 'website_tree_sha256': current}
    if data.get('website_tree_sha256') != current:
        return {'ready': False, 'reason': 'Ringkasan QA dibuat dari source yang berbeda. Jalankan ulang QA pada source sekarang.', 'website_tree_sha256': current}
    failing = {k: v for k, v in data.get('suites', {}).items() if v.get('FAIL', 0) or v.get('ERROR', 0) or not v.get('PASS', 0)}
    if failing or not data.get('suites'):
        return {'ready': False, 'reason': f'Ada rangkaian QA yang gagal atau kosong: {sorted(failing)}', 'website_tree_sha256': current}
    return {'ready': True, 'reason': 'Semua rangkaian QA lulus pada source saat ini.', 'website_tree_sha256': current, 'suites': data['suites']}


def assess(root: Path, config: dict, profile: str, allow_test_hosts: bool = False) -> dict:
    """Satu-satunya penentu kelayakan sebuah profil. bangun_rilis dan gate_rilis memanggil fungsi ini."""
    if profile not in PROFILES:
        raise ConfigError(f'Profil tidak dikenal: {profile}. Pilih salah satu dari {PROFILES}.')
    gaps = []
    if profile in ('staging', 'production'):
        gaps += _account_gaps(config, allow_test_hosts)
    if profile == 'staging':
        try:
            validate_url(config.get('site_url'), 'site_url', False, allow_test_hosts)
        except ValueError as exc:
            gaps.append(_gap('site_url', str(exc)))
    if profile == 'production':
        try:
            validate_url(config.get('site_url'), 'site_url', True, allow_test_hosts)
        except ValueError as exc:
            gaps.append(_gap('site_url', str(exc)))
        gaps += _url_check_gaps(root, config)
        gaps += _evidence_gaps(root, config)
        fe = frontend_evidence(root)
        if not fe['ready']:
            gaps.append(_gap('frontend_qa', fe['reason']))
    return {'profile': profile, 'eligible': not gaps, 'gaps': gaps}


def scopes(root: Path, config: dict) -> dict:
    """Tiga lingkup kesiapan yang tidak boleh disamakan satu sama lain."""
    fe = frontend_evidence(root)
    account_gaps = _account_gaps(config, False) + _url_check_gaps(root, config)
    account_gaps += [g for g in _evidence_gaps(root, config) if g['code'] in ('account_flow_verified', 'product_claims_verified')]
    live = {'ready': False, 'reason': f'Belum ada {EVIDENCE_DIR}/live-smoke.json dari tools/smoke_live.py terhadap site_url.'}
    smoke = Path(root) / EVIDENCE_DIR / 'live-smoke.json'
    if smoke.is_file():
        try:
            data = json.loads(smoke.read_text(encoding='utf-8'))
            if not config.get('site_url') or data.get('site_url') != config.get('site_url'):
                live['reason'] = 'live-smoke.json bukan untuk site_url yang dikonfigurasi.'
            elif data.get('ok') is not True:
                live['reason'] = 'Smoke test hosting mencatat kegagalan.'
            else:
                live = {'ready': True, 'reason': f'Smoke test lulus pada {data.get("checked_at")}.'}
        except (OSError, json.JSONDecodeError):
            live['reason'] = 'live-smoke.json tidak dapat dibaca.'
    return {
        'FRONTEND_READY': {'ready': fe['ready'], 'reason': fe['reason']},
        'ACCOUNT_PRODUCT_E2E_READY': {'ready': not account_gaps, 'reason': 'Terpenuhi.' if not account_gaps else '; '.join(g['message'] for g in account_gaps)},
        'LIVE_DEPLOYMENT_VERIFIED': live,
    }


# ---------------------------------------------------------------- transformasi HTML
def _tags(pattern_attr: str) -> str:
    return r'<(?P<tag>[a-z0-9]+)\b[^>]*\b' + re.escape(pattern_attr) + r'(?:="[^"]*")?[^>]*>'


def _set_attr(tag: str, name: str, value: str) -> str:
    quoted = html.escape(value, quote=True)
    if re.search(r'\b' + re.escape(name) + r'="[^"]*"', tag):
        return re.sub(r'\b' + re.escape(name) + r'="[^"]*"', lambda m: f'{name}="{quoted}"', tag, count=1)
    return re.sub(r'(/?>)$', lambda m: f' {name}="{quoted}"' + m.group(1), tag, count=1)


def _drop_attr(tag: str, name: str) -> str:
    return re.sub(r'\s+' + re.escape(name) + r'(?:="[^"]*")?', '', tag)


def _add_bool_attr(tag: str, name: str) -> str:
    return re.sub(r'(/?>)$', lambda m: f' {name}=""' + m.group(1), _drop_attr(tag, name), count=1)


def _sub_exact(pattern: str, repl, text: str, expected, label: str, flags=0) -> str:
    """Substitusi yang gagal keras bila jumlah kecocokan tidak sesuai: mencegah perubahan parsial yang diam-diam."""
    new, n = re.subn(pattern, repl, text, flags=flags)
    ok = n in expected if isinstance(expected, (tuple, list, range)) else n == expected
    if not ok:
        raise ConfigError(f'Struktur HTML tidak sesuai untuk "{label}": ditemukan {n} kecocokan.')
    return new


def transform_page(name: str, text: str, config: dict, profile: str) -> str:
    """Mengubah satu halaman sumber (keadaan preview) menjadi keadaan profil. Murni: tanpa I/O."""
    text = _sub_exact(r'<meta\b(?=[^>]*\bname="jp-release-profile")[^>]*>',
                      lambda m: _set_attr(m.group(0), 'content', profile), text, 1, 'penanda profil')
    if profile == 'preview':
        return text
    register = config['registration_url']
    login = config.get('login_url')
    site = (config.get('site_url') or '').rstrip('/')

    if name == 'index.html':
        text = _sub_exact(_tags('data-register-link'), lambda m: _set_attr(m.group(0), 'href', register), text, range(1, 50), 'CTA daftar')
        note = r'(<p\b[^>]*\bdata-access-note(?:="[^"]*")?[^>]*>)(.*?)(</p>)'
        if profile == 'staging':
            text = _sub_exact(note, lambda m: m.group(1) + '\n       ' + STAGING_NOTE + '\n      ' + m.group(3), text, 1, 'catatan akses', re.S)
        else:
            text = _sub_exact(r'\s*' + note, '', text, 1, 'catatan akses', re.S)
            text = _sub_exact(r'<meta\b(?=[^>]*\bname="robots")[^>]*>', '<meta content="index, follow" name="robots"/>', text, 1, 'robots')
    elif name == 'daftar.html':
        text = _sub_exact(_tags('data-registration-closed'), lambda m: _add_bool_attr(m.group(0), 'hidden'), text, 1, 'status tertutup')
        text = _sub_exact(_tags('data-registration-open'), lambda m: _drop_attr(m.group(0), 'hidden'), text, 1, 'status terbuka')
        text = _sub_exact(_tags('data-registration-destination'), lambda m: _set_attr(m.group(0), 'href', register), text, 1, 'tujuan daftar')
        if login:
            text = _sub_exact(_tags('data-login-link'), lambda m: _set_attr(_drop_attr(m.group(0), 'hidden'), 'href', login), text, 1, 'tautan login')
        staging = _tags('data-staging-note')
        if profile == 'staging':
            text = _sub_exact(staging, lambda m: _drop_attr(m.group(0), 'hidden'), text, 1, 'tanda lingkungan uji')

    if profile == 'production':
        og_image = site + '/assets/media/kosmetik-02-896.webp'
        text = _sub_exact(r'<meta\b(?=[^>]*\bproperty="og:image")[^>]*>',
                          lambda m: _set_attr(m.group(0), 'content', og_image), text, 1, 'og:image')
        if name in ('index.html', 'daftar.html'):
            canonical = site + ('/' if name == 'index.html' else '/daftar.html')
            extra = (f'<link href="{html.escape(canonical, quote=True)}" rel="canonical"/>\n  '
                     f'<meta content="{html.escape(canonical, quote=True)}" property="og:url"/>\n ')
            text = _sub_exact(r'</head>', lambda m: ' ' + extra + m.group(0), text, 1, 'canonical')
        if name == 'index.html':
            text = _sub_exact(r'("@type": "WebSite",)', lambda m: m.group(1) + '\n  "url": ' + json.dumps(site + '/') + ',', text, 1, 'JSON-LD url')
        if name == '404.html':
            base_path = urlsplit(site + '/').path or '/'
            text = _sub_exact(r'<base\b[^>]*>', lambda m: _set_attr(m.group(0), 'href', base_path), text, 1, 'base href')
    return text


def extra_files(config: dict, profile: str) -> dict:
    """Berkas tambahan yang hanya sah pada rilis publik."""
    if profile != 'production':
        return {}
    site = config['site_url'].rstrip('/')
    today = date.today().isoformat()
    return {
        'robots.txt': f'User-agent: *\nAllow: /\nDisallow: /daftar.html\n\nSitemap: {site}/sitemap.xml\n',
        'sitemap.xml': ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                        f'  <url><loc>{html.escape(site + "/")}</loc><lastmod>{today}</lastmod></url>\n</urlset>\n'),
    }


def scan_output(directory: Path, config: dict, profile: str, allow_test_hosts: bool = False) -> list:
    """Pemeriksaan akhir atas keluaran yang SUDAH dibangun, sebelum boleh diganti namanya menjadi dist/<profil>."""
    problems = []
    for name in PAGES:
        text = (Path(directory) / name).read_text(encoding='utf-8')
        for host in re.findall(r'https?://([A-Za-z0-9.\-]+)', text):
            if host_is_reserved(host) and not (allow_test_hosts and host.endswith('.test')):
                problems.append(f'{name}: host cadangan/uji bocor ke keluaran ({host}).')
        if f'content="{profile}" name="jp-release-profile"' not in text:
            problems.append(f'{name}: penanda profil tidak sesuai.')
        if profile != 'production' and 'content="noindex, follow" name="robots"' not in text:
            problems.append(f'{name}: keluaran {profile} harus tetap noindex.')
    index = (Path(directory) / 'index.html').read_text(encoding='utf-8')
    hrefs = re.findall(r'<a\b[^>]*\bdata-register-link(?:="[^"]*")?[^>]*>', index)
    expected = 'daftar.html' if profile == 'preview' else config['registration_url']
    if not hrefs or any(f'href="{html.escape(expected, quote=True)}"' not in h for h in hrefs):
        problems.append('index.html: ada CTA daftar yang tidak menuju tujuan profil ini.')
    if profile == 'production' and 'data-access-note' in index:
        problems.append('index.html: catatan akses pratinjau masih ada pada keluaran produksi.')
    if profile != 'production' and 'data-access-note' not in index:
        problems.append('index.html: status akses hilang pada keluaran non-produksi.')
    return problems


# ---------------------------------------------------------------- build atomik
def plan(root: Path, config: dict, profile: str, allow_test_hosts: bool = False) -> dict:
    """Dry-run: menilai kelayakan dan menghitung seluruh keluaran DI MEMORI. Tidak menulis apa pun."""
    root = Path(root)
    verdict = assess(root, config, profile, allow_test_hosts)
    result = {'profile': profile, 'eligible': verdict['eligible'], 'gaps': verdict['gaps'], 'changed': [], 'added': [], 'pages': {}, 'extra': {}}
    if not verdict['eligible']:
        return result
    web = root / 'website'
    for name in PAGES:
        src = (web / name).read_text(encoding='utf-8')
        out = transform_page(name, src, config, profile)
        result['pages'][name] = out
        if out != src:
            result['changed'].append(name)
    result['extra'] = extra_files(config, profile)
    result['added'] = sorted(result['extra'])
    return result


def build(root: Path, config: dict, profile: str, out_dir: Path | None = None, allow_test_hosts: bool = False) -> dict:
    """Bangun dist/<profil>/ secara atomik. Bila ada syarat yang belum terpenuhi: tidak ada berkas yang dibuat/diubah.
    Keluaran sebelumnya disimpan satu generasi sebagai <profil>.prev untuk rollback."""
    root = Path(root)
    p = plan(root, config, profile, allow_test_hosts)
    if not p['eligible']:
        return {**{k: p[k] for k in ('profile', 'eligible', 'gaps')}, 'written': False}
    out_dir = Path(out_dir) if out_dir else root / 'dist' / profile
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f'.{profile}-', dir=out_dir.parent))
    try:
        stage = tmp / 'site'
        shutil.copytree(root / 'website', stage)
        for name, text in p['pages'].items():
            (stage / name).write_text(text, encoding='utf-8')
        for name, text in p['extra'].items():
            (stage / name).write_text(text, encoding='utf-8')
        problems = scan_output(stage, config, profile, allow_test_hosts)
        if problems:
            return {'profile': profile, 'eligible': False, 'written': False, 'gaps': [_gap('output_scan', m) for m in problems]}
        manifest = {
            'version': VERSION, 'profile': profile, 'built_on': date.today().isoformat(),
            'source_tree_sha256': tree_hash(root / 'website'), 'output_tree_sha256': tree_hash(stage),
            'config_fingerprint': url_fingerprint(config),
            'changed_pages': p['changed'], 'added_files': p['added'],
            'files': {q.relative_to(stage).as_posix(): sha256_file(q) for q in sorted(stage.rglob('*')) if q.is_file()},
        }
        prev = out_dir.with_name(out_dir.name + '.prev')
        if out_dir.exists():
            if prev.exists():
                shutil.rmtree(prev)
            out_dir.rename(prev)
            old_manifest = out_dir.with_name(out_dir.name + '.manifest.json')
            if old_manifest.exists():
                old_manifest.replace(out_dir.with_name(out_dir.name + '.prev.manifest.json'))
        stage.rename(out_dir)
        out_dir.with_name(out_dir.name + '.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        return {'profile': profile, 'eligible': True, 'written': True, 'gaps': [], 'out': str(out_dir), 'manifest': manifest}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def rollback(root: Path, profile: str, out_dir: Path | None = None) -> dict:
    """Tukar dist/<profil> dengan generasi sebelumnya. website/ tidak tersentuh."""
    out_dir = Path(out_dir) if out_dir else Path(root) / 'dist' / profile
    prev = out_dir.with_name(out_dir.name + '.prev')
    if not prev.is_dir():
        return {'rolled_back': False, 'reason': f'Tidak ada generasi sebelumnya ({prev.name}).'}
    swap = out_dir.with_name(out_dir.name + '.swap')
    cur_m, prev_m = out_dir.with_name(out_dir.name + '.manifest.json'), out_dir.with_name(out_dir.name + '.prev.manifest.json')
    if out_dir.exists():
        out_dir.rename(swap)
    prev.rename(out_dir)
    if swap.exists():
        swap.rename(prev)
    a = cur_m.read_text(encoding='utf-8') if cur_m.exists() else None
    b = prev_m.read_text(encoding='utf-8') if prev_m.exists() else None
    if b is not None:
        cur_m.write_text(b, encoding='utf-8')
    if a is not None:
        prev_m.write_text(a, encoding='utf-8')
    return {'rolled_back': True, 'active_tree_sha256': tree_hash(out_dir)}
