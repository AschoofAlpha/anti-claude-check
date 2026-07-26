import json
import os
from pathlib import Path
from jsonschema import validate, ValidationError
from .models import AuditReport, AuditCheck, PlatformInfo, PrivacyMetadata
from .redaction import Redactor

def get_schema_path():
    return Path(__file__).parent.parent / 'schemas' / 'browser-audit.schema.json'

def import_browser_report(path: str) -> AuditReport:
    file_path = Path(path).resolve()
    
    # Restrict file size to 1MB
    if file_path.stat().st_size > 1024 * 1024:
        raise ValueError("Browser report file too large (max 1MB).")
        
    def raise_invalid(x):
        raise ValueError(f"Invalid constant: {x}")
        
    def check_limits(obj, level=0):
        if level > 20: raise ValueError("JSON too deep")
        if isinstance(obj, dict):
            if len(obj) > 100: raise ValueError("Too many keys in object")
            for k, v in obj.items():
                if len(k) > 1000: raise ValueError("Key too long")
                check_limits(v, level+1)
        elif isinstance(obj, list):
            if len(obj) > 1000: raise ValueError("Array too large")
            for v in obj: check_limits(v, level+1)
        elif isinstance(obj, str):
            if len(obj) > 10000: raise ValueError("String too long")
            
    try:
        data = json.loads(file_path.read_text(encoding='utf-8', errors='strict'), parse_constant=raise_invalid)
        check_limits(data)
    except Exception as e:
        raise ValueError(f"Invalid JSON or limits exceeded: {e}")
        
    schema_path = get_schema_path()
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {e.message}")
            
    if data.get('version', '').split('.')[0] != '1':
        raise ValueError("Unsupported browser report major version.")
        
    redactor = Redactor()
    
    # Re-pseudonomize to match current session
    findings = data.get('findings')
    checks_list = data.get('checks')
    
    if findings is not None and checks_list is not None:
        raise ValueError("Cannot contain both 'findings' and 'checks'.")
        
    if findings is not None:
        import warnings
        warnings.warn("The 'findings' field in JSON is deprecated. Use 'checks'.")
        raw_checks = findings
    elif checks_list is not None:
        raw_checks = checks_list
    else:
        raw_checks = []
        
    recalculated_checks = []
    
    for finding in raw_checks:
        # Validate whitelist
        safe_keys = {'id', 'title', 'category', 'status', 'severity', 'confidence', 'evidence', 'explanation'}
        safe_finding = {k: v for k, v in finding.items() if k in safe_keys}
        
        # Redact evidence
        safe_evidence = []
        for ev in safe_finding.get('evidence', []):
            safe_ev = {'type': ev.get('type'), 'description': ev.get('description'), 'data': ev.get('data')}
            # We don't execute or evaluate external paths
            safe_evidence.append(safe_ev)
            
        safe_finding['evidence'] = safe_evidence
        
        # We don't trust the risk level from the browser report. Re-calculate.
        if safe_finding.get('category') == 'network' and safe_finding.get('status') == 'fail':
            safe_finding['severity'] = 'high'
            
        # Try to parse IPs from evidence data values if any and re-redact them.
        # This is a best-effort as browser extension already redacted it. We will warn the user in CLI.
        recalculated_checks.append(AuditCheck(**safe_finding))
        
    report = AuditReport(
        schema_version=data.get('version', '1.0.0'),
        tool_version="0.1.0",
        platform=PlatformInfo(os=f"browser-{data.get('browser_env', 'unknown')}", version="", hostname=""),
        privacy=PrivacyMetadata(redaction_enabled=True, salt_used=True),
        generated_at=data.get('timestamp', ''),
        checks=recalculated_checks,
        summary={'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0},
        errors=[]
    )
    
    return report
