import os
from pathlib import Path

def is_profile_in_use(profile_dir: str) -> bool:
    """Checks if a given Chrome profile directory is currently in use."""
    profile_path = Path(profile_dir)
    if not profile_path.exists():
        return False
        
    # Check SingletonLock (Linux/Mac)
    lock_file = profile_path / 'SingletonLock'
    if lock_file.exists():
        # Usually a symlink pointing to hostname-pid
        if lock_file.is_symlink():
            try:
                target = lock_file.readlink()
                # Target is usually hostname-pid
                # For basic detection, just presence of valid lock is enough
                return True
            except OSError:
                pass
                
    # Check SingletonCookie (Windows/Mac/Linux)
    cookie_file = profile_path / 'SingletonCookie'
    if cookie_file.exists():
        return True
        
    # Check SingletonSocket (Linux/Mac)
    socket_file = profile_path / 'SingletonSocket'
    if socket_file.exists():
        return True
        
    # Check lockfile (Windows)
    win_lock = profile_path / 'lockfile'
    if win_lock.exists():
        try:
            # On Windows, if Chrome is running, this file is locked exclusively
            with open(win_lock, 'a') as f:
                pass
        except IOError:
            return True

    return False
