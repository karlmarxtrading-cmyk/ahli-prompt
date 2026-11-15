#!/usr/bin/env python3
"""Pemeriksaan source final; tidak menyimpulkan kemampuan backend dari HTML."""
from pathlib import Path
from bs4 import BeautifulSoup
import json, re, hashlib, subprocess, csv, importlib.util, tempfile, shutil, sys
ROOT=Path(__file__).resolve().parents[1]; WEB=ROOT/'website'; OUT=ROOT/'qa/hasil';OUT.mkdir(exist_ok=True)
results=[]
def check(name,condition,detail='',status=None):
 results.append({'test':name,'status':status or ('PASS' if condition else 'FAIL'),'detail':detail})
def norm(s):return ' '.join(s.split())
s=BeautifulSoup((WEB/'index.html').read_text(),'html.parser')
check('Canon 01 persis',norm(s.h1.get_text(' ',strip=True))=='Kunci DNA Brand kamu untuk hasil generate yang selalu konsisten.')
check('Canon 02 persis',norm(s.select_one('#video-title').get_text(' ',strip=True))=='Cukup satu klik: hasilkan estetika produk menjadi prompt siap pakai.')
check('Satu H1',len(s.find_all('h1'))==1)
check('Bahasa Indonesia',s.html.get('lang')=='id')
check('Hasil foto dan video mendahului masalah',[x.get('id') for x in s.select('main > section')][:3]==['beranda','hasil-video','ide'])
text=norm(s.main.get_text(' ',strip=True))
check('Tidak ada contoh kode/prompt di homepage',not s.main.select('code, pre, .editor, .learn-illustration, .guide-illustration, .sv-prompt'))
check('Tidak ada tutorial operasional',all(x not in text.lower() for x in ['three-quarter','key fill rim','langkah 3 dari 6','no text or logo','kamera 45°','belajar sambil membuat']))
check('Tidak ada testimonial palsu',not s.main.select('blockquote'))
check('Tidak ada form atau penyimpanan akun palsu',not s.select('form,input[type=password]') and 'localStorage' not in (WEB/'js/main.js').read_text())
check('Dua seri aset terpisah',bool(s.select_one('#case-kosmetik') and s.select_one('#case-kuliner')))
manifest=json.loads((ROOT/'bukti/ASET_MANIFEST.json').read_text())
for r in manifest['images']:
 check('Aset gambar sumber '+str(r['id'])+' terpakai',any(t.get('src')==r['variants'][-1]['url'] for t in s.select('img')))
check('Empat video baru',len(s.find_all('video'))==4)
for v in s.find_all('video'):
 check('Kontrol native '+v['id'],v.has_attr('controls') and v.has_attr('playsinline') and v.get('preload')=='none' and not v.has_attr('autoplay') and not v.has_attr('loop'))
 check('Deskripsi video '+v['id'],s.find(id=v.get('aria-describedby')) is not None)
 check('Fallback video '+v['id'],s.find('a',href=v.source['src']) is not None)
for m in manifest['videos']:
 p=WEB/m['website_url'];check('Video identik sumber '+str(m['id']),hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'])
 completed=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 check('Decode penuh audio/video '+str(m['id']),completed.returncode==0,completed.stderr.decode()[:400])
check('CSS dasar investor tidak berubah',(WEB/'css/styles.css').read_bytes()==(ROOT/'bukti/source_sebelum/css/styles.css').read_bytes())
check('Perubahan CSS dipisahkan',(WEB/'css/sales.css').is_file())
urls=[]
for page in list(WEB.glob('*.html'))+list((ROOT/'dokumentasi_internal').glob('*.html')):
 soup=BeautifulSoup(page.read_text(),'html.parser'); ids=[t['id'] for t in soup.find_all(id=True)]
 check('ID unik: '+page.name,len(ids)==len(set(ids)))
 check('H1 tunggal: '+page.name,len(soup.find_all('h1'))==1)
 for t in soup.find_all(True):
  for attr in ['src','href','poster']:
   url=t.get(attr)
   if not url or url.startswith(('http:','https:','data:','mailto:','tel:')):continue
   if url.startswith('#'):
    check('Anchor '+page.name+url,url[1:] in ids)
   else:
    part=url.split('#')[0];p=(WEB/part.lstrip('/')) if part.startswith('/') else page.parent/part
    check('Resource '+page.name+' -> '+url,p.exists())
    if part and not part.endswith('/') and p.is_file():urls.append(str(p.resolve()))
 for t in soup.select('img'):
  check('Alt gambar '+page.name+': '+t.get('alt','')[:24],bool(t.get('alt')) and t.has_attr('width') and t.has_attr('height'))
 for t in soup.find_all(srcset=True):
  for item in t['srcset'].split(','):
   rel=item.strip().split()[0];check('Srcset '+rel,(page.parent/rel).is_file())
check('CTA menuju halaman akses yang ada',all(a['href']=='daftar.html' for a in s.select('[data-register-link]')))
entry=BeautifulSoup((WEB/'daftar.html').read_text(),'html.parser')
check('Halaman akses jujur',not entry.select_one('[data-registration-closed]').has_attr('hidden') and entry.select_one('[data-registration-open]').has_attr('hidden') and not entry.select('form'))
check('Status akun terlihat di homepage','akses akun segera hadir' in text.lower())
check('Pratinjau tidak diindeks sebelum rilis',s.find('meta',attrs={'name':'robots'})['content']=='noindex, follow')
check('JS syntax',subprocess.run(['node','--check',str(WEB/'js/main.js')],stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode==0)
for script in ['tools/aktifkan_rilis.py','tools/gate_rilis.py','pratinjau_lokal.py']:
 check('Python compile '+script,subprocess.run([sys.executable,'-m','py_compile',str(ROOT/script)],stderr=subprocess.PIPE).returncode==0)
sys.path.insert(0,str(ROOT/'tools'))
from aktifkan_rilis import validate_url, apply
from gate_rilis import assess
for bad in ['javascript:alert(1)','http://site.com/register','https://example.com/register','https://user:pass@domain.com/','https://jago.invalid/register','https://domain.com/\nregister']:
 try:validate_url(bad,'test'); valid=False
 except ValueError:valid=True
 check('Penolakan URL tidak aman/contoh: '+repr(bad),valid)
config=json.loads((ROOT/'konfigurasi/rilis.json').read_text())
check('Gerbang rilis tidak PASS palsu',assess(config)['status']=='NOT_READY_FOR_PUBLIC_RELEASE')
with tempfile.TemporaryDirectory() as td:
 root=Path(td);shutil.copytree(WEB,root/'website')
 fixture={'registration_url':'https://akun.brand-verifikasi.co.id/register','login_url':'https://akun.brand-verifikasi.co.id/login','site_url':'https://brand-verifikasi.co.id','public_release_approved':False}
 apply(root,fixture,True)
 a=BeautifulSoup((root/'website/index.html').read_text(),'html.parser');b=BeautifulSoup((root/'website/daftar.html').read_text(),'html.parser')
 check('Helper aktivasi mengubah CTA pada fixture',all(t['href']==fixture['registration_url'] for t in a.select('[data-register-link]')),'Fixture lokal; URL tidak dikunjungi dan bukan layanan resmi.')
 check('Helper aktivasi membuka tautan akun pada fixture',b.select_one('[data-registration-closed]').has_attr('hidden') and not b.select_one('[data-registration-open]').has_attr('hidden') and b.select_one('[data-registration-destination]')['href']==fixture['registration_url'])
 check('Helper tidak membuka indeks tanpa persetujuan',a.find('meta',attrs={'name':'robots'})['content']=='noindex, follow')
 check('Helper memasang canonical pada fixture',a.select_one('link[rel=canonical]')['href']==fixture['site_url']+'/')
counts={k:sum(r['status']==k for r in results) for k in ['PASS','FAIL','BLOCKED']}
(OUT/'static-results.json').write_text(json.dumps({'scope':'Source final, media full decode, activation helper on isolated fixture only','counts':counts,'results':results},ensure_ascii=False,indent=2))
print('STATIC',counts)
for r in results:
 if r['status']=='FAIL':print('FAIL',r['test'],r['detail'])
