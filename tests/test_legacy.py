import subprocess
import os
import sys
import json

def test_windows_collector_selftest():
    if os.name != 'nt':
        return
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'collect_windows_network.ps1'))
    result = subprocess.run(
        ['pwsh', '-NoProfile', '-File', script_path, '-SelfTest'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Error: {result.stderr}"
    assert "Self-test passed." in result.stdout

def test_windows_collector_json():
    if os.name != 'nt':
        return
        
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'collect_windows_network.ps1'))
    result = subprocess.run(
        ['pwsh', '-NoProfile', '-File', script_path],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Error: {result.stderr}"
    
    # Check if we can parse the JSON
    data = json.loads(result.stdout)
    assert 'SchemaVersion' in data
    assert 'System' in data
    assert 'Browsers' in data
    assert 'ClaudeCode' in data

if __name__ == '__main__':
    test_windows_collector_selftest()
    test_windows_collector_json()
    print("All legacy tests passed.")
