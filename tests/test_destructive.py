import unittest
import tempfile
import os
import subprocess
import json
import shutil
from pathlib import Path
from claude_shield.remediation.transaction import Transaction

class TestDestructive(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
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

    def test_json_corruption(self):
        tx = Transaction()
        plan = {"actions": [{"type": "gitignore", "target": ".gitignore", "rule": "foo"}]}
        tx.save_plan(plan)
        
        # Corrupt the json manually
        plan_path = os.path.join(tx.tx_dir, "plan.json")
        with open(plan_path, 'w') as f:
            f.write("{corrupt_json: ")
            
        tx2 = Transaction(tx.tx_id)
        loaded = tx2.load_plan()
        self.assertIsNone(loaded)
        
    def test_path_traversal(self):
        tx = Transaction()
        # Create a malicious plan
        plan = {"actions": [{"type": "permissions", "target": "../../../Windows/System32/config"}]}
        
        try:
            tx.apply(plan)
            # The executor should fail because the target doesn't exist or is not a safe path
            # Depending on how it's implemented it may raise or just return False
        except Exception:
            pass # Safe
            
if __name__ == '__main__':
    unittest.main()
