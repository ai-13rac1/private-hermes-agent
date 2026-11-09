"""Direct Chromium NetLog observation of actual model/preview DNS and preconnects."""
import json
from pathlib import Path
import sys
import tempfile
from playwright.sync_api import sync_playwright

password = Path(sys.argv[1]).read_text()
for origin in ('http://127.0.0.1:19120', 'https://webapp-test.example.ts.net:10000'):
    with tempfile.TemporaryDirectory(prefix='private-hermes-netlog-') as folder:
        log = Path(folder) / 'network.json'
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                f'--log-net-log={log}', '--net-log-capture-mode=Everything', '--no-proxy-server',
                '--host-resolver-rules=MAP webapp-test.example.ts.net 127.0.0.1'])
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto(origin + '/login')
            page.locator('input[name=username]').fill('admin')
            page.locator('input[name=password]').fill(password)
            page.locator('button[type=submit]').click()
            page.wait_for_url(lambda url:'/login' not in url)
            page.goto(origin + '/#/private-content-qualification')
            page.get_by_text('Private content qualification message.', exact=False).wait_for(timeout=30000)
            # Transfer the malicious hints to the actual private preview shell.
            page.evaluate('''() => {
              const f=document.createElement('iframe');f.sandbox='allow-scripts';
              f.src='/assets/webapp-preview.html';document.body.append(f);
              f.onload=()=>f.contentWindow.postMessage({type:'hermes-preview-document',html:
                '<link rel="dns-prefetch" href="//private-hint.invalid"><link rel="preconnect" href="https://public.test:19202"><img src="https://public.test:19202/probe.png">'},'*');
            }''')
            page.wait_for_timeout(1500)
            # Deliberate navigation proves the observer catches resolver attempts;
            # The reserved .invalid positive-control name cannot select an external HTTP endpoint.
            try:
                page.goto('http://positive.private-content.invalid:19202/control', timeout=5000)
            except Exception as error:
                assert 'ERR_NAME_NOT_RESOLVED' in str(error), str(error)
            context.close()
            browser.close()
        data = json.loads(log.read_text())
        names = {value:name for name,value in data['constants']['logEventTypes'].items()}
        events = [event for event in data['events'] if any(part in names.get(event['type'],'')
                  for part in ('HOST_RESOLVER', 'DNS_TRANSACTION', 'TCP_CONNECT', 'PRECONNECT'))]
        automatic = [event for event in events if any(host in json.dumps(event.get('params',{}))
                     for host in ('public.test', 'private-hint.invalid'))]
        control = [event for event in events if 'positive.private-content.invalid' in json.dumps(event.get('params',{}))]
        assert not automatic, [(names[event['type']],event.get('params')) for event in automatic]
        assert control, ('NetLog positive-control resolver attempt was not observed', [names[event['type']] for event in data['events'] if 'positive.private-content.invalid' in json.dumps(event.get('params',{}))])
        print('PASS: direct Chromium resolver/TCP/preconnect NetLog has no model/preview canary activity; deliberate-navigation positive control observed (' + origin + ')')
