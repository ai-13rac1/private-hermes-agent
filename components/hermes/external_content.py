"""Deployment external-content policy. Content enforcement follows in P1-2/P1-3."""
from hermes_bootstrap import PRIVATE_HERMES_EXTERNAL_CONTENT

MODES = ('tor_proxied', 'ask', 'off', 'browser_native')


def deployment_mode():
    value = PRIVATE_HERMES_EXTERNAL_CONTENT
    if value not in MODES:
        raise ValueError('WEBAPP_EXTERNAL_CONTENT must be tor_proxied, ask, off or browser_native')
    return value
