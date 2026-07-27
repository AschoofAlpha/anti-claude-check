import subprocess
import os
import datetime
from pathlib import Path

from .discovery import detect_browser
from .chrome_flags import DEFAULT_FLAGS, sanitize_flags
from .profile import get_profile_dir, load_manifest, is_valid_profile_id, save_manifest
from .lifecycle import is_profile_in_use

def launch_profile(profile_id: str, custom_browser_path: str = None, disable_extensions: bool = False, extra_args: list = None) -> subprocess.Popen:
    if not is_valid_profile_id(profile_id):
        raise ValueError("Invalid profile ID")
        
    p_dir = get_profile_dir(profile_id)
    if not p_dir.exists():
        raise FileNotFoundError("Profile not found")
        
    profile_data_dir = p_dir / 'profile'
    
    if is_profile_in_use(str(profile_data_dir)):
        raise Exception("Profile is already in use by another process")
        
    manifest = load_manifest(profile_id)
    if not manifest:
        raise Exception("Invalid profile manifest")
        
    browser_info = detect_browser(custom_browser_path)
    if not browser_info["detected"]:
        raise Exception("Browser executable not found or not safe")
        
    flags = list(DEFAULT_FLAGS)
    flags.append(f"--user-data-dir={str(profile_data_dir)}")
    
    if disable_extensions and "--disable-extensions" not in flags:
        flags.append("--disable-extensions")
        
    if extra_args:
        flags.extend(sanitize_flags(extra_args))
        
    # Launch
    # We do not use shell=True to prevent injection
    cmd = [browser_info["path"]] + flags
    
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Update manifest
    manifest["launch_count"] = manifest.get("launch_count", 0) + 1
    manifest["last_launch"] = datetime.datetime.utcnow().isoformat() + "Z"
    save_manifest(profile_id, manifest)
    
    return process
