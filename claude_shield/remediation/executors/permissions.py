import os
import uuid
import stat
from typing import Dict, Any
from .base import RemediationExecutor

class PermissionsExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "permissions"

    @property
    def executor_version(self) -> str:
        return "1.0.0"

    def inspect(self, target: str) -> str:
        if not os.path.exists(target):
            return "not_exists"
        st = os.stat(target)
        return str(st.st_mode)

    def plan(self, target: str) -> Dict[str, Any]:
        if not os.path.exists(target):
            return None
            
        # We don't support Windows ACL fixes here
        if os.name == 'nt':
            return None

        # Do not modify symlinks or directories unless specified (we only fix files generally)
        if os.path.islink(target) or not os.path.isfile(target):
            return None
            
        st = os.stat(target)
        current_mode = st.st_mode
        
        # Check if it's already safe (no group/other permissions)
        if (current_mode & 0o077) == 0:
            return None
            
        # Do not modify files we don't own (if POSIX)
        if hasattr(os, 'getuid') and st.st_uid != os.getuid():
            return None

        new_mode = current_mode & ~0o077

        return {
            "action_id": str(uuid.uuid4()),
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "target": target,
            "risk": "low",
            "requires_confirmation": True,
            "requires_admin": False,
            "reversible": True,
            "before_fingerprint": str(current_mode),
            "expected_after_fingerprint": str(new_mode),
            "side_effects": ["Removes read/write/execute permissions for group and others"],
            "limitations": ["Does not fix Windows ACLs", "Does not change ownership"],
            "planned_change": {
                "old_mode": oct(current_mode),
                "new_mode": oct(new_mode)
            }
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        if os.name == 'nt':
            return False
            
        target = plan["target"]
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("File permissions changed before apply")
            
        new_mode = int(plan["planned_change"]["new_mode"], 8)
        
        # Keep old mode for rollback
        plan["planned_change"]["rollback_data"] = {"old_mode": plan["before_fingerprint"]}
        
        os.chmod(target, new_mode)
        return True

    def verify(self, plan: Dict[str, Any]) -> str:
        target = plan["target"]
        if not os.path.exists(target):
            return "failed"
            
        current = self.inspect(target)
        if current == plan["expected_after_fingerprint"]:
            return "verified"
            
        if (int(current) & 0o077) != 0:
            return "drift_detected"
            
        return "partial"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        
        if self.inspect(target) == plan["before_fingerprint"]:
            return True
            
        if self.inspect(target) != plan["expected_after_fingerprint"]:
            raise Exception("Rollback aborted: drift detected")
            
        old_mode_str = plan.get("planned_change", {}).get("rollback_data", {}).get("old_mode")
        if not old_mode_str:
            return False
            
        old_mode = int(old_mode_str)
        os.chmod(target, old_mode)
        return True
