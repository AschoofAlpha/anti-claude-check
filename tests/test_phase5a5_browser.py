import unittest
import os
import shutil
import tempfile
import json
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from claude_shield.browser.discovery import detect_browser, is_safe_executable
from claude_shield.browser.profile import create_profile, load_manifest, is_profile_in_use, get_profile_dir, list_profiles, quarantine_profile, reset_profile
from claude_shield.browser.launcher import launch_profile
from claude_shield.browser.inspection import inspect_profile, calculate_risk
from claude_shield.browser.chrome_flags import sanitize_flags

class TestPhase5a5Browser(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_home = os.environ.get('HOME', '')
        os.environ['HOME'] = self.test_dir
        
        # We also need to mock Path.home() because some modules import Path at module level
        self.patcher = patch('claude_shield.browser.profile.Path.home')
        self.mock_home = self.patcher.start()
        self.mock_home.return_value = Path(self.test_dir)
        
    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)
        if self.original_home:
            os.environ['HOME'] = self.original_home
        else:
            del os.environ['HOME']
            
    # --- DISCOVERY TESTS ---
    
    @patch('claude_shield.browser.discovery.is_safe_executable')
    @patch('claude_shield.browser.discovery.os.path.exists')
    def test_discovery_no_browser(self, mock_exists, mock_safe):
        mock_exists.return_value = False
        info = detect_browser()
        self.assertFalse(info["detected"])
        
    @patch('claude_shield.browser.discovery.get_browser_version')
    @patch('claude_shield.browser.discovery.is_safe_executable')
    @patch('claude_shield.browser.discovery.os.path.exists')
    def test_discovery_custom_path(self, mock_exists, mock_safe, mock_version):
        mock_exists.return_value = True
        mock_safe.return_value = True
        mock_version.return_value = "114.0.0.0"
        
        info = detect_browser("/custom/chrome")
        self.assertTrue(info["detected"])
        self.assertEqual(info["version"], "114.0.0.0")

    def test_sanitize_flags(self):
        flags = [
            "--no-first-run",
            "--disable-blink-features=AutomationControlled", # Prohibited
            "--remote-debugging-port=9222", # Prohibited
            "--disable-extensions"
        ]
        sanitized = sanitize_flags(flags)
        self.assertIn("--no-first-run", sanitized)
        self.assertIn("--disable-extensions", sanitized)
        self.assertNotIn("--disable-blink-features=AutomationControlled", sanitized)
        self.assertNotIn("--remote-debugging-port=9222", sanitized)

    # --- CREATE & PROFILE TESTS ---
    
    def test_create_profile(self):
        info = {"path": "/fake/chrome", "version": "1.0", "detected": True}
        pid = create_profile(info)
        
        self.assertIsNotNone(pid)
        p_dir = get_profile_dir(pid)
        self.assertTrue(p_dir.exists())
        self.assertTrue((p_dir / 'manifest.json').exists())
        self.assertTrue((p_dir / 'profile').exists())
        self.assertTrue((p_dir / 'audit').exists())
        
        manifest = load_manifest(pid)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["profile_id"], pid)
        self.assertEqual(manifest["browser_version"], "1.0")
        
        profiles = list_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["profile_id"], pid)

    # --- LAUNCH TESTS ---
    
    @patch('claude_shield.browser.launcher.subprocess.Popen')
    @patch('claude_shield.browser.launcher.detect_browser')
    def test_launch_profile(self, mock_detect, mock_popen):
        mock_detect.return_value = {"detected": True, "path": "/fake/chrome", "version": "1.0"}
        mock_popen.return_value = MagicMock()
        
        pid = create_profile({"path": "/fake/chrome", "version": "1.0"})
        
        process = launch_profile(pid, disable_extensions=True, extra_args=["--some-safe-arg"])
        self.assertIsNotNone(process)
        
        # Check that subprocess was called with correct args
        called_args = mock_popen.call_args[0][0]
        self.assertEqual(called_args[0], "/fake/chrome")
        self.assertIn("--disable-extensions", called_args)
        self.assertIn("--some-safe-arg", called_args)
        
        # Ensure user-data-dir is present
        data_dir_arg = next(arg for arg in called_args if arg.startswith("--user-data-dir="))
        self.assertTrue(data_dir_arg.endswith("profile"))
        
        # Verify launch count incremented
        manifest = load_manifest(pid)
        self.assertEqual(manifest["launch_count"], 1)

    @patch('claude_shield.browser.launcher.is_profile_in_use')
    def test_launch_in_use(self, mock_in_use):
        mock_in_use.return_value = True
        pid = create_profile({"path": "/fake/chrome"})
        with self.assertRaises(Exception) as context:
            launch_profile(pid)
        self.assertIn("in use", str(context.exception))
        
    # --- INSPECT TESTS ---
    
    def test_inspect_empty(self):
        pid = create_profile({"path": "/fake/chrome"})
        report = inspect_profile(pid)
        self.assertTrue(report["managed"])
        self.assertFalse(report["in_use"])
        self.assertEqual(report["extension_count"], 0)
        self.assertFalse(report["sync_configuration_detected"])
        
        risk = calculate_risk(report)
        self.assertEqual(risk, "Pass")
        
    def test_inspect_with_data(self):
        pid = create_profile({"path": "/fake/chrome"})
        p_dir = get_profile_dir(pid)
        
        # Mock some extensions and cookies
        ext_dir = p_dir / 'profile' / 'Extensions'
        ext_dir.mkdir(parents=True)
        (ext_dir / 'ext1').mkdir()
        (ext_dir / 'ext2').mkdir()
        
        cookies_dir = p_dir / 'profile' / 'Network'
        cookies_dir.mkdir(parents=True)
        (cookies_dir / 'Cookies').touch()
        
        report = inspect_profile(pid)
        self.assertEqual(report["extension_count"], 2)
        self.assertTrue(report["cookie_store_present"])
        self.assertFalse(report["password_store_present"])
        
        risk = calculate_risk(report)
        self.assertEqual(risk, "Info")
        
    # --- LIFECYCLE / QUARANTINE / RESET TESTS ---

    def test_quarantine_profile(self):
        pid = create_profile({"path": "/fake/chrome"})
        
        quarantine_profile(pid)
        
        # The profile dir should not exist in the root anymore
        self.assertFalse(get_profile_dir(pid).exists())
        
        # It should be in quarantine
        q_dir = Path(self.test_dir) / '.claude-shield' / 'browser-profiles' / 'quarantine'
        self.assertTrue(q_dir.exists())
        q_items = list(q_dir.iterdir())
        self.assertEqual(len(q_items), 1)
        self.assertIn(pid, q_items[0].name)
        
    def test_reset_profile(self):
        pid = create_profile({"path": "/fake/chrome"})
        
        old_path, new_id = reset_profile(pid)
        
        self.assertEqual(pid, new_id) # ID stays the same
        self.assertTrue(os.path.exists(old_path)) # Old data exists in quarantine
        
        # New profile dir should be fresh
        p_dir = get_profile_dir(pid)
        self.assertTrue(p_dir.exists())
        
        manifest = load_manifest(pid)
        self.assertEqual(manifest["generation"], 2)
        
    @patch('claude_shield.browser.profile.is_profile_in_use')
    def test_quarantine_in_use(self, mock_in_use):
        pid = create_profile({"path": "/fake/chrome"})
        mock_in_use.return_value = True
        
        with self.assertRaises(Exception) as context:
            quarantine_profile(pid)
        self.assertIn("in use", str(context.exception))

if __name__ == '__main__':
    unittest.main()
