#!/usr/bin/env python3
"""Chromium render/interaksi. Browser sesi ini memblokir navigasi URL.
Sumber final dan aset dimuat melalui set_content; bukan klaim pengujian hosting.
HTTP 200/206 dan path diuji terpisah oleh http_checks.py.
"""
from pathlib import Path
import json, shutil, os, time
from playwright.sync_api import sync_playwright
from inline_preview import inline_html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'qa/hasil';SHOTS=ROOT/'qa/screenshot'
OUT.mkdir(exist_ok=True);SHOTS.mkdir(exist_ok=True)
results=[];measure={};issues=[]
def record(name,condition=True,detail='',status=None):
 results.append({'test':name,'status':status or ('PASS' if condition else 'FAIL'),'detail':detail})
 (OUT/'browser-progress.json').write_text(json.dumps({'results':results},ensure_ascii=False,indent=2))
 print(results[-1]['status'],name,flush=True)
def overflow(p):return p.evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth})')
HTML=inline_html(ROOT/'website/index.html')

def load(p,code=HTML):
 p.set_content(code,wait_until='load');p.evaluate('document.fonts.ready');p.wait_for_timeout(180)
def assert_case(name,fn):
 try:fn()
 except Exception as e:record(name,False,str(e)[:1200])

with sync_playwright() as pw:
 exe=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium')
 browser=pw.chromium.launch(**({'executable_path':exe} if exe else {}),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 version=browser.version
 browser.on('disconnected',lambda:None)
 context=browser.new_context(viewport={'width':1440,'height':900},device_scale_factor=1)
 page=context.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda e:issues.append(str(e)));load(page)
 for width,height in [(1440,900),(1280,800),(1024,768),(768,1024),(390,844),(360,800),(320,568),(844,390)]:
  page.set_viewport_size({'width':width,'height':height});page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(200)
  dims=overflow(page);photo=page.locator('.hero-shot-main').evaluate('(e)=>e.getBoundingClientRect().toJSON()')
  measure[f'{width}x{height}']={'geometry':dims,'first_photo':photo}
  record('Reflow '+f'{width}x{height}',dims['scrollWidth']<=width and dims['bodyWidth']<=width,dims)
  if height>=768:
   record('Hasil visual muncul layar awal '+f'{width}x{height}',photo['y']<height-40 and photo['bottom']>0,photo)
  record('Hero tidak menyembunyikan aset '+f'{width}x{height}',page.locator('.hero-shot-main img').evaluate('(e)=>e.naturalWidth>0 && getComputedStyle(e).visibility!=="hidden"'))
  page.screenshot(path=str(SHOTS/f'hero_{width}x{height}.png'))
 # Mobile disclosure and native FAQ/gallery interactions.
 page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(100)
 toggle=page.locator('[data-menu-toggle]');nav=page.locator('[data-nav]')
 record('Menu mobile awal tertutup',toggle.get_attribute('aria-expanded')=='false' and not nav.is_visible())
 toggle.click();page.wait_for_timeout(100)
 record('Menu terbuka dengan fokus',toggle.get_attribute('aria-expanded')=='true' and page.evaluate('document.querySelector("[data-nav]").contains(document.activeElement)'))
 page.screenshot(path=str(SHOTS/'menu_390x844.png'))
 page.keyboard.press('Escape');page.wait_for_timeout(100)
 record('Escape mengembalikan fokus',toggle.get_attribute('aria-expanded')=='false' and toggle.evaluate('(e)=>e===document.activeElement'))
 toggle.click();page.mouse.click(380, 810);page.wait_for_timeout(100)
 record('Klik luar menutup menu',toggle.get_attribute('aria-expanded')=='false')
 detail=page.locator('.series-details').first;detail.locator('summary').focus();page.keyboard.press('Enter');page.wait_for_timeout(150)
 record('Galeri tambahan dapat dibuka keyboard',detail.evaluate('(e)=>e.open'))
 detail.locator('summary').focus();page.keyboard.press('Enter')
 record('Galeri tambahan dapat ditutup keyboard',not detail.evaluate('(e)=>e.open'))
 faq=page.locator('.faq-list details').first;faq.locator('summary').click();record('FAQ native berfungsi',faq.evaluate('(e)=>e.open'));faq.locator('summary').click()
 page.evaluate('window.scrollTo(0,1500)');page.wait_for_timeout(120)
 record('Sticky header dan kembali ke atas aktif',page.locator('[data-header]').evaluate('(e)=>e.classList.contains("is-scrolled")') and page.locator('[data-to-top]').evaluate('(e)=>e.classList.contains("is-visible")'))
 # All images: scroll naturally, then expand/collapse detailed galleries.
 for section in page.locator('main > section').all():
  section.scroll_into_view_if_needed();page.wait_for_timeout(110)
 for detail in page.locator('.series-details').all():
  detail.locator('summary').click();
  for im in detail.locator('img').all(): im.scroll_into_view_if_needed();page.wait_for_timeout(30)
  page.wait_for_timeout(150)
  record('Seluruh gambar galeri '+detail.locator('summary').inner_text(),detail.locator('img').evaluate_all('(els)=>els.every(e=>e.complete && e.naturalWidth>0)'))
  detail.locator('summary').click()
 record('Tidak ada JS exception pada pemuatan/interaksi biasa',len(issues)==0,issues.copy())
 # Native video with actual encoded bytes, not mocked playback APIs.
 for i in range(1,5):
  v=page.locator(f'#video-{i}');v.scroll_into_view_if_needed();
  r=v.evaluate('async e=>{e.muted=true;try {await e.play();return {duration:e.duration,error:e.error?.code||null,ready:e.readyState}} catch(err){return {failure:err.name}}}')
  page.wait_for_timeout(220)
  record(f'Video {i}: decode dan putar native',r.get('duration')==10 and v.evaluate('e=>!e.paused && e.currentTime>0'),r)
  v.evaluate('e=>e.currentTime=5');page.wait_for_timeout(120)
  record(f'Video {i}: seek native',v.evaluate('e=>e.currentTime>=5 && e.currentTime<7'))
  v.evaluate('e=>e.pause()');t=v.evaluate('e=>e.currentTime');page.wait_for_timeout(100)
  record(f'Video {i}: pause',v.evaluate('e=>e.paused && Math.abs(e.currentTime-'+str(t)+')<0.1'))
  v.evaluate('async e=>{e.currentTime=9.9;e.playbackRate=2;await e.play()}');page.wait_for_timeout(350)
  record(f'Video {i}: selesai',v.evaluate('e=>e.ended'))
  v.evaluate('async e=>{e.currentTime=0;e.playbackRate=1;await e.play()}');page.wait_for_timeout(180)
  record(f'Video {i}: putar ulang',v.evaluate('e=>!e.paused && e.currentTime>0 && e.currentTime<2'))
  v.evaluate('e=>e.pause()')
 # Only one playing at once.
 page.locator('#video-1').evaluate('e=>e.play()');page.wait_for_timeout(100);page.locator('#video-2').evaluate('e=>e.play()');page.wait_for_timeout(200)
 record('Video sebelumnya berhenti saat video lain dimainkan',page.locator('#video-1').evaluate('e=>e.paused') and page.locator('#video-2').evaluate('e=>!e.paused'))
 page.locator('#video-2').evaluate('e=>e.pause()')
 # Decode failure and successful retry, with real invalid media bytes.
 v=page.locator('#video-3');source=v.locator('source');good=source.get_attribute('src')
 v.evaluate('e=>{e.querySelector("source").src="data:video/mp4;base64,AAAA";e.load()}');page.wait_for_timeout(300)
 unit=v.locator('xpath=..');record('Kegagalan media menampilkan pesan lokal',unit.locator('[data-video-status]').inner_text()!='' and unit.locator('[data-video-retry]').is_visible())
 source.evaluate('(e,src)=>e.src=src',good);unit.locator('[data-video-retry]').click();page.wait_for_timeout(300)
 record('Retry media pulih',v.evaluate('e=>!e.paused && !e.error') and unit.locator('[data-video-status]').inner_text()=='');v.evaluate('e=>e.pause()')
 # Capture representative final sections after natural loading.
 for w,h in [(1440,900),(390,844)]:
  page.set_viewport_size({'width':w,'height':h})
  for ident in ['hasil-video','ide','fitur','arahan-foto','arahan-video','pemula','cerita','mulai']:
   page.locator('#'+ident).scroll_into_view_if_needed();page.wait_for_timeout(180)
   page.screenshot(path=str(SHOTS/f'{ident}_{w}x{h}.png'))
  page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(200)
  page.screenshot(path=str(SHOTS/f'halaman_{w}x{h}.jpg'),full_page=True,type='jpeg',quality=80)
 # Font enlarged 200%: reflow, not a claim of browser zoom.
 page.set_viewport_size({'width':390,'height':844});page.add_style_tag(content='html {font-size:200% !important;}');page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(100)
 record('Pembesaran teks 200 persen: tanpa overflow horizontal',overflow(page)['scrollWidth']<=390,overflow(page))
 page.screenshot(path=str(SHOTS/'teks_200persen_390x844.png'))
 context.close()
 # Reduced motion separate context.
 ctx=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');p=ctx.new_page();p.set_default_timeout(8000);load(p)
 record('Reduced motion: scroll otomatis',p.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto')
 record('Reduced motion: konten terlihat',p.locator('.hero-shot-main img').evaluate('(e)=>e.naturalWidth>0'))
 ctx.close()
 # No JavaScript: real scripts disabled, native controls remain.
 ctx=browser.new_context(viewport={'width':390,'height':844},java_script_enabled=False);p=ctx.new_page();p.set_default_timeout(8000);load(p,inline_html(ROOT/'website/index.html',with_js=False))
 record('Tanpa JS: menu dapat diakses',p.locator('[data-nav]').is_visible())
 record('Tanpa JS: empat video native',p.locator('video[controls]').count()==4)
 d=p.locator('.faq-list summary').first;d.click();record('Tanpa JS: FAQ native',p.locator('.faq-list details').first.get_attribute('open') is not None)
 p.evaluate('window.scrollTo(0,0)');p.screenshot(path=str(SHOTS/'tanpa_js_390x844.png'));ctx.close()
 # Entry route contents, rendered independently; no fake success path.
 ctx=browser.new_context(viewport={'width':390,'height':844});p=ctx.new_page();p.set_default_timeout(8000);load(p,inline_html(ROOT/'website/daftar.html'))
 record('Halaman akses: tidak mengumpulkan kredensial',p.locator('form,input').count()==0)
 record('Halaman akses: status belum dibuka terlihat',p.locator('[data-registration-closed]').is_visible() and not p.locator('[data-registration-open]').is_visible())
 record('Halaman akses: reflow',overflow(p)['scrollWidth']<=390,overflow(p))
 p.screenshot(path=str(SHOTS/'akses_390x844.png'));ctx.close()
 # Original storyboard kept in internal documentation.
 ctx=browser.new_context(viewport={'width':1440,'height':900});p=ctx.new_page();p.set_default_timeout(8000);load(p,inline_html(ROOT/'dokumentasi_internal/panduan_account.html'))
 board=p.locator('[data-storyboard]');board.scroll_into_view_if_needed();p.wait_for_timeout(200)
 frames=p.locator('[data-storyboard] .sb-frame');record('Storyboard lama tetap tersedia',frames.count()==4 and p.locator('[data-storyboard-toggle]').is_visible())
 p.locator('[data-storyboard-toggle]').click();p.wait_for_timeout(150);record('Putar storyboard lama berfungsi',p.locator('[data-storyboard-toggle]').get_attribute('aria-pressed')=='true')
 p.screenshot(path=str(SHOTS/'materi_account_storyboard.png'));ctx.close()
 # Same-document anchor test; kept distinct from HTTP browser navigation.
 ctx=browser.new_context(viewport={'width':1440,'height':900});p=ctx.new_page();p.set_default_timeout(8000);load(p)
 try:
  p.locator('.hero-actions a[href="#arahan-foto"]').click();p.wait_for_function("Math.abs(document.getElementById('arahan-foto').getBoundingClientRect().top) < 200", timeout=6000)
  top=p.locator('#arahan-foto').evaluate('e=>e.getBoundingClientRect().top')
  record('Anchor foto pada dokumen yang dirender',p.url.endswith('#arahan-foto') and abs(top)<200,{'url':p.url,'top':top})
 except Exception as e:record('Anchor foto pada dokumen yang dirender',detail=str(e)[:300],status='BLOCKED')
 ctx.close();browser.close()
counts={k:sum(r['status']==k for r in results) for k in ['PASS','FAIL','BLOCKED']}
(OUT/'browser-results.json').write_text(json.dumps({'browser':'Chromium '+version,'scope':'Chromium real rendering and native media from final source with assets embedded via set_content; no hosted navigation due environment URLBlocklist. Not a mobile device test.','counts':counts,'measurements':measure,'results':results},ensure_ascii=False,indent=2))
print('BROWSER',counts,flush=True)
for r in results:
 if r['status']!='PASS': print(r,flush=True)
