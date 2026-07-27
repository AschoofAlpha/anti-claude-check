import os
import shutil
import hashlib
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any
from .base import RemediationExecutor

class QuarantineExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "quarantine"

    @property
    def executor_version(self) -> str:
        return "1.0.0"

    def inspect(self, target: str) -> str:
        if not os.path.exists(target):
            return "not_exists"
        with open(target, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def plan(self, target: str) -> Dict[str, Any]:
        if not os.path.exists(target):
            return None
            
        # Refuse to automatically plan isolation for raw .env or browser data unless explicitly commanded
        # In a real app we'd verify the target against explicit user intent flag, 
        # but for the plan generation we'll allow it if it's a report or log
        basename = os.path.basename(target)
        if basename == '.env' or 'browser-profiles' in target:
            return None
            
        before_hash = self.inspect(target)
        
        return {
            "action_id": str(uuid.uuid4()),
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "target": target,
            "risk": "medium",
            "requires_confirmation": True,
            "requires_admin": False,
            "reversible": True,
            "before_fingerprint": before_hash,
            "expected_after_fingerprint": "not_exists",
            "side_effects": [f"Moves {target} to Claude Shield quarantine directory"],
            "limitations": ["Does not securely wipe the file from disk"],
            "planned_change": {}
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("File changed before apply")
            
        q_dir = Path.home() / '.claude-shield' / 'quarantine'
        q_dir.mkdir(parents=True, exist_ok=True)
        if os.name == 'posix':
            os.chmod(q_dir, 0o700)
            
        timestamp = int(datetime.datetime.utcnow().timestamp())
        dest_name = f"{os.path.basename(target)}_{timestamp}_{uuid.uuid4().hex[:8]}"
        dest_path = q_dir / dest_name
        
        plan["planned_change"]["rollback_data"] = {"quarantine_path": str(dest_path)}
        
        shutil.move(target, str(dest_path))
        return True

    def verify(self, plan: Dict[str, Any]) -> str:
        target = plan["target"]
        if os.path.exists(target):
            return "failed"
            
        q_path = plan.get("planned_change", {}).get("rollback_data", {}).get("quarantine_path")
        if not q_path or not os.path.exists(q_path):
            return "partial"
            
        return "verified"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        
        if self.inspect(target) == plan["before_fingerprint"]:
            return True
            
        if self.inspect(target) != plan["expected_after_fingerprint"]:
            raise Exception("Rollback aborted: new file exists at target location")
            
        q_path = plan.get("planned_change", {}).get("rollback_data", {}).get("quarantine_path")
        if not q_path or not os.path.exists(q_path):
            return False
            
        shutil.move(q_path, target)
        return True
