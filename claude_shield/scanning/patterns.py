import re
from typing import Dict, Pattern

CREDENTIAL_PATTERNS: Dict[str, Pattern] = {
    'pem_private_key': re.compile(r'-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP|ED25519)?\s*PRIVATE\s+KEY-----', re.IGNORECASE),
    'bearer_token': re.compile(r'Bearer\s+[a-zA-Z0-9\-\._~+/]+=*', re.IGNORECASE),
    'basic_auth': re.compile(r'Basic\s+[a-zA-Z0-9+/=]+', re.IGNORECASE),
    'api_key_field': re.compile(r'(?i)(?:api_?key|access_?token|secret_?key|auth_?token|password)\s*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{16,})[\'"]?'),
    'aws_access_key': re.compile(r'(?i)AKIA[0-9A-Z]{16}'),
    'aws_secret_key': re.compile(r'(?i)aws_secret_access_key\s*[:=]\s*[\'"]?[a-zA-Z0-9/+=]{40}[\'"]?'),
    'github_token': re.compile(r'(?i)gh[p|u|s|o|r]_[a-zA-Z0-9]{36}'),
    'slack_token': re.compile(r'(?i)xox[baprs]-[a-zA-Z0-9]+'),
}
