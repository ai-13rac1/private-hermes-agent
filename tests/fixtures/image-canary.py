"""Controlled HTTP/TLS image destinations; never forwards requests externally."""
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl
import threading
from PIL import Image

buffer = io.BytesIO()
Image.new('RGB', (2, 2), 'blue').save(buffer, format='PNG')
PNG = buffer.getvalue()
EVENTS = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Query strings may contain fixture tokens; do not log URLs.

    def do_GET(self):
        if self.path == '/events':
            body, mime, code = json.dumps(EVENTS).encode(), 'application/json', 200
        else:
            EVENTS.append({'path': self.path, 'headers': dict(self.headers)})
            body, mime, code = PNG, 'image/png', 200
            if self.path.startswith('/redirect-private'):
                self.send_response(302)
                self.send_header('Location', 'http://10.203.83.3:8080/private-hop')
                self.end_headers()
                return
            if self.path.startswith('/redirect-other'):
                self.send_response(302)
                self.send_header('Location', 'http://other.test:8080/other-hop')
                self.end_headers()
                return
            if self.path.startswith('/redirect-same'):
                self.send_response(302)
                self.send_header('Location', '/image')
                self.end_headers()
                return
            if self.path.startswith('/loop'):
                self.send_response(302)
                self.send_header('Location', '/loop')
                self.end_headers()
                return
            if self.path.startswith('/stream-huge'):
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.end_headers()
                try:
                    for _ in range(26):
                        self.wfile.write(b'x' * (1024 * 1024))
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            if self.path.startswith('/active'):
                body = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
                mime = 'image/svg+xml'
            if self.path.startswith('/false-type'):
                body = b'<html><script>alert(1)</script></html>'
            if self.path.startswith('/huge'):
                self.send_response(200)
                self.send_header('Content-Length', str(26 * 1024 * 1024))
                self.end_headers()
                return
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


for port in (8080, 8337, 8000, 9120):
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
server = ThreadingHTTPServer(('0.0.0.0', 8443), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/run/test-tls/cert.pem', '/run/test-tls/key.pem')
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
