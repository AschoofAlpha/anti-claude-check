# Claude Shield - Platform Support Matrix (v0.9.0-beta.1)

This document outlines the testing and support status for different platforms and environments for Claude Shield.

## Operating Systems

| OS | Supported | Status | Notes |
| :--- | :---: | :--- | :--- |
| **Windows 10/11** | ✅ | Native Support (Primary) | Fully tested on real hardware. Full support for POSIX-fallback via WSL, Docker detection, Windows Proxy, and ACL rules. |
| **macOS (Darwin)** | ⚠️ | Partial Support (Beta) | Requires `bash` or `zsh`. Tested via mock environments. Proxy detection may require manual configuration depending on networking stack. |
| **Linux (Ubuntu/Debian)**| ✅ | Native Support | Tested via mock environments. Full support for POSIX `stat` permissions, `/etc/resolv.conf`, and standard `http_proxy` variables. |

## Virtualization & Environments

| Environment | Supported | Status | Notes |
| :--- | :---: | :--- | :--- |
| **WSL 2 (Windows)** | ✅ | Supported | Path translation and namespace bridging is fully tested. Egress validation successfully traverses vSwitch. |
| **Docker Containers** | ✅ | Supported | Detected via `.dockerenv`. Cgroup scanning and bridge networking checks are fully supported. |
| **Remote SSH / VS Code** | ✅ | Supported | Tested for agentic workflows where terminal egress differs from host browser egress. |

## Network & Proxy Topologies

| Topology | Supported | Status | Notes |
| :--- | :---: | :--- | :--- |
| **Direct Connection** | ✅ | Supported | IPv4 and IPv6 tested. |
| **Environment Proxy (`HTTP_PROXY`)** | ✅ | Supported | Properly propagates to curl and runtime probes. |
| **System Proxy (Windows/macOS)** | ⚠️ | Beta | Windows Registry proxy detection supported. macOS system proxy requires `scutil` which is currently mocked. |
| **Transparent Proxy / VPN** | ✅ | Supported | Automatically detected via anomaly heuristic comparing TLS handshake metadata against DNS expected routes. |

## Browser Profile Import

| Browser | Supported | Profile Type | Notes |
| :--- | :---: | :--- | :--- |
| **Google Chrome** | ✅ | Default / Clean Profile | Requires explicit flag or Chrome to be closed. |
| **Microsoft Edge** | ⚠️ | Beta | Structurally similar to Chrome; imported as Chromium-based payload. |
| **Mozilla Firefox** | ❌ | Planned | SQLite based profile formats not currently natively scanned without extension payload. |

## Remediation Capabilities

| Executor | Windows | macOS | Linux | Reversible |
| :--- | :---: | :---: | :---: | :---: |
| `gitignore` | ✅ | ✅ | ✅ | ✅ |
| `env-template`| ✅ | ✅ | ✅ | ✅ |
| `permissions` | ⚠️ | ✅ | ✅ | ✅ |
| `git-unstage` | ✅ | ✅ | ✅ | ✅ |
| `quarantine` | ✅ | ✅ | ✅ | ✅ |

*Note: Windows `permissions` executor operates with limited precision due to NTFS mapping abstractions in Python's `os.stat`.*
