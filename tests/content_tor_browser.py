"""Authenticated real image retrieval, Tor failure and explicit recovery retry."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

password = Path(sys.argv[1]).read_text()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    try:
        page = browser.new_page()
        page.goto('http://127.0.0.1:19120/login')
        page.locator('input[name=username]').fill('admin')
        page.locator('input[name=password]').fill(password)
        page.locator('button[type=submit]').click()
        page.wait_for_url(lambda url:'/login' not in url)
        def image():
            return page.evaluate('''async () => {
              const response=await fetch('/api/private-content/image',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({url:'https://www.python.org/static/img/python-logo.png'})});
              const data=await response.json();
              return {status:response.status,raster:typeof data.data_url==='string' && data.data_url.startsWith('data:image/png;base64,'),reason:data.detail};
            }''')
        def image_after_bootstrap():
            # Bootstrap health does not guarantee that a particular exit can
            # resolve or connect to this host immediately. Keep the existing
            # allowed-path cadence for these observed transport failures only;
            # policy/other errors and Tor-stopped checks still fail immediately.
            for attempt in range(4):
                result = image()
                if result['status'] != 502 or result.get('reason') not in (
                        'Public image DNS resolution failed',
                        'Image connection failed; retry through Tor or open externally'):
                    return result
                if attempt < 3:
                    page.wait_for_timeout(2000)
            return result
        result = image_after_bootstrap()
        assert result['status']==200 and result['raster'], result
        print('READY_TOR_DOWN',flush=True)
        assert input()=='down'
        result=image()
        assert result['status']==502 and not result['raster'], result
        print('READY_TOR_RESTART',flush=True)
        assert input()=='restart'
        result=image_after_bootstrap()
        assert result['status']==200 and result['raster'], result
        print('PASS: authenticated public raster retrieval, Tor loss without direct fallback, explicit retry after Tor recovery',flush=True)
    finally:
        browser.close()
