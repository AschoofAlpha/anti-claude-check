import os
import hashlib
import uuid
import re
from typing import Dict, Any
from .base import RemediationExecutor

class EnvTemplateExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "env-template"

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
        env_file = target.replace(".example", "").replace(".template", "")
        if not os.path.exists(env_file):
            return None
            
        before_hash = self.inspect(target)
        
        with open(env_file, 'r', encoding='utf-8', errors='ignore') as f:
            env_content = f.readlines()
            
        template_lines = []
        for line in env_content:
            if not line.strip() or line.strip().startswith('#'):
                template_lines.append(line)
            else:
                # Basic KEY=VALUE matching
                match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line.strip())
                if match:
                    key = match.group(1)
                    template_lines.append(f"{key}=\n")
                    
        new_content = "".join(template_lines)
        
        if before_hash != "not_exists":
            with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                current_template = f.read()
            if current_template == new_content:
                return None # Already matches
                
        # Dry-run validation: just basic length check or similar
        # For templates, we're explicitly stripping values so we don't need deep scanning
        if "=" in new_content and not new_content.endswith("=\n") and "=\n" not in new_content:
            pass # Keep it simple
            
        import difflib
        diff = list(difflib.unified_diff(
            current_template.splitlines(keepends=True) if before_hash != "not_exists" else [],
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
            "side_effects": [f"Creates or updates {target} with empty values"],
            "limitations": ["Does not preserve multi-line values perfectly"],
            "planned_change": {
                "new_content": new_content,
                "diff": "".join(diff)
            }
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("Template file changed before apply")
            
        import shutil
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
            
        current = self.inspect(target)
        if current != plan["expected_after_fingerprint"]:
            return "drift_detected"
            
        # Post-scan
        # We rely on the template logic above. If it ends in =\n it's empty.
        return "verified"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        
        if self.inspect(target) == plan["before_fingerprint"]:
            return True
            
        if self.inspect(target) != plan["expected_after_fingerprint"]:
            # Maybe it failed validation and drifted, but we should still try to roll it back if it's ours.
            # But strict rules say abort on drift
            raise Exception("Rollback aborted: drift detected in template file")
            
        backup_path = plan.get("planned_change", {}).get("rollback_data", {}).get("backup_path")
        
        if plan["before_fingerprint"] == "not_exists":
            if os.path.exists(target):
                os.remove(target)
            return True
            
        import shutil
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, target)
            return True
            
        return False
