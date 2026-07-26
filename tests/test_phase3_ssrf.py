import unittest
import socket
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from claude_shield.probes.safety import resolve_and_validate_url

class TestSSRF(unittest.TestCase):
    def test_direct_ips(self):
        blocked = [
            "127.0.0.1", "::1", "0.0.0.0", "169.254.169.254",
            "10.0.0.1", "172.16.0.1", "192.168.1.1", "100.64.0.1",
            "fc00::1", "fe80::1", "ff00::1", "::ffff:127.0.0.1"
        ]
        for ip in blocked:
            with self.assertRaises(ValueError, msg=f"Failed to block {ip}"):
                resolve_and_validate_url(f"https://[{ip}]" if ":" in ip else f"https://{ip}")
                
    @patch('claude_shield.probes.safety.socket.getaddrinfo')
    def test_dns_resolution(self, mock_getaddrinfo):
        # Mocking public IP
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('192.0.2.10', 443))]
        resolve_and_validate_url("https://example.com")
        
        # Mocking private IP
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('10.0.0.1', 443))]
        with self.assertRaises(ValueError):
            resolve_and_validate_url("https://example.internal")
            
        # Mocking mixed IPs
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('192.0.2.10', 443)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('10.0.0.1', 443))
        ]
        with self.assertRaises(ValueError):
            resolve_and_validate_url("https://example.mixed")

    @patch('claude_shield.probes.http_probe.socket.create_connection')
    @patch('claude_shield.probes.http_probe.ssl.create_default_context')
    def test_pinned_https_connection(self, mock_ssl_ctx, mock_create_conn):
        from claude_shield.probes.http_probe import fetch_http, PinnedHTTPSConnection
        
        mock_ctx_instance = unittest.mock.MagicMock()
        mock_ssl_ctx.return_value = mock_ctx_instance
        
        conn = PinnedHTTPSConnection('example.com', 443, pinned_ip='192.0.2.100')
        conn._context = mock_ctx_instance
        conn.connect()
        
        # TCP connection to pinned IP
        mock_create_conn.assert_called_with(('192.0.2.100', 443), conn.timeout, conn.source_address)
        
        # TLS SNI using hostname
        mock_ctx_instance.wrap_socket.assert_called_once_with(
            mock_create_conn.return_value, 
            server_hostname='example.com'
        )

if __name__ == '__main__':
    unittest.main()
