"""Real browser-result files through authenticated native APIs; no model/provider."""
import base64
import json
from pathlib import Path
import sys
from urllib.parse import quote
from playwright.sync_api import sync_playwright

password = Path(sys.argv[1]).read_text()
origin = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:19120'
manifest = '/api/files/read?path=' + quote('/opt/data/cache/browser-use/fixture-artifacts.json', safe='')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-proxy-server',
                               '--host-resolver-rules=MAP webapp-test.example.ts.net 127.0.0.1'])
    context = browser.new_context(ignore_https_errors=True)
    external = []
    context.on('request', lambda r: external.append(r.url)
               if r.url.startswith(('http:', 'https:')) and not r.url.startswith(origin + '/') else None)
    page = context.new_page()
    page.goto(origin + '/login')
    assert page.evaluate('p=>fetch(p).then(r=>r.status)', manifest) == 401
    assert page.evaluate('''async password => (await fetch('/auth/password-login', {
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({provider:'basic',username:'admin',password})})).status''', password) == 200
    # The API page avoids mounting saved chats that may deliberately load content.
    page.goto(origin + '/api/config')
    result = page.evaluate('p=>fetch(p).then(r=>r.json())', manifest)
    artifacts = json.loads(base64.b64decode(result['data_url'].split(',', 1)[1]))
    shot = page.evaluate('p=>fetch(p).then(r=>r.json())',
                         '/api/files/read?path=' + quote(artifacts['screenshot'], safe=''))
    assert base64.b64decode(shot['data_url'].split(',', 1)[1]).startswith(b'\x89PNG')
    assert page.evaluate('''data=>new Promise((resolve,reject)=>{
      const image=new Image();image.onload=()=>resolve(image.naturalWidth>0);
      image.onerror=reject;image.src=data;document.body.append(image);
    })''', shot['data_url'])
    download = '/api/fs/download?path=' + quote(artifacts['download'], safe='')
    result = page.evaluate('p=>fetch(p).then(async r=>({status:r.status,body:await r.text()}))', download)
    assert result == {'status': 200, 'body': 'executor-download'}, result
    page.evaluate('()=>fetch("/auth/logout",{method:"POST"})')
    assert page.evaluate('p=>fetch(p).then(r=>r.status)', manifest) == 401
    assert page.evaluate('p=>fetch(p).then(r=>r.status)', download) == 401
    assert not external, external
    browser.close()
print('PASS: authenticated browser screenshots render and executor downloads transfer; logout denies both; no external viewer requests')
