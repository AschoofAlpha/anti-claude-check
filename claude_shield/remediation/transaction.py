import os
import json
import datetime
import tempfile
from pathlib import Path
from typing import Dict, Any

from .executors import get_executor

class TransactionError(Exception):
    pass

class Transaction:
    def __init__(self, transaction_id: str = None):
        self.base_dir = Path.home() / '.claude-shield' / 'transactions'
        
        if transaction_id:
            if '..' in transaction_id or '/' in transaction_id or '\\' in transaction_id:
                raise TransactionError("Invalid transaction ID format")
            self.tx_id = transaction_id
            self.tx_dir = self.base_dir / self.tx_id
            if not self.tx_dir.exists():
                raise TransactionError(f"Transaction {self.tx_id} not found")
        else:
            import secrets
            self.tx_id = f"{datetime.datetime.utcnow().strftime('%Y-%m-%dT%H%M%SZ')}-{secrets.token_hex(4)}"
            self.tx_dir = self.base_dir / self.tx_id
            
            try:
                self.base_dir.mkdir(parents=True, exist_ok=True)
                if os.name == 'posix':
                    os.chmod(self.base_dir, 0o700)
                
                if self.tx_dir.exists():
                    raise TransactionError("Transaction directory already exists")
                self.tx_dir.mkdir()
                if os.name == 'posix':
                    os.chmod(self.tx_dir, 0o700)
            except Exception as e:
                raise TransactionError(f"Failed to create transaction directory: {e}")

        self.plan_file = self.tx_dir / 'plan.json'
        self.applied_file = self.tx_dir / 'applied.json'
        
        self.plan = {}

    def _atomic_write_json(self, path: Path, data):
        fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.tmp")
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            if os.name == 'posix':
                os.chmod(temp_path, 0o600)
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise TransactionError(f"Failed atomic write to {path}: {e}")

    def load_plan(self):
        if self.plan_file.exists():
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                try:
                    self.plan = json.load(f)
                except json.JSONDecodeError:
                    return None
        return self.plan

    def save_plan(self, plan: Dict[str, Any]):
        self.plan = plan
        self._atomic_write_json(self.plan_file, plan)

    def load_applied(self):
        if self.applied_file.exists():
            with open(self.applied_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
        
    def _save_applied(self, results: list):
        self._atomic_write_json(self.applied_file, results)

    def apply(self, plan: Dict[str, Any]):
        expires = plan.get("expires")
        if expires:
            exp_time = datetime.datetime.strptime(expires, "%Y-%m-%dT%H:%M:%S.%fZ")
            if datetime.datetime.utcnow() > exp_time:
                raise TransactionError("status: drift_detected (Plan expired)")
                
        actions = plan.get("actions", [])
        applied_results = []
        
        for action in actions:
            # Write applying state (minimally just append to results)
            # In a true persistent state engine we'd write applying state first.
            ex_id = action.get("executor_id")
            executor = get_executor(ex_id)
            if not executor:
                self._handle_failure(applied_results, action, "Executor not found")
                return
                
            if executor.executor_version != action.get("executor_version"):
                self._handle_failure(applied_results, action, "status: drift_detected (Executor version mismatch)")
                return
                
            # Drift check
            current_fp = executor.inspect(action["target"])
            if current_fp != action["before_fingerprint"]:
                self._handle_failure(applied_results, action, "status: drift_detected (Pre-apply fingerprint mismatch)")
                return
                
            try:
                success = executor.apply(action, self.tx_id)
                if success:
                    applied_results.append({
                        "action": action,
                        "status": "completed"
                    })
                    self._save_applied(applied_results)
                else:
                    self._handle_failure(applied_results, action, "Executor apply returned False")
                    return
            except Exception as e:
                self._handle_failure(applied_results, action, str(e))
                return
                
    def _handle_failure(self, applied_results, failed_action, reason):
        applied_results.append({
            "action": failed_action,
            "status": "failed",
            "reason": reason
        })
        self._save_applied(applied_results)
        self.rollback(applied_results)
        raise TransactionError(f"Transaction aborted and rolled back. Reason: {reason}")
        
    def verify(self) -> Dict[str, str]:
        results = {}
        applied = self.load_applied()
        for res in applied:
            if res["status"] == "completed":
                action = res["action"]
                executor = get_executor(action["executor_id"])
                if executor:
                    try:
                        v_status = executor.verify(action)
                        results[action["action_id"]] = v_status
                    except Exception:
                        results[action["action_id"]] = "failed"
        return results

    def rollback(self, applied_results=None):
        if applied_results is None:
            applied_results = self.load_applied()
            
        rollback_results = []
        for res in reversed(applied_results):
            if res["status"] == "completed":
                action = res["action"]
                executor = get_executor(action["executor_id"])
                if executor:
                    try:
                        success = executor.rollback(action, self.tx_id)
                        rollback_results.append({
                            "action_id": action["action_id"],
                            "status": "rollback_completed" if success else "rollback_partial"
                        })
                    except Exception as e:
                        rollback_results.append({
                            "action_id": action["action_id"],
                            "status": "manual_intervention_required",
                            "reason": str(e)
                        })
                        
        # Append rollback events to applied log to keep audit trail
        applied_results.extend([{"type": "rollback", "results": rollback_results}])
        self._save_applied(applied_results)
        
        for r in rollback_results:
            if r["status"] in ("rollback_partial", "manual_intervention_required"):
                print("Rollback failed:", rollback_results)
                raise TransactionError("Rollback incomplete. manual_intervention_required.")
