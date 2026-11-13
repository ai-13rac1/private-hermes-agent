"""Test-only HTTP byte proxy into the Tor namespace; no deployment listener."""
from contextlib import contextmanager
import os
from pathlib import Path
import select
import socket
import socketserver
import subprocess
import sys
import threading
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from deployment import engine_command


class Bridge(socketserver.StreamRequestHandler):
    rbufsize = 0

    def handle(self):
        try:
            self.relay()
        except (ConnectionResetError, BrokenPipeError):
            pass  # Browsers abandon speculative and navigation connections.

    def relay(self):
        container, address = self.server.container, self.server.address
        socks = self.connection.recv(1, socket.MSG_PEEK) == b'\x05'
        if socks:
            version, count = self.rfile.read(2)
            methods = self.rfile.read(count)
            self.connection.sendall(b'\x05\x00' if 0 in methods else b'\x05\x02')
            if 0 not in methods:
                assert self.rfile.read(1) == b'\x01'
                self.rfile.read(self.rfile.read(1)[0])
                self.rfile.read(self.rfile.read(1)[0])
                self.connection.sendall(b'\x01\x00')
            assert self.rfile.read(4) == b'\x05\x01\x00\x03'
            destination = self.rfile.read(self.rfile.read(1)[0]).decode()
            target_port = int.from_bytes(self.rfile.read(2), 'big')
            if destination != address or target_port != 80:
                self.connection.sendall(b'\x05\x05\x00\x01' + b'\x00' * 6)
                return  # Refuse background requests and HTTPS-first probes.
            self.connection.sendall(b'\x05\x00\x00\x01' + b'\x00' * 6)
        line = self.rfile.readline()
        if not line:
            return  # Browsers may abandon speculative proxy connections.
        method, target, protocol = line.decode().strip().split(' ', 2)
        tunnel = socks
        if method == 'CONNECT':
            if target != address + ':80':
                self.connection.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n')
                return
            while self.rfile.readline() not in (b'\r\n', b'\n', b''):
                pass
            self.connection.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            line = self.rfile.readline()
            if not line:
                return
            method, target, protocol = line.decode().strip().split(' ', 2)
            tunnel = True
        url = urlsplit(target)
        if not tunnel and (url.hostname != address or (url.port or 80) != 80 or url.scheme not in ('http', 'ws')):
            self.connection.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n')
            return
        path = url.path or '/'
        if url.query:
            path += '?' + url.query
        relay = '''import socket,sys,select,os
s=socket.create_connection(('10.203.86.3',8080))
while True:
 ready,_,_=select.select([s,sys.stdin.buffer],[],[])
 for source in ready:
  data=s.recv(65536) if source is s else os.read(0,65536)
  if not data: sys.exit(0)
  if source is s: os.write(1,data)
  else: s.sendall(data)
'''
        child = subprocess.Popen([*engine_command(), 'exec', '-i', '--user', '101:102', container,
                                  'python3', '-c', relay], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            child.stdin.write(f'{method} {path} {protocol}\r\n'.encode()); child.stdin.flush()
            while True:
                ready, _, _ = select.select([self.connection, child.stdout], [], [])
                for source in ready:
                    data = self.connection.recv(65536) if source is self.connection else os.read(child.stdout.fileno(), 65536)
                    if not data:
                        return
                    if source is self.connection:
                        child.stdin.write(data); child.stdin.flush()
                    else:
                        self.connection.sendall(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            child.stdin.close()
            child.terminate()
            child.wait()


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True



@contextmanager
def proxy(container, address):
    with Server(('127.0.0.1', 0), Bridge) as server:
        server.container, server.address = container, address
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield server.server_address[1]
        finally:
            server.shutdown()
