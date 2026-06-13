#!/usr/bin/env python3
"""Local preview server for the built site (dist/).

Over `python -m http.server` it (a) sends no-store headers so you always see the
latest `python3 build.py` output, and (b) registers the correct MIME types for
.svg / .woff2 / .webmanifest, which some Python builds don't know (serving them
as application/octet-stream can stop the browser from using them).

    python3 build.py && python3 serve.py     # http://localhost:8000
"""
import http.server
import mimetypes
import socketserver
import sys
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIST = str(Path(__file__).resolve().parent / "dist")

for ext, mime in {
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".webmanifest": "application/manifest+json",
}.items():
    mimetypes.add_type(mime, ext)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class Server(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with Server(("", PORT), Handler) as httpd:
        print(f"Serving {DIST} at http://localhost:{PORT}  (Ctrl+C to stop)")
        httpd.serve_forever()
