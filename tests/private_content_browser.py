"""Real built renderer, controlled TLS/proxy canaries, local and simulated Funnel."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import struct
import sys
import tempfile
import threading
import zlib
from playwright.sync_api import Error, sync_playwright
from browser_proxy import Observer, tunnels

password_path, mode = Path(sys.argv[1]), sys.argv[2]
PASSWORD = password_path.read_text()
LOCAL = 'http://127.0.0.1:19120'
PUBLIC = 'https://webapp-test.example.ts.net:10000'
CANARY = 'https://public.test:19202'


def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
PNG = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 2, 2, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress((b'\0' + b'\0\0\xff' * 2) * 2)) + chunk(b'IEND', b'')
DATA = 'data:image/png;base64,' + base64.b64encode(PNG).decode()
requests, connections = [], []


class Canary(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args):
        pass
    def do_GET(self):
        requests.append({'path': self.path, 'referrer': self.headers.get('Referer')})
        body, mime = (PNG, 'image/png') if self.path.endswith('.png') else (b'controlled external destination', 'text/plain')
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class TLSServer(ThreadingHTTPServer):
    daemon_threads = True
    def get_request(self):
        sock, address = super().get_request()
        connections.append(address)
        return tls.wrap_socket(sock, server_side=True), address


tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.load_cert_chain(password_path.parent / 'tls/cert.pem', password_path.parent / 'tls/key.pem')
canary = TLSServer(('127.0.0.1', 19202), Canary)
observer = ThreadingHTTPServer(('127.0.0.1', 0), Observer)
observer.daemon_threads = True
for server in (canary, observer):
    threading.Thread(target=server.serve_forever, daemon=True).start()


def fetch(page, path, payload=None):
    return page.evaluate('''async ({path,payload}) => {
      const response=await fetch(path,payload===null?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      return {status:response.status,body:await response.json()};
    }''', {'path': path, 'payload': payload})


def login(page, origin):
    page.goto(origin + '/login')
    page.locator('input[name=username]').fill('admin')
    page.locator('input[name=password]').fill(PASSWORD)
    page.locator('button[type=submit]').click()
    page.wait_for_url(lambda url: '/login' not in url)
    page.wait_for_load_state('domcontentloaded')


def attachment_download(page, url, expected):
    page.evaluate("""href => {
      const a=document.createElement('a');a.id='qualification-download';
      a.href=href;a.textContent='Download active fixture';document.body.append(a);
    }""", url)
    with page.expect_download() as clicked:
        page.locator('#qualification-download').click()
    assert Path(clicked.value.path()).read_bytes() == expected
    page.locator('#qualification-download').evaluate('(a) => a.remove()')


def relay_checks(page, context, origin):
    saved = fetch(page, '/api/gateway-connections', {
        'kind': 'remote', 'label': 'Disposable relay', 'url': 'http://10.203.84.10:8000',
        'authMode': 'token', 'token': 'disposable-relay-token'})
    assert saved['status'] == 200, saved
    assert 'disposable-relay-token' not in json.dumps(saved), saved
    connection_id = saved['body']['connection']['id']
    base = '/api/relay/' + connection_id
    try:
        with context.browser.new_context(ignore_https_errors=True,
                proxy={'server': f'http://127.0.0.1:{observer.server_port}',
                       'bypass': '127.0.0.1,localhost'}) as anonymous:
            response = anonymous.request.get(origin + base + '/relay/page.html', max_redirects=0)
            assert response.status in (401, 302, 303), response.status
        for path in ('page.html', 'image.svg'):
            response = page.request.get(origin + base + '/relay/' + path)
            assert response.status == 200, response.status
            headers = response.headers
            assert headers['content-disposition'] == 'attachment', headers
            assert headers['content-type'] == 'application/octet-stream', headers
            assert headers['x-content-type-options'] == 'nosniff', headers
            assert "default-src 'none'" in headers['content-security-policy'], headers
            assert 'x-private-hermes-trusted-page' not in headers, headers
            assert 'set-cookie' not in headers and 'link' not in headers, headers
            url = origin + base + '/relay/' + path
            attachment_download(page, url, response.body())
            # The native relay requires same-origin Fetch Metadata. An address-
            # bar/new-tab navigation must not exercise the saved credential.
            tab = context.new_page()
            try:
                assert tab.goto(url).status == 403
            finally:
                tab.close()
        # Actual raster rendering through the native relay remains available.
        result = page.evaluate('''async path => {
          const image = new Image(); image.src = path; document.body.append(image);
          try { await image.decode(); return image.naturalWidth; } finally { image.remove(); }
        }''', base + '/relay/image.png')
        assert result == 1, result
        # Attempt to embed each active response. Attachment/CSP must prevent execution
        # and remote subresources even when the native upstream content is hostile.
        page.evaluate('''base => {
          for (const name of ['page.html', 'image.svg']) {
            const frame = document.createElement('iframe'); frame.dataset.relayTest = '1';
            frame.src = base + '/relay/' + name; document.body.append(frame);
          }
        }''', base)
        page.wait_for_timeout(500)
        page.locator('iframe[data-relay-test]').evaluate_all('(frames) => frames.forEach(frame => frame.remove())')
        assert not any('/relay' in request['path'] for request in requests), requests
    finally:
        response = page.request.delete(origin + '/api/gateway-connections/' + connection_id)
        assert response.status == 200, response.status


try:
    with sync_playwright() as playwright:
        for engine in (sys.argv[3:] or ('chromium', 'firefox', 'webkit')):
            browser = getattr(playwright, engine).launch(headless=True)
            try:
                for origin in (LOCAL, PUBLIC):
                    tunnel_start = len(tunnels)
                    context = browser.new_context(ignore_https_errors=True,
                        proxy={'server': f'http://127.0.0.1:{observer.server_port}', 'bypass': '127.0.0.1,localhost'})
                    page = context.new_page()
                    chat_frames = []
                    page.on('websocket', lambda ws: ws.on('framereceived', lambda frame: chat_frames.append(frame)))
                    login(page, origin)
                    page.get_by_text('ready', exact=True).first.wait_for(timeout=30000)
                    editor = page.locator('[data-slot="composer-rich-input"]').first
                    editor.fill('qualification-stream')
                    editor.press('Enter')
                    try:
                        page.get_by_text('PRIVATE-CHAT-STREAM-OK', exact=False).wait_for(timeout=30000)
                    except Exception:
                        print('Disposable UI state:', page.locator('body').inner_text()[-2500:], 'Observed tunnels:', tunnels, flush=True)
                        raise
                    assert any('PRIVATE-CHAT-' in str(frame) for frame in chat_frames), 'No live chat text arrived over WebSocket'
                    value = fetch(page, '/api/private-content/policy')
                    assert value['status'] == 200 and value['body']['mode'] == mode, value
                    for grant in value['body']['origins']:
                        assert fetch(page, '/api/private-content/consent', {'origin':grant, 'remember':False})['status'] == 200
                    image_calls = []
                    failed_once = set()
                    # UI fixture only: actual backend socket/consent behavior is independently
                    # qualified by images_smoke. No public endpoint is exposed for a canary.
                    def image_response(route):
                        image_calls.append(route.request.post_data_json)
                        source = route.request.post_data_json['url']
                        if mode == 'tor_proxied' and source.endswith('/markdown.png') and source not in failed_once:
                            failed_once.add(source)
                            route.fulfill(status=502, content_type='application/json', body=json.dumps({'detail':'Controlled Tor image failure'}))
                            return
                        route.fulfill(status=200, content_type='application/json',
                                      headers={'Cache-Control':'no-store'}, body=json.dumps({'data_url':DATA}))
                    page.route('**/api/private-content/image', image_response)
                    begin = len(requests)
                    begin_connections = len(connections)
                    page.goto(origin + '/#/private-content-qualification')
                    page.get_by_text('Private content qualification message.', exact=False).wait_for(timeout=30000)
                    page.locator('[data-slot="aui_markdown-image"]').first.wait_for(timeout=30000)
                    page.wait_for_timeout(1500)
                    if mode != 'browser_native':
                        assert len(requests) == begin and len(connections) == begin_connections, (engine,origin,mode,requests[begin:])
                        assert page.get_by_text('Social and interactive players are unavailable', exact=False).count() > 0
                        assert page.get_by_text('External video playback is unavailable', exact=False).count() > 0
                        assert page.get_by_text('External audio playback is unavailable', exact=False).count() > 0
                        if mode == 'ask':
                            assert not image_calls, image_calls
                            page.get_by_role('button', name='Load once through Tor / retry').first.click()
                            page.wait_for_function('''() => [...document.images].some(i => i.src.startsWith('data:image/png') && i.complete && i.naturalWidth===2)''')
                            assert len(image_calls) == 1 and image_calls[0]['load_once'] is True
                            policy = fetch(page, '/api/private-content/policy')
                            assert policy['body']['origins'] == [], policy
                            with page.expect_response(lambda r: r.url.endswith('/api/private-content/consent')
                                                      and r.request.method == 'POST') as remembered:
                                page.get_by_role('button', name='Remember this origin for Tor images').first.click()
                            assert remembered.value.status == 200
                            assert remembered.value.json()['origins'] == [CANARY]
                            # The one persistent settings surface is available even once images load.
                            page.goto(origin + '/#/settings?tab=config%3Aappearance&page=chat-display')
                            page.get_by_role('button', name='Image permissions', exact=True).first.click(timeout=15000)
                            dialog = page.get_by_role('dialog', name='Private image permissions')
                            with page.expect_response(lambda r: r.url.endswith('/api/private-content/consent')
                                                      and r.request.method == 'POST') as revoked:
                                dialog.get_by_role('button', name='Revoke', exact=True).click()
                            assert revoked.value.status == 200
                            assert revoked.value.json()['origins'] == []
                            policy = fetch(page, '/api/private-content/policy')
                            assert policy['body']['origins'] == [], policy
                            dialog.get_by_role('button', name='Close', exact=True).click()
                        elif mode == 'off':
                            assert not image_calls and page.get_by_role('button', name='Load once through Tor / retry').count() == 0
                        else:
                            assert image_calls and all(not call['load_once'] for call in image_calls)
                            failure = page.locator('[data-private-content="image"]').filter(has_text='Controlled Tor image failure')
                            failure.get_by_role('button', name='Load once through Tor / retry').click()
                            page.wait_for_function('''() => [...document.images].some(i => i.src.startsWith('data:image/png') && i.complete && i.naturalWidth===2)''')
                        assert len(requests) == begin and len(connections) == begin_connections
                        assert all(host == 'webapp-test.example.ts.net' for host, port in tunnels[tunnel_start:]), tunnels[tunnel_start:]
                    else:
                        page.wait_for_function('''() => [...document.images].some(i => i.src.includes('public.test') && i.complete && i.naturalWidth===2)''')
                        assert len(requests) > begin
                        assert not image_calls
                    page.goto(origin + '/#/private-content-qualification')
                    page.get_by_text('Private content qualification message.', exact=False).wait_for()
                    for asset in ('active.html', 'active.svg'):
                        response = context.request.get(origin + '/dashboard-plugins/privacy-assets/' + asset)
                        assert response.status == 200, (asset,response.status)
                        assert response.headers.get('content-disposition') == 'attachment'
                        assert response.headers.get('content-type') == 'application/octet-stream'
                        assert response.headers.get('x-content-type-options') == 'nosniff'
                        assert 'sandbox' in response.headers.get('content-security-policy','')
                        url = origin + '/dashboard-plugins/privacy-assets/' + asset
                        attachment_download(page, url, response.body())
                        tab = context.new_page()
                        try:
                            with tab.expect_download() as navigated:
                                try:
                                    tab.goto(url)
                                except Error:
                                    pass  # The required download aborts navigation.
                            assert Path(navigated.value.path()).read_bytes() == response.body()
                        finally:
                            tab.close()

                    # Real same-origin local bytes and authenticated playback remain usable.
                    page.goto(origin + '/#/private-content-qualification')
                    page.get_by_text('Private content qualification message.', exact=False).wait_for()
                    page.wait_for_function('''() => { const i=document.querySelector('img[alt="Local fixture image"]'); return i && i.complete && i.naturalWidth>0 }''')
                    page.wait_for_function('''() => [...document.querySelectorAll('audio')].some(a => !a.src.includes('public.test') && a.readyState>0 && a.duration>0)''')
                    page.evaluate("""async () => {
                      const video=[...document.querySelectorAll('video')].find(v=>!v.src.includes('public.test'));
                      if(!video) throw new Error('Local video player missing');
                      video.muted=true; await video.play();
                    }""")
                    page.wait_for_function('''() => [...document.querySelectorAll('video')].some(v=>!v.src.includes('public.test') && v.videoWidth>0)''')
                    # Verify inert preview server with malicious HTML transferred through the actual shell.
                    if mode != 'browser_native':
                        before = len(requests)
                        page.evaluate(r'''origin => {
                          const f=document.createElement('iframe'); f.sandbox='allow-scripts';
                          f.src='/assets/webapp-preview.html'; document.body.append(f);
                          f.onload=()=>f.contentWindow.postMessage({type:'hermes-preview-document',scripts:true,
                            html:`<img src="${origin}/preview.png"><link rel="preconnect" href="${origin}"><script>fetch('${origin}/fetch');new RTCPeerConnection();location.href='${origin}/navigate'<\/script><iframe src="${origin}/frame"></iframe>`},'*');
                        }''', CANARY)
                        page.frame_locator('iframe[src="/assets/webapp-preview.html"]').last.locator('#source').get_by_text('<img',exact=False).wait_for(timeout=5000)
                        page.wait_for_timeout(300)
                        assert len(requests) == before
                    # Exercise extra tabs after chat/media checks so they cannot
                    # interrupt the fresh page's initial WebSocket subscription.
                    relay_checks(page, context, origin)
                    # Deliberate link navigation remains a real browser request, with no referrer.
                    link = page.get_by_role('link', name='Privacy deliberate external link', exact=True)
                    link.evaluate('''link => link.addEventListener('click', event => {
                      window.__qualificationClick = {trusted:event.isTrusted, active:navigator.userActivation?.isActive};
                    }, {capture:true, once:true})''')
                    try:
                        with context.expect_page() as popup:
                            link.click()
                    except Exception:
                        print('External-link diagnostic:', engine, mode, origin, page.url,
                              link.evaluate('link => ({html:link.outerHTML, click:window.__qualificationClick})'),
                              [event for event in requests if event['path'] == '/deliberate'], flush=True)
                        raise
                    child = popup.value
                    child.wait_for_load_state('domcontentloaded')
                    assert child.url == CANARY + '/deliberate'
                    navigation = [event for event in requests if event['path'] == '/deliberate'][-1]
                    assert not navigation['referrer'], navigation
                    child.close()
                    context.close()
                    print(f'PASS: {engine} {browser.version} {mode} {"HTTPS" if origin==PUBLIC else "local"} actual model/tool rendering, TCP/TLS canary observation, consent/fallback/local content/link behavior', flush=True)
            finally:
                browser.close()
finally:
    observer.shutdown(); observer.server_close()
    canary.shutdown(); canary.server_close()
