import abc
from typing import Dict, Any, List

class RemediationExecutor(abc.ABC):
    @property
    @abc.abstractmethod
    def executor_id(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def executor_version(self) -> str:
        pass

    @abc.abstractmethod
    def inspect(self, target: str) -> str:
        """Return the current before_fingerprint (e.g. file hash or git state)."""
        pass

    @abc.abstractmethod
    def plan(self, target: str) -> Dict[str, Any]:
        """
        Return a strict plan object:
        {
            "action_id": "random-id",
            "executor_id": self.executor_id,
            "executor_version": self.executor_version,
            "target": target,
            "risk": "low",
            "requires_confirmation": bool,
            "requires_admin": bool,
            "reversible": bool,
            "before_fingerprint": str,
            "expected_after_fingerprint": str,
            "side_effects": list,
            "limitations": list,
            "planned_change": dict
        }
        """
        pass

    @abc.abstractmethod
    def apply(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        """
        Apply the change. Must back up data internally or via transaction manager
        so rollback is possible. Returns True if successful.
        """
        pass

    @abc.abstractmethod
    def verify(self, plan: Dict[str, Any]) -> str:
        """
        Verify the change has taken effect.
        Must return one of:
        verified, drift_detected, partial, failed, manual_intervention_required
        """
        pass

    @abc.abstractmethod
    def rollback(self, plan: Dict[str, Any], transaction_id: str) -> bool:
        """Revert the change using the backup created in apply. Must be idempotent."""
        pass
