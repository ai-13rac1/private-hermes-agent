"""Real socket destinations, redirects and DNS rebinding against isolated canaries."""
import http.client
import json
import socket
import time
from unittest.mock import patch
from hermes_cli import private_public_images as images

PUBLIC = '11.203.88.3'
lookups = []


def resolve(host, port, *args, **kwargs):
    lookups.append(host)
    addresses = [PUBLIC] if host in ('public.test', 'other.test') else ['10.203.83.3'] if host == 'host.docker.internal' else [host]
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (ip, port)) for ip in addresses]


def events():
    connection = http.client.HTTPConnection(PUBLIC, 8080, timeout=3)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    sock.connect((PUBLIC, 8080))
    connection.sock = sock
    connection.request('GET', '/events')
    response = connection.getresponse()
    result = json.loads(response.read())
    connection.close()
    return result


def refused(url, *, same_origin_only=False):
    try:
        images.fetch_image(url, same_origin_only=same_origin_only)
    except images.ImageRefused:
        return
    raise AssertionError('Unsafe or unsupported image was retrieved')


for attempt in range(60):
    try:
        events()
        break
    except OSError:
        time.sleep(.1)
else:
    raise RuntimeError('Controlled image server did not start')

with patch.object(images.socket, 'getaddrinfo', side_effect=resolve):
    for url in ('http://public.test:8080/image?fixture-token=private',
                'http://public.test:8080/redirect-same', 'https://public.test:8443/image'):
        data, mime = images.fetch_image(url)
        assert data.startswith(b'\x89PNG') and mime == 'image/png'
    # All requests used original Host, TLS validated public.test (not numeric IP).
    received = events()
    assert received[-1]['headers']['Host'] == 'public.test:8443'
    for event in received:
        assert not {'cookie', 'authorization', 'referer', 'proxy-authorization'} & {k.lower() for k in event['headers']}
    for url in ('http://127.0.0.1:9120/image', 'http://169.254.169.254/image',
                'http://10.203.83.3:8337/image', 'http://10.203.84.10:8000/image',
                'http://192.168.65.1/image', 'http://host.docker.internal/image',
                'http://2130706433/image', 'http://0177.0.0.1/image',
                'http://0x7f000001/image', 'http://[::1]/image', 'file:///etc/passwd',
                'http://user:password@public.test:8080/image', 'http://public.test:0/image',
                'http://public.test%00.invalid/image', 'http://public.test\\@127.0.0.1/image'):
        before = len(events())
        refused(url)
        assert len(events()) == before, 'Forbidden destination received a request'
    before = len(events())
    refused('http://public.test:8080/redirect-private')
    assert len(events()) == before + 1
    lookups.clear()
    before = len(events())
    refused('http://public.test:8080/redirect-other', same_origin_only=True)
    assert lookups == ['public.test'] and len(events()) == before + 1
    images.fetch_image('http://public.test:8080/redirect-other')
    assert events()[-1]['path'] == '/other-hop'
    for path in ('active', 'false-type', 'huge', 'stream-huge', 'loop'):
        refused('http://public.test:8080/' + path)

    before = len(events())
    refused('https://other.test:8443/image')  # Certificate is for public.test only.
    refused('http://public.test:8081/image')  # Dependency failure: no weaker retry.
    assert len(events()) == before
    images.fetch_image('http://public.test:8080/image')  # Ordinary retry remains usable.

# A DNS answer changes after validation: connecting must not ask DNS again.
calls = []
def rebinding(host, port, *args, **kwargs):
    calls.append(host)
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '',
             (PUBLIC if len(calls) == 1 else '10.203.83.3', port))]
with patch.object(images.socket, 'getaddrinfo', side_effect=rebinding):
    images.fetch_image('http://public.test:8080/image')
    assert calls == ['public.test']
    calls.clear()
    refused('http://public.test:8080/redirect-same')
    assert len(calls) == 2

# Reject a mixed public/private DNS set before any connection.
with patch.object(images.socket, 'getaddrinfo', return_value=[
    (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', (PUBLIC, 8080)),
    (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('10.203.83.3', 8080)),
]):
    before = len(events())
    refused('http://public.test:8080/image')
    assert len(events()) == before
print('PASS: real public HTTP/TLS sockets, Host/SNI, redirects, no credential headers, private/Teep/MCP denial, DNS pinning, raster/size rejection')

# Exercise the real native cookie-auth middleware and password provider, not a
# substitute auth gate. Only disposable credentials and temporary consent state.
from pathlib import Path
import secrets
import tempfile
from fastapi.testclient import TestClient
from hermes_cli import web_server
from hermes_cli import private_external_content as content
from hermes_cli.dashboard_auth import clear_providers, register_provider
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password

clear_providers()
register_provider(BasicAuthProvider(username='admin', password_hash=hash_password('fixture-password'),
                                    secret=secrets.token_bytes(32)))
app = web_server.app
app.state.auth_required = True
app.state.bound_host = '0.0.0.0'
app.state.bound_port = 9120
app.state.ui_surface = 'webapp'
app.state.trusted_public_hosts = frozenset()
LOCAL = 'http://localhost:9120'
client = TestClient(app, base_url=LOCAL)
headers = {'Origin': LOCAL, 'Sec-Fetch-Site': 'same-origin'}
with tempfile.TemporaryDirectory() as folder:
    content.CONSENT_DB = Path(folder) / 'consent.sqlite3'
    for path in ('/api/private-content/policy', '/api/media/proxy?url=http://public.test:8080/image'):
        assert client.get(path).status_code in (401, 403)
    assert client.post('/api/private-content/image', json={'url': 'http://public.test:8080/image'},
                       headers=headers).status_code in (401, 403)
    login = client.post('/auth/password-login', headers=headers,
                        json={'provider': 'basic', 'username': 'admin', 'password': 'fixture-password'})
    assert login.status_code == 200, login.text
    assert client.get('/api/media/proxy?url=http://public.test:8080/image').status_code == 404
    before = len(events())
    for origin in ('null', 'http://localhost:9121', 'https://external.test'):
        response = client.post('/api/private-content/consent',
            headers={**headers, 'Origin': origin}, json={'origin': 'http://public.test:8080', 'remember': True})
        assert response.status_code == 403
    assert client.post('/api/private-content/consent', headers={'Origin': LOCAL},
        json={'origin': 'http://public.test:8080', 'remember': True}).status_code == 403
    assert not content.CONSENT_DB.exists()
    with patch.object(images.socket, 'getaddrinfo', side_effect=resolve):
        content.PRIVATE_HERMES_EXTERNAL_CONTENT = 'ask'
        response = client.post('/api/private-content/image', headers=headers,
                               json={'url': 'http://public.test:8080/image'})
        assert response.status_code == 403, response.text
        assert len(events()) == before
        response = client.post('/api/private-content/image', headers=headers,
                               json={'url': 'http://public.test:8080/image', 'load_once': True})
        assert response.status_code == 200, response.text
        assert client.get('/api/private-content/policy').json()['origins'] == []
        response = client.post('/api/private-content/consent', headers=headers,
            json={'origin': 'http://public.test:8080', 'remember': True})
        assert response.status_code == 200, response.text
        assert content.CONSENT_DB.stat().st_mode & 0o777 == 0o600
        assert client.post('/api/private-content/image', headers=headers,
                           json={'url': 'http://public.test:8080/image'}).status_code == 200
        assert content.grants('https://localhost:9120') == []
        # Reopen the native database; remembered grants survive connection lifetime.
        assert content.grants(LOCAL) == ['http://public.test:8080']
        client.post('/api/private-content/consent', headers=headers,
                    json={'origin': 'http://public.test:8080', 'remember': False}).raise_for_status()
        before = len(events())
        assert client.post('/api/private-content/image', headers=headers,
                           json={'url': 'http://public.test:8080/image'}).status_code == 403
        content.PRIVATE_HERMES_EXTERNAL_CONTENT = 'off'
        assert client.post('/api/private-content/image', headers=headers,
            json={'url': 'http://public.test:8080/image', 'load_once': True}).status_code == 403
        assert len(events()) == before
        for mode in ('tor_proxied', 'browser_native'):
            content.PRIVATE_HERMES_EXTERNAL_CONTENT = mode
            assert client.post('/api/private-content/image', headers=headers,
                               json={'url': 'http://public.test:8080/image'}).status_code == 200
print('PASS: native auth, forged/opaque consent denial, ask load-once/remember/revoke, independent ingress origins, off ceiling and old-proxy removal')

for event in events():
    assert not {'cookie', 'authorization', 'referer', 'proxy-authorization'} & {k.lower() for k in event['headers']}
print('PASS: streaming size cap, redirect loop, TLS identity failure, failed dependency and explicit retry')
