import unittest
import tempfile
import os
import subprocess
import json
import shutil
from pathlib import Path
from claude_shield.remediation.planner import generate_plan
from claude_shield.remediation.transaction import Transaction

class TestE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        # Initialize git repo
        subprocess.run(['git', 'init'], capture_output=True)
        # Setup fake home to avoid touching real ~/.claude-shield
        self.fake_home = tempfile.mkdtemp()
        os.environ['USERPROFILE'] = self.fake_home
        os.environ['HOME'] = self.fake_home

    def tearDown(self):
        os.chdir(self.old_cwd)
        def remove_readonly(func, path, _):
            import stat
            os.chmod(path, stat.S_IWRITE)
            try:
                func(path)
            except:
                pass
        shutil.rmtree(self.temp_dir, onerror=remove_readonly)
        shutil.rmtree(self.fake_home, onerror=remove_readonly)

    def test_scenario_a_safe_workspace(self):
        with open('.gitignore', 'w') as f:
            f.write(".env\n")
        
        checks = []
        plan = generate_plan(checks)
        self.assertFalse(plan.get('actions'))

    def test_scenario_b_sensitive_env(self):
        with open('.env', 'w') as f:
            f.write("SECRET=123456\n")
        
        subprocess.run(['git', 'add', '.env'], capture_output=True)
        
        checks = [
            {"risk_type": "missing_gitignore", "target": ".gitignore", "rule": ".env"},
            {"risk_type": "missing_env_example", "target": ".env.example"}
        ]
        
        plan = generate_plan(checks)
        self.assertTrue(plan.get('actions'))
        
        plan_str = json.dumps(plan)
        self.assertNotIn('123456', plan_str)
        
        tx = Transaction()
        tx.save_plan(plan)
        tx.apply(plan)
        
        self.assertTrue(os.path.exists('.env.example'))
        with open('.gitignore', 'r') as f:
            self.assertIn('.env', f.read())
            
        try:
            tx.rollback()
        except Exception as e:
            print("Rollback exception:", e)
            raise
        self.assertFalse(os.path.exists('.env.example'))

    def test_scenario_e_drift_and_conflict(self):
        with open('.gitignore', 'w') as f:
            f.write("old\n")
            
        checks = [{"risk_type": "missing_gitignore", "target": ".gitignore"}]
        plan = generate_plan(checks)
        
        # Modify the file to cause drift before apply
        with open('.gitignore', 'w') as f:
            f.write("new\n")
        self.assertTrue(plan.get('actions'))

    def test_scenario_c_unredacted_report(self):
        from claude_shield.remediation.executors.report_redaction import ReportRedactionExecutor
        from claude_shield.remediation.executors.quarantine import QuarantineExecutor
        
        raw_report = {
            "ip": "192.0.2.10",
            "path": "C:\\Users\\SecretUser\\docs",
            "token": "ghp_1234567890abcdef1234567890abcdef12345678"
        }
        with open('report.json', 'w') as f:
            json.dump(raw_report, f)
            
        redact_ex = ReportRedactionExecutor()
        r_plan = redact_ex.plan('report.json')
        self.assertIsNotNone(r_plan)
        
        tx = Transaction()
        redact_ex.apply(r_plan, tx.tx_id)
        
        # Verify original file intact
        self.assertTrue(os.path.exists('report.json'))
        
        # Verify redacted copy
        redacted_file = 'report.redacted.json'
        self.assertTrue(os.path.exists(redacted_file))
        with open(redacted_file, 'r') as f:
            content = f.read()
            self.assertNotIn('ghp_1234567890abcdef1234567890abcdef12345678', content)
            self.assertNotIn('192.0.2.10', content)
            
        self.assertEqual(redact_ex.verify(r_plan), 'verified')
        redact_ex.rollback(r_plan, tx.tx_id)
        self.assertFalse(os.path.exists(redacted_file))
        
        # Test Quarantine
        q_ex = QuarantineExecutor()
        q_plan = q_ex.plan('report.json')
        self.assertIsNotNone(q_plan)
        q_ex.apply(q_plan, tx.tx_id)
        self.assertFalse(os.path.exists('report.json'))
        self.assertEqual(q_ex.verify(q_plan), 'verified')
        q_ex.rollback(q_plan, tx.tx_id)
        self.assertTrue(os.path.exists('report.json'))

    def test_scenario_d_clean_chrome_profile(self):
        from claude_shield.browser.profile import create_profile, get_profile_dir, load_manifest
        from claude_shield.browser.inspection import inspect_profile
        from claude_shield.remediation.executors.browser_profile import BrowserProfileRemediationExecutor
        
        info = {"path": "/fake/chrome", "version": "1.0", "detected": True}
        profile_id = create_profile(info)
        p_dir = get_profile_dir(profile_id)
        self.assertTrue(p_dir.exists())
        
        # Add fake cookie/extension data
        profile_user_dir = p_dir / 'profile'
        profile_user_dir.mkdir(parents=True, exist_ok=True)
        with open(profile_user_dir / 'Cookies', 'w') as f:
            f.write("fake_cookie_data\n")
            
        info = inspect_profile(profile_id)
        self.assertTrue(info["cookie_store_present"])
        
        ex = BrowserProfileRemediationExecutor()
        plan = ex.plan(profile_id)
        self.assertIsNotNone(plan)
        
        tx = Transaction()
        ex.apply(plan, tx.tx_id)
        self.assertEqual(ex.verify(plan), 'verified')
        
        # Rollback reset
        ex.rollback(plan, tx.tx_id)
        manifest = load_manifest(profile_id)
        self.assertEqual(manifest.get("status"), "active")
        self.assertTrue((profile_user_dir / 'Cookies').exists())
            
if __name__ == '__main__':
    unittest.main()
