import os
import sys
import tempfile
import subprocess
import shutil
from typing import Optional, Dict, Any
from pathlib import Path

COMMON_PATHS = {
    'nt': [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ],
    'posix': [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
}

def is_safe_executable(path: str) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    if os.name == 'posix' and not os.access(path, os.X_OK):
        return False
    return True

def get_browser_version(path: str) -> str:
    try:
        if os.name == 'nt':
            # Use wmic to get version on Windows
            result = subprocess.run(
                ['wmic', 'datafile', 'where', f'name="{path.replace(os.sep, os.sep*2)}"', 'get', 'Version'],
                capture_output=True, text=True, timeout=2
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                return lines[1].strip()
        else:
            result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def detect_browser(custom_path: Optional[str] = None) -> Dict[str, Any]:
    candidates = [custom_path] if custom_path else COMMON_PATHS.get(os.name, [])
    
    for c in candidates:
        if c and os.path.exists(c) and is_safe_executable(c):
            # Check symlink
            is_symlink = os.path.islink(c)
            # Check if canonical
            canonical = os.path.realpath(c)
            version = get_browser_version(canonical)
            
            # Simple check if it's in a user writable suspicious dir (e.g. Temp)
            # In a real app we'd do more thorough checks
            temp_dir = tempfile.gettempdir() if 'tempfile' in sys.modules else '/tmp'
            is_suspicious = canonical.startswith(temp_dir)
            
            return {
                "detected": True,
                "path": canonical,
                "version": version,
                "is_symlink": is_symlink,
                "is_suspicious_location": is_suspicious,
                "is_executable": True
            }
            
    return {
        "detected": False,
        "path": None,
        "version": "unknown",
        "is_symlink": False,
        "is_suspicious_location": False,
        "is_executable": False
    }
