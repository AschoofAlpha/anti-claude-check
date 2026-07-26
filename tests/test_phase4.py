import unittest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from claude_shield.scanning.file_scanner import FileScanner
from claude_shield.scanning.entropy import is_high_entropy
from claude_shield.checks.credentials import run_credential_scan
from claude_shield.checks.git_security import run_git_security_check
from claude_shield.browser_import import import_browser_report
from claude_shield.checks.wsl import check_wsl
from claude_shield.checks.docker import check_docker

class TestPhase4Scanner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.test_dir.name)
        
        # Create some files
        (self.workspace / "normal.txt").write_text("Hello world")
        (self.workspace / "secret.env").write_text("API_KEY=AKIAIOSFODNN7REALKEY\n")
        
        # Symlink
        try:
            os.symlink(self.workspace / "normal.txt", self.workspace / "symlink.txt")
        except:
            pass # Windows symlink might fail without admin
            
        # Large file mock
        with open(self.workspace / "large.bin", "wb") as f:
            f.seek(1024 * 1024) # 1 MB
            f.write(b'\0')
            
        # Git dir
        (self.workspace / ".git").mkdir()
        (self.workspace / ".git" / "config").write_text("secret")

    def tearDown(self):
        self.test_dir.cleanup()
        
    def test_file_scanner_limits(self):
        scanner = FileScanner(str(self.workspace), max_file_size=500000) # 500KB
        files = list(scanner.scan())
        
        names = [f.name for f in files]
        self.assertIn("normal.txt", names)
        self.assertIn("secret.env", names)
        self.assertNotIn("large.bin", names) # Filtered by size
        self.assertNotIn("config", names) # Filtered because in .git

    def test_entropy(self):
        self.assertFalse(is_high_entropy("password123"))
        # Base64 string that is highly random
        self.assertTrue(is_high_entropy("vA8zTq2yXmN1pKjL9oR4uE6cW7gB3xH5fS0dYjM=", threshold=3.5))

    @patch('claude_shield.checks.credentials.is_tracked_by_git')
    def test_credential_scan(self, mock_git):
        mock_git.return_value = False
        
        check = run_credential_scan(str(self.workspace))
        self.assertEqual(check.status, "fail")
        self.assertEqual(check.severity, "low") # Untracked
        
        # Simulate tracked
        mock_git.return_value = True
        check2 = run_credential_scan(str(self.workspace))
        self.assertEqual(check2.severity, "high")
        
        # Ensure path is redacted or relative
        path_in_evidence = check2.evidence[0].data['path']
        self.assertTrue("secret.env" in path_in_evidence)

        # Ensure example token logic drops severity but doesn't ignore
        (self.workspace / "example.env").write_text("API_KEY=AKIAIOSFODNN7EXAMPLE\n")
        check3 = run_credential_scan(str(self.workspace))
        
        # Check that evidence was found but maybe scored differently
        self.assertTrue(len(check3.evidence) > 0)

class TestPhase4Git(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.test_dir.name)
        
    def tearDown(self):
        self.test_dir.cleanup()
        
    def test_git_no_repo(self):
        check = run_git_security_check(str(self.workspace))
        self.assertEqual(check.status, "skipped")
        
    def test_git_missing_gitignore(self):
        (self.workspace / ".git").mkdir()
        check = run_git_security_check(str(self.workspace))
        self.assertEqual(check.status, "warning")
        
    def test_git_good_gitignore(self):
        (self.workspace / ".git").mkdir()
        (self.workspace / ".gitignore").write_text(".env\nnode_modules/")
        check = run_git_security_check(str(self.workspace))
        self.assertEqual(check.status, "pass")

class TestPhase4Virtualization(unittest.TestCase):
    @patch('claude_shield.checks.wsl.subprocess.run')
    def test_wsl_mock(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="NAME           STATE           VERSION\n* Ubuntu         Running         2\n".encode('utf-16le'))
        check = check_wsl()
        self.assertEqual(check.status, "pass")
        self.assertTrue(len(check.evidence) > 0)
        self.assertEqual(check.evidence[0].data['distribution_count'], 1)
        self.assertEqual(check.evidence[0].data['running_distribution_count'], 1)
        self.assertEqual(check.evidence[0].data['versions_detected'], ['2'])

    @patch('claude_shield.checks.docker.subprocess.run')
    def test_docker_mock(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        check = check_docker()
        self.assertEqual(check.status, "skipped")

class TestPhase4BrowserImport(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.test_dir.name)
        
    def tearDown(self):
        self.test_dir.cleanup()
        
    def test_import_valid(self):
        report = {
            "version": "1.0.0",
            "browser_env": "chrome",
            "timestamp": "2026-07-25T10:00:00Z",
            "findings": [
                {
                    "id": "network.webrtc",
                    "title": "WebRTC Check",
                    "category": "network",
                    "status": "fail",
                    "severity": "medium",
                    "confidence": "confirmed",
                    "evidence": []
                }
            ]
        }
        
        path = self.workspace / "report.json"
        path.write_text(json.dumps(report))
        
        parsed = import_browser_report(str(path))
        self.assertEqual(len(parsed.checks), 1)
        # Severity should be upgraded to high per browser import rules
        self.assertEqual(parsed.checks[0].severity, "high")
        
    def test_import_invalid_size(self):
        path = self.workspace / "large.json"
        with open(path, "w") as f:
            f.write(" " * (1024 * 1024 + 10))
            
        with self.assertRaises(ValueError):
            import_browser_report(str(path))

if __name__ == '__main__':
    unittest.main()
