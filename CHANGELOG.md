# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-08-03

### Fixed
- PyPI metadata: added `license = "MIT"` (previously showed as None).
- README image paths switched to absolute raw.githubusercontent URLs so the social preview and audit demo render on the PyPI project page (relative paths broke inside the wheel).

## [1.1.0] - 2026-08-03

### Added
- `run_full_audit()` combined entry point: collector + redaction + analysis + live egress probes in one call.
- Six new audit checks consuming previously unused collector fields:
  - `network.policy_group` — policy-group selection chain (no URL-test/fallback/load-balance auto selectors).
  - `network.dns_respect_rules` — `respect-rules` DNS behavior.
  - `network.dns_ipv6` — DNS IPv6 consistency.
  - `network.dns_encrypted` — encrypted upstream presence.
  - `network.dns_physical_resolver` — physical-ISP DNS resolvers on local adapters.
  - `network.tun_stack` — TUN stack (gvisor etc.).
- `claude_shield/analyze.py` analysis library with `run_legacy_collector()`, `analyze_snapshot()`, `summarize()`.
- GitHub Actions CI (Python 3.11/3.12 matrix, pytest + coverage).
- Bilingual pain-point README intro, social preview hero, and audit report demo image.

### Removed
- Interactive CLI (`cli.py`, `reporting.py`, launcher scripts, console entry points).
- Browser audit page (`assets/browser-audit.html`) and browser profile management (`browser/`, `browser_import.py`).
- Remediation transaction engine, credentials scanning, and `checks/`/`scanning/` modules.
- Browser scoring fields from `models.py` / `schema.py`.

### Changed
- Analysis logic moved from `cli.py` into the `claude_shield.analyze` library.
- Social preview redesigned around the account-flagging pain point; bilingual (EN/中文).
- Repository description and README intro rewritten in plain language.
- Version bumped to `1.1.0` stable.

## [1.1.0-beta.1] - 2026-07-27

### Added
- Safety hardening: redaction of local identifiers before sharing, explicit approval for state-changing actions.
- Identity restoration guidance (do not spoof, do not hide automation, do not fabricate identity).

## [1.0.0] - 2026-07-26

### Added
- Read-only Windows collector for proxy, DNS, IPv6, system, and Claude Code privacy settings.
- Clash Verge / Mihomo checks: rule mode, system proxy, service/TUN state, `strict-route`, fake-IP, DNS hijacking, LAN access, policy selection.
- Three-tier recommendations: **Must fix**, **Optional consistency**, **Leave alone**.
- Optional reversible privacy environment-variable remediation.
- POSIX collector (limited environment summary).
