"""Browser onion-origin checks through a local byte proxy, without Tor publication."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright
from onion_transport import proxy

container, address, password_path = sys.argv[1:]
origin = 'http://' + address

with proxy(container, address) as port:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True,
            proxy={'server': f'http://127.0.0.1:{port}'})
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(origin + '/login')
            page.locator('input[name=username]').fill('admin')
            page.locator('input[name=password]').fill(Path(password_path).read_text())
            page.locator('button[type=submit]').click()
            page.wait_for_url(lambda url: '/login' not in url, timeout=30000)
            cookies = context.cookies(origin)
            sessions = [c for c in cookies if 'hermes_session_at' in c['name']]
            assert sessions and all(not c['secure'] and c['httpOnly'] and c['sameSite'] == 'Lax' for c in sessions)
            assert all(c['domain'] == address and not c['name'].startswith('__Host-') for c in sessions)
            status = page.evaluate("async()=> (await fetch('/api/config')).status")
            assert status == 200, status
            policy = page.evaluate("async()=> (await fetch('/api/private-content/policy')).json()")
            assert policy['mode'] == 'tor_proxied'
            # Chromium does not attach Fetch Metadata to HTTP onion origins.
            # Exercise server consent scoping with explicit fixture metadata;
            # actual Tor Browser's browser-generated headers are checked separately.
            consent = context.request.post(origin + '/api/private-content/consent',
                headers={'Origin': origin, 'Sec-Fetch-Site': 'same-origin',
                         'Cookie': '; '.join(c['name']+'='+c['value'] for c in cookies)},
                data={'origin': 'https://public.test', 'remember': True})
            assert consent.status == 200, consent.text()
            assert consent.json()['origins'] == ['https://public.test']
            other = browser.new_context()
            assert other.request.get(origin + '/api/config').status in (401, 403)
            other.close()
            denied = context.request.post(origin + '/api/webapp/socket-ticket?socket=host-terminal',
                headers={'Origin': 'http://localhost:19120',
                         'Cookie': '; '.join(c['name']+'='+c['value'] for c in cookies)})
            assert denied.status == 403
            # Native renewal uses the refresh cookie once access is absent.
            for cookie in sessions:
                context.clear_cookies(name=cookie['name'])
            status = page.evaluate("async()=> (await fetch('/api/config')).status")
            assert status == 200, status
            assert any('hermes_session_at' in c['name'] for c in context.cookies(origin))
            result = page.evaluate('''async () => {
              const r=await fetch('/api/webapp/socket-ticket?socket=host-terminal',{method:'POST'});
              if(!r.ok) throw new Error('ticket '+r.status);
              const {ticket}=await r.json();
              return await new Promise((resolve,reject)=>{
                const ws=new WebSocket(location.origin.replace(/^http/,'ws')+'/api/host-terminal?ticket='+encodeURIComponent(ticket));
                ws.binaryType='arraybuffer';let output='';
                const timer=setTimeout(()=>{ws.close();reject(new Error('stream timeout'));},20000);
                ws.onopen=()=>ws.send("printf 'ONION-%s\\n' STREAM\\n");
                ws.onmessage=e=>{output+=typeof e.data==='string'?e.data:new TextDecoder().decode(e.data);
                  if(output.includes('ONION-STREAM')){clearTimeout(timer);ws.close();resolve(true);}};
                ws.onerror=()=>{clearTimeout(timer);reject(new Error('socket rejected'));};
              });
            }''')
            assert result
            with page.expect_response(lambda r: r.url == origin + '/auth/logout') as logout:
                page.evaluate("()=>{void fetch('/auth/logout',{method:'POST'});}")
            assert logout.value.status in (200, 302, 303)
            assert not [c for c in context.cookies(origin) if 'hermes_session_at' in c['name']]
            context.close()
            print('PASS: Chromium onion-origin login, host-only HTTP cookies, refresh, CSRF, WebSocket stream and logout', flush=True)
        finally:
            browser.close()
