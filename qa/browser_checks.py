#!/usr/bin/env python3
"""Uji browser atas BERKAS DISTRIBUSI melalui HTTP (bukan dokumen dengan aset ditanamkan).

Skrip menyalakan pratinjau_lokal.py pada port acak untuk folder yang diuji, dengan header keamanan aktif,
lalu Chromium (Playwright) benar-benar bernavigasi ke URL itu. Semua aset dimuat lewat jaringan loopback.

  python3 qa/browser_checks.py --profile preview                       → website/
  python3 qa/browser_checks.py --profile staging --site <folder> --config <rilis.json> --fixture

Batas: satu mesin (Chromium desktop headless). Ukuran ponsel/tablet adalah EMULASI viewport. Bukan Safari/iOS,
bukan Android fisik, bukan Firefox, bukan pembaca layar, bukan hosting produksi.
"""
import argparse
import json
import sys
import threading
import time
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))
import rilis_core as core  # noqa: E402
import pratinjau_lokal  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--profile', required=True, choices=core.PROFILES)
ap.add_argument('--site')
ap.add_argument('--config', default=str(ROOT / 'konfigurasi' / 'rilis.json'))
ap.add_argument('--fixture', action='store_true')
ap.add_argument('--quick', action='store_true', help='Hanya skenario status akses (dipakai untuk build fixture staging/production).')
ap.add_argument('--out')
ap.add_argument('--shots')
args = ap.parse_args()
PROFILE = args.profile
SITE = Path(args.site) if args.site else (ROOT / 'website' if PROFILE == 'preview' else ROOT / 'dist' / PROFILE)
CONFIG = core.load_config(Path(args.config))
SHOTS = Path(args.shots) if args.shots else ROOT / 'qa' / 'screenshot'
SHOTS.mkdir(parents=True, exist_ok=True)
TAG = PROFILE + ('-fixture' if args.fixture else '')

server = pratinjau_lokal.make_server(str(SITE), 0, security_headers=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{server.server_address[1]}/'

VIEWPORTS = [(1440, 900), (1280, 800), (1024, 768), (768, 1024), (390, 844), (360, 800), (320, 568), (844, 390)]
results, measure = [], {}
SECTIONS = ['beranda', 'hasil-video', 'ide', 'fitur', 'arahan-foto', 'arahan-video', 'pemula', 'cerita', 'mulai']


def test(name, criteria=''):
    def deco(fn):
        t0 = time.time()
        try:
            detail = fn()
            status = 'PASS'
        except AssertionError as e:
            detail, status = str(e)[:1500], 'FAIL'
        except Exception as e:
            detail, status = ''.join(traceback.format_exception_only(type(e), e)).strip()[:900], 'ERROR'
        results.append({'test': name, 'criteria': criteria, 'status': status, 'detail': detail, 'seconds': round(time.time() - t0, 1)})
        print(status, '-', name, flush=True)
        return fn
    return deco


JS_OVERFLOW = """() => {
  const de = document.documentElement, iw = de.clientWidth, outside = [], clipped = [];
  const menuClosed = el => el.closest('.nav-list') && !el.closest('.nav-list.is-open') && matchMedia('(max-width: 960px)').matches && de.classList.contains('js');
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.position === 'fixed' || menuClosed(el)) continue;
    if (el.closest('details:not([open])') && el.tagName !== 'SUMMARY' && !el.matches('details')) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (r.right > iw + 1 || r.left < -1) outside.push((el.className || el.tagName) + ' ' + Math.round(r.left) + '..' + Math.round(r.right));
  }
  for (const el of document.querySelectorAll('h1,h2,h3,p,a,button,summary,figcaption,li,span,b')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || !el.clientWidth) continue;
    if ((cs.overflowX === 'hidden' || cs.overflow === 'hidden') && el.scrollWidth > el.clientWidth + 1) clipped.push(el.className || el.tagName);
  }
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, outside: outside.slice(0, 8), clipped: clipped.slice(0, 8)};
}"""

JS_HERO = """() => {
  const q = s => document.querySelector(s), top = s => Math.round(q(s).getBoundingClientRect().top);
  const img = q('.hero-shot-main img'), r = img.getBoundingClientRect(), vh = innerHeight;
  const visible = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
  const area = s => { const b = q(s).getBoundingClientRect(); return Math.round(b.width * b.height); };
  return {title: top('.hero-title'), lead: top('.hero-lead'), results: top('.hero-results'), actions: top('.hero-actions'), summary: top('.benefit-summary'),
    imageTop: Math.round(r.top), imageH: Math.round(r.height), visibleFraction: +(visible / r.height).toFixed(2),
    mosaicArea: area('.hero-mosaic'), summaryArea: area('.benefit-summary'), currentSrc: img.currentSrc.split('/').pop(), loaded: img.complete && img.naturalWidth > 0,
    h1Px: parseFloat(getComputedStyle(q('.hero-title')).fontSize), leadPx: parseFloat(getComputedStyle(q('.hero-lead')).fontSize), h1: q('h1').innerText.replace(/\\s+/g, ' ').trim()};
}"""

JS_SETTLED = "() => new Promise(r => { let last = scrollY, n = 0; const i = setInterval(() => { if (scrollY === last) { if (++n > 4) { clearInterval(i); r(true); } } else { n = 0; last = scrollY; } }, 80); })"
INIT = "window.__csp = []; document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + (e.blockedURI || 'inline')));"


def new_page(browser, w, h, **ctx):
    context = browser.new_context(viewport={'width': w, 'height': h}, **ctx)
    context.add_init_script(INIT)
    page = context.new_page()
    page.set_default_timeout(15000)
    log = {'console': [], 'pageerror': [], 'failed': [], 'bad': [], 'requests': []}
    page.on('console', lambda m: log['console'].append(m.text) if m.type in ('error', 'warning') else None)
    page.on('pageerror', lambda e: log['pageerror'].append(str(e)))
    page.on('requestfailed', lambda r: log['failed'].append(r.url))
    page.on('response', lambda r: (log['requests'].append({'url': r.url.replace(URL, ''), 'status': r.status, 'type': r.request.resource_type}), log['bad'].append(f'{r.status} {r.url}') if r.status >= 400 else None))
    page._log = log
    return context, page


def load(page, path=''):
    resp = page.goto(URL + path)
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    return resp


def clean(page, allow_bad=(), allow_aborted_media=False):
    log = page._log
    if allow_aborted_media:      # Chromium membatalkan unduhan awal saat beralih ke permintaan Range ketika seek
        log['failed'] = [u for u in log['failed'] if not u.endswith('.mp4')]
    bad = [b for b in log['bad'] if not any(a in b for a in allow_bad)]
    console = [c for c in log['console'] if not any(a in c for a in allow_bad)]
    csp = page.evaluate('window.__csp || []')
    assert not bad and not log['failed'], (bad, log['failed'])
    assert not log['pageerror'] and not console, (log['pageerror'], console)
    assert not csp, f'pelanggaran CSP: {csp}'


def wait_for(page, expr, timeout=15000):
    """Pengganti wait_for_function: yang itu memakai eval di halaman dan (dengan benar) diblokir CSP situs."""
    end = time.time() + timeout / 1000
    while time.time() < end:
        if page.evaluate(expr):
            return True
        page.wait_for_timeout(100)
    raise AssertionError('batas waktu menunggu: ' + expr[:140])


def click_native_play(page, vid):
    """Klik tombol Putar/Jeda pada panel kontrol native Chromium (kiri bawah pemutar)."""
    box = page.locator('#' + vid).bounding_box()
    page.mouse.click(box['x'] + 24, box['y'] + box['height'] - 47)


def vstate(page, vid, expr):
    return page.evaluate(f"(() => {{ const v = document.getElementById('{vid}'); return {expr}; }})()")


def wait_playing(page, vid, after=0.3, timeout=15000):
    wait_for(page, f"(() => {{ const v = document.getElementById('{vid}'); return !v.paused && v.currentTime > {after}; }})()", timeout)


REG = CONFIG.get('registration_url')

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    version = browser.version
    ua = None

    # ================================================================== status akses per profil
    @test(f'[{PROFILE}] Semua CTA daftar mengarah ke tujuan profil dan dapat diikuti', 'A10 A11')
    def _():
        ctx, page = new_page(browser, 1440, 900)
        visited = []
        if PROFILE != 'preview':
            # Host tujuan adalah layanan luar. Pada build fixture, permintaan ke host .test dijawab halaman penanda;
            # yang dibuktikan hanya bahwa klik menavigasi ke URL konfigurasi, BUKAN bahwa layanan akun bekerja.
            ctx.route('https://**/*', lambda r: (visited.append(r.request.url), r.fulfill(status=200, content_type='text/html', body='<title>FIXTURE</title><h1>Halaman penanda fixture</h1>'))[1])
        load(page)
        hrefs = page.evaluate("[...document.querySelectorAll('[data-register-link]')].map(a => a.getAttribute('href'))")
        expected = 'daftar.html' if PROFILE == 'preview' else REG
        assert len(hrefs) == 7 and all(h == expected for h in hrefs), hrefs
        global ua
        ua = page.evaluate('navigator.userAgent')
        out = {'cta': len(hrefs), 'href': expected}
        link = page.locator('#beranda .hero-actions [data-register-link]')
        link.focus(); page.keyboard.press('Enter')
        if PROFILE == 'preview':
            page.wait_for_url('**/daftar.html'); page.wait_for_load_state('networkidle')
            st = page.evaluate("""({closed: getComputedStyle(document.querySelector('[data-registration-closed]')).display !== 'none', open: getComputedStyle(document.querySelector('[data-registration-open]')).display !== 'none',
                text: document.querySelector('[data-registration-closed] .section-lead').innerText, forms: document.querySelectorAll('form,input').length, robots: document.querySelector('meta[name=robots]').content})""")
            page.screenshot(path=str(SHOTS / f'{TAG}_akses_1440x900.png'))
            assert st['closed'] and not st['open'] and 'belum dibuka' in st['text'] and st['forms'] == 0 and st['robots'] == 'noindex, follow', st
            page.locator('[data-registration-closed] a').click(); page.wait_for_url('**/index.html#arahan-foto')
            out['daftar'] = st
            clean(page)
        else:
            page.wait_for_url(REG)
            assert visited and visited[0] == REG, visited
            out['navigated_to'] = page.url
            out['catatan'] = 'Tujuan dijawab halaman penanda fixture; layanan akun nyata tidak diuji.' if args.fixture else ''
        ctx.close()
        return out

    @test(f'[{PROFILE}] Halaman akses dan status di homepage sesuai profil (390x844)', 'A10 A11')
    def _():
        ctx, page = new_page(browser, 390, 844)
        load(page)
        note = page.evaluate("(document.querySelector('[data-access-note]') || {innerText: null}).innerText")
        meta = page.evaluate("({robots: document.querySelector('meta[name=robots]').content, profile: document.querySelector('meta[name=jp-release-profile]').content, canonical: (document.querySelector('link[rel=canonical]') || {}).href || null})")
        load(page, 'daftar.html')
        st = page.evaluate("""(() => { const vis = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0; };
            return {closed: vis('[data-registration-closed]'), open: vis('[data-registration-open]'), staging: vis('[data-staging-note]'), login: vis('[data-login-link]'),
                    dest: document.querySelector('[data-registration-destination]').getAttribute('href'), forms: document.querySelectorAll('form,input').length, sw: document.documentElement.scrollWidth}; })()""")
        page.screenshot(path=str(SHOTS / f'{TAG}_akses_390x844.png'))
        ctx.close()
        assert meta['profile'] == PROFILE and st['forms'] == 0 and st['sw'] <= 390, (meta, st)
        if PROFILE == 'preview':
            assert 'Akses akun segera hadir' in (note or '') and meta['robots'] == 'noindex, follow' and meta['canonical'] is None, (note, meta)
            assert st['closed'] and not st['open'] and not st['staging'], st
        elif PROFILE == 'staging':
            assert 'Lingkungan uji' in (note or '') and meta['robots'] == 'noindex, follow' and meta['canonical'] is None, (note, meta)
            assert st['open'] and not st['closed'] and st['staging'] and st['dest'] == REG, st
        else:
            assert note is None and meta['robots'] == 'index, follow' and meta['canonical'] == CONFIG['site_url'].rstrip('/') + '/', (note, meta)
            assert st['open'] and not st['closed'] and not st['staging'] and st['dest'] == REG, st
        return {'note': note, **meta, **st}

    if not args.quick:
        # ============================================================== per viewport
        for (w, h) in VIEWPORTS:
            tag = f'{w}x{h}'

            @test(f'[{tag}] Layar awal: Canon 01, hasil foto terlihat, tanpa scroll horizontal', 'A01 A03 A13')
            def _():
                ctx, page = new_page(browser, w, h)
                load(page)
                page.screenshot(path=str(SHOTS / f'hero_{tag}.png'))
                hero, ov = page.evaluate(JS_HERO), page.evaluate(JS_OVERFLOW)
                measure.setdefault('hero', {})[tag] = hero
                clean(page); ctx.close()
                assert hero['h1'] == 'Kunci DNA Brand kamu untuk hasil generate yang selalu konsisten.', hero['h1']
                assert ov['scrollWidth'] <= ov['clientWidth'] and not ov['outside'] and not ov['clipped'], ov
                assert hero['loaded'], 'gambar hero belum dimuat'
                assert hero['title'] < hero['results'] and hero['mosaicArea'] > hero['summaryArea'], hero
                if w <= 960 and h > 480:
                    seq = [hero[k] for k in ('title', 'lead', 'results', 'actions', 'summary')]
                    assert seq == sorted(seq), f'urutan visual berbeda dari DOM: {seq}'
                if (w, h) in ((390, 844), (360, 800)):
                    assert hero['visibleFraction'] >= 0.6, hero['visibleFraction']
                elif h >= 768:
                    assert hero['visibleFraction'] >= 0.5, hero['visibleFraction']
                assert hero['h1Px'] >= 26 and hero['leadPx'] >= 15, (hero['h1Px'], hero['leadPx'])
                return {k: hero[k] for k in ('visibleFraction', 'imageTop', 'imageH', 'currentSrc', 'h1Px', 'leadPx')}

            @test(f'[{tag}] Seluruh halaman: gambar, tanpa 4xx/console/CSP, media tidak dimuat sebelum Putar', 'A08 A13')
            def _():
                ctx, page = new_page(browser, w, h, reduced_motion='reduce')
                load(page)
                total = page.evaluate('document.documentElement.scrollHeight'); y = 0
                while y < total:
                    page.evaluate(f'scrollTo(0,{y})'); page.wait_for_timeout(110); y += h
                page.evaluate('scrollTo(0,0)'); page.wait_for_load_state('networkidle'); page.wait_for_timeout(250)
                imgs = page.evaluate("[...document.images].filter(i => !i.closest('details:not([open])')).map(i => ({src: i.currentSrc.split('/').pop(), ok: i.complete && i.naturalWidth > 0}))")
                ov = page.evaluate(JS_OVERFLOW)
                media = [r for r in page._log['requests'] if r['url'].endswith(('.mp4', '.vtt'))]
                vids = page.evaluate("[...document.querySelectorAll('video')].map(v => [v.paused, v.currentTime, v.readyState])")
                if tag in ('1440x900', '768x1024', '390x844', '320x568'):
                    page.screenshot(path=str(SHOTS / f'halaman_{tag}.jpg'), full_page=True, type='jpeg', quality=78)
                clean(page); ctx.close()
                assert imgs and all(i['ok'] for i in imgs), [i for i in imgs if not i['ok']]
                assert not media, f'media dimuat sebelum Putar: {media}'
                assert vids == [[True, 0, 0]] * 4, vids
                assert ov['scrollWidth'] <= ov['clientWidth'] and not ov['outside'] and not ov['clipped'], ov
                return {'images_visible': len(imgs), 'requests': len(page._log['requests'])}

        # ============================================================== anchor dan navigasi
        for (w, h) in [(1440, 900), (390, 844)]:
            tag = f'{w}x{h}'

            @test(f'[{tag}] Anchor internal: target benar, heading tidak tertutup header, video tetap diam', 'A10')
            def _():
                out = {}
                cases = [('.hero-actions a[href="#arahan-foto"]', 'arahan-foto'), ('.hero-side a.text-link[href="#hasil-video"]', 'hasil-video'), ('.cta-actions a[href="#hasil-video"]', 'hasil-video'),
                         ('.footer-nav a[href="#fitur"]', 'fitur'), ('.footer-nav a[href="#pemula"]', 'pemula'), ('a.to-top', 'beranda')]
                for mode in ('pointer', 'keyboard'):
                    for sel, target in cases:
                        ctx, page = new_page(browser, w, h)
                        load(page)
                        link = page.locator(sel)
                        if target == 'beranda':
                            page.evaluate('scrollTo(0, 3000)'); page.wait_for_timeout(400)
                        link.scroll_into_view_if_needed()
                        if mode == 'pointer':
                            link.click()
                        else:
                            link.focus(); page.keyboard.press('Enter')
                        page.evaluate(JS_SETTLED)
                        info = page.evaluate("""(id) => { const t = document.getElementById(id), hd = document.querySelector('[data-header]').getBoundingClientRect(), hh = (t.querySelector('h1,h2') || t).getBoundingClientRect();
                            return {hash: location.hash, headerBottom: Math.round(hd.bottom), headingTop: Math.round(hh.top), vh: innerHeight, playing: [...document.querySelectorAll('video')].some(v => !v.paused)}; }""", target)
                        ctx.close()
                        assert info['hash'] == '#' + target and not info['playing'], (sel, info)
                        if target != 'beranda':
                            assert info['headerBottom'] <= info['headingTop'] < info['vh'], (sel, info)
                        out[f'{mode} {sel}'] = info['headingTop']
                return out

        @test('[1440x900] Navigasi header: lima tautan, penanda aktif mengikuti gulir, anchor #cara-kerja', 'A10 A14')
        def _():
            ctx, page = new_page(browser, 1440, 900)
            load(page)
            out = {}
            for label, target in (('Visual Brand', 'arahan-foto'), ('Konten Affiliate', 'hasil-video'), ('Manfaat', 'fitur'), ('Tanya Jawab', 'pemula'), ('Beranda', 'beranda')):
                page.locator('.nav-link', has_text=label).click(); page.evaluate(JS_SETTLED); page.wait_for_timeout(250)
                cur = page.evaluate("[...document.querySelectorAll('.nav-link[aria-current]')].map(a => a.getAttribute('href'))")
                assert page.evaluate('location.hash') == '#' + target, label
                out[label] = cur
                assert '#' + target in cur and len(cur) == 1, (label, cur)
            load(page, '#cara-kerja'); page.evaluate(JS_SETTLED)
            top = page.evaluate("document.getElementById('faq-title').getBoundingClientRect().top")
            clean(page); ctx.close()
            assert 0 < top < 900, top
            return out

        # ============================================================== video
        @test('Video: tidak autoplay saat muat, gulir, pindah tab, dan muat ulang; tanpa permintaan media', 'A08')
        def _():
            ctx, page = new_page(browser, 1440, 900)
            load(page)
            st = lambda: page.evaluate("[...document.querySelectorAll('video')].map(v => [v.paused, v.currentTime, v.autoplay, v.loop, v.muted])")
            snaps = [st()]
            page.locator('#hasil-video').scroll_into_view_if_needed(); page.wait_for_timeout(2000); snaps.append(st())
            page.evaluate('scrollTo(0, document.documentElement.scrollHeight)'); page.wait_for_timeout(500); page.locator('#video-3').scroll_into_view_if_needed(); page.wait_for_timeout(1200); snaps.append(st())
            other = ctx.new_page(); other.goto('about:blank'); other.bring_to_front(); other.wait_for_timeout(600); page.bring_to_front(); page.wait_for_timeout(600); other.close(); snaps.append(st())
            page.reload(); page.wait_for_load_state('networkidle'); page.locator('#video-1').scroll_into_view_if_needed(); page.wait_for_timeout(1200); snaps.append(st())
            media = [r for r in page._log['requests'] if r['url'].endswith(('.mp4', '.vtt'))]
            ctx.close()
            assert all(s == [[True, 0, False, False, False]] * 4 for s in snaps), snaps
            assert not media, media
            return {'checkpoints': len(snaps), 'media_requests': 0}

        for i in range(1, 5):
            vid = f'video-{i}'

            @test(f'Video {i}: Putar, Jeda, seek, suara, keyboard, selesai tanpa loop, putar ulang, layar penuh', 'A07 A08')
            def _():
                ctx, page = new_page(browser, 1440, 900)
                load(page)
                v = page.locator('#' + vid); v.scroll_into_view_if_needed(); page.wait_for_timeout(400)
                if i == 1:
                    page.screenshot(path=str(SHOTS / 'video_poster_1440x900.png'))
                box = v.bounding_box()
                meta0 = vstate(page, vid, "({controls: v.controls, inline: v.playsInline, preload: v.getAttribute('preload'), poster: v.poster.split('/').pop()})")
                click_native_play(page, vid); wait_playing(page, vid, 0.8)
                played = vstate(page, vid, "({t: v.currentTime, muted: v.muted, volume: v.volume, audioBytes: v.webkitAudioDecodedByteCount, videoBytes: v.webkitVideoDecodedByteCount, duration: v.duration, w: v.videoWidth, h: v.videoHeight, src: v.currentSrc.split('/').pop()})")
                ratio = box['width'] / box['height']
                mp4 = [r for r in page._log['requests'] if r['url'].endswith(f'affiliate-0{i}.mp4')]
                others = [r['url'] for r in page._log['requests'] if r['url'].endswith('.mp4') and not r['url'].endswith(f'affiliate-0{i}.mp4')]
                if i == 1:
                    page.screenshot(path=str(SHOTS / 'video_memutar_1440x900.png'))
                click_native_play(page, vid); wait_for(page, f"document.getElementById('{vid}').paused")
                t1 = vstate(page, vid, 'v.currentTime'); page.wait_for_timeout(600); t2 = vstate(page, vid, 'v.currentTime')
                page.evaluate(f"document.getElementById('{vid}').currentTime = 5.5"); wait_for(page, f"!document.getElementById('{vid}').seeking")
                seek = vstate(page, vid, 'v.currentTime')
                v.focus(); page.keyboard.press('Space'); wait_for(page, f"!document.getElementById('{vid}').paused")
                page.keyboard.press('Space'); wait_for(page, f"document.getElementById('{vid}').paused")
                page.keyboard.press('ArrowRight'); page.wait_for_timeout(250); arrow = vstate(page, vid, 'v.currentTime')
                vol = vstate(page, vid, "(v.volume = 0.4, v.muted = true, [v.volume, v.muted])"); vstate(page, vid, "(v.volume = 1, v.muted = false, 1)")
                page.evaluate(f"document.getElementById('{vid}').currentTime = 8.6"); page.keyboard.press('Space')
                wait_for(page, f"document.getElementById('{vid}').ended"); page.wait_for_timeout(900)
                ended = vstate(page, vid, "({ended: v.ended, paused: v.paused, t: +v.currentTime.toFixed(2), loop: v.loop})")
                page.keyboard.press('Space')
                wait_for(page, f"(() => {{ const v = document.getElementById('{vid}'); return !v.paused && v.currentTime > 0.25 && v.currentTime < 4; }})()")
                page.keyboard.press('Space')
                page.evaluate(f"document.getElementById('{vid}').addEventListener('click', e => {{ e.currentTarget.requestFullscreen().then(() => window.__fs = 'ok', err => window.__fs = String(err)); }}, {{once: true}})")
                page.mouse.click(box['x'] + box['width'] / 2, box['y'] + 50); wait_for(page, 'window.__fs !== undefined')
                fs = page.evaluate("({fs: window.__fs, el: document.fullscreenElement ? document.fullscreenElement.id : null})")
                clean(page, allow_aborted_media=True); ctx.close()
                assert meta0 == {'controls': True, 'inline': True, 'preload': 'none', 'poster': f'affiliate-0{i}-poster.jpg'}, meta0
                assert played['src'] == f'affiliate-0{i}.mp4' and abs(played['duration'] - 10) < 0.05 and (played['w'], played['h']) == (480, 854), played
                assert played['muted'] is False and played['volume'] == 1 and played['audioBytes'] > 0 and played['videoBytes'] > 0, played
                assert abs(ratio - 480 / 854) < 0.005 and box['width'] <= 480, (ratio, box)
                assert mp4 and all(r['status'] in (200, 206) for r in mp4) and not others, (mp4, others)
                assert abs(t1 - t2) < 0.01 and abs(seek - 5.5) < 0.2 and arrow > seek and vol == [0.4, True], (t1, t2, seek, arrow, vol)
                assert ended['ended'] and ended['paused'] and not ended['loop'] and abs(ended['t'] - 10) < 0.1, ended
                assert fs == {'fs': 'ok', 'el': vid}, fs
                return {'duration': played['duration'], 'audioDecodedBytes': played['audioBytes'], 'box': f"{round(box['width'])}x{round(box['height'])}", 'seek': seek, 'ended': ended, 'fullscreen': fs['fs'], 'http': sorted({r['status'] for r in mp4})}

            @test(f'Video {i}: caption Indonesia dimuat, tersinkron, dan sama dengan teks narasi di halaman', 'A18')
            def _():
                ctx, page = new_page(browser, 1440, 900)
                load(page)
                page.locator('#' + vid).scroll_into_view_if_needed()
                info = page.evaluate(f"""async () => {{ const v = document.getElementById('{vid}'), t = v.textTracks[0]; t.mode = 'showing';
                    for (let n = 0; n < 60 && !(t.cues && t.cues.length); n++) await new Promise(r => setTimeout(r, 100));
                    const cues = [...t.cues].map(c => [c.startTime, c.endTime, c.text]);
                    v.preload = 'auto'; v.load(); await new Promise(r => v.addEventListener('loadeddata', r, {{once: true}}));
                    v.currentTime = cues[1][0] + 0.2; await new Promise(r => v.addEventListener('seeked', r, {{once: true}})); await new Promise(r => setTimeout(r, 300));
                    return {{kind: t.kind, lang: t.language, label: t.label, cues, active: [...t.activeCues].map(c => c.text), page: v.closest('[data-media-unit]').querySelector('.media-transcript p').textContent.replace(/\\s+/g, ' ').trim()}}; }}""")
                page.locator('#' + vid).screenshot(path=str(SHOTS / f'video_{i}_caption.png'))
                clean(page, allow_aborted_media=True); ctx.close()
                assert info['kind'] == 'captions' and info['lang'] == 'id' and len(info['cues']) >= 5, info
                assert info['active'] == [info['cues'][1][2]], info['active']
                assert ' '.join(c[2] for c in info['cues']) == info['page'], 'caption berbeda dari teks narasi'
                assert info['cues'][-1][1] <= 10.0 and all(a[1] <= b[0] + 1e-6 for a, b in zip(info['cues'], info['cues'][1:])), info['cues']
                return {'cues': len(info['cues']), 'active_at_cue_2': info['active'][0], 'label': info['label']}

        @test('Video: memutar satu video menjeda video lain', 'A08')
        def _():
            ctx, page = new_page(browser, 1440, 900)
            load(page)
            page.locator('#video-1').scroll_into_view_if_needed(); click_native_play(page, 'video-1'); wait_playing(page, 'video-1')
            page.locator('#video-2').scroll_into_view_if_needed(); click_native_play(page, 'video-2'); wait_playing(page, 'video-2')
            page.wait_for_timeout(300)
            st = page.evaluate("[...document.querySelectorAll('video')].map(v => v.id + ':' + (v.paused ? 'jeda' : 'putar'))")
            clean(page, allow_aborted_media=True); ctx.close()
            assert sorted(st) == ['video-1:jeda', 'video-2:putar', 'video-3:jeda', 'video-4:jeda'], st
            return st

        def error_case(vid_n, kind):
            vid = f'video-{vid_n}'
            ctx, page = new_page(browser, 390, 844)
            pattern = f'**/affiliate-0{vid_n}.mp4'
            if kind == '404':
                page.route(pattern, lambda r: r.fulfill(status=404, body='tidak ada'))
            elif kind == 'offline':
                page.route(pattern, lambda r: r.abort('internetdisconnected'))
            else:
                page.route(pattern, lambda r: r.fulfill(status=200, content_type='video/mp4', body=b'bukan berkas video' * 500))
            load(page)
            v = page.locator('#' + vid); v.scroll_into_view_if_needed(); page.wait_for_timeout(300)
            unit = "document.getElementById('%s').closest('[data-media-unit]')" % vid
            pre = page.evaluate(f"({{text: {unit}.querySelector('[data-video-status]').textContent.trim(), retryHidden: {unit}.querySelector('[data-video-retry]').hidden}})")
            click_native_play(page, vid)
            wait_for(page, f"{unit}.querySelector('[data-video-status]').textContent.trim().length > 0")
            info = page.evaluate(f"""(() => {{ const u = {unit}, s = u.querySelector('[data-video-status]'), b = u.querySelector('[data-video-retry]'), a = u.querySelector('a.media-fallback');
                const vis = e => {{ const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden'; }};
                const others = [...document.querySelectorAll('[data-video-status]')].filter(x => x !== s).map(x => x.textContent.trim()).join('');
                return {{text: s.textContent.trim(), role: s.getAttribute('role'), statusVisible: vis(s), retryVisible: vis(b), isButton: b.tagName === 'BUTTON' && b.type === 'button', fallbackVisible: vis(a), fallbackHref: a.getAttribute('href'), insideVideo: !!s.closest('video'), others}}; }})()""")
            page.locator(f'#{vid}').evaluate("e => e.closest('[data-media-unit]').querySelector('[data-video-status]').scrollIntoView({block: 'center'})")
            page.screenshot(path=str(SHOTS / f'video_gagal_{kind}_390x844.png'))
            page.unroute(pattern)
            page.locator(f'#{vid}').evaluate("e => e.closest('[data-media-unit]').querySelector('[data-video-retry]').focus()"); page.keyboard.press('Enter')
            wait_playing(page, vid)
            rec = page.evaluate(f"({{text: {unit}.querySelector('[data-video-status]').textContent.trim(), retryHidden: {unit}.querySelector('[data-video-retry]').hidden}})")
            head = page.request.get(URL + info['fallbackHref'], headers={'Range': 'bytes=0-99'})
            alt = {'status': head.status, 'type': head.headers.get('content-type'), 'range': head.headers.get('content-range')}
            ctx.close()
            assert pre == {'text': '', 'retryHidden': True}, pre
            assert 'belum dapat diputar' in info['text'] and info['role'] == 'status' and info['statusVisible'] and not info['insideVideo'] and info['others'] == '', info
            assert info['retryVisible'] and info['isButton'] and info['fallbackVisible'] and info['fallbackHref'] == f'assets/media/affiliate-0{vid_n}.mp4', info
            assert rec == {'text': '', 'retryHidden': True}, rec
            assert alt['status'] == 206 and alt['type'] == 'video/mp4' and alt['range'].startswith('bytes 0-99/'), alt
            return {'message': info['text'], 'recovered_with_keyboard': True, 'fallback': alt}

        for n, kind in ((1, '404'), (2, 'offline'), (3, 'rusak'), (4, '404')):
            test(f'Video {n} gagal ({kind}): pesan lokal, Coba putar lagi, tautan alternatif 206, pemulihan', 'A08')(lambda n=n, kind=kind: error_case(n, kind))

        # ============================================================== tanpa JS / JS gagal / reduced motion
        for (w, h) in [(1440, 900), (390, 844)]:
            tag = f'{w}x{h}'

            @test(f'[{tag}] Tanpa JavaScript: navigasi, hasil, FAQ, galeri, narasi, video native, CTA tetap berfungsi', 'A14')
            def _():
                ctx, page = new_page(browser, w, h, java_script_enabled=False)
                page.goto(URL); page.wait_for_load_state('networkidle')
                page.screenshot(path=str(SHOTS / f'tanpa_js_{tag}.png'))
                info = page.evaluate("""() => { const vis = el => { if (!el) return false; const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0; }; const de = document.documentElement;
                    return {js: de.classList.contains('js'), nav: [...document.querySelectorAll('.nav-link')].every(vis), toggle: vis(document.querySelector('[data-menu-toggle]')), hero: document.querySelector('.hero-shot-main img').naturalWidth > 0,
                        controls: [...document.querySelectorAll('video')].every(v => v.controls), retry: [...document.querySelectorAll('[data-video-retry]')].some(vis), reveals: [...document.querySelectorAll('.reveal')].every(vis),
                        buttons: [...document.querySelectorAll('button')].filter(vis).length, sw: de.scrollWidth, cw: de.clientWidth}; }""")
                for sel in ('.faq-list details', '.series-details', '.media-transcript'):
                    d = page.locator(sel).first; d.locator('summary').scroll_into_view_if_needed(); d.locator('summary').click()
                    assert d.evaluate('e => e.open'), sel
                page.locator('#video-1').scroll_into_view_if_needed(); click_native_play(page, 'video-1')
                playing = False
                for _i in range(60):        # tanpa JS, wait_for_function berbasis rAF tidak berjalan
                    page.wait_for_timeout(250)
                    if vstate(page, 'video-1', '!v.paused && v.currentTime > 0.5'):
                        playing = True; break
                page.goto(URL); page.locator('.hero-actions a[href="#arahan-foto"]').click(); page.wait_for_timeout(400)
                hash1 = page.evaluate('location.hash')
                ctx.close()
                assert info['js'] is False and info['nav'] and not info['toggle'] and info['hero'] and info['controls'], info
                assert not info['retry'] and info['reveals'] and info['buttons'] == 0 and info['sw'] <= info['cw'], info
                assert playing and hash1 == '#arahan-foto'
                return {**info, 'video_native_playable': True, 'details_open': 3}

        @test('[390x844] main.js gagal dimuat: flag.js mencabut kelas js, navigasi cadangan tampil, tanpa tombol mati', 'A14')
        def _():
            ctx, page = new_page(browser, 390, 844)
            page.route('**/js/main.js', lambda r: r.abort())
            page.goto(URL); page.wait_for_load_state('load'); page.wait_for_timeout(500)
            info = page.evaluate("""() => { const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
                return {js: document.documentElement.classList.contains('js'), nav: [...document.querySelectorAll('.nav-link')].every(vis), toggle: vis(document.querySelector('[data-menu-toggle]')), buttons: [...document.querySelectorAll('button')].filter(vis).length, csp: window.__csp}; }""")
            ctx.close()
            assert info == {'js': False, 'nav': True, 'toggle': False, 'buttons': 0, 'csp': []}, info
            return info

        @test('Reduced motion: tanpa animasi berjalan, gulir langsung, video tetap dapat diputar manual', 'A14')
        def _():
            ctx, page = new_page(browser, 390, 844, reduced_motion='reduce')
            load(page)
            info = page.evaluate("({scroll: getComputedStyle(document.documentElement).scrollBehavior, reveals: [...document.querySelectorAll('.reveal')].every(e => e.classList.contains('is-visible')), running: document.getAnimations().filter(a => a.playState === 'running').length, paused: [...document.querySelectorAll('video')].every(v => v.paused)})")
            page.locator('#video-4').scroll_into_view_if_needed(); click_native_play(page, 'video-4'); wait_playing(page, 'video-4')
            clean(page, allow_aborted_media=True); ctx.close()
            assert info == {'scroll': 'auto', 'reveals': True, 'running': 0, 'paused': True}, info
            return info

        # ============================================================== keyboard, menu, fokus
        @test('[390x844] Menu mobile: buka, fokus tautan pertama, urutan Tab, Escape, klik luar, tujuan tiap tautan', 'A14')
        def _():
            ctx, page = new_page(browser, 390, 844)
            load(page)
            tg = page.locator('[data-menu-toggle]')
            closed = page.evaluate("getComputedStyle(document.querySelector('[data-nav]')).visibility")
            tg.focus(); page.keyboard.press('Enter'); page.wait_for_timeout(350)
            a = page.evaluate("({exp: document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded'), label: document.querySelector('[data-menu-toggle]').getAttribute('aria-label'), focus: document.activeElement.textContent.trim(), vis: getComputedStyle(document.querySelector('[data-nav]')).visibility})")
            page.screenshot(path=str(SHOTS / 'menu_390x844.png'))
            order = []
            for _i in range(6):
                order.append(page.evaluate("document.activeElement.textContent.replace(/\\s+/g, ' ').trim()")); page.keyboard.press('Tab')
            tg.focus()
            if page.evaluate("document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded')") == 'false':
                page.keyboard.press('Enter'); page.wait_for_timeout(300)
            page.keyboard.press('Escape'); page.wait_for_timeout(350)
            b = page.evaluate("({exp: document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded'), focusIsToggle: document.activeElement === document.querySelector('[data-menu-toggle]'), vis: getComputedStyle(document.querySelector('[data-nav]')).visibility})")
            tg.click(); page.wait_for_timeout(350); page.mouse.click(195, 800); page.wait_for_timeout(350)
            c = page.evaluate("document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded')")
            dest = {}
            for label, target in (('Visual Brand', 'arahan-foto'), ('Konten Affiliate', 'hasil-video'), ('Manfaat', 'fitur'), ('Tanya Jawab', 'pemula')):
                page.evaluate('scrollTo(0,0)'); page.wait_for_timeout(250); tg.click(); page.wait_for_timeout(300)
                page.locator('#nav-menu a.nav-link', has_text=label).click(); page.evaluate(JS_SETTLED)
                d = page.evaluate("(id) => { const t = document.getElementById(id); return {hash: location.hash, top: Math.round(t.getBoundingClientRect().top), exp: document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded'), focusOnTarget: document.activeElement === t, navVis: getComputedStyle(document.querySelector('[data-nav]')).visibility}; }", target)
                assert d['hash'] == '#' + target and d['exp'] == 'false' and d['navVis'] == 'hidden' and 0 <= d['top'] <= 130 and d['focusOnTarget'], (label, d)
                dest[label] = d['top']
            clean(page); ctx.close()
            assert closed == 'hidden' and a == {'exp': 'true', 'label': 'Tutup menu', 'focus': 'Beranda', 'vis': 'visible'}, (closed, a)
            assert order == ['Beranda', 'Visual Brand', 'Konten Affiliate', 'Manfaat', 'Tanya Jawab', 'Mulai dengan Jago Prompt'], order
            assert b == {'exp': 'false', 'focusIsToggle': True, 'vis': 'hidden'} and c == 'false', (b, c)
            return {'open': a, 'tab_order': order, 'escape': b, 'outside_click_closes': True, 'destinations': dest}

        @test('[1440x900] Skip link dan urutan Tab: mengikuti urutan baca, fokus terlihat, siklus kembali ke awal', 'A14')
        def _():
            ctx, page = new_page(browser, 1440, 900, reduced_motion='reduce')
            load(page)
            page.keyboard.press('Tab')
            skip = page.evaluate("(() => { const a = document.activeElement, r = a.getBoundingClientRect(); return {text: a.textContent.trim(), visible: r.top >= 0 && r.bottom <= innerHeight && r.width > 0}; })()")
            page.screenshot(path=str(SHOTS / 'skip_link_1440x900.png'))
            page.keyboard.press('Enter'); page.wait_for_timeout(300)
            after = page.evaluate("({hash: location.hash, active: document.activeElement.id || document.activeElement.tagName})")
            page.keyboard.press('Tab')
            first_in_main = page.evaluate("!!document.activeElement.closest('main')")
            load(page)
            seq = []
            for _i in range(90):
                page.keyboard.press('Tab')
                item = page.evaluate("""() => { const a = document.activeElement; if (!a || a === document.body) return null; const cs = getComputedStyle(a), r = a.getBoundingClientRect();
                    return {tag: a.tagName, name: (a.getAttribute('aria-label') || a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 44), outline: cs.outlineStyle + ' ' + cs.outlineWidth, inView: r.top >= 0 && r.bottom <= innerHeight + 1}; }""")
                if item is None or (seq and item['name'] == seq[0]['name'] and item['tag'] == seq[0]['tag']):
                    break
                seq.append(item)
            dom = page.evaluate("""() => [...document.querySelectorAll('a[href],button,summary,video[controls]')].filter(e => { const cs = getComputedStyle(e), r = e.getBoundingClientRect(); return !e.hidden && cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && !(e.closest('details:not([open])') && e.tagName !== 'SUMMARY'); }).map(a => (a.getAttribute('aria-label') || a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 44))""")
            ctx.close()
            names = [s['name'] for s in seq]
            dd = lambda xs: [n for k, n in enumerate(xs) if k == 0 or n != xs[k - 1]]       # kontrol dalam panel native menambah perhentian berlabel sama
            assert skip == {'text': 'Lewati ke konten', 'visible': True} and after['hash'] == '#konten' and first_in_main, (skip, after, first_in_main)
            assert dd(names) == dd(dom), {'tab': dd(names), 'dom': dd(dom)}
            no_outline = [s for s in seq if s['tag'] != 'VIDEO' and (s['outline'].startswith('none') or s['outline'].endswith(' 0px'))]
            assert not no_outline, no_outline
            off = [s['name'] for s in seq if not s['inView'] and s['tag'] != 'VIDEO']
            assert not off, off
            return {'stops': len(seq), 'unique': len(dd(names)), 'skip_link': skip, 'after_skip': after}

        @test('[390x844] FAQ dan disclosure galeri dengan keyboard; seluruh 31 gambar termuat setelah dibuka', 'A06 A14')
        def _():
            ctx, page = new_page(browser, 390, 844, reduced_motion='reduce')
            load(page)
            out = {}
            for k in range(4):
                d = page.locator('.faq-list details').nth(k); d.locator('summary').focus(); page.keyboard.press('Enter')
                assert d.evaluate('e => e.open'); page.keyboard.press('Space'); assert not d.evaluate('e => e.open')
            for d in page.locator('.series-details').all():
                d.locator('summary').focus(); page.keyboard.press('Enter'); page.wait_for_timeout(200)
                for im in d.locator('img').all():
                    im.scroll_into_view_if_needed(); page.wait_for_timeout(40)
                page.wait_for_load_state('networkidle')
                out[d.locator('summary').inner_text()] = d.locator('img').count()
                assert d.locator('img').evaluate_all('els => els.every(e => e.complete && e.naturalWidth > 0)')
            total = page.evaluate("document.documentElement.scrollHeight"); y = 0
            while y < total:
                page.evaluate(f'scrollTo(0,{y})'); page.wait_for_timeout(90); y += 844
            page.wait_for_load_state('networkidle')
            uniq = page.evaluate("[...new Set([...document.images].filter(i => i.complete && i.naturalWidth > 0 && /assets\\/media\\/(kosmetik|kuliner)-/.test(i.currentSrc)).map(i => i.currentSrc.replace(/-\\d+\\.webp$/, '').split('/').pop()))].length")
            ov = page.evaluate(JS_OVERFLOW)
            page.locator('.series-details').first.scroll_into_view_if_needed(); page.screenshot(path=str(SHOTS / 'galeri_terbuka_390x844.png'))
            clean(page); ctx.close()
            assert uniq == 31, uniq
            assert ov['scrollWidth'] <= ov['clientWidth'] and not ov['outside'], ov
            return {'faq': 4, 'galleries': out, 'unique_source_images_loaded': uniq}

        @test('Kontras teks seluruh halaman dan ukuran target interaktif (1440 dan 390)', 'A13')
        def _():
            out = {}
            for (w, h) in [(1440, 900), (390, 844)]:
                ctx, page = new_page(browser, w, h, reduced_motion='reduce')
                load(page)
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true); document.querySelectorAll('[data-video]').forEach(v => v.dispatchEvent(new Event('error')))")
                data = page.evaluate("""() => {
                  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[,\\s\\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
                  const over = (f, b) => ({r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a), b: f.b * f.a + b.b * (1 - f.a), a: 1});
                  const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(c.r) + .7152 * f(c.g) + .0722 * f(c.b); };
                  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05); };
                  const bgOf = el => { let layers = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a === 1) break; } }
                    let base = {r: 255, g: 255, b: 255, a: 1}; if (layers.length && layers[layers.length - 1].a === 1) base = layers.pop(); for (const l of layers.reverse()) base = over(l, base); return base; };
                  const rows = [];
                  for (const el of document.body.querySelectorAll('*')) {
                    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
                    const cs = getComputedStyle(el), r = el.getBoundingClientRect(); if (cs.display === 'none' || cs.visibility === 'hidden' || !r.width || el.closest('video')) continue;
                    const fg = parse(cs.color), bg = bgOf(el), size = parseFloat(cs.fontSize), large = size >= 24 || (size >= 18.66 && +cs.fontWeight >= 700);
                    rows.push({text: el.textContent.trim().replace(/\\s+/g, ' ').slice(0, 36), cls: String(el.className || el.tagName), size, ratio: +ratio(over(fg, bg), bg).toFixed(2), need: large ? 3 : 4.5});
                  }
                  const targets = [...document.querySelectorAll('a[href], button, summary')].filter(e => { const cs = getComputedStyle(e), r = e.getBoundingClientRect(); return !e.hidden && cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && !e.closest('video'); })
                    .map(e => { const r = e.getBoundingClientRect(); return {name: (e.getAttribute('aria-label') || e.textContent).trim().replace(/\\s+/g, ' ').slice(0, 34), w: Math.round(r.width), h: Math.round(r.height), inline: getComputedStyle(e).display === 'inline'}; });
                  return {rows, targets};
                }""")
                ctx.close()
                fails = [r for r in data['rows'] if r['ratio'] < r['need']]
                small = [t for t in data['targets'] if (t['w'] < 24 or t['h'] < 24) and not t['inline']]
                out[f'{w}x{h}'] = {'text_nodes': len(data['rows']), 'min_ratio': min(r['ratio'] for r in data['rows']), 'targets': len(data['targets']), 'min_target_h': min(t['h'] for t in data['targets'] if not t['inline']), 'below_44': sorted({t['name'] + f" {t['w']}x{t['h']}" for t in data['targets'] if t['h'] < 44 and not t['inline']})}
                assert not fails, fails[:8]
                assert not small, small
            measure['contrast_targets'] = out
            return out

        @test('Zoom 200%/400% dan teks 200%: tanpa scroll horizontal, CTA terjangkau', 'A13')
        def _():
            out = {}
            for name, (w, h, dpr, fs) in {'1440x900 @200%': (720, 450, 2, None), '1280x800 @200%': (640, 400, 2, None), '1280x1024 @400% (reflow 320)': (320, 256, 4, None), '390x844 teks 200%': (390, 844, 1, '200%'), '1280x800 teks 200%': (1280, 800, 1, '200%')}.items():
                ctx, page = new_page(browser, w, h, device_scale_factor=dpr, reduced_motion='reduce')
                load(page)
                if fs:
                    page.evaluate(f"document.documentElement.style.fontSize = '{fs}'")     # lewat CSSOM; <style> sisipan akan diblokir CSP
                    page.wait_for_timeout(300)
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)"); page.wait_for_timeout(200)
                ov = page.evaluate(JS_OVERFLOW)
                cta = page.evaluate("[...document.querySelectorAll('[data-register-link], .hero-actions a, a.media-fallback')].filter(e => getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0 && !(e.closest('.nav-list') && !e.closest('.nav-list.is-open') && matchMedia('(max-width: 960px)').matches)).map(e => { const r = e.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1; })")
                page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(SHOTS / ('zoom_' + name.replace(' ', '_').replace('%', 'pct').replace('@', 'at').replace('(', '').replace(')', '') + '.png')))
                ctx.close()
                out[name] = {'scrollWidth': ov['scrollWidth'], 'clientWidth': ov['clientWidth'], 'outside': ov['outside'], 'clipped': ov['clipped'], 'cta_reachable': all(cta)}
                assert ov['scrollWidth'] <= ov['clientWidth'] and not ov['outside'] and not ov['clipped'] and all(cta), (name, ov)
            return out

        @test('Gambar gagal dimuat: alt tampil, ruang tetap, tanpa overflow', 'A13')
        def _():
            ctx, page = new_page(browser, 390, 844)
            page.route('**/*.webp', lambda r: r.abort())
            page.goto(URL); page.wait_for_load_state('load'); page.wait_for_timeout(500)
            info = page.evaluate("(() => { const m = document.querySelector('.hero-shot-main'), r = m.getBoundingClientRect(), i = m.querySelector('img'); return {h: Math.round(r.height), alt: i.alt.length, broken: i.naturalWidth === 0, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, h1: !!document.querySelector('h1').innerText}; })()")
            page.screenshot(path=str(SHOTS / 'gambar_gagal_390x844.png')); ctx.close()
            assert info['broken'] and info['alt'] > 20 and info['h'] > 150 and info['sw'] <= info['cw'] and info['h1'], info
            return info

        @test('Font gagal dimuat: fallback terbaca, tanpa overflow', 'A13')
        def _():
            ctx, page = new_page(browser, 390, 844)
            page.route('**/*.woff2', lambda r: r.abort())
            page.goto(URL); page.wait_for_load_state('load'); page.wait_for_timeout(500)
            ov, hero = page.evaluate(JS_OVERFLOW), page.evaluate(JS_HERO)
            page.screenshot(path=str(SHOTS / 'font_gagal_390x844.png')); ctx.close()
            assert ov['scrollWidth'] <= ov['clientWidth'] and not ov['outside'] and not ov['clipped'], ov
            return {'scrollWidth': ov['scrollWidth'], 'visibleFraction': hero['visibleFraction']}

        # ============================================================== halaman 404 dan keamanan
        @test('Halaman 404: status 404 nyata, halaman khusus, tautan pulang berfungsi dari path bertingkat', 'A10')
        def _():
            ctx, page = new_page(browser, 390, 844)
            resp = page.goto(URL + 'tidak-ada/dalam/x'); page.wait_for_load_state('networkidle')
            info = page.evaluate("({h1: document.querySelector('h1').innerText, css: getComputedStyle(document.querySelector('.cta-card')).borderRadius, logo: document.querySelector('.brand img').naturalWidth, robots: document.querySelector('meta[name=robots]').content, csp: window.__csp})")
            page.screenshot(path=str(SHOTS / '404_390x844.png'))
            page.locator('main a.btn').click(); page.wait_for_load_state('networkidle')
            home = page.evaluate("document.querySelector('h1').innerText.replace(/\\s+/g, ' ')")
            status = resp.status
            ctx.close()
            assert status == 404 and 'belum ditemukan' in info['h1'] and info['logo'] > 0 and info['css'] != '0px' and info['robots'] == 'noindex, follow' and info['csp'] == [], info
            assert home.startswith('Kunci DNA Brand kamu'), home
            return {'status': status, **info}

        @test('Keamanan: header terpasang, CSP efektif memblokir skrip sisipan, tanpa pelanggaran pada pemakaian normal', 'A15')
        def _():
            ctx, page = new_page(browser, 1280, 800)
            resp = load(page)
            headers = {k: resp.headers.get(k.lower()) for k in ('Content-Security-Policy', 'X-Content-Type-Options', 'Referrer-Policy', 'X-Frame-Options')}
            meta = page.evaluate("document.querySelector('meta[http-equiv=Content-Security-Policy]').content")
            before = page.evaluate('window.__csp.length')
            page.evaluate("(() => { const s = document.createElement('script'); s.textContent = 'window.__injected = 1'; document.head.appendChild(s); const x = document.createElement('script'); x.src = 'https://cdn.jagoprompt.test/x.js'; document.head.appendChild(x); const i = document.createElement('img'); i.src = 'https://cdn.jagoprompt.test/p.png'; document.body.appendChild(i); })()")
            page.wait_for_timeout(500)
            after = page.evaluate("({injected: window.__injected || 0, violations: window.__csp})")
            ctx.close()
            assert before == 0, 'ada pelanggaran CSP pada pemuatan normal'
            assert all(headers.values()) and "script-src 'self'" in meta, headers
            assert after['injected'] == 0 and len(after['violations']) >= 3, after
            return {'headers': headers, 'blocked': after['violations']}

        # ============================================================== tangkapan per section dan performa lab
        @test('Tangkapan layar tiap section (1440 dan 390) dari source final', 'A04 A20')
        def _():
            n = 0
            for (w, h) in [(1440, 900), (390, 844)]:
                ctx, page = new_page(browser, w, h, reduced_motion='reduce')
                load(page)
                for ident in SECTIONS:
                    el = page.locator('#' + ident); el.scroll_into_view_if_needed(); page.wait_for_timeout(300)
                    page.wait_for_load_state('networkidle')
                    el.screenshot(path=str(SHOTS / f'bagian_{ident}_{w}x{h}.png')); n += 1
                el = page.locator('.site-footer'); el.scroll_into_view_if_needed(); el.screenshot(path=str(SHOTS / f'bagian_footer_{w}x{h}.png')); n += 1
                ctx.close()
            return {'screenshots': n}

        @test('Performa LAB melalui HTTP loopback: tanpa throttling dan dengan throttling jaringan + CPU', 'A16')
        def _():
            out = {}
            profiles = {'tanpa throttling': None, 'throttling 1,6 Mbps / RTT 150 ms / CPU 4x': {'down': 1.6 * 1024 * 1024 / 8, 'up': 750 * 1024 / 8, 'latency': 150, 'cpu': 4}}
            for (w, h) in [(1440, 900), (390, 844)]:
                for label, th in profiles.items():
                    ctx, page = new_page(browser, w, h)
                    page.add_init_script("window.__cls = 0; window.__lcp = null; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({type: 'layout-shift', buffered: true}); new PerformanceObserver(l => { const e = l.getEntries().pop(); window.__lcp = {t: Math.round(e.startTime), url: (e.url || '').split('/').pop(), el: e.element ? e.element.tagName : null}; }).observe({type: 'largest-contentful-paint', buffered: true});")
                    if th:
                        cdp = ctx.new_cdp_session(page)
                        cdp.send('Network.enable')
                        cdp.send('Network.emulateNetworkConditions', {'offline': False, 'downloadThroughput': th['down'], 'uploadThroughput': th['up'], 'latency': th['latency']})
                        cdp.send('Emulation.setCPUThrottlingRate', {'rate': th['cpu']})
                    page.goto(URL, timeout=90000); page.wait_for_load_state('networkidle', timeout=90000); page.wait_for_timeout(700)
                    res = page.evaluate("performance.getEntriesByType('resource').map(r => ({n: r.name.split('/').pop(), b: r.transferSize}))")
                    m = page.evaluate("(() => { const n = performance.getEntriesByType('navigation')[0], p = performance.getEntriesByName('first-contentful-paint')[0]; return {fcp_ms: p ? Math.round(p.startTime) : null, lcp: window.__lcp, cls: +window.__cls.toFixed(4), dcl_ms: Math.round(n.domContentLoadedEventEnd), load_ms: Math.round(n.loadEventEnd), html_bytes: n.transferSize}; })()")
                    ctx.close()
                    m['initial_transfer_bytes'] = sum(r['b'] for r in res) + m.pop('html_bytes'); m['initial_requests'] = len(res) + 1
                    out[f'{w}x{h} · {label}'] = m
                    assert not any(r['n'].endswith(('.mp4', '.vtt')) for r in res), 'media dimuat pada muat awal'
                    assert m['cls'] < 0.1, m
            measure['performance_lab'] = out
            return out

    browser.close()

server.shutdown(); server.server_close()
counts = {k: sum(r['status'] == k for r in results) for k in ('PASS', 'FAIL', 'ERROR')}
out = Path(args.out) if args.out else ROOT / 'qa' / 'hasil' / f'browser-{TAG}.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({
    'profile': PROFILE, 'fixture': args.fixture, 'quick': args.quick,
    'method': 'Chromium bernavigasi ke server HTTP loopback yang melayani berkas distribusi apa adanya, dengan header keamanan aktif. Bukan set_content, bukan aset ditanamkan.',
    'environment': {'browser': 'Chromium ' + version, 'user_agent': ua, 'mode': 'headless', 'os': 'Linux (kontainer)', 'server': 'pratinjau_lokal.py (Range/206, 404.html, MIME eksplisit, header keamanan)'},
    'limits': ['Viewport ponsel/tablet = emulasi pada Chromium desktop, bukan perangkat fisik.', 'Safari/iOS, Chrome Android nyata, dan Firefox tidak diuji (browser tidak dapat dipasang di lingkungan ini).',
               'Pembaca layar tidak dijalankan.', 'Server loopback, bukan hosting produksi; angka performa adalah pengukuran lab.'] + (['Build fixture dengan host .test: layanan akun nyata tidak dihubungi.'] if args.fixture else []),
    'site_tree_sha256': core.tree_hash(SITE), 'counts': counts, 'results': results, 'measurements': measure}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'BROWSER[{TAG}]', counts)
sys.exit(0 if not counts['FAIL'] and not counts['ERROR'] else 1)
