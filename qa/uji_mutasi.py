#!/usr/bin/env python3
"""Uji mutasi: membuktikan pemeriksaan statis benar-benar bisa GAGAL.

Tiap mutasi diterapkan pada salinan sementara website/, lalu check_static (profil preview) dijalankan.
Lulus = pemeriksaan yang relevan gagal seperti seharusnya.   python3 qa/uji_mutasi.py
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tmp = Path(tempfile.mkdtemp(prefix='jp-mutasi-')); rows = []


def sub(f, a, b):
    def fn(site):
        p = site / f; t = p.read_text(encoding='utf-8'); assert a in t, (f, a); p.write_text(t.replace(a, b, 1), encoding='utf-8')
    return fn


def mutate(name, fn, expect):
    site = tmp / name; shutil.copytree(ROOT / 'website', site); fn(site); out = tmp / (name + '.json')
    subprocess.run([sys.executable, '-B', str(ROOT / 'qa/check_static.py'), '--profile', 'preview', '--site', str(site), '--out', str(out)], capture_output=True, text=True)
    fails = [x['test'] for x in json.loads(out.read_text(encoding='utf-8'))['results'] if x['status'] == 'FAIL']
    ok = any(expect in f for f in fails)
    rows.append({'test': name, 'status': 'PASS' if ok else 'FAIL', 'detail': fails[:6]}); print('PASS' if ok else 'FAIL', name, fails[:2])


try:
    mutate('canon01_diubah', sub('index.html', 'selalu konsisten.', 'lebih konsisten.'), 'Canon 01')
    mutate('canon02_diubah', sub('index.html', 'Cukup satu klik:', 'Cukup beberapa klik:'), 'Canon 02')
    mutate('cta_ke_url_luar_pada_preview', sub('index.html', 'data-register-link="" href="daftar.html"', 'data-register-link="" href="https://akun.contoh.id/daftar"'), '[preview] CTA')
    mutate('status_belum_dibuka_disembunyikan', sub('daftar.html', '<div data-registration-closed="">', '<div data-registration-closed="" hidden="">'), 'Halaman akses jujur')
    mutate('indeks_dibuka_pada_preview', sub('index.html', 'content="noindex, follow"', 'content="index, follow"'), 'tidak diindeks')
    mutate('caption_dihapus', lambda s: (s / 'assets/media/affiliate-02.id.vtt').unlink(), 'Caption Indonesia')
    mutate('autoplay_ditambah', sub('index.html', 'controls="" data-video=""', 'autoplay="" controls="" data-video=""'), 'Kontrol native')
    mutate('script_inline', sub('index.html', '<script src="js/flag.js">', '<script>alert(1)</script><script src="js/flag.js">'), 'Tanpa script inline')
    mutate('form_palsu', sub('daftar.html', '<p class="kicker">', '<form><input type="email"></form><p class="kicker">'), 'form')
    mutate('berkas_internal_ikut_dipublikasikan', lambda s: (s / 'rilis.json').write_text('{}'), 'Folder publik')
    mutate('video_kelima_ditambahkan', lambda s: shutil.copy(s / 'assets/media/affiliate-01.mp4', s / 'assets/media/affiliate-05.mp4'), 'tidak dipakai')
    mutate('css_investor_diubah', lambda s: (s / 'css/styles.css').write_text((s / 'css/styles.css').read_text(encoding='utf-8') + '\n/* x */', encoding='utf-8'), 'CSS dasar investor')
finally:
    shutil.rmtree(tmp, ignore_errors=True)
counts = {k: sum(r['status'] == k for r in rows) for k in ('PASS', 'FAIL', 'ERROR')}
(ROOT / 'qa/hasil/mutation-results.json').write_text(json.dumps({'scope': 'Uji mutasi atas salinan website/. PASS berarti mutasi terdeteksi oleh pemeriksaan statis.', 'counts': counts, 'results': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('MUTASI', counts); sys.exit(0 if not counts['FAIL'] else 1)
