# Release Notes - Claude Shield v0.9.0-beta.1

## Highlights

Claude Shield `v0.9.0-beta.1` is the first Beta Release Candidate for the Claude privacy audit and low-risk environment remediation toolkit.

### Key Features Included
- 🔍 **Static Privacy & Security Auditor**: Scans local workspaces, environment variables, credentials, Git state, WSL, Docker, and browser reports for risk indicators.
- 🛡️ **Transactional Remediation Engine**: Whitelisted local executors for `.gitignore` rules, `.env` template generation, file staging removal, quarantine, and Clean Chrome Profile management.
- 🔄 **Atomic Rollback Lifecycle**: Manifest-tracked transaction history with automatic drift detection and 100% reversible rollbacks.
- 🔒 **Zero-Leak Data Redaction**: Single-report pseudonymous salting and regex dictionary redaction for IPs, paths, tokens, cookies, auth headers, and hostnames.
- 🌐 **Safe Egress Probes**: SSRF-protected HTTPS network probes adhering to standard system and environment proxy routes (`HTTP_PROXY`/`NO_PROXY`).

### Release Readiness Verdict
- **Platform Grade**: `Ready for Windows/Linux Beta (Linux/macOS: Tested with mocks)`
- **Automated Tests**: 71/71 Passed (0 Failures, 0 Errors).
