#!/usr/bin/env python3
"""Server pratinjau lokal (pustaka standar Python 3 saja). Bukan server produksi.

Meniru perilaku hosting statis yang relevan untuk website ini:
  - Range/206 untuk video (seek), 416 untuk rentang tidak valid
  - 404.html dengan status 404 untuk path yang tidak ada
  - MIME eksplisit untuk .webp .woff2 .vtt .mp4
  - opsional --security-headers: header pada konfigurasi/hosting/header_keamanan.json

Pakai:  python3 pratinjau_lokal.py                      → http://127.0.0.1:8080/  (folder website/)
        python3 pratinjau_lokal.py --dir dist/staging --port 9000 --security-headers
"""
import argparse, json, os, re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
MIME = {'.webp': 'image/webp', '.woff2': 'font/woff2', '.vtt': 'text/vtt; charset=utf-8', '.mp4': 'video/mp4',
        '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
        '.json': 'application/json', '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml', '.svg': 'image/svg+xml'}


def load_security_headers():
    path = os.path.join(HERE, 'konfigurasi', 'hosting', 'header_keamanan.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)['headers']


class RangeHandler(SimpleHTTPRequestHandler):
    extra_headers = {}

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIME.get(ext) or super().guess_type(path)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        for k, v in self.extra_headers.items():
            self.send_header(k, v)
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        page = os.path.join(self.directory, '404.html')
        if code == 404 and os.path.isfile(page):
            with open(page, 'rb') as f:
                body = f.read()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def send_head(self):
        self._range = None
        header = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not header or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r'bytes=(\d*)-(\d*)$', header.strip())
        size = os.path.getsize(path)
        if not m or (m.group(1) == '' and m.group(2) == ''):
            return super().send_head()
        if m.group(1) == '':
            start, end = max(0, size - int(m.group(2))), size - 1
        else:
            start, end = int(m.group(1)), min(int(m.group(2) or size - 1), size - 1)
        if start >= size or start > end:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        f = open(path, 'rb')
        f.seek(start)
        self._range = (start, end)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        if not getattr(self, '_range', None):
            return super().copyfile(source, outputfile)
        remaining = self._range[1] - self._range[0] + 1
        while remaining > 0:
            chunk = source.read(min(65536, remaining))
            if not chunk:
                break
            try:
                outputfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                break
            remaining -= len(chunk)

    def log_message(self, *a):
        pass


def make_server(directory, port=0, security_headers=False):
    handler = type('Handler', (RangeHandler,), {'extra_headers': load_security_headers() if security_headers else {}})
    return ThreadingHTTPServer(('127.0.0.1', port), partial(handler, directory=directory))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--dir', default=os.path.join(HERE, 'website'))
    ap.add_argument('--security-headers', action='store_true')
    a = ap.parse_args()
    srv = make_server(os.path.abspath(a.dir), a.port, a.security_headers)
    print(f'Pratinjau: http://127.0.0.1:{srv.server_address[1]}/  (Ctrl+C untuk berhenti)', flush=True)
    try:
        srv.serve_forever()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
