#!/usr/bin/env python3
"""Jalankan seluruh QA pada source saat ini dan tulis qa/hasil/ringkasan.json.

Urutan:
  1. statis      profil preview atas website/
  2. rilis       uji sistem rilis (kasus positif dan negatif) pada salinan sementara
  3. http        server pratinjau lokal atas website/
     mutasi      12 mutasi pada salinan website/ harus terdeteksi oleh pemeriksaan statis
  4. browser     Chromium lewat HTTP atas website/ (profil preview, lengkap)
  5. fixture     build staging dan production dengan host .test di folder sementara → statis + browser (skenario akses)
  6. gate        tools/gate_rilis.py --write

ringkasan.json mengikat hasil pada hash isi website/. tools/rilis_core.py memakai berkas ini sebagai bukti
FRONTEND_READY; bila source berubah sesudahnya, bukti otomatis tidak berlaku.

  python3 qa/jalankan_semua.py [--skip-browser]
"""
import argparse, json, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rilis_core as core  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--skip-browser', action='store_true'); args = ap.parse_args()
OUT = ROOT / 'qa' / 'hasil'; OUT.mkdir(parents=True, exist_ok=True)
PY = [sys.executable, '-B']
suites, log = {}, []


def run(name, cmd, result_file):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    counts = {'PASS': 0, 'FAIL': 0, 'ERROR': 1}
    if result_file.is_file():
        data = json.loads(result_file.read_text(encoding='utf-8'))
        counts = {k: data['counts'].get(k, 0) for k in ('PASS', 'FAIL', 'ERROR')}
    if r.returncode != 0 and not (counts['FAIL'] or counts['ERROR']):
        counts['ERROR'] = 1
    suites[name] = {**counts, 'file': result_file.relative_to(ROOT).as_posix(), 'seconds': round(time.time() - t0, 1), 'command': ' '.join(Path(c).name if c == sys.executable else str(c).replace(str(ROOT) + '/', '') for c in cmd)}
    log.append(f'{name}: {counts}')
    print(f'{name}: {counts}', flush=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-800:])


before = core.tree_hash(ROOT / 'website')
for stale in OUT.glob('*.json'):
    stale.unlink()
run('statis_preview', PY + ['qa/check_static.py', '--profile', 'preview'], OUT / 'static-preview.json')
run('sistem_rilis', PY + ['qa/test_rilis.py'], OUT / 'release-system-results.json')
run('http_lokal', PY + ['qa/http_checks.py'], OUT / 'http-results.json')
run('uji_mutasi', PY + ['qa/uji_mutasi.py'], OUT / 'mutation-results.json')
if not args.skip_browser:
    run('browser_preview', PY + ['qa/browser_checks.py', '--profile', 'preview'], OUT / 'browser-preview.json')

# ---- build fixture: membuktikan aturan profil staging/production. Host .test; folder sementara; tidak masuk paket.
tmp = Path(tempfile.mkdtemp(prefix='jp-fixture-'))
try:
    fx = tmp / 'paket'; fx.mkdir()
    shutil.copytree(ROOT / 'website', fx / 'website')
    ev = fx / core.EVIDENCE_DIR; ev.mkdir(parents=True)
    cfg = {'version': core.VERSION, 'site_url': 'https://www.jagoprompt.test', 'registration_url': 'https://akun.jagoprompt.test/daftar', 'login_url': 'https://akun.jagoprompt.test/masuk',
           'account_requires_login': True, 'official_hosts': ['akun.jagoprompt.test'], 'gates': {}}
    for key in core.GATES:
        (ev / f'{key}.md').write_text('bukti fixture\n', encoding='utf-8')
        cfg['gates'][key] = {'status': True, 'evidence': f'{core.EVIDENCE_DIR}/{key}.md', 'verified_by': 'Fixture QA', 'date': '2026-11-15'}
    (ev / 'url-check.json').write_text(json.dumps({'config_fingerprint': core.url_fingerprint(cfg), 'results': [{'key': k, 'ok': True} for k in ('site_url', 'registration_url', 'login_url')]}), encoding='utf-8')
    (fx / 'qa/hasil').mkdir(parents=True)
    (fx / 'qa/hasil/ringkasan.json').write_text(json.dumps({'website_tree_sha256': core.tree_hash(fx / 'website'), 'suites': {'fixture': {'PASS': 1, 'FAIL': 0}}}), encoding='utf-8')
    cfg_path = tmp / 'rilis.fixture.json'; cfg_path.write_text(json.dumps(cfg), encoding='utf-8')
    for profile in ('staging', 'production'):
        built = core.build(fx, cfg, profile, allow_test_hosts=True)
        if not built.get('written'):
            suites[f'statis_{profile}_fixture'] = {'PASS': 0, 'FAIL': 1, 'ERROR': 0, 'detail': built['gaps']}
            continue
        site = fx / 'dist' / profile
        run(f'statis_{profile}_fixture', PY + ['qa/check_static.py', '--profile', profile, '--site', str(site), '--config', str(cfg_path), '--fixture', '--out', str(OUT / f'static-{profile}-fixture.json')], OUT / f'static-{profile}-fixture.json')
        if not args.skip_browser:
            run(f'browser_{profile}_fixture', PY + ['qa/browser_checks.py', '--profile', profile, '--site', str(site), '--config', str(cfg_path), '--fixture', '--quick', '--out', str(OUT / f'browser-{profile}-fixture.json')], OUT / f'browser-{profile}-fixture.json')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

after = core.tree_hash(ROOT / 'website')
summary = {
    'version': core.VERSION, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'website_tree_sha256': after, 'website_unchanged_during_qa': before == after,
    'tools_sha256': {p.name: core.sha256_file(p) for p in sorted((ROOT / 'tools').glob('*.py'))},
    'note': 'Jumlah per rangkaian berbeda satuan (atribut, skenario, permintaan HTTP) dan tidak dijumlahkan menjadi skor kesiapan. Rangkaian *_fixture memakai host .test dan hanya membuktikan aturan profil.',
    'browser_skipped': args.skip_browser, 'suites': suites}
(OUT / 'ringkasan.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
subprocess.run(PY + ['tools/gate_rilis.py', '--write'], cwd=ROOT)
bad = {k: v for k, v in suites.items() if v['FAIL'] or v['ERROR']}
print('RINGKASAN', 'SEMUA LULUS' if not bad else f'ADA KEGAGALAN: {sorted(bad)}')
sys.exit(0 if not bad and before == after else 1)
