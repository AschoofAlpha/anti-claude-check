import os
import uuid
import hashlib
from typing import Dict, Any
from .base import RemediationExecutor

class ReportRedactionExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "redact-report"

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
        if not os.path.exists(target):
            return None
            
        if not target.endswith('.json') and not target.endswith('.md'):
            return None
            
        before_hash = self.inspect(target)
        
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        from ...redaction import Redactor
        redactor = Redactor()
        if target.endswith('.json'):
            import json
            try:
                data = json.loads(content)
                redacted_data = redactor.scan_and_redact(data)
                new_content = json.dumps(redacted_data, indent=2)
            except Exception:
                new_content = redactor._redact_string(content)
        else:
            new_content = redactor._redact_string(content)
            
        if content == new_content:
            return None # Already redacted or nothing to redact
            
        # We output to a new file, not in place
        if target.endswith('.json'):
            new_target = target.replace('.json', '.redacted.json')
        else:
            new_target = target.replace('.md', '.redacted.md')

        import difflib
        diff = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=target,
            tofile=new_target + " (planned)"
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
            "side_effects": [f"Creates {new_target} with redacted content"],
            "limitations": ["Original file is kept intact"],
            "planned_change": {
                "new_target": new_target,
                "new_content": new_content,
                "diff": "".join(diff)
            }
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("Report file changed before apply")
            
        new_target = plan["planned_change"]["new_target"]
        
        # This action creates a new file, so rollback means deleting the new file.
        plan["planned_change"]["rollback_data"] = {"created_file": new_target}
        
        with open(new_target, 'w', encoding='utf-8', newline='') as f:
            f.write(plan["planned_change"]["new_content"])
            
        return True

    def verify(self, plan: Dict[str, Any]) -> str:
        new_target = plan["planned_change"]["new_target"]
        if not os.path.exists(new_target):
            return "failed"
            
        current = self.inspect(new_target)
        if current != plan["expected_after_fingerprint"]:
            return "drift_detected"
            
        # We trust Redactor here
        return "verified"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        new_target = plan.get("planned_change", {}).get("rollback_data", {}).get("created_file")
        if not new_target:
            return False
            
        if os.path.exists(new_target):
            # Only remove if it matches what we wrote
            if self.inspect(new_target) == plan["expected_after_fingerprint"]:
                os.remove(new_target)
                return True
            else:
                raise Exception("Rollback aborted: redacted file has been modified")
                
        return True # already gone
