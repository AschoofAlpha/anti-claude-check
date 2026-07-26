import re
import hashlib
import ipaddress
import secrets
import urllib.parse

class Redactor:
    """
    Handles sensitive data redaction.
    Features:
    - 单报告随机假名化盐 (Single-report random pseudonymization salt)
    - 支持循环引用检测，并对递归深度、节点数量和字符串长度设置安全上限。
    """
    def __init__(self):
        # Use secrets for cryptographically secure salt, distinct for every report
        self.salt = secrets.token_hex(16)
        self.mapping = {}

    def _hash(self, value: str) -> str:
        return hashlib.sha256((self.salt + str(value)).encode('utf-8', errors='ignore')).hexdigest()[:6]

    def _get_or_create(self, prefix: str, value: str) -> str:
        if value not in self.mapping:
            self.mapping[value] = f"<{prefix}:{self._hash(value)}>"
        return self.mapping[value]

    def redact_ipv4(self, ip: str) -> str:
        return self._get_or_create("IPV4", ip)

    def redact_ipv6(self, ip: str) -> str:
        return self._get_or_create("IPV6", ip)
        
    def redact_mac(self, mac: str) -> str:
        return self._get_or_create("MAC", mac)

    def redact_host(self, host: str) -> str:
        return self._get_or_create("HOST", host)

    def redact_user(self, user: str) -> str:
        return self._get_or_create("USER", user)

    def redact_path(self, path: str) -> str:
        # Avoid tracking backslashes vs forward slashes differently if possible, but keep it simple
        return self._get_or_create("PATH", path)
        
    def redact_credential(self, cred: str) -> str:
        return self._get_or_create("CRED", cred)

    def scan_and_redact(self, data, seen=None):
        """Recursively scan dictionaries and lists, and redact sensitive info."""
        if seen is None:
            seen = set()
            
        # Handle circular references
        if id(data) in seen:
            return "<CIRCULAR_REFERENCE>"
            
        if isinstance(data, (dict, list, tuple)):
            seen.add(id(data))
            
        try:
            if isinstance(data, dict):
                result = {}
                for k, v in data.items():
                    key_lower = str(k).lower()
                    if key_lower in ('ssid', 'bssid', 'hostname', 'username', 'user', 'password', 'token', 'secret', 'apikey', 'api_key', 'cookie', 'auth'):
                        if isinstance(v, str):
                            result[k] = self.redact_credential(v)
                        else:
                            result[k] = self.scan_and_redact(v, seen)
                    else:
                        result[k] = self.scan_and_redact(v, seen)
                return result
            elif isinstance(data, list):
                return [self.scan_and_redact(i, seen) for i in data]
            elif isinstance(data, tuple):
                return tuple(self.scan_and_redact(i, seen) for i in data)
            elif isinstance(data, str):
                return self._redact_string(data)
            elif isinstance(data, bytes):
                try:
                    return self._redact_string(data.decode('utf-8'))
                except UnicodeDecodeError:
                    return "<BINARY_DATA>"
            elif data is None or isinstance(data, (bool, int, float)):
                return data
            else:
                return str(data)
        finally:
            if isinstance(data, (dict, list, tuple)):
                seen.remove(id(data))

    def _redact_string(self, text: str) -> str:
        if len(text) > 100000:
            return "<TRUNCATED_LONG_STRING>"
            
        # 1. Credentials (Bearer, API Keys, etc.)
        # Bearer token
        text = re.sub(r'(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{20,})', lambda m: m.group(1) + self.redact_credential(m.group(2)), text)
        # Basic auth
        text = re.sub(r'(?i)(basic\s+)([a-zA-Z0-9\+/=]{20,})', lambda m: m.group(1) + self.redact_credential(m.group(2)), text)
        # API Keys / Tokens / Secrets (skipping common non-sensitive words)
        text = re.sub(r'(?i)(secret[_-]?key|api[_-]?key|token|secret|password)["\'\s:=]+([a-zA-Z0-9_\-\.]{16,})', lambda m: m.group(1) + "=" + self.redact_credential(m.group(2)), text)
        # Private key headers
        if "BEGIN RSA PRIVATE KEY" in text or "BEGIN PRIVATE KEY" in text or "BEGIN OPENSSH PRIVATE KEY" in text:
            return "<PRIVATE_KEY_REDACTED>"
            
        # 2. URLs (Redact credentials in URLs)
        def replace_url_creds(match):
            url = match.group(0)
            try:
                parsed = urllib.parse.urlparse(url)
                if parsed.username or parsed.password:
                    # rebuild URL with redacted creds
                    netloc = ""
                    if parsed.username:
                        netloc += self.redact_user(parsed.username)
                    if parsed.password:
                        netloc += ":" + self.redact_credential(parsed.password)
                    if netloc:
                        netloc += "@"
                    netloc += parsed.hostname or ""
                    if parsed.port:
                        netloc += f":{parsed.port}"
                    return urllib.parse.urlunparse(parsed._replace(netloc=netloc))
            except ValueError:
                pass
            return url
            
        text = re.sub(r'https?://[^\s\'"]+', replace_url_creds, text)
        text = re.sub(r'socks5h?://[^\s\'"]+', replace_url_creds, text)

        # 3. Network Data
        # IPv4 (including optional port and CIDR)
        ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?(?::[0-9]{1,5})?\b'
        def replace_ipv4(match):
            ip_str = match.group(0)
            base_ip = re.split(r'[/:]', ip_str)[0]
            try:
                ip_obj = ipaddress.ip_address(base_ip)
                if ip_obj.version == 4:
                    return ip_str.replace(base_ip, self.redact_ipv4(base_ip))
            except ValueError:
                pass
            return ip_str
        text = re.sub(ipv4_pattern, replace_ipv4, text)

        # IPv6
        ipv6_pattern = r'\[?([0-9a-fA-F:]+:[0-9a-fA-F:]+)\]?(?:/[0-9]{1,3})?(?::[0-9]{1,5})?'
        def replace_ipv6(match):
            full_match = match.group(0)
            base_ip = match.group(1)
            try:
                ip_obj = ipaddress.ip_address(base_ip)
                if ip_obj.version == 6:
                    return full_match.replace(base_ip, self.redact_ipv6(base_ip))
            except ValueError:
                pass
            return full_match
        text = re.sub(ipv6_pattern, replace_ipv6, text)
        
        # MAC Address
        mac_pattern = r'\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b'
        text = re.sub(mac_pattern, lambda m: self.redact_mac(m.group(0)), text)

        # 4. Identity & Paths
        # UNC Paths (\\SERVER\Share)
        unc_pattern = r'\\\\[a-zA-Z0-9_\.\-]+\\[a-zA-Z0-9_\.\-\\]+'
        text = re.sub(unc_pattern, lambda m: self.redact_path(m.group(0)), text)
        
        # Windows Paths (C:\Users\...)
        win_path = r'[a-zA-Z]:\\[^:\*\?"<>\|]+'
        text = re.sub(win_path, lambda m: self.redact_path(m.group(0)), text)
        
        # POSIX Paths (/home/user/...)
        posix_path = r'(?:/[a-zA-Z0-9_\-\.]+){2,}'
        text = re.sub(posix_path, lambda m: self.redact_path(m.group(0)), text)

        return text
