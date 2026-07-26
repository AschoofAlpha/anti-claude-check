import os
from pathlib import Path
from typing import Dict, Any

from .profile import get_profile_dir, load_manifest, is_valid_profile_id
from .lifecycle import is_profile_in_use

def inspect_profile(profile_id: str) -> Dict[str, Any]:
    if not is_valid_profile_id(profile_id):
        raise ValueError("Invalid profile ID")
        
    p_dir = get_profile_dir(profile_id)
    if not p_dir.exists():
        raise FileNotFoundError("Profile not found")
        
    manifest = load_manifest(profile_id)
    if not manifest:
        manifest = {}
        
    profile_data_dir = p_dir / 'profile'
    
    in_use = is_profile_in_use(str(profile_data_dir))
    
    ext_dir = profile_data_dir / 'Extensions'
    ext_count = 0
    has_proxy_ext = False
    if ext_dir.exists() and ext_dir.is_dir():
        for d in ext_dir.iterdir():
            if d.is_dir():
                ext_count += 1
                # Check for common proxy extension indicators in manifest
                for ver_dir in d.iterdir():
                    ext_manifest = ver_dir / 'manifest.json'
                    if ext_manifest.exists():
                        try:
                            content = ext_manifest.read_text(errors='ignore')
                            if 'proxy' in content.lower():
                                has_proxy_ext = True
                        except:
                            pass
                            
    has_sync = (profile_data_dir / 'Sync Data').exists()
    has_cookies = (profile_data_dir / 'Network' / 'Cookies').exists() or (profile_data_dir / 'Cookies').exists()
    has_passwords = (profile_data_dir / 'Login Data').exists()
    has_sw = (profile_data_dir / 'Service Worker').exists()
    
    report = {
        "profile_id": f"<PROFILE:{profile_id[:8]}...>",
        "managed": manifest.get("managed_by_claude_shield", False),
        "in_use": in_use,
        "extension_count": ext_count,
        "sync_configuration_detected": has_sync,
        "cookie_store_present": has_cookies,
        "password_store_present": has_passwords,
        "service_worker_data_present": has_sw,
        "proxy_extension_suspected": has_proxy_ext
    }
    
    return report

def calculate_risk(report: Dict[str, Any]) -> str:
    if not report.get("managed"):
        return "Warning"
    if report.get("in_use"):
        # Not really a risk for the profile contents, but a blocker for operations
        pass
    if report.get("sync_configuration_detected"):
        return "Medium"
    if report.get("proxy_extension_suspected"):
        return "High"
        
    return "Info" if (report.get("cookie_store_present") or report.get("extension_count", 0) > 0) else "Pass"
