"""Compose handles dotenv interpolation; this module validates feature settings."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'components/webapp'))
from settings import Settings, proxy_config


def settings():
    result = subprocess.run(['docker', 'compose', '-f', 'compose.yaml', 'config', '--format', 'json'],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    return Settings.read(json.loads(result.stdout)['x-deployment'])


def compose(config, all_ingress=False):
    command = ['docker', 'compose', '-f', 'compose.yaml']
    if config.funnel or all_ingress:
        command += ['-f', 'compose.funnel.yaml']
    return command


def render(config):
    path = ROOT / 'config/webapp/proxy.cfg'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(proxy_config(config))
