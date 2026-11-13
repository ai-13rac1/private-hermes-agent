"""Exercise the exact in-container namespace-owner assertion with procfs values."""
from pathlib import Path
import unittest
from unittest.mock import patch
import smoke


class NamespaceOwnerTests(unittest.TestCase):
    def status(self, uid, gid):
        return {'Uid': '\t' + '\t'.join([str(uid)] * 4),
                'Gid': '\t' + '\t'.join([str(gid)] * 4), 'Groups': '\t',
                **{key: '\t0000000000000000' for key in
                   ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd')},
                'NoNewPrivs': '\t1'}

    def check(self, status, uid, gid):
        text = '\n'.join(f'{key}:{value}' for key, value in status.items()) + '\n'
        with patch.object(Path, 'read_text', return_value=text):
            exec(smoke.namespace_owner_check(uid, gid), {})

    def test_accepts_expected_tor_and_endpoint_identities(self):
        for uid, gid in ((101, 102), (65534, 65534)):
            with self.subTest(uid=uid, gid=gid):
                self.check(self.status(uid, gid), uid, gid)

    def test_rejects_root_saved_identity_groups_and_retained_privileges(self):
        changes = [('Uid', '\t0\t0\t0\t0'), ('Gid', '\t0\t0\t0\t0'),
                   ('Uid', '\t101\t101\t0\t101'), ('Gid', '\t102\t102\t0\t102'),
                   ('Uid', '\t65534\t65534\t65534\t65534'), ('Groups', '\t102'),
                   ('NoNewPrivs', '\t0')]
        changes += [(key, '\t0000000000000001') for key in
                    ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd')]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                status = self.status(101, 102)
                status[key] = value
                with self.assertRaises(AssertionError):
                    self.check(status, 101, 102)
