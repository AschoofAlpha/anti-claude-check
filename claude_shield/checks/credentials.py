import os
import stat
import subprocess
from pathlib import Path
from ..models import AuditCheck, Evidence
from ..scanning.file_scanner import FileScanner
from ..scanning.patterns import CREDENTIAL_PATTERNS
from ..scanning.entropy import is_high_entropy
from ..redaction import Redactor

def is_tracked_by_git(file_path: Path) -> bool:
    try:
        # Check if file is tracked by git
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', str(file_path)],
            capture_output=True,
            cwd=file_path.parent
        )
        return result.returncode == 0
    except Exception:
        return False

def check_file_permissions(file_path: Path) -> bool:
    # Returns True if file permissions are too wide (e.g., readable by others on POSIX)
    if os.name == 'nt':
        # Simple check for Windows is harder without pywin32, default to False (safe)
        return False
    else:
        st = file_path.stat()
        return bool(st.st_mode & stat.S_IROTH)

import hashlib
import secrets
import re

def is_false_positive(value: str) -> bool:
    if len(value) > 200: return True # Too long
    if re.fullmatch(r'[a-fA-F0-9]{40}', value): return True # SHA-1 / Git Object ID
    if re.fullmatch(r'[a-fA-F0-9]{64}', value): return True # SHA-256
    if re.fullmatch(r'[a-fA-F0-9]{128}', value): return True # SHA-512
    if re.fullmatch(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}', value): return True # UUID
    if value.startswith('sha256-') or value.startswith('sha384-') or value.startswith('sha512-'): return True # SRI
    val_lower = value.lower()
    if 'test' in val_lower or 'example' in val_lower or 'mock' in val_lower or 'placeholder' in val_lower: return True
    if 'example.com' in val_lower or '127.0.0.1' in val_lower: return True
    return False

def run_credential_scan(workspace: str) -> AuditCheck:
    scanner = FileScanner(workspace)
    redactor = Redactor()
    
    findings = []
    
    # Session salt for fingerprinting
    session_salt = secrets.token_hex(16)
    
    for path in scanner.scan():
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    for name, pattern in CREDENTIAL_PATTERNS.items():
                        m = pattern.search(line)
                        if m:
                            matched_value = m.group(0) if len(m.groups()) == 0 else m.group(1)
                            
                            # False positive rigid filters
                            if len(matched_value) > 200: continue
                            if re.fullmatch(r'[a-fA-F0-9]{40}', matched_value): continue # SHA-1
                            if re.fullmatch(r'[a-fA-F0-9]{64}', matched_value): continue # SHA-256
                            if re.fullmatch(r'[a-fA-F0-9]{128}', matched_value): continue # SHA-512
                            if re.fullmatch(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}', matched_value): continue
                            if matched_value.startswith('sha256-') or matched_value.startswith('sha384-') or matched_value.startswith('sha512-'): continue
                            
                            is_tracked = is_tracked_by_git(path)
                            too_wide = check_file_permissions(path)
                            
                            # Pseudonomize path if outside workspace, otherwise relative
                            try:
                                rel_path = str(path.relative_to(Path(workspace).resolve()))
                            except ValueError:
                                rel_path = redactor.redact_path(str(path))
                                
                            # Scoring model - baseline
                            risk = "low"
                            confidence = "probable"
                            
                            val_lower = matched_value.lower()
                            line_lower = line.lower()
                            
                            # Downgrade dummy values, but don't ignore
                            if any(w in val_lower for w in ['test', 'example', 'mock', 'dummy', 'fake', 'placeholder', 'your_']):
                                risk = "info"
                                confidence = "possible"
                                
                            if 'example.com' in line_lower:
                                # Doesn't immediately invalidate the token, but lowers confidence
                                confidence = "possible"
                                
                            # Upgrade contexts based on tracked/permissions
                            if is_tracked and name == 'pem_private_key':
                                risk = "critical"
                                confidence = "confirmed"
                            elif is_tracked and risk != "info":
                                risk = "high"
                                confidence = "confirmed"
                            elif too_wide and risk != "info":
                                risk = "medium"
                                
                            # High entropy standalone token downgrades to info/possible unless context confirms
                            if name == 'high_entropy' and confidence != "confirmed":
                                if risk != "low":
                                    risk = "info"
                                confidence = "possible"
                                
                            # Value fingerprint
                            fingerprint = hashlib.sha256(f"{session_salt}:{matched_value}".encode()).hexdigest()
                                
                            findings.append({
                                "credential_type": name,
                                "path": rel_path,
                                "line": line_num,
                                "tracked_by_git": is_tracked,
                                "confidence": confidence,
                                "value_fingerprint": f"<SECRET:{fingerprint[:16]}>",
                                "risk": risk
                            })
                            break
        except Exception:
            pass

    status = "pass"
    severity = "info"
    explanation = "No credentials detected in scanned files."
    
    if findings:
        status = "fail"
        max_risk = max((f['risk'] for f in findings), key=lambda x: {"info":0, "low":1, "medium":2, "high":3, "critical":4}[x])
        severity = max_risk
        explanation = f"Detected {len(findings)} potential credentials."
        
    evidence = [Evidence(type="credential_finding", description=f"Found {f['credential_type']}", data=f) for f in findings]
    
    return AuditCheck(
        id="security.credentials.scan",
        title="Workspace Credential Scan",
        category="security",
        status=status,
        severity=severity,
        confidence="possible" if findings else "confirmed",
        evidence=evidence,
        explanation=explanation
    )
