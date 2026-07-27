import os
import json
import uuid
import datetime
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .. import __version__

from .lifecycle import is_profile_in_use

def get_browser_profiles_dir() -> Path:
    return Path.home() / '.claude-shield' / 'browser-profiles'

def get_profile_dir(profile_id: str) -> Path:
    return get_browser_profiles_dir() / profile_id

def ensure_base_dir():
    base_dir = get_browser_profiles_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    # Ensure private permissions on unix
    if os.name == 'posix':
        os.chmod(base_dir, 0o700)

def is_valid_profile_id(profile_id: str) -> bool:
    # Just basic UUID check
    try:
        uuid.UUID(profile_id)
        return True
    except ValueError:
        return False

def create_profile(browser_info: Dict[str, Any]) -> str:
    ensure_base_dir()
    profile_id = str(uuid.uuid4())
    p_dir = get_profile_dir(profile_id)
    
    if p_dir.exists():
        raise Exception("Profile ID collision")
        
    p_dir.mkdir(parents=True, exist_ok=False)
    
    if os.name == 'posix':
        os.chmod(p_dir, 0o700)
        
    # Create internal structure
    (p_dir / 'profile').mkdir()
    (p_dir / 'audit').mkdir()
    
    manifest = {
        "schema_version": "1.0",
        "profile_id": profile_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "tool_version": __version__,
        "browser_path_pseudonym": os.path.basename(browser_info.get("path", "unknown")),
        "browser_version": browser_info.get("version", "unknown"),
        "status": "active",
        "managed_by_claude_shield": True,
        "launch_count": 0,
        "last_audit_time": None,
        "security_options_enabled": ["isolated_directory", "no_sync", "no_first_run"]
    }
    
    with open(p_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
        
    return profile_id

def load_manifest(profile_id: str) -> Optional[Dict[str, Any]]:
    manifest_path = get_profile_dir(profile_id) / 'manifest.json'
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None

def save_manifest(profile_id: str, manifest: Dict[str, Any]):
    manifest_path = get_profile_dir(profile_id) / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

def list_profiles() -> list:
    base_dir = get_browser_profiles_dir()
    if not base_dir.exists():
        return []
        
    profiles = []
    for d in base_dir.iterdir():
        if d.is_dir() and is_valid_profile_id(d.name):
            manifest = load_manifest(d.name)
            if manifest:
                in_use = is_profile_in_use(str(d / 'profile'))
                profiles.append({
                    "profile_id": manifest["profile_id"],
                    "created_at": manifest["created_at"],
                    "status": manifest["status"],
                    "in_use": in_use
                })
    return profiles

def quarantine_profile(profile_id: str) -> bool:
    if not is_valid_profile_id(profile_id):
        raise ValueError("Invalid profile ID")
        
    p_dir = get_profile_dir(profile_id)
    if not p_dir.exists():
        raise FileNotFoundError("Profile not found")
        
    if is_profile_in_use(str(p_dir / 'profile')):
        raise Exception("Profile is in use, cannot quarantine")
        
    manifest = load_manifest(profile_id)
    if not manifest or not manifest.get("managed_by_claude_shield"):
        raise Exception("Not a Claude Shield managed profile")
        
    quarantine_dir = get_browser_profiles_dir() / 'quarantine'
    quarantine_dir.mkdir(exist_ok=True)
    
    dest = quarantine_dir / f"{profile_id}_{int(datetime.datetime.utcnow().timestamp())}"
    
    # Check for symlink escapes before move
    if p_dir.is_symlink():
        raise Exception("Profile root is a symlink")
        
    shutil.move(str(p_dir), str(dest))
    return True

def reset_profile(profile_id: str) -> Tuple[str, str]:
    """Returns (old_quarantine_path, new_generation_id).
    Since we don't want to just wipe, we quarantine and create a new one,
    or we increment generation ID inside the manifest.
    For this implementation, we will move to quarantine and create fresh directory."""
    if not is_valid_profile_id(profile_id):
        raise ValueError("Invalid profile ID")
        
    p_dir = get_profile_dir(profile_id)
    if not p_dir.exists():
        raise FileNotFoundError("Profile not found")
        
    if is_profile_in_use(str(p_dir / 'profile')):
        raise Exception("Profile is in use, cannot reset")
        
    manifest = load_manifest(profile_id)
    if not manifest or not manifest.get("managed_by_claude_shield"):
        raise Exception("Not a Claude Shield managed profile")
        
    quarantine_dir = get_browser_profiles_dir() / 'quarantine'
    quarantine_dir.mkdir(exist_ok=True)
    
    dest = quarantine_dir / f"{profile_id}_reset_{int(datetime.datetime.utcnow().timestamp())}"
    shutil.move(str(p_dir), str(dest))
    
    # Recreate the profile
    p_dir.mkdir(parents=True, exist_ok=False)
    if os.name == 'posix':
        os.chmod(p_dir, 0o700)
    (p_dir / 'profile').mkdir()
    (p_dir / 'audit').mkdir()
    
    generation = manifest.get("generation", 1) + 1
    new_manifest = {
        **manifest,
        "generation": generation,
        "previous_generation_path": str(dest.name),
        "last_reset": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    save_manifest(profile_id, new_manifest)
    
    return str(dest), profile_id
