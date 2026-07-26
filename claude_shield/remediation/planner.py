import uuid
import datetime
from typing import List, Dict, Any

from .executors import get_executor, EXECUTORS

def get_applicable_executors_for_risk(risk_type: str) -> List[str]:
    mapping = {
        "missing_gitignore": ["gitignore"],
        "sensitive_report_unredacted": ["redact-report", "quarantine"],
        "permissions_too_broad": ["permissions"],
        "file_git_staged": ["git-unstage"],
        "missing_env_example": ["env-template"],
        "clean_profile_reset_required": ["browser-profile-reset"],
        # Only suggest, do not plan automatic fix
        "token_leaked_in_history": [],
        "windows_acl_broad": [],
        "dns_anomaly": [],
        "proxy_egress_mismatch": [],
        "ipv6_routing_anomaly": [],
        "browser_terminal_egress_mismatch": []
    }
    return mapping.get(risk_type, [])

def generate_plan(checks_results: List[Dict[str, Any]], requested_actions: List[str] = None) -> Dict[str, Any]:
    plan_actions = []
    
    for check in checks_results:
        # We assume check result has 'risk_type' and 'target'
        risk_type = check.get("risk_type")
        target = check.get("target")
        
        if not risk_type or not target:
            continue
            
        applicable = get_applicable_executors_for_risk(risk_type)
        
        for ex_id in applicable:
            if requested_actions and ex_id not in requested_actions:
                continue
                
            executor = get_executor(ex_id)
            if executor:
                action_plan = executor.plan(target)
                if action_plan:
                    plan_actions.append(action_plan)
                    
    plan_id = f"<PLAN:{str(uuid.uuid4())[:8]}>"
    expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + "Z"
    
    return {
        "plan_id": plan_id,
        "actions": plan_actions,
        "risk_level": "Low" if plan_actions else "None",
        "expires": expires
    }

def print_dry_run(plan: Dict[str, Any], fmt="terminal"):
    if fmt == "json":
        import json
        print(json.dumps(plan, indent=2))
        return
        
    actions = plan.get("actions", [])
    if not actions:
        print("No remediations required or generated.")
        return
        
    print("Remediation plan created\n")
    print(f"Plan ID: {plan.get('plan_id')}")
    print(f"Actions: {len(actions)}")
    print(f"Risk level: {plan.get('risk_level')}")
    print(f"Expires: {plan.get('expires')}\n")
    
    for idx, action in enumerate(actions, 1):
        print(f"{idx}. {action.get('executor_id')}")
        print(f"   Target: {action.get('target')}")
        print(f"   Reversible: {'Yes' if action.get('reversible') else 'No'}")
        print(f"   Confirmation required: {'Yes' if action.get('requires_confirmation') else 'No'}")
        diff = action.get("planned_change", {}).get("diff")
        if diff:
            print(f"   Diff preview available.")
        print()
        
    print("No changes have been made.")
