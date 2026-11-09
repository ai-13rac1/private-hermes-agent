"""Deployment policy and narrowly scoped authenticated Tor-image consent."""
import asyncio
import base64
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

from hermes_bootstrap import PRIVATE_HERMES_EXTERNAL_CONTENT

MODES = ('tor_proxied', 'ask', 'off', 'browser_native')
# Deployment-owned location, independent of model-editable active profile settings.
CONSENT_DB = Path('/opt/data/webapp-image-consent.sqlite3')


def deployment_mode():
    value = PRIVATE_HERMES_EXTERNAL_CONTENT
    if value not in MODES:
        raise ValueError('WEBAPP_EXTERNAL_CONTENT must be tor_proxied, ask, off or browser_native')
    return value


@contextmanager
def consent_db():
    try:
        fd = os.open(CONSENT_DB, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    db = sqlite3.connect(CONSENT_DB)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS tor_images '
                       '(browser_origin TEXT, external_origin TEXT, PRIMARY KEY(browser_origin, external_origin))')
            yield db
    finally:
        db.close()


def grants(browser):
    with consent_db() as db:
        return [row[0] for row in db.execute('SELECT external_origin FROM tor_images WHERE browser_origin=? '
                                            'ORDER BY external_origin', (browser,))]


def change_grant(browser, external, remember):
    with consent_db() as db:
        if remember:
            db.execute('INSERT OR IGNORE INTO tor_images VALUES (?, ?)', (browser, external))
        else:
            db.execute('DELETE FROM tor_images WHERE browser_origin=? AND external_origin=?', (browser, external))


def browser_origin(request, *, mutation=False):
    from fastapi import HTTPException
    from hermes_cli.dashboard_auth.request_utils import _http_origin
    target = _http_origin(f'{request.url.scheme}://{request.url.netloc}')
    origins = request.headers.getlist('origin')
    sites = request.headers.getlist('sec-fetch-site')
    if (target is None or (mutation and (len(origins) != 1 or _http_origin(origins[0]) != target
                                        or sites != ['same-origin']))):
        raise HTTPException(403, 'Image consent requires an authenticated same-origin browser action')
    scheme, host, port = target
    authority = host if port == (443 if scheme == 'https' else 80) else f'{host}:{port}'
    return f'{scheme}://{authority}'


def mount_content_routes(application):
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse
    from hermes_cli.private_public_images import ImageRefused, fetch_image, parse_url

    def authenticated(request):
        # Native middleware guards /api; retain the route-level native check too.
        from hermes_cli.web_server import _require_token
        _require_token(request)

    async def body(request):
        if request.headers.get('content-type', '').split(';', 1)[0] != 'application/json':
            raise HTTPException(415, 'Use a same-origin JSON request')
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except ValueError:
            raise HTTPException(400, 'Invalid image request') from None

    @application.get('/api/private-content/policy')
    async def policy(request: Request):
        authenticated(request)
        return JSONResponse({'mode': deployment_mode(), 'origins': grants(browser_origin(request))},
                            headers={'Cache-Control': 'no-store'})

    @application.post('/api/private-content/consent')
    async def consent(request: Request):
        authenticated(request)
        browser = browser_origin(request, mutation=True)
        payload = await body(request)
        try:
            external = parse_url(payload.get('origin'))[4]
        except ImageRefused as error:
            raise HTTPException(error.status, error.reason) from None
        remember = payload.get('remember')
        if type(remember) is not bool or payload.get('origin') != external:
            raise HTTPException(400, 'Specify one exact external origin and remember boolean')
        if deployment_mode() == 'off' and remember:
            raise HTTPException(403, 'External content is disabled by deployment policy')
        change_grant(browser, external, remember)
        return JSONResponse({'origins': grants(browser)}, headers={'Cache-Control': 'no-store'})

    @application.post('/api/private-content/image')
    async def image(request: Request):
        authenticated(request)
        browser = browser_origin(request, mutation=True)
        payload = await body(request)
        mode = deployment_mode()
        if mode == 'off':
            raise HTTPException(403, 'External content is disabled by deployment policy')
        try:
            url = payload.get('url')
            external = parse_url(url)[4]
            once = payload.get('load_once', False)
            if type(once) is not bool:
                raise HTTPException(400, 'load_once must be boolean')
            if mode == 'ask' and not once and external not in grants(browser):
                raise HTTPException(403, 'Approve this Tor image retrieval first')
            data, mime = await asyncio.to_thread(fetch_image, url, same_origin_only=(mode == 'ask'))
        except ImageRefused as error:
            raise HTTPException(error.status, error.reason) from None
        return JSONResponse({'data_url': f'data:{mime};base64,{base64.b64encode(data).decode("ascii")}'},
                            headers={'Cache-Control': 'no-store'})
