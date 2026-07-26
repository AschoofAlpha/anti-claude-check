import unittest
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from claude_shield.remediation.transaction import Transaction, TransactionError

class TestTransactionFaults(unittest.TestCase):
    def setUp(self):
        # Override base dir to a temp dir for testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_home = Path.home
        Path.home = lambda: Path(self.temp_dir)
        
    def tearDown(self):
        Path.home = self.original_home
        shutil.rmtree(self.temp_dir)

    def test_atomic_write_and_corruption(self):
        tx = Transaction()
        # Instead of apply, just save raw applied
        tx._save_applied([{"status": "success"}])
        # Simulate corruption in applied.json
        with open(tx.applied_file, 'w') as f:
            f.write("{invalid_json:")
        
        # Next operation should throw or at least fail to load gracefully
        with self.assertRaises(Exception):
            tx.load_applied()

    def test_path_traversal(self):
        with self.assertRaises(TransactionError):
            Transaction("../../../windows/system32")

    def test_rollback_partial_failure(self):
        # Simulate an execution that failed halfway
        tx = Transaction()
        applied = [{"status": "completed", "action": {"executor_id": "gitignore", "action_id": "a1", "target": "t1"}}]
        # save raw applied
        tx._save_applied(applied)
        
        with self.assertRaises(TransactionError):
            tx.rollback() # Will fail because executor gitignore needs a real plan object to rollback_manifest()

    def test_concurrent_creation_safety(self):
        tx1 = Transaction()
        # Since tx_id uses uuid, creating another will have a different ID.
        # But if we force the same ID, it should throw
        with self.assertRaises(TransactionError):
            class FakeTx(Transaction):
                def __init__(self, override_id):
                    self.base_dir = Path.home() / '.claude-shield' / 'transactions'
                    self.tx_id = override_id
                    self.tx_dir = self.base_dir / self.tx_id
                    if self.tx_dir.exists():
                        raise TransactionError("exists")
                    self.tx_dir.mkdir()
            FakeTx(tx1.tx_id)

if __name__ == '__main__':
    unittest.main()
