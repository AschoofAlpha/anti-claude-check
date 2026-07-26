# Platform Support Matrix (v0.9.0-beta.1)

## Environment Support Summary

| Platform | Verification Mode | Status | Notes |
| :--- | :--- | :---: | :--- |
| **Windows 10/11** | Real Hardware | ✅ Verified | Primary development target. All executors, registry probe checks, and PowerShell fallbacks tested on physical OS. |
| **Linux (Ubuntu/Debian)** | Tested with mocks | ⚠️ Beta (Mocked) | System calls, `/etc/resolv.conf`, POSIX `stat` permissions, and environment proxy probes verified via test suite mocks. |
| **macOS (Darwin)** | Tested with mocks | ⚠️ Beta (Mocked) | Core Python runtime and CLI functionality validated via mocks. Native `scutil` system proxy integration mocked. |
| **WSL 2** | Real Hardware | ✅ Verified | Interop paths, environment variable propagation, and vSwitch egress checks verified. |
| **Docker Containers** | Real Hardware / Mocks | ✅ Verified | Container detection via `.dockerenv` and cgroup validation verified. |

## Permissions & Isolation Controls

| OS Family | Local State Path | Permissions Model | Notes |
| :--- | :--- | :--- | :--- |
| **POSIX (Linux/macOS)** | `~/.claude-shield/` | Explicit `0o700` / `0o600` | Directories and files enforce strict user-only read/write flags via `os.chmod`. |
| **Windows (NTFS)** | `%USERPROFILE%\.claude-shield\` | User ACL Inheritance | Relies on standard Windows user folder ACLs. Does not claim POSIX-equivalent mode control. |
