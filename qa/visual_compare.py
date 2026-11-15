#!/usr/bin/env python3
"""Bandingkan tampilan 1.4.0 dengan baseline 1.3.0 per section (Chromium, HTTP loopback).

  python3 qa/visual_compare.py --baseline /path/ke/ekstrak-1.3.0/website

Baseline 1.3.0 tidak disertakan ulang di paket ini (hindari arsip berulang); arahkan --baseline ke folder
website/ hasil ekstrak JAGO_PROMPT_REKONSTRUKSI_SALES_1.3.0_20261115.zip. Hasil: qa/hasil/visual-compare.json
dan gambar selisih di qa/screenshot/banding_*.png. Ini bukti perbandingan, BUKAN persetujuan investor.
"""
import argparse, json, sys, threading
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
import pratinjau_lokal, rilis_core as core  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--baseline', required=True); a = ap.parse_args()
SHOTS = ROOT / 'qa' / 'screenshot'; SHOTS.mkdir(parents=True, exist_ok=True)
servers = {}
for name, d in (('baseline', a.baseline), ('final', ROOT / 'website')):
    s = pratinjau_lokal.make_server(str(d), 0); threading.Thread(target=s.serve_forever, daemon=True).start(); servers[name] = s
SECTIONS = ['beranda', 'hasil-video', 'ide', 'fitur', 'arahan-foto', 'arahan-video', 'pemula', 'cerita', 'mulai']
rows = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for (w, h) in [(1440, 900), (390, 844)]:
        shots = {}; boxes = {}
        for name, s in servers.items():
            ctx = b.new_context(viewport={'width': w, 'height': h}, reduced_motion='reduce'); p = ctx.new_page()
            p.goto(f'http://127.0.0.1:{s.server_address[1]}/'); p.wait_for_load_state('networkidle'); p.evaluate('document.fonts.ready')
            total = p.evaluate('document.documentElement.scrollHeight'); y = 0
            while y < total:
                p.evaluate(f'scrollTo(0,{y})'); p.wait_for_timeout(100); y += h
            p.wait_for_load_state('networkidle'); p.evaluate('scrollTo(0,0)'); p.wait_for_timeout(300)
            p.evaluate("document.querySelector('[data-header]').style.position = 'static'; document.querySelector('[data-to-top]').style.display = 'none'")
            for ident in SECTIONS + ['footer']:
                el = p.locator('.site-footer' if ident == 'footer' else '#' + ident)
                path = SHOTS / f'_tmp_{name}_{ident}_{w}.png'; el.screenshot(path=str(path)); shots[(name, ident)] = path
                boxes[(name, ident)] = el.evaluate("""root => { const o = root.getBoundingClientRect(); return [...root.querySelectorAll('*')].filter(e => !e.closest('details:not([open])') || e.tagName === 'SUMMARY' || e.matches('details')).map(e => { const r = e.getBoundingClientRect(); return [e.tagName + '.' + String(e.className && e.className.baseVal === undefined ? e.className : ''), +(r.left - o.left).toFixed(1), +(r.top - o.top).toFixed(1), +r.width.toFixed(1), +r.height.toFixed(1)]; }); }""")
            ctx.close()
        for ident in SECTIONS + ['footer']:
            A, B = Image.open(shots[('baseline', ident)]).convert('RGB'), Image.open(shots[('final', ident)]).convert('RGB')
            row = {'section': ident, 'viewport': f'{w}x{h}', 'baseline_size': A.size, 'final_size': B.size}
            ba, bb = boxes[('baseline', ident)], boxes[('final', ident)]
            row['elements'] = [len(ba), len(bb)]
            if len(ba) == len(bb) and [x[0] for x in ba] == [x[0] for x in bb]:
                row['layout_max_delta_px'] = max((abs(x[k] - y[k]) for x, y in zip(ba, bb) for k in (1, 2, 3, 4)), default=0)
            else:
                row['layout_max_delta_px'] = None
            if A.size == B.size:
                diff = ImageChops.difference(A, B).convert('L').point(lambda v: 255 if v > 12 else 0)
                changed = diff.histogram()[255]
                row['changed_pixel_pct'] = round(100 * changed / (A.size[0] * A.size[1]), 3)
                soft = ImageChops.difference(A.filter(ImageFilter.GaussianBlur(2)), B.filter(ImageFilter.GaussianBlur(2))).convert('L').point(lambda v: 255 if v > 24 else 0)
                row['changed_after_blur_pct'] = round(100 * soft.histogram()[255] / (A.size[0] * A.size[1]), 3)
                if changed:
                    box = diff.getbbox(); row['changed_bbox'] = box
                    side = Image.new('RGB', (A.size[0] * 2 + 10, A.size[1]), 'white'); side.paste(A, (0, 0)); side.paste(B, (A.size[0] + 10, 0))
                    side.save(SHOTS / f'banding_{ident}_{w}x{h}.png')
            else:
                row['changed_pixel_pct'] = None
                row['note'] = 'ukuran section berubah'
                hh = max(A.size[1], B.size[1]); side = Image.new('RGB', (A.size[0] + B.size[0] + 10, hh), 'white'); side.paste(A, (0, 0)); side.paste(B, (A.size[0] + 10, 0))
                side.save(SHOTS / f'banding_{ident}_{w}x{h}.png')
            rows.append(row)
            for n in ('baseline', 'final'):
                shots[(n, ident)].unlink()
    version = b.version; b.close()
for s in servers.values():
    s.shutdown(); s.server_close()
identical = [r for r in rows if r['changed_pixel_pct'] == 0]
same_layout = [r for r in rows if r['layout_max_delta_px'] is not None and r['layout_max_delta_px'] <= 1.0]
out = {'method': 'Tangkapan elemen per section, header statis, reduced motion, ambang selisih kanal 12/255. Chromium ' + version,
       'baseline': 'website/ dari JAGO_PROMPT_REKONSTRUKSI_SALES_1.3.0_20261115.zip', 'baseline_tree_sha256': core.tree_hash(Path(a.baseline)),
       'final_tree_sha256': core.tree_hash(ROOT / 'website'), 'pixel_identical': len(identical), 'layout_within_1px': len(same_layout), 'total': len(rows),
       'reading': 'layout_max_delta_px = pergeseran terbesar kotak elemen terhadap section. Selisih piksel kecil dengan layout sama berasal dari anti-alias teks pada posisi sub-piksel.', 'rows': rows}
(ROOT / 'qa/hasil/visual-compare.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('VISUAL piksel identik', len(identical), '· layout ≤1px', len(same_layout), 'dari', len(rows))
for r in rows:
    if r['layout_max_delta_px'] is None or r['layout_max_delta_px'] > 1.0: print('  layout berubah', {k: r[k] for k in ('section', 'viewport', 'elements', 'layout_max_delta_px', 'baseline_size', 'final_size')})
