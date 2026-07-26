import unittest
import os
import sys
import json
import subprocess
import socket
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from claude_shield.probes.safety import validate_url, validate_resolved_ip
from claude_shield.probes.http_probe import fetch_http
from claude_shield.probes.egress import extract_ip, check_egress_consistency
from claude_shield.probes.base import ProbeContext, ProbeEndpoint
from claude_shield.probes.base import ProbeError

class TestPhase3Safety(unittest.TestCase):
    @patch('claude_shield.probes.safety.socket.getaddrinfo')
    def test_url_safety(self, mock_dns):
        mock_dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('8.8.8.8', 443))]
        self.assertTrue(validate_url("https://example.com"))
        
        with self.assertRaises(ValueError):
            validate_url("http://example.com")  # Not HTTPS
            
        with self.assertRaises(ValueError):
            validate_url("https://user:pass@example.com")  # Auth
            
        with self.assertRaises(ValueError):
            validate_url("https://localhost")
            
        with self.assertRaises(ValueError):
            validate_url("https://127.0.0.1")
            
        with self.assertRaises(ValueError):
            validate_url("https://10.0.0.1")
            
        with self.assertRaises(ValueError):
            validate_url("https://169.254.169.254")

    def test_ip_extraction(self):
        self.assertEqual(extract_ip("192.0.2.10"), "192.0.2.10")
        self.assertEqual(extract_ip("ip=192.0.2.10\nloc=US"), "192.0.2.10")
        self.assertEqual(extract_ip("2001:db8::10"), "2001:db8::10")
        self.assertIsNone(extract_ip("Hello World"))

class TestPhase3Egress(unittest.TestCase):
    @patch('claude_shield.probes.egress.run_python_probe')
    @patch('claude_shield.probes.egress.run_curl_probe')
    def test_egress_consistency_pass(self, mock_curl, mock_py):
        mock_py.return_value = ("192.0.2.10", "direct_pinned")
        mock_curl.return_value = ("192.0.2.10", "direct_pinned")
        
        ep = ProbeEndpoint("test", "test", "https://example.com", True, True, False, "text", 1024)
        ctx = ProbeContext(5, ep)
        
        check = check_egress_consistency(ctx)
        self.assertEqual(check.status, "pass")
        self.assertEqual(len(check.evidence), 3) # IPv4, IPv6, proxy_metadata
        
        # Test Redaction works
        ev = check.evidence[0]
        self.assertTrue(ev.data["observed_address"].startswith("<IPV4:"))

    @patch('claude_shield.probes.egress.run_python_probe')
    @patch('claude_shield.probes.egress.run_curl_probe')
    def test_egress_consistency_warning(self, mock_curl, mock_py):
        mock_py.return_value = ("192.0.2.10", "direct_pinned")
        mock_curl.return_value = ("198.51.100.20", "direct_pinned")
        
        ep = ProbeEndpoint("test", "test", "https://example.com", True, True, False, "text", 1024)
        ctx = ProbeContext(5, ep)
        
        check = check_egress_consistency(ctx)
        self.assertEqual(check.status, "warning")
        self.assertTrue("differ across runtimes" in check.explanation)

    @patch('claude_shield.probes.egress.run_python_probe')
    @patch('claude_shield.probes.egress.run_curl_probe')
    def test_egress_consistency_unknown(self, mock_curl, mock_py):
        mock_py.return_value = ("192.0.2.10", "direct_pinned")
        mock_curl.return_value = None
        
        ep = ProbeEndpoint("test", "test", "https://example.com", True, True, False, "text", 1024)
        ctx = ProbeContext(5, ep)
        
        check = check_egress_consistency(ctx)
        self.assertEqual(check.status, "unknown")
        self.assertEqual(len(check.evidence), 2) # Diff, proxy_metadata

if __name__ == '__main__':
    unittest.main()
