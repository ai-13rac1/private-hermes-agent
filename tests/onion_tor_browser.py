"""Installed Tor Browser HTTP-origin check using a disposable automated profile.

The local byte proxy isolates browser semantics from live Tor rendezvous.
"""
import os
from pathlib import Path
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.service import Service
from onion_transport import proxy

container, address, password_path = sys.argv[1:]
origin = 'http://' + address
os.environ['TOR_SKIP_LAUNCH'] = '1'
os.environ['SE_AVOID_STATS'] = 'true'
os.environ['SE_OFFLINE'] = 'true'
with proxy(container, address) as port:
    os.environ['TOR_SOCKS_HOST'] = '127.0.0.1'
    os.environ['TOR_SOCKS_PORT'] = str(port)
    options = webdriver.FirefoxOptions()
    options.binary_location = os.environ['TOR_BROWSER_BINARY']
    options.add_argument('-headless')
    for key, value in {
        'extensions.torlauncher.start_tor': False,
        'extensions.torlauncher.prompt_at_startup': False,
        'torbrowser.settings.enabled': False,
        'network.proxy.type': 1,
        'network.proxy.http': '',
        'network.proxy.ssl': '',
        'network.proxy.socks': '127.0.0.1',
        'network.proxy.socks_port': port,
        'network.proxy.socks_version': 5,
        'network.proxy.socks_remote_dns': True,
        'network.proxy.no_proxies_on': '',
    }.items():
        options.set_preference(key, value)
    # An explicit local driver prevents Selenium Manager from running at all.
    # Manager's default automatic discovery sends Plausible usage statistics.
    driver_path = os.environ.get('GECKODRIVER', '')
    if not driver_path or not Path(driver_path).is_file():
        raise SystemExit('Set GECKODRIVER to an existing local driver; automatic discovery is disabled.')
    service = Service(executable_path=driver_path, service_args=['--allow-system-access'])
    driver = webdriver.Firefox(options=options, service=service)
    try:
        driver.set_page_load_timeout(60)
        driver.get(origin + '/login')
        driver.find_element(By.NAME, 'username').send_keys('admin')
        driver.find_element(By.NAME, 'password').send_keys(Path(password_path).read_text())
        driver.find_element(By.CSS_SELECTOR, 'button[type=submit]').click()
        WebDriverWait(driver, 30).until(lambda d: '/login' not in d.current_url)
        def fetch_status(path, method='GET'):
            return driver.execute_async_script('''const done=arguments[arguments.length-1];
              fetch(arguments[0],{method:arguments[1],cache:'no-store',
                headers:{Accept:'application/json','Content-Type':'application/json'}})
                .then(r=>done(r.status)).catch(e=>done(String(e)));
            ''', path, method)
        assert fetch_status('/api/config') == 200
        consent = driver.execute_async_script('''const done=arguments[arguments.length-1];
          fetch('/api/private-content/consent',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({origin:'https://public.test',remember:true})})
            .then(async r=>done({status:r.status,body:await r.json()})).catch(e=>done(String(e)));
        ''')
        assert consent['status'] == 200 and consent['body']['origins'] == ['https://public.test'], consent
        # Tor Browser's first-party partition attributes are not represented by
        # WebDriver get_cookies(). Inspect only flags, never cookie values.
        with driver.context(driver.CONTEXT_CHROME):
            cookies = driver.execute_script('''return Array.from(Services.cookies.getCookiesWithOriginAttributes(
                JSON.stringify({privateBrowsingId:1}),arguments[0]))
              .filter(c=>c.host===arguments[0]&&c.name.includes('hermes_session_at'))
              .map(c=>({host:c.host,secure:c.isSecure,httpOnly:c.isHttpOnly,
                        lax:c.sameSite===Ci.nsICookie.SAMESITE_LAX}));''', address)
            assert cookies and all(c['httpOnly'] and not c['secure'] and c['lax'] for c in cookies), cookies
            driver.execute_script('''for(const c of Array.from(Services.cookies.getCookiesWithOriginAttributes(
                JSON.stringify({privateBrowsingId:1}),arguments[0]))){
              if(c.host===arguments[0]&&c.name.includes('hermes_session_at'))
                Services.cookies.remove(c.host,c.name,c.path,c.originAttributes);
            }''', address)
        assert fetch_status('/api/config') == 200
        # The SPA navigates on logout, aborting the old page's awaited fetch.
        # Observe cleared native cookies and a fresh unauthenticated page.
        driver.execute_script("void fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json'}});")
        def signed_out(browser):
            with browser.context(browser.CONTEXT_CHROME):
                return browser.execute_script('''return !Array.from(Services.cookies.getCookiesWithOriginAttributes(
                  JSON.stringify({privateBrowsingId:1}),arguments[0])).some(c=>
                    c.name.includes('hermes_session_at')||c.name.includes('hermes_session_rt'));''', address)
        WebDriverWait(driver, 30).until(signed_out)
        driver.get(origin + '/login')
        status = fetch_status('/api/config')
        assert status in (401, 403), status
        print('PASS: Tor Browser ' + driver.capabilities['browserVersion'] +
              ' onion HTTP login, cookie flags, refresh and logout in a disposable profile', flush=True)
    finally:
        driver.quit()
