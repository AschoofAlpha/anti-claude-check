import unittest
import subprocess
import os
import tempfile
import sys
from pathlib import Path

class TestFallback(unittest.TestCase):
    def test_powershell_fallback(self):
        if os.name != 'nt':
            self.skipTest("PowerShell test only runs on Windows")
            
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'anti-claude-check.ps1'))
        
        # We can't easily mock python globally in PS without a lot of setup,
        # but we can check if it runs remediate successfully without python if we bypass the python call?
        # A simpler way: just run `claude-shield.ps1 remediate` directly with a fake PATH so python is not found.
        
        temp_dir = tempfile.mkdtemp()
        env = os.environ.copy()
        # Remove any path containing python
        env['PATH'] = temp_dir
        
        # Test remediation rejection
        result = subprocess.run(
            ['pwsh', '-NoProfile', '-File', script_path, 'remediate'],
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires python", result.stdout.lower() + result.stderr.lower())

if __name__ == '__main__':
    unittest.main()
