"""Live disposable onion rendezvous/authentication check using a separate Tor."""
import http.client
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time

address, password = json.load(sys.stdin)


def exact(stream, count):
    result = b''
    while len(result) < count:
        data = stream.recv(count - len(result))
        if not data:
            raise OSError('Tor client connection closed')
        result += data
    return result


def request(method, path, data=None, cookie=''):
    with socket.create_connection(('127.0.0.1', 19050), timeout=45) as stream:
        stream.sendall(b'\x05\x01\x00')
        assert exact(stream, 2) == b'\x05\x00'
        name = address.encode()
        stream.sendall(b'\x05\x01\x00\x03' + bytes([len(name)]) + name + struct.pack('!H', 80))
        header = exact(stream, 4)
        if header[1] != 0:
            raise OSError('Tor rendezvous pending, SOCKS status ' + str(header[1]))
        size = {1: 4, 4: 16}.get(header[3])
        if size is None:
            size = exact(stream, 1)[0]
        exact(stream, size + 2)
        body = json.dumps(data).encode() if data is not None else b''
        headers = (f'{method} {path} HTTP/1.1\r\nHost: {address}\r\nOrigin: http://{address}\r\n'
                   f'Connection: close\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n')
        if cookie:
            headers += 'Cookie: ' + cookie + '\r\n'
        stream.sendall(headers.encode() + b'\r\n' + body)
        response = http.client.HTTPResponse(stream)
        response.begin()
        status, cookies = response.status, response.headers.get_all('Set-Cookie', [])
        response.read()
        return status, cookies


with tempfile.TemporaryDirectory() as temporary:
    with (Path(temporary) / 'tor.log').open('w') as output:
        child = subprocess.Popen(['tor', '--DataDirectory', temporary + '/state', '--SocksPort', '19050',
                                  '--Log', 'notice stdout'], stdout=output, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 600  # Test deadline, not deployment policy.
            while True:
                if child.poll() is not None:
                    raise RuntimeError('Separate Tor client exited before rendezvous')
                try:
                    status, _ = request('GET', '/login')
                    assert status == 200, status
                    break
                except OSError as error:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Live rendezvous test deadline exceeded') from error
                    print('Waiting for disposable onion publication/client circuit', flush=True)
                    time.sleep(5)
            assert request('GET', '/api/config')[0] in (401, 403)
            status, cookies = request('POST', '/auth/password-login',
                {'provider': 'basic', 'username': 'admin', 'password': password})
            assert status == 200, status
            session = '; '.join(value.split(';')[0] for value in cookies)
            assert request('GET', '/api/config', cookie=session)[0] == 200
            print('PASS: separate Tor client live onion rendezvous, authentication and protected API', flush=True)
        finally:
            child.terminate()
            child.wait()
