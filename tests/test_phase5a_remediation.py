import unittest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from claude_shield.remediation.executors.gitignore import GitIgnoreExecutor
from claude_shield.remediation.executors.quarantine import QuarantineExecutor
from claude_shield.remediation.executors.env_template import EnvTemplateExecutor
from claude_shield.remediation.executors.permissions import PermissionsExecutor
from claude_shield.remediation.executors.git_unstage import GitUnstageExecutor
from claude_shield.remediation.transaction import Transaction
from unittest.mock import MagicMock

class TestRemediationMVP(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_home = os.environ.get('HOME', '')
        os.environ['HOME'] = self.test_dir
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        os.environ['HOME'] = self.original_home

    @patch('claude_shield.remediation.transaction.Path.home')
    def test_gitignore_executor(self, mock_home):
        mock_home.return_value = Path(self.test_dir)
        executor = GitIgnoreExecutor()
        target = os.path.join(self.test_dir, ".gitignore")
        with open(target, 'w') as f:
            f.write("node_modules/\n")
            
        plan = executor.plan(target)
        self.assertIsNotNone(plan)
        self.assertIsNotNone(plan["action_id"])
        self.assertEqual(plan["executor_id"], "gitignore")
        
        tx = Transaction()
        success = executor.apply(plan, tx.tx_id)
        self.assertTrue(success)
        
        self.assertTrue(executor.verify(plan))
        
        with open(target, 'r') as f:
            content = f.read()
            self.assertIn(".env", content)
            
        success = executor.rollback(plan, tx.tx_id)
        self.assertTrue(success)
        
        with open(target, 'r') as f:
            content = f.read()
            self.assertNotIn(".env", content)

    @patch('claude_shield.remediation.transaction.Path.home')
    def test_quarantine_executor(self, mock_home):
        mock_home.return_value = Path(self.test_dir)
        executor = QuarantineExecutor()
        target = os.path.join(self.test_dir, "bad_report.json")
        with open(target, 'w') as f:
            f.write("{}")
            
        plan = executor.plan(target)
        self.assertIsNotNone(plan)
        self.assertIsNotNone(plan["action_id"])
        self.assertEqual(plan["executor_id"], "quarantine")
        
        tx = Transaction()
        # Mock Path.home for quarantine apply too
        with patch('claude_shield.remediation.executors.quarantine.Path.home') as mock_q_home:
            mock_q_home.return_value = Path(self.test_dir)
            success = executor.apply(plan, tx.tx_id)
            self.assertTrue(success)
            self.assertTrue(executor.verify(plan))
            
            self.assertFalse(os.path.exists(target))
            
            success = executor.rollback(plan, tx.tx_id)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(target))

    def test_env_template_executor(self):
        executor = EnvTemplateExecutor()
        env_path = os.path.join(self.test_dir, ".env")
        target = os.path.join(self.test_dir, ".env.example")
        
        with open(env_path, 'w') as f:
            f.write("SECRET=12345\n")
            
        plan = executor.plan(target)
        self.assertIsNotNone(plan)
        self.assertIsNotNone(plan["action_id"])
        self.assertEqual(plan["executor_id"], "env-template")
        
        tx = Transaction()
        success = executor.apply(plan, tx.tx_id)
        self.assertTrue(success)
        
        # Verify template
        self.assertTrue(os.path.exists(target))
        with open(target, 'r') as f:
            content = f.read()
            self.assertEqual(content, "SECRET=\n")
            
        v_status = executor.verify(plan)
        self.assertTrue(v_status)


    @patch('claude_shield.remediation.transaction.Path.home')
    def test_permissions_executor(self, mock_home):
        mock_home.return_value = Path(self.test_dir)
        executor = PermissionsExecutor()
        target = os.path.join(self.test_dir, "sensitive.key")
        with open(target, 'w') as f:
            f.write("key=123")
            
        with patch('claude_shield.remediation.executors.permissions.os') as mock_os:
            mock_os.name = 'posix'
            mock_st = MagicMock()
            mock_st.st_mode = 0o666
            mock_st.st_uid = 1000
            mock_os.stat.return_value = mock_st
            mock_os.getuid.return_value = 1000
            mock_os.chmod = MagicMock()
            mock_os.path.exists.return_value = True
            mock_os.path.isfile.return_value = True
            mock_os.path.islink.return_value = False
            
            plan = executor.plan(target)
            self.assertIsNotNone(plan)
            self.assertIsNotNone(plan["action_id"])
            self.assertEqual(plan["executor_id"], "permissions")
            
            tx = Transaction()
            
            success = executor.apply(plan, tx.tx_id)
            self.assertTrue(success)
            mock_os.chmod.assert_called_once_with(target, 0o600)
            
            # verify
            mock_st.st_mode = 0o600
            v_status = executor.verify(plan)
            self.assertEqual(v_status, "verified")
            
            # rollback
            success = executor.rollback(plan, tx.tx_id)
            self.assertTrue(success)
            mock_os.chmod.assert_called_with(target, 0o666)
                
            with patch('claude_shield.remediation.executors.permissions.os.chmod') as mock_chmod_rollback:
                with patch('claude_shield.remediation.executors.permissions.os.name', 'posix'):
                    success = executor.rollback(plan, tx.tx_id)
                self.assertTrue(success)

    @patch('claude_shield.remediation.transaction.Path.home')
    @patch('claude_shield.remediation.executors.git_unstage.subprocess.run')
    def test_git_unstage_executor(self, mock_run, mock_home):
        mock_home.return_value = Path(self.test_dir)
        executor = GitUnstageExecutor()
        target = os.path.join(self.test_dir, "staged_file.txt")
        
        # mock repo exists
        with patch('claude_shield.remediation.executors.git_unstage.os.path.exists', return_value=True):
            # 1. plan
            mock_run.return_value = MagicMock(returncode=0, stdout="100644 abcdef123 0       staged_file.txt\n")
            plan = executor.plan(target)
            self.assertIsNotNone(plan)
            self.assertIsNotNone(plan["action_id"])
            self.assertEqual(plan["executor_id"], "git-unstage")
            self.assertIsNotNone(plan["before_fingerprint"])
            
            # 2. apply
            tx = Transaction()
            success = executor.apply(plan, tx.tx_id)
            self.assertTrue(success)
            
            # 3. verify
            mock_run.return_value = MagicMock(returncode=1, stdout="") # not in index
            v_status = executor.verify(plan)
            self.assertEqual(v_status, "verified")
            
            # 4. rollback
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            success = executor.rollback(plan, tx.tx_id)
            self.assertTrue(success)
        mock_run.assert_called_with(
            ['git', 'update-index', '--add', '--cacheinfo', f"100644,abcdef123,{target}"],
            capture_output=True,
            timeout=10,
            env=mock_run.call_args_list[-1][1]['env']
        )

if __name__ == '__main__':
    unittest.main()
