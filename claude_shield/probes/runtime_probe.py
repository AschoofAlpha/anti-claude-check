import subprocess
import shutil
from .http_probe import fetch_http
from .base import ProbeError

def run_python_probe(url: str, timeout: int, is_custom: bool = False):
    try:
        return fetch_http(url, timeout=timeout, is_custom=is_custom)
    except ProbeError:
        return None, "unavailable"
    except Exception:
        return None, "unavailable"

def run_curl_probe(url: str, timeout: int):
    if not shutil.which('curl'):
        return None, "unavailable"
        
    # Determine ssrf_validation_mode for curl based on proxy
    from .http_probe import get_proxy_metadata
    has_proxy = get_proxy_metadata()["proxy_configuration_detected"]
    ssrf_mode = "proxy_limited" if has_proxy else "unavailable"
        
    try:
        # Prevent curlrc usage
        env = {}
        result = subprocess.run(
            ['curl', '-s', '-q', '--max-time', str(timeout), url],
            capture_output=True,
            text=True,
            timeout=timeout+1,
            env=env
        )
        if result.returncode == 0:
            return result.stdout, ssrf_mode
        return None, ssrf_mode
    except Exception:
        return None, ssrf_mode
