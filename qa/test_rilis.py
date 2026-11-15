#!/usr/bin/env python3
"""Uji sistem rilis: konfigurasi, build per profil, gate, bukti, rollback, dan kasus negatif.

Semua pengujian berjalan pada SALINAN paket di folder sementara. Host fixture memakai TLD cadangan `.test`
(RFC 6761) yang hanya diterima bila kode uji meneruskan allow_test_hosts=True; jalur CLI tidak punya opsi itu,
sehingga fixture tidak dapat bocor menjadi domain produksi. Tidak ada jaringan luar yang dihubungi.

  python3 qa/test_rilis.py            → qa/hasil/release-system-results.json
"""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))
import rilis_core as core  # noqa: E402
import gate_rilis  # noqa: E402
import periksa_url  # noqa: E402
import smoke_live  # noqa: E402
import pratinjau_lokal  # noqa: E402

REG, LOGIN, SITE = 'https://akun.jagoprompt.test/daftar', 'https://akun.jagoprompt.test/masuk', 'https://www.jagoprompt.test'
EMPTY_GATES = {k: {'status': False, 'evidence': None, 'verified_by': None, 'date': None} for k in core.GATES}


def soup(path):
    return BeautifulSoup(Path(path).read_text(encoding='utf-8'), 'html.parser')


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='jp-rilis-'))
        self.root = self.tmp / 'paket'
        self.root.mkdir()
        shutil.copytree(ROOT / 'website', self.root / 'website')
        shutil.copytree(ROOT / 'tools', self.root / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
        (self.root / 'konfigurasi').mkdir()
        self.web_hash = core.tree_hash(self.root / 'website')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- pembantu
    def cfg(self, **over):
        c = {'version': core.VERSION, 'site_url': None, 'registration_url': None, 'login_url': None,
             'account_requires_login': None, 'official_hosts': [], 'gates': copy.deepcopy(EMPTY_GATES)}
        c.update(over)
        return c

    def staging_cfg(self, **over):
        base = dict(registration_url=REG, login_url=LOGIN, account_requires_login=True, official_hosts=['akun.jagoprompt.test'])
        base.update(over)
        return self.cfg(**base)

    def full_cfg(self):
        """Fixture 'semua terpenuhi': menulis berkas bukti nyata di salinan sementara."""
        c = self.staging_cfg(site_url=SITE)
        ev = self.root / core.EVIDENCE_DIR
        ev.mkdir(parents=True, exist_ok=True)
        for key in core.GATES:
            (ev / f'{key}.md').write_text(f'Bukti fixture untuk {key}\n', encoding='utf-8')
            c['gates'][key] = {'status': True, 'evidence': f'{core.EVIDENCE_DIR}/{key}.md', 'verified_by': 'Penguji Fixture', 'date': '2026-11-15'}
        self.write_url_check(c)
        self.write_qa_summary()
        return c

    def write_url_check(self, c, ok=True, fingerprint=None):
        ev = self.root / core.EVIDENCE_DIR
        ev.mkdir(parents=True, exist_ok=True)
        rows = [{'key': k, 'url': c[k], 'ok': ok, 'detail': 'terjangkau' if ok else 'status HTTP 503'} for k in ('site_url', 'registration_url', 'login_url') if c.get(k)]
        (ev / 'url-check.json').write_text(json.dumps({'config_fingerprint': fingerprint or core.url_fingerprint(c), 'results': rows}), encoding='utf-8')

    def write_qa_summary(self, tree=None, fail=0):
        out = self.root / 'qa' / 'hasil'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'ringkasan.json').write_text(json.dumps({'website_tree_sha256': tree or core.tree_hash(self.root / 'website'),
                                                        'suites': {'static': {'PASS': 10, 'FAIL': fail}}}), encoding='utf-8')

    def assert_untouched(self):
        self.assertEqual(core.tree_hash(self.root / 'website'), self.web_hash, 'website/ berubah')

    def assert_no_output(self, profile):
        self.assertFalse((self.root / 'dist' / profile).exists(), f'dist/{profile} tidak boleh ada')
        leftovers = [p.name for p in (self.root / 'dist').glob('.*')] if (self.root / 'dist').exists() else []
        self.assertEqual(leftovers, [], 'folder sementara tertinggal')

    def codes(self, result):
        return {g['code'] for g in result['gaps']}


class Preview(Case):
    def test_preview_selalu_layak_dan_identik_dengan_source(self):
        r = core.build(self.root, self.cfg(), 'preview')
        self.assertTrue(r['written'])
        self.assertEqual(core.tree_hash(self.root / 'dist' / 'preview'), self.web_hash)
        self.assert_untouched()

    def test_source_adalah_keadaan_preview_yang_jujur(self):
        s, d = soup(self.root / 'website/index.html'), soup(self.root / 'website/daftar.html')
        self.assertTrue(all(a['href'] == 'daftar.html' for a in s.select('[data-register-link]')))
        self.assertIn('Akses akun segera hadir', s.select_one('[data-access-note]').get_text())
        self.assertFalse(d.select_one('[data-registration-closed]').has_attr('hidden'))
        self.assertTrue(d.select_one('[data-registration-open]').has_attr('hidden'))
        self.assertEqual(s.find('meta', attrs={'name': 'robots'})['content'], 'noindex, follow')


class DryRun(Case):
    def test_dry_run_tidak_menulis_apa_pun_untuk_semua_profil(self):
        c = self.full_cfg()
        before = core.tree_hash(self.root)
        for profile in core.PROFILES:
            p = core.plan(self.root, c, profile, allow_test_hosts=True)
            self.assertTrue(p['eligible'], (profile, p['gaps']))
        self.assertEqual(core.tree_hash(self.root), before)
        self.assertFalse((self.root / 'dist').exists())

    def test_cli_dry_run_tidak_menulis(self):
        (self.root / 'konfigurasi/rilis.json').write_text(json.dumps(self.cfg()), encoding='utf-8')
        before = core.tree_hash(self.root)
        for profile, code in (('preview', 0), ('staging', 2), ('production', 2)):
            r = subprocess.run([sys.executable, '-B', str(self.root / 'tools/bangun_rilis.py'), '--profile', profile, '--root', str(self.root), '--config', str(self.root / 'konfigurasi/rilis.json')], capture_output=True, text=True)
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        self.assertEqual(core.tree_hash(self.root), before)


class Staging(Case):
    def test_konfigurasi_kosong_ditolak_tanpa_keluaran(self):
        r = core.build(self.root, self.cfg(), 'staging')
        self.assertFalse(r['written'])
        self.assertEqual(self.codes(r), {'registration_url', 'account_requires_login'})
        self.assert_no_output('staging')
        self.assert_untouched()

    def test_staging_mengarahkan_cta_tetapi_tetap_bertanda_uji_dan_noindex(self):
        r = core.build(self.root, self.staging_cfg(), 'staging', allow_test_hosts=True)
        self.assertTrue(r['written'], r['gaps'])
        out = self.root / 'dist' / 'staging'
        s, d = soup(out / 'index.html'), soup(out / 'daftar.html')
        self.assertTrue(all(a['href'] == REG for a in s.select('[data-register-link]')))
        self.assertEqual(len(s.select('[data-register-link]')), len(soup(self.root / 'website/index.html').select('[data-register-link]')))
        self.assertIn('Lingkungan uji', s.select_one('[data-access-note]').get_text())
        self.assertTrue(d.select_one('[data-registration-closed]').has_attr('hidden'))
        self.assertFalse(d.select_one('[data-registration-open]').has_attr('hidden'))
        self.assertFalse(d.select_one('[data-staging-note]').has_attr('hidden'))
        self.assertEqual(d.select_one('[data-registration-destination]')['href'], REG)
        self.assertEqual(d.select_one('[data-login-link]')['href'], LOGIN)
        self.assertFalse(d.select_one('[data-login-link]').has_attr('hidden'))
        for page in core.PAGES:
            p = soup(out / page)
            self.assertEqual(p.find('meta', attrs={'name': 'robots'})['content'], 'noindex, follow', page)
            self.assertEqual(p.find('meta', attrs={'name': 'jp-release-profile'})['content'], 'staging', page)
            self.assertIsNone(p.select_one('link[rel=canonical]'), page)
        self.assertFalse((out / 'robots.txt').exists())
        self.assert_untouched()

    def test_login_tidak_wajib_bila_alur_tidak_memerlukannya(self):
        c = self.staging_cfg(login_url=None, account_requires_login=False)
        r = core.build(self.root, c, 'staging', allow_test_hosts=True)
        self.assertTrue(r['written'], r['gaps'])
        self.assertTrue(soup(self.root / 'dist/staging/daftar.html').select_one('[data-login-link]').has_attr('hidden'))

    def test_login_wajib_bila_alur_memerlukannya(self):
        r = core.build(self.root, self.staging_cfg(login_url=None), 'staging', allow_test_hosts=True)
        self.assertIn('login_url', self.codes(r))
        self.assert_no_output('staging')

    def test_host_di_luar_official_hosts_ditolak(self):
        r = core.build(self.root, self.staging_cfg(official_hosts=['lain.jagoprompt.test']), 'staging', allow_test_hosts=True)
        self.assertIn('official_hosts', self.codes(r))
        self.assert_no_output('staging')

    def test_build_berulang_menghasilkan_keluaran_identik(self):
        c = self.staging_cfg()
        a = core.build(self.root, c, 'staging', allow_test_hosts=True)['manifest']['output_tree_sha256']
        b = core.build(self.root, c, 'staging', allow_test_hosts=True)['manifest']['output_tree_sha256']
        third = core.build(self.root, c, 'staging', allow_test_hosts=True)['manifest']['output_tree_sha256']
        self.assertEqual(a, b)
        self.assertEqual(b, third)
        self.assertEqual(core.tree_hash(self.root / 'dist/staging'), a)
        self.assert_untouched()

    def test_perubahan_konfigurasi_berulang_dan_rollback(self):
        c1 = self.staging_cfg()
        h1 = core.build(self.root, c1, 'staging', allow_test_hosts=True)['manifest']['output_tree_sha256']
        c2 = self.staging_cfg(registration_url='https://akun.jagoprompt.test/daftar-baru')
        h2 = core.build(self.root, c2, 'staging', allow_test_hosts=True)['manifest']['output_tree_sha256']
        self.assertNotEqual(h1, h2)
        self.assertEqual(core.tree_hash(self.root / 'dist/staging.prev'), h1)
        r = core.rollback(self.root, 'staging')
        self.assertTrue(r['rolled_back'])
        self.assertEqual(core.tree_hash(self.root / 'dist/staging'), h1)
        self.assertEqual(json.loads((self.root / 'dist/staging.manifest.json').read_text())['output_tree_sha256'], h1)
        self.assertEqual(core.tree_hash(self.root / 'dist/staging.prev'), h2)
        self.assert_untouched()

    def test_rollback_tanpa_generasi_sebelumnya_dilaporkan(self):
        core.build(self.root, self.staging_cfg(), 'staging', allow_test_hosts=True)
        self.assertFalse(core.rollback(self.root, 'staging')['rolled_back'])


class ProductionNegatif(Case):
    def test_url_saja_tidak_membuka_produksi(self):
        c = self.staging_cfg(site_url=SITE)
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertFalse(r['written'])
        self.assertTrue(set(core.GATES) <= self.codes(r))
        self.assertIn('url_check', self.codes(r))
        self.assertIn('frontend_qa', self.codes(r))
        self.assert_no_output('production')
        self.assert_untouched()

    def test_setiap_gerbang_yang_belum_terpenuhi_menolak_aktivasi(self):
        for missing in core.GATES:
            with self.subTest(gerbang=missing):
                c = self.full_cfg()
                c['gates'][missing] = {'status': False, 'evidence': None, 'verified_by': None, 'date': None}
                r = core.build(self.root, c, 'production', allow_test_hosts=True)
                self.assertFalse(r['written'])
                self.assertEqual(self.codes(r), {missing})
                self.assert_no_output('production')

    def test_true_tanpa_bukti_ditolak(self):
        for missing in core.GATES:
            with self.subTest(gerbang=missing):
                c = self.full_cfg()
                c['gates'][missing] = {'status': True, 'evidence': None, 'verified_by': 'X', 'date': '2026-11-15'}
                r = core.build(self.root, c, 'production', allow_test_hosts=True)
                self.assertEqual(self.codes(r), {missing})
                self.assertIn('tanpa bukti', r['gaps'][0]['message'])

    def test_boolean_datar_gaya_1_3_0_tidak_cukup(self):
        c = self.full_cfg()
        del c['gates']
        for key in core.GATES:
            c[key] = True
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertEqual(self.codes(r), set(core.GATES))
        self.assert_no_output('production')

    def test_bukti_kosong_hilang_atau_di_luar_folder_ditolak(self):
        c = self.full_cfg()
        (self.root / core.EVIDENCE_DIR / 'audio_review_completed.md').write_text('', encoding='utf-8')
        c['gates']['media_publication_approved']['evidence'] = core.EVIDENCE_DIR + '/tidak-ada.md'
        c['gates']['public_release_approved']['evidence'] = 'website/index.html'
        c['gates']['account_flow_verified']['evidence'] = core.EVIDENCE_DIR + '/../../website/index.html'
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertEqual(self.codes(r), {'audio_review_completed', 'media_publication_approved', 'public_release_approved', 'account_flow_verified'})

    def test_penanggung_jawab_dan_tanggal_wajib(self):
        c = self.full_cfg()
        c['gates']['product_claims_verified']['verified_by'] = ' '
        c['gates']['public_release_approved']['date'] = '15/11/2026'
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertEqual(self.codes(r), {'product_claims_verified', 'public_release_approved'})

    def test_bukti_keterjangkauan_url_wajib_segar_dan_lulus(self):
        c = self.full_cfg()
        (self.root / core.EVIDENCE_DIR / 'url-check.json').unlink()
        self.assertEqual(self.codes(core.build(self.root, c, 'production', allow_test_hosts=True)), {'url_check'})
        self.write_url_check(c, fingerprint='0' * 64)
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertEqual(self.codes(r), {'url_check'})
        self.assertIn('URL yang berbeda', r['gaps'][0]['message'])
        self.write_url_check(c, ok=False)
        self.assertEqual(self.codes(core.build(self.root, c, 'production', allow_test_hosts=True)), {'url_check'})
        self.assert_no_output('production')

    def test_mengganti_url_sesudah_diperiksa_membatalkan_bukti(self):
        c = self.full_cfg()
        c['registration_url'] = 'https://akun.jagoprompt.test/lain'
        self.assertEqual(self.codes(core.build(self.root, c, 'production', allow_test_hosts=True)), {'url_check'})

    def test_qa_frontend_harus_dari_source_saat_ini_dan_tanpa_gagal(self):
        c = self.full_cfg()
        self.write_qa_summary(tree='f' * 64)
        self.assertEqual(self.codes(core.build(self.root, c, 'production', allow_test_hosts=True)), {'frontend_qa'})
        self.write_qa_summary(fail=1)
        self.assertEqual(self.codes(core.build(self.root, c, 'production', allow_test_hosts=True)), {'frontend_qa'})
        (self.root / 'qa/hasil/ringkasan.json').unlink()
        self.assertEqual(self.codes(core.build(self.root, c, 'production', allow_test_hosts=True)), {'frontend_qa'})

    def test_fixture_tidak_dapat_dipakai_lewat_jalur_cli(self):
        c = self.full_cfg()
        (self.root / 'konfigurasi/rilis.json').write_text(json.dumps(c), encoding='utf-8')
        for profile in ('staging', 'production'):
            r = subprocess.run([sys.executable, '-B', str(self.root / 'tools/bangun_rilis.py'), '--profile', profile, '--apply', '--root', str(self.root), '--config', str(self.root / 'konfigurasi/rilis.json')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn('host contoh, lokal, atau cadangan', r.stdout)
            self.assert_no_output(profile)

    def test_url_tidak_aman_atau_contoh_ditolak(self):
        bad = ['javascript:alert(1)', 'http://jagoprompt.id/daftar', 'https://example.com/register', 'https://user:pass@jagoprompt.id/',
               'https://jago.invalid/register', 'https://jagoprompt.id/\nregister', 'https://jagoprompt.id/daftar#form', 'https://localhost/daftar',
               'https://127.0.0.1/daftar', 'https://akun.jagoprompt.test/daftar', 'https://sub.example.org/x', 'https://intranet/daftar',
               'https://jagoprompt.id/a b', '//jagoprompt.id/daftar', 'https://jagoprompt.id:99999/', 123, ['https://jagoprompt.id']]
        for value in bad:
            with self.subTest(url=value):
                with self.assertRaises(ValueError):
                    core.validate_url(value, 'uji')
        self.assertEqual(core.validate_url('https://akun.jagoprompt.id/daftar?ref=beranda', 'uji'), 'https://akun.jagoprompt.id/daftar?ref=beranda')


class ProductionPositif(Case):
    def test_semua_gerbang_berbukti_menghasilkan_keluaran_produksi(self):
        c = self.full_cfg()
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertTrue(r['written'], r['gaps'])
        out = self.root / 'dist' / 'production'
        s, d, e = soup(out / 'index.html'), soup(out / 'daftar.html'), soup(out / '404.html')
        self.assertTrue(all(a['href'] == REG for a in s.select('[data-register-link]')))
        self.assertIsNone(s.select_one('[data-access-note]'))
        self.assertNotIn('segera hadir', s.get_text().lower())
        self.assertEqual(s.find('meta', attrs={'name': 'robots'})['content'], 'index, follow')
        self.assertEqual(d.find('meta', attrs={'name': 'robots'})['content'], 'noindex, follow')
        self.assertEqual(e.find('meta', attrs={'name': 'robots'})['content'], 'noindex, follow')
        self.assertEqual(s.select_one('link[rel=canonical]')['href'], SITE + '/')
        self.assertEqual(d.select_one('link[rel=canonical]')['href'], SITE + '/daftar.html')
        self.assertIsNone(e.select_one('link[rel=canonical]'))
        self.assertEqual(s.find('meta', attrs={'property': 'og:url'})['content'], SITE + '/')
        self.assertEqual(s.find('meta', attrs={'property': 'og:image'})['content'], SITE + '/assets/media/kosmetik-02-896.webp')
        self.assertEqual(json.loads(s.find('script', type='application/ld+json').string)['url'], SITE + '/')
        self.assertTrue(d.select_one('[data-registration-closed]').has_attr('hidden'))
        self.assertFalse(d.select_one('[data-registration-open]').has_attr('hidden'))
        self.assertTrue(d.select_one('[data-staging-note]').has_attr('hidden'))
        self.assertIn('Sitemap: ' + SITE + '/sitemap.xml', (out / 'robots.txt').read_text())
        self.assertIn('<loc>' + SITE + '/</loc>', (out / 'sitemap.xml').read_text())
        for page in core.PAGES:
            self.assertEqual(soup(out / page).find('meta', attrs={'name': 'jp-release-profile'})['content'], 'production')
        # selain 3 halaman + 2 berkas baru, semua berkas identik dengan source
        m = r['manifest']
        same = [k for k, v in m['files'].items() if (self.root / 'website' / k).is_file() and core.sha256_file(self.root / 'website' / k) == v]
        self.assertEqual(len(m['files']) - len(same), 5)
        self.assert_untouched()

    def test_site_url_dengan_subfolder_mengatur_base_404(self):
        c = self.full_cfg()
        c['site_url'] = SITE + '/promo'
        self.write_url_check(c)
        r = core.build(self.root, c, 'production', allow_test_hosts=True)
        self.assertTrue(r['written'], r['gaps'])
        self.assertEqual(soup(self.root / 'dist/production/404.html').find('base')['href'], '/promo/')

    def test_host_fixture_bocor_terdeteksi_pada_keluaran(self):
        c = self.full_cfg()
        stage = self.tmp / 'scan'
        shutil.copytree(self.root / 'website', stage)
        for name in core.PAGES:
            (stage / name).write_text(core.transform_page(name, (stage / name).read_text(encoding='utf-8'), c, 'production'), encoding='utf-8')
        problems = core.scan_output(stage, c, 'production', allow_test_hosts=False)
        self.assertTrue(any('bocor' in p for p in problems), problems)
        self.assertEqual(core.scan_output(stage, c, 'production', allow_test_hosts=True), [])


class Konsistensi(Case):
    def test_gate_dan_build_selalu_sepakat(self):
        full = self.full_cfg()
        variants = [self.cfg(), self.staging_cfg(), self.staging_cfg(site_url=SITE), full]
        broken = copy.deepcopy(full)
        broken['gates']['audio_review_completed']['status'] = False
        variants.append(broken)
        for c in variants:
            rep = gate_rilis.report(self.root, c, allow_test_hosts=True)
            for profile in core.PROFILES:
                self.assertEqual(rep['profiles'][profile]['eligible'], core.plan(self.root, c, profile, allow_test_hosts=True)['eligible'], profile)
            self.assertEqual(rep['status'] == 'READY_FOR_PUBLIC_RELEASE', rep['profiles']['production']['eligible'])

    def test_tiga_lingkup_dilaporkan_terpisah(self):
        self.write_qa_summary()
        s = core.scopes(self.root, self.cfg())
        self.assertTrue(s['FRONTEND_READY']['ready'])
        self.assertFalse(s['ACCOUNT_PRODUCT_E2E_READY']['ready'])
        self.assertFalse(s['LIVE_DEPLOYMENT_VERIFIED']['ready'])
        c = self.full_cfg()
        self.assertTrue(core.scopes(self.root, c)['ACCOUNT_PRODUCT_E2E_READY']['ready'] is False)  # tanpa allow_test_hosts, host .test tidak sah
        (self.root / core.EVIDENCE_DIR / 'live-smoke.json').write_text(json.dumps({'site_url': 'https://lain.jagoprompt.test', 'ok': True}), encoding='utf-8')
        self.assertFalse(core.scopes(self.root, c)['LIVE_DEPLOYMENT_VERIFIED']['ready'])
        (self.root / core.EVIDENCE_DIR / 'live-smoke.json').write_text(json.dumps({'site_url': SITE, 'ok': False}), encoding='utf-8')
        self.assertFalse(core.scopes(self.root, c)['LIVE_DEPLOYMENT_VERIFIED']['ready'])
        (self.root / core.EVIDENCE_DIR / 'live-smoke.json').write_text(json.dumps({'site_url': SITE, 'ok': True, 'checked_at': 'x'}), encoding='utf-8')
        self.assertTrue(core.scopes(self.root, c)['LIVE_DEPLOYMENT_VERIFIED']['ready'])

    def test_struktur_html_rusak_gagal_utuh_tanpa_keluaran_parsial(self):
        p = self.root / 'website/index.html'
        p.write_text(p.read_text(encoding='utf-8').replace('data-access-note=""', ''), encoding='utf-8')
        with self.assertRaises(core.ConfigError):
            core.build(self.root, self.staging_cfg(), 'staging', allow_test_hosts=True)
        self.assert_no_output('staging')

    def test_konfigurasi_rusak_dilaporkan_spesifik(self):
        cfg = self.root / 'konfigurasi/rilis.json'
        cfg.write_text('{ bukan json', encoding='utf-8')
        r = subprocess.run([sys.executable, '-B', str(self.root / 'tools/bangun_rilis.py'), '--profile', 'preview', '--apply', '--root', str(self.root), '--config', str(cfg)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn('KONFIGURASI TIDAK SAH', r.stdout)
        self.assertFalse((self.root / 'dist').exists())

    def test_nama_lama_aktifkan_rilis_tidak_lagi_mengubah_website(self):
        (self.root / 'konfigurasi/rilis.json').write_text(json.dumps(self.cfg(registration_url='https://akun.jagoprompt.id/daftar', official_hosts=['akun.jagoprompt.id'], account_requires_login=False, site_url='https://jagoprompt.id')), encoding='utf-8')
        r = subprocess.run([sys.executable, '-B', str(self.root / 'tools/aktifkan_rilis.py'), '--apply', '--root', str(self.root), '--config', str(self.root / 'konfigurasi/rilis.json')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assert_untouched()
        self.assert_no_output('production')


class PeriksaUrl(Case):
    def run_check(self, fetcher, **over):
        c = self.staging_cfg(site_url=SITE, **over)
        return periksa_url.check(c, fetcher=fetcher, allow_test_hosts=True)

    def test_semua_terjangkau(self):
        r = self.run_check(lambda u: {'status': 200, 'final_url': u, 'content_type': 'text/html; charset=utf-8'})
        self.assertTrue(r['ok'])
        self.assertEqual(len(r['results']), 3)

    def test_status_galat_redirect_asing_dan_bukan_html_ditolak(self):
        self.assertFalse(self.run_check(lambda u: {'status': 503, 'final_url': u, 'content_type': 'text/html'})['ok'])
        self.assertFalse(self.run_check(lambda u: {'status': 200, 'final_url': 'https://pihak-lain.jagoprompt.test/x', 'content_type': 'text/html'})['ok'])
        self.assertFalse(self.run_check(lambda u: {'status': 200, 'final_url': u.replace('https', 'http'), 'content_type': 'text/html'})['ok'])
        self.assertFalse(self.run_check(lambda u: {'status': 200, 'final_url': u, 'content_type': 'application/json'})['ok'])

        def boom(u):
            raise OSError('DNS gagal')
        r = self.run_check(boom)
        self.assertFalse(r['ok'])
        self.assertIn('DNS gagal', r['results'][0]['detail'])

    def test_tanpa_url_tidak_pernah_lulus(self):
        r = periksa_url.check(self.cfg(), fetcher=lambda u: {'status': 200, 'final_url': u, 'content_type': 'text/html'})
        self.assertFalse(r['ok'])

    def test_jalur_nyata_menolak_host_fixture_tanpa_menghubungi_jaringan(self):
        called = []
        r = periksa_url.check(self.staging_cfg(site_url=SITE), fetcher=lambda u: called.append(u))
        self.assertFalse(r['ok'])
        self.assertEqual(called, [])


class SmokeLokal(Case):
    """Menguji skrip smoke test terhadap server pratinjau lokal. BUKAN bukti deployment."""

    def serve(self, directory):
        srv = pratinjau_lokal.make_server(str(directory), 0, security_headers=True)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        return f'http://127.0.0.1:{srv.server_address[1]}'

    def test_keluaran_utuh_lulus_dan_berkas_yang_diubah_terdeteksi(self):
        m = core.build(self.root, self.cfg(), 'preview')['manifest']
        base = self.serve(self.root / 'dist/preview')
        r = smoke_live.run(base, m, 'preview')
        self.assertTrue(r['ok'], [x for x in r['results'] if x['status'] != 'PASS'])
        css = self.root / 'dist/preview/css/sales.css'
        css.write_text(css.read_text(encoding='utf-8') + '\n/* berubah di server */', encoding='utf-8')
        r2 = smoke_live.run(base, m, 'preview')
        self.assertFalse(r2['ok'])
        self.assertEqual([x['test'] for x in r2['results'] if x['status'] == 'FAIL'], ['GET css/sales.css'])

    def test_profil_yang_salah_terdeteksi(self):
        m = core.build(self.root, self.cfg(), 'preview')['manifest']
        base = self.serve(self.root / 'dist/preview')
        r = smoke_live.run(base, m, 'production')
        failed = {x['test'] for x in r['results'] if x['status'] == 'FAIL'}
        self.assertIn('Produksi: beranda boleh diindeks', failed)
        self.assertIn('Penanda profil = production', failed)

    def test_url_lokal_tidak_pernah_menjadi_bukti_rilis(self):
        core.build(self.root, self.cfg(), 'preview')
        base = self.serve(self.root / 'dist/preview')
        r = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/smoke_live.py'), '--profile', 'preview', '--url', base], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('URL lokal ditolak', r.stdout)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    rows = []

    class Recorder(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test); rows.append({'test': test.id().split('.', 1)[1], 'status': 'PASS', 'detail': (test.shortDescription() or '')})

        def addFailure(self, test, err):
            super().addFailure(test, err); rows.append({'test': test.id().split('.', 1)[1], 'status': 'FAIL', 'detail': self._exc_info_to_string(err, test)[-1200:]})

        def addError(self, test, err):
            super().addError(test, err); rows.append({'test': test.id().split('.', 1)[1], 'status': 'ERROR', 'detail': self._exc_info_to_string(err, test)[-1200:]})

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                rows.append({'test': str(subtest), 'status': 'FAIL', 'detail': self._exc_info_to_string(err, test)[-1200:]})

    result = unittest.TextTestRunner(resultclass=Recorder, verbosity=1).run(suite)
    counts = {k: sum(r['status'] == k for r in rows) for k in ('PASS', 'FAIL', 'ERROR')}
    out = ROOT / 'qa' / 'hasil'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'release-system-results.json').write_text(json.dumps({
        'scope': 'Sistem rilis pada salinan sementara dengan host fixture .test; tanpa jaringan luar. Bukan bukti layanan akun atau deployment.',
        'tools_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / 'tools').glob('*.py'))},
        'counts': counts, 'results': rows}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('RILIS', counts)
    sys.exit(0 if result.wasSuccessful() else 1)
