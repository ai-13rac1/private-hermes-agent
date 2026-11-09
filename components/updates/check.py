"""Anonymous GET-only upstream checks. Executed in the agent's Tor namespace."""
import hashlib
import json
import sys
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler, Request

OPENER = build_opener(ProxyHandler({}))
MANIFESTS = ', '.join(('application/vnd.oci.image.index.v1+json',
                       'application/vnd.docker.distribution.manifest.list.v2+json',
                       'application/vnd.oci.image.manifest.v1+json',
                       'application/vnd.docker.distribution.manifest.v2+json'))


def fetch(url, headers=None):
    request = Request(url, headers={'User-Agent': 'private-hermes-update-check', **(headers or {})}, method='GET')
    with OPENER.open(request, timeout=30) as response:
        body = response.read()
        return json.loads(body), response.headers.get('Docker-Content-Digest') or 'sha256:' + hashlib.sha256(body).hexdigest()


def image_digest(channel, request=fetch):
    repository, tag = channel.rsplit(':', 1)
    if '/' not in repository:
        repository = 'library/' + repository
    token, _ = request('https://auth.docker.io/token?' + urlencode({
        'service': 'registry.docker.io', 'scope': f'repository:{repository}:pull'}))
    manifest, digest = request(f'https://registry-1.docker.io/v2/{repository}/manifests/{tag}',
                               {'Authorization': 'Bearer ' + token['token'], 'Accept': MANIFESTS})
    return digest, {digest, *(m['digest'] for m in manifest.get('manifests', []))}


def check(data, request=fetch, progress=None):
    checks = []
    for entry in [*data['images'], *data['sources']]:
        row = {'name': entry['name'], 'pinned': entry['pinned']}
        try:
            if 'channel' in entry:
                upstream, accepted = image_digest(entry['channel'], request)
                same = entry['pinned'].split('@')[1] in accepted
                row['channel'] = entry['channel']
            else:
                commits, _ = request(f"https://api.github.com/repos/{entry['repository']}/commits?per_page=1")
                upstream = commits[0]['sha']
                same = entry['pinned'] == upstream
                row['channel'] = entry['repository'] + ' default branch'
            row.update(upstream=upstream, status='matches' if same else 'different')
        except Exception as error:
            row.update(status='error', error=f'{type(error).__name__}: {error}')
        checks.append(row)
        if progress:
            progress(row)
    return {'checks': checks, 'unpinned_bases': data['unpinned_bases']}


if __name__ == '__main__':
    print(json.dumps(check(json.load(sys.stdin), progress=lambda row: print(
        f"Checked {row['name']}: {row['status']}", file=sys.stderr, flush=True))))
