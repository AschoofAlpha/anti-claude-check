import unittest
import os
import sys

# Add the project root to sys.path so we can import claude_shield
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from claude_shield.redaction import Redactor
from claude_shield.remediation.transaction import Transaction

class TestRedaction(unittest.TestCase):
    def test_ip_redaction(self):
        redactor = Redactor()
        redacted1 = redactor.redact_ipv4('192.0.2.10')
        redacted2 = redactor.redact_ipv4('192.0.2.10')
        self.assertEqual(redacted1, redacted2)
        self.assertTrue(redacted1.startswith('<IPV4:'))
        
        redacted3 = redactor.redact_ipv4('10.0.0.1')
        self.assertNotEqual(redacted1, redacted3)
        
    def test_json_scan(self):
        redactor = Redactor()
        data = {
            "Hostname": "FAKE-DESKTOP-1234",
            "Servers": ["192.0.2.10", "198.51.100.20"],
            "nested": {"ip": "192.0.2.10"}
        }
        res = redactor.scan_and_redact(data)
        self.assertEqual(res["Servers"][0], res["nested"]["ip"])
        self.assertTrue(res["Servers"][0].startswith('<IPV4:'))

class TestTransaction(unittest.TestCase):
    def test_manifest_creation(self):
        tx = Transaction()
        # Mock some applied changes
        applied = [{"status": "completed", "action": {"action_id": "test"}}]
        tx._save_applied(applied)
        
        # Test load applied
        loaded = tx.load_applied()
        self.assertEqual(len(loaded), 1)

if __name__ == '__main__':
    unittest.main()
