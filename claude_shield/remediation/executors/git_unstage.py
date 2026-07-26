import os
import subprocess
import uuid
from typing import Dict, Any
from .base import RemediationExecutor

class GitUnstageExecutor(RemediationExecutor):
    @property
    def executor_id(self) -> str:
        return "git-unstage"

    @property
    def executor_version(self) -> str:
        return "1.0.0"
        
    def _get_git_env(self):
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_PAGER'] = 'cat'
        return env

    def inspect(self, target: str) -> str:
        if not os.path.exists('.git'):
            return "not_a_repo"
            
        try:
            # Check if file is in index
            result = subprocess.run(
                ['git', 'ls-files', '-s', target],
                capture_output=True, text=True, timeout=5,
                env=self._get_git_env()
            )
            if result.returncode != 0 or not result.stdout.strip():
                return "not_in_index"
                
            return result.stdout.strip()
        except Exception:
            return "error"

    def plan(self, target: str) -> Dict[str, Any]:
        state = self.inspect(target)
        if state in ("not_a_repo", "not_in_index", "error"):
            return None
            
        # Parse the index state: mode blob stage file
        parts = state.split()
        if len(parts) < 4:
            return None
            
        mode, blob, stage = parts[0], parts[1], parts[2]
        
        # Refuse to unstage if it's a conflict or intent-to-add
        if stage != "0":
            return None

        # Determine expected after state: not in index
        return {
            "action_id": str(uuid.uuid4()),
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "target": target,
            "risk": "low",
            "requires_confirmation": True,
            "requires_admin": False,
            "reversible": True,
            "before_fingerprint": state,
            "expected_after_fingerprint": "not_in_index",
            "side_effects": ["Removes file from Git index (unstage)"],
            "limitations": ["Does not modify workspace file", "Does not rewrite git history"],
            "planned_change": {
                "mode": mode,
                "blob": blob
            }
        }

    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        if self.inspect(target) != plan["before_fingerprint"]:
            raise Exception("Git index changed before apply")
            
        plan["planned_change"]["rollback_data"] = {
            "mode": plan["planned_change"]["mode"],
            "blob": plan["planned_change"]["blob"]
        }
        
        subprocess.run(
            ['git', 'rm', '--cached', target],
            check=True, capture_output=True, timeout=10,
            env=self._get_git_env()
        )
        return True

    def verify(self, plan: Dict[str, Any]) -> str:
        target = plan["target"]
        current = self.inspect(target)
        
        if current == plan["expected_after_fingerprint"]:
            return "verified"
            
        if current != plan["before_fingerprint"]:
            return "drift_detected"
            
        return "failed"

    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        target = plan["target"]
        
        if self.inspect(target) == plan["before_fingerprint"]:
            return True
            
        if self.inspect(target) != plan["expected_after_fingerprint"]:
            raise Exception("Rollback aborted: drift detected in Git index")
            
        mode = plan.get("planned_change", {}).get("rollback_data", {}).get("mode")
        blob = plan.get("planned_change", {}).get("rollback_data", {}).get("blob")
        
        if not mode or not blob:
            return False
            
        # Re-add the exact blob to the index
        # git update-index --add --cacheinfo <mode>,<blob>,<path>
        result = subprocess.run(
            ['git', 'update-index', '--add', '--cacheinfo', f"{mode},{blob},{target}"],
            capture_output=True, timeout=10,
            env=self._get_git_env()
        )
        return result.returncode == 0
