# Known Limitations (v0.9.0-beta.1)

## Architecture & Security Boundaries

### 1. Scope of Remediation
Claude Shield strictly operates within local workspace scopes using whitelist-based executors. It **does not** support:
- System-wide DNS modifications or resolver overrides.
- Global system proxy, routing table, or firewall changes.
- Disabling physical network adapters or OS-level IPv6 stacks.
- Windows Registry network subkey mutations.
- TLS interception or Man-in-the-Middle certificate injection.
- Browser fingerprint spoofing (User-Agent, Canvas, WebGL, AudioContext).

### 2. Egress & SSRF Risk Mitigation
- **Mitigation Scope**: Reduces SSRF and DNS rebinding risks across covered probe paths by validating IPv4/IPv6 addresses against standard public/private CIDR lists before issuing requests (`ssrf_validation_mode: direct_pinned`).
- **Metadata Visibility**: HTTP/TLS probes connect directly or via user-configured proxies; standard TCP connection metadata remains visible to destination probe servers.

### 3. Cross-Platform Validation Status
- **Windows**: Primary native platform, fully tested on physical hardware.
- **Linux & macOS**: Core logic verified via unit tests and mock environments (**Tested with mocks**). macOS system proxy queries (`scutil`) are currently mocked.

### 4. File Permission Controls
- **POSIX**: Enforces `0o700` directory and `0o600` file modes.
- **Windows**: Relies on standard Windows user folder ACL inheritance (`%USERPROFILE%\.claude-shield`). Does not claim POSIX-equivalent mode enforcement.
