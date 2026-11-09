"""Install native webapp settings during the existing networkless bootstrap."""
from auth import validate


def configure(config, credentials, username):
    credentials = validate(credentials)
    config['terminal'].update({'ssh_host': '10.203.82.3', 'ssh_port': 2222,
                               'ssh_user': 'runner', 'ssh_key': '/run/agent-ssh/id_ed25519'})
    config['webapp'] = {'enabled': True, 'host': '0.0.0.0', 'port': 9120, 'public_url': ''}
    dashboard = config.setdefault('dashboard', {})
    dashboard['trusted_proxies'] = ['10.203.85.3']
    dashboard['public_url'] = ''
    dashboard['basic_auth'] = {'username': username, **credentials}
    dashboard['session_token_auth'] = {'enabled': False}
