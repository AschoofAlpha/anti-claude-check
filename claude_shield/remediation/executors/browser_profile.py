import os
import uuid
import json
from pathlib import Path
from typing import Dict, Any
from .base import RemediationExecutor

class BrowserProfileRemediationExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "browser-profile-reset"

    @property
    def executor_version(self) -> str:
        return "1.0.0"

    def inspect(self, target: str) -> str:
        # Target should be the profile UUID
        from ...browser.profile import get_profile_dir, load_manifest, is_valid_profile_id
        
        if not is_valid_profile_id(target):
            return "invalid_id"
            
        p_dir = get_profile_dir(target)
        if not p_dir.exists():
            return "not_exists"
            
        manifest = load_manifest(target)
        if not manifest or not manifest.get("managed_by_claude_shield"):
            return "not_managed"
            
        from ...browser.lifecycle import is_profile_in_use
        if is_profile_in_use(str(p_dir / 'profile')):
            return "in_use"
            
        # The fingerprint is the generation ID
        return str(manifest.get("generation", 1))

    def plan(self, target: str) -> Dict[str, Any]:
        state = self.inspect(target)
        if state in ("invalid_id", "not_exists", "not_managed", "in_use"):
            return None
            
        generation = int(state)
        
        return {
            "action_id": str(uuid.uuid4()),
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "target": target,
            "risk": "medium",
            "requires_confirmation": True,
            "requires_admin": False,
            "reversible": True,
            "before_fingerprint": state,
            "expected_after_fingerprint": str(generation + 1),
            "side_effects": ["Quarantines current browser profile data", "Creates a fresh profile directory"],
            "limitations": ["Cannot reset if browser is currently running"],
            "planned_change": {
                "diff": f"Quarantine generation {generation} and create generation {generation + 1}\n"
            }
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("Profile changed before apply")
            
        from ...browser.profile import reset_profile
        old_path, new_id = reset_profile(target)
        
        plan["planned_change"]["rollback_data"] = {"quarantined_path": old_path}
        return True

    def verify(self, plan: Dict[str, Any]) -> str:
        target = plan["target"]
        current = self.inspect(target)
        if current == plan["expected_after_fingerprint"]:
            return "verified"
        if current == plan["before_fingerprint"]:
            return "failed"
        return "drift_detected"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        if self.inspect(target) == plan["before_fingerprint"]:
            return True
            
        if self.inspect(target) != plan["expected_after_fingerprint"]:
            raise Exception("Rollback aborted: Profile generation drift detected")
            
        q_path = plan.get("planned_change", {}).get("rollback_data", {}).get("quarantined_path")
        if not q_path or not os.path.exists(q_path):
            return False
            
        from ...browser.profile import get_profile_dir
        p_dir = get_profile_dir(target)
        
        import shutil
        if p_dir.exists():
            shutil.rmtree(p_dir)
            
        shutil.move(q_path, str(p_dir))
        return True
