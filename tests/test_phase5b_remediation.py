import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from claude_shield.remediation.executors import get_executor
from claude_shield.remediation.transaction import Transaction, TransactionError

class TestPhase5BRemediation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_gitignore_executor(self):
        executor = get_executor("gitignore")
        self.assertIsNotNone(executor)
        self.assertEqual(executor.executor_id, "gitignore")
        
        target = os.path.join(self.temp_dir, ".gitignore")
        
        # Test Plan when not exists
        plan = executor.plan(target)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["before_fingerprint"], "not_exists")
        
        # Test apply
        tx_id = "test-tx-id"
        with patch('claude_shield.remediation.transaction.Transaction') as mock_tx_class:
            mock_tx = MagicMock()
            mock_tx.tx_dir = Path(self.temp_dir)
            mock_tx_class.return_value = mock_tx
            
            success = executor.apply(plan, tx_id)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(target))
            
            # Verify
            v_status = executor.verify(plan)
            self.assertEqual(v_status, "verified")

    def test_quarantine_executor(self):
        executor = get_executor("quarantine")
        self.assertIsNotNone(executor)
        
        target = os.path.join(self.temp_dir, "sensitive.log")
        with open(target, 'w') as f:
            f.write("test data")
            
        plan = executor.plan(target)
        self.assertIsNotNone(plan)
        
        with patch('claude_shield.remediation.transaction.Transaction') as mock_tx_class:
            mock_tx = MagicMock()
            mock_tx_class.return_value = mock_tx
            
            # Mock the quarantine dir to temp_dir
            with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
                success = executor.apply(plan, "test-tx")
                self.assertTrue(success)
                self.assertFalse(os.path.exists(target)) # Moved away
                
                v_status = executor.verify(plan)
                self.assertEqual(v_status, "verified")
                
                success = executor.rollback(plan, "test-tx")
                self.assertTrue(success)
                self.assertTrue(os.path.exists(target)) # Restored

    def test_transaction_atomicity(self):
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            tx = Transaction()
            
            # Save a plan
            plan_data = {
                "actions": [
                    {
                        "action_id": "test_action",
                        "executor_id": "gitignore",
                        "executor_version": "1.0.0",
                        "target": os.path.join(self.temp_dir, ".gitignore"),
                        "before_fingerprint": "wrong_fingerprint",
                        "expected_after_fingerprint": "dummy",
                        "planned_change": {"new_content": "dummy"}
                    }
                ]
            }
            tx.save_plan(plan_data)
            
            self.assertTrue(os.path.exists(tx.plan_file))
            
            # Apply should fail because fingerprint of dummy will mismatch if we don't mock executor correctly
            # Just testing that failure triggers TransactionError
            with self.assertRaises(TransactionError):
                tx.apply(plan_data)

from pathlib import Path
if __name__ == '__main__':
    unittest.main()
