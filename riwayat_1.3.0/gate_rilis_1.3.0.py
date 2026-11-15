#!/usr/bin/env python3
"""Gerbang rilis komersial, terpisah dari kelulusan tampilan dan HTML."""
import json
from pathlib import Path
from aktifkan_rilis import validate_url
ROOT=Path(__file__).resolve().parents[1]

def assess(config):
    gaps=[]
    for key in ['registration_url','site_url']:
        try:validate_url(config.get(key),key)
        except ValueError as e:gaps.append(str(e))
    for key,label in [('account_flow_verified','Pendaftaran/login layanan nyata belum terverifikasi'),('audio_review_completed','Isi audio dan kebutuhan caption empat video belum diverifikasi'),('media_publication_approved','Izin publikasi media belum dicatat'),('product_claims_verified','Klaim satu klik dan konsistensi hasil belum diuji pada produk nyata'),('public_release_approved','Persetujuan rilis publik belum dicatat')]:
        if config.get(key) is not True:gaps.append(label)
    return {'status':'READY_FOR_PUBLIC_RELEASE' if not gaps else 'NOT_READY_FOR_PUBLIC_RELEASE','gaps':gaps}
if __name__=='__main__':
    result=assess(json.loads((ROOT/'konfigurasi/rilis.json').read_text(encoding='utf-8')))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if not result['gaps'] else 2)
