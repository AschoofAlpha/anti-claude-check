import os
import shutil
import hashlib
import uuid
import stat
from pathlib import Path
from typing import Dict, Any
from .base import RemediationExecutor

class GitIgnoreExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "gitignore"

    @property
    def executor_version(self) -> str:
        return "1.0.0"

    def _hash_file(self, target: str) -> str:
        if not os.path.exists(target):
            return "not_exists"
        with open(target, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def inspect(self, target: str) -> str:
        return self._hash_file(target)

    def plan(self, target: str) -> Dict[str, Any]:
        before_hash = self._hash_file(target)
        
        # We must not ignore examples automatically
        rules_to_add = [".env", ".env.local", ".env.*.local", "reports/", ".claude-shield/"]
        forbidden_rules = [".env.example", ".env.template", ".env.sample"]
        
        current_content = ""
        if os.path.exists(target):
            # If it's a symlink or weird file, we can't reliably plan
            if os.path.islink(target) or not os.path.isfile(target):
                return None
            try:
                with open(target, 'r', encoding='utf-8') as f:
                    current_content = f.read()
            except UnicodeDecodeError:
                # File encoding cannot be reliably preserved
                return None
                
        existing_lines = [line.strip() for line in current_content.splitlines()]
        
        # Check conflicts
        for rule in rules_to_add:
            negation = f"!{rule}"
            if negation in existing_lines:
                return None # Conflict with ! rule
                
        if "BEGIN Claude Shield managed rules" in current_content:
            return None # Already managed
            
        new_content = current_content
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'
            
        new_content += "# BEGIN Claude Shield managed rules\n"
        for r in rules_to_add:
            new_content += f"{r}\n"
        new_content += "# END Claude Shield managed rules\n"
            
        import difflib
        diff = list(difflib.unified_diff(
            current_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=target,
            tofile=target + " (planned)"
        ))

        return {
            "action_id": str(uuid.uuid4()),
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "target": target,
            "risk": "low",
            "requires_confirmation": True,
            "requires_admin": False,
            "reversible": True,
            "before_fingerprint": before_hash,
            "expected_after_fingerprint": hashlib.sha256(new_content.encode('utf-8')).hexdigest(),
            "side_effects": ["Modifies git index ignored status for matching files"],
            "limitations": ["Nested .gitignore or info/exclude may override these rules"],
            "planned_change": {
                "new_content": new_content,
                "diff": "".join(diff)
            }
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("File changed before apply")
            
        from ..transaction import Transaction
        tx = Transaction(transaction_id)
        backup_path = tx.tx_dir / f"backup_{hashlib.md5(target.encode()).hexdigest()}"
        
        if plan["before_fingerprint"] != "not_exists":
            shutil.copy2(target, backup_path)
            
        plan["planned_change"]["rollback_data"] = {"backup_path": str(backup_path)}
        
        with open(target, 'w', encoding='utf-8', newline='') as f:
            f.write(plan["planned_change"]["new_content"])
            
        return True

    def verify(self, plan: Dict[str, Any]) -> str:
        target = plan["target"]
        if not os.path.exists(target):
            return "failed"
            
        current_hash = self.inspect(target)
        if current_hash != plan["expected_after_fingerprint"]:
            return "drift_detected"
            
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if "BEGIN Claude Shield managed rules" in content:
            return "verified"
            
        return "failed"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        
        # Idempotency check: if it matches before_fingerprint already, we are done
        if self.inspect(target) == plan["before_fingerprint"]:
            return True
            
        # Stop if drift occurred since apply (expected_after_fingerprint should match current)
        # Note: if it's partially drifted, we might still want to roll back, but safe default is reject.
        # But wait, rollback should work if the current state is EXACTLY what we applied
        if self.inspect(target) != plan["expected_after_fingerprint"]:
            raise Exception(f"Rollback aborted: drift detected in {target}")
            
        backup_path = plan.get("planned_change", {}).get("rollback_data", {}).get("backup_path")
        
        if plan["before_fingerprint"] == "not_exists":
            if os.path.exists(target):
                os.remove(target)
            return True
            
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, target)
            return True
            
        return False
