from pathlib import Path
from bs4 import BeautifulSoup
import re,base64,mimetypes
ROOT=Path(__file__).resolve().parents[1]

def datauri(path):
 path=Path(path);m=mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
 return 'data:'+m+';base64,'+base64.b64encode(path.read_bytes()).decode()

def inline_html(path,with_media=True,with_js=True):
 path=Path(path);root=path.parent;s=BeautifulSoup(path.read_text(),'html.parser')
 for tag in s.find_all('link'):
  href=tag.get('href','')
  if not href or href.startswith(('http','data:')):continue
  p=(root/href).resolve()
  if not p.exists():continue
  if 'stylesheet' in tag.get('rel',[]):
   css=p.read_text()
   css=re.sub(r'url\([\'"]?([^\)\'\"]+)[\'"]?\)',lambda m:'url("'+datauri(p.parent/m.group(1))+'")' if (p.parent/m.group(1)).is_file() else m.group(0),css)
   style=s.new_tag('style');style.string=css;tag.replace_with(style)
  else:tag.decompose()
 for tag in s.find_all('script',src=True):
  p=root/tag['src']
  if with_js:
   content=p.read_text();tag.attrs={};tag.string=content
  else:tag.decompose()
 if not with_js:
  for tag in s.find_all('script'):
   if tag.get('type')!='application/ld+json':tag.decompose()
 for tag in s.find_all(['img','video','source']):
  for attr in ['src','poster']:
   value=tag.get(attr)
   if value and not value.startswith(('data:','http')):
    p=(root/value).resolve()
    if p.is_file() and (with_media or p.suffix!='.mp4'):tag[attr]=datauri(p)
  if tag.has_attr('srcset'):
   tag['srcset']=', '.join(datauri(root/item.strip().split()[0])+' '+item.strip().split()[1] for item in tag['srcset'].split(','))
 return str(s)

