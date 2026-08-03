import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from claude_shield.analyze import analyze_snapshot


def _ids(checks):
    return {c.id: c for c in checks}


class TestSystemLevelChecks(unittest.TestCase):

    def test_service_mode_full_pass(self):
        checks = analyze_snapshot({"System": {
            "MihomoProcessRunning": True,
            "ServiceModeActive": True,
            "MixedPortListening": True,
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.service"].status, "pass")

    def test_service_mode_partial_warning(self):
        checks = analyze_snapshot({"System": {
            "MihomoProcessRunning": True,
            "ServiceModeActive": False,
            "MixedPortListening": False,
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.service"].status, "warning")
        self.assertEqual(ids["network.service"].severity, "low")

    def test_service_mode_none_unknown(self):
        checks = analyze_snapshot({"System": {
            "MihomoProcessRunning": False,
            "ServiceModeActive": False,
            "MixedPortListening": False,
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.service"].status, "unknown")

    def test_teredo_disabled_pass(self):
        checks = analyze_snapshot({"System": {
            "Teredo": {"Available": True, "Type": "Disabled", "Disabled": True},
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.teredo"].status, "pass")

    def test_teredo_enabled_warning(self):
        checks = analyze_snapshot({"System": {
            "Teredo": {"Available": True, "Type": "Client", "Disabled": False},
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.teredo"].status, "warning")

    def test_ipv6_binding_no_physical_enabled_pass(self):
        checks = analyze_snapshot({"System": {
            "ActiveAdapterIPv6Bindings": [
                {"Interface": "vEthernet", "Classification": "VirtualOrOther", "Enabled": True},
                {"Interface": "Realtek", "Classification": "Physical", "Enabled": False},
            ],
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.ipv6_binding"].status, "pass")

    def test_ipv6_binding_physical_enabled_warning(self):
        checks = analyze_snapshot({"System": {
            "ActiveAdapterIPv6Bindings": [
                {"Interface": "Realtek", "Classification": "Physical", "Enabled": True},
            ],
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.ipv6_binding"].status, "warning")

    def test_env_proxy_present_unknown(self):
        checks = analyze_snapshot({"System": {
            "ProxyEnvironmentVariables": [
                {"Scope": "Process", "Name": "HTTP_PROXY", "Present": True},
                {"Scope": "User", "Name": "NO_PROXY", "Present": True},
            ],
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.env_proxy"].status, "unknown")
        self.assertIn("HTTP_PROXY", ids["network.env_proxy"].explanation)
        self.assertIn("NO_PROXY", ids["network.env_proxy"].explanation)
        # values must never appear in the explanation
        self.assertNotIn("://", ids["network.env_proxy"].explanation)

    def test_env_proxy_absent_pass(self):
        checks = analyze_snapshot({"System": {
            "ProxyEnvironmentVariables": [
                {"Scope": "Process", "Name": "HTTP_PROXY", "Present": False},
            ],
        }})
        ids = _ids(checks)
        self.assertEqual(ids["network.env_proxy"].status, "pass")

    def test_locale_consistent_pass(self):
        checks = analyze_snapshot({"System": {
            "Culture": "en-US",
            "UICulture": "en-US",
            "SystemLocale": "en-US",
            "UserLanguageList": ["en-US", "zh-Hans-SG"],
        }})
        ids = _ids(checks)
        self.assertEqual(ids["system.locale"].status, "pass")

    def test_locale_mismatch_warning(self):
        checks = analyze_snapshot({"System": {
            "Culture": "en-US",
            "UICulture": "en-GB",
            "SystemLocale": "zh-CN",
            "UserLanguageList": ["ja-JP"],
        }})
        ids = _ids(checks)
        self.assertEqual(ids["system.locale"].status, "warning")

    def test_system_checks_run_without_mihomo(self):
        # Regression: system checks must run even when Mihomo config is absent
        checks = analyze_snapshot({"System": {
            "Teredo": {"Available": True, "Disabled": True},
        }})
        ids = _ids(checks)
        self.assertIn("network.teredo", ids)
        self.assertIn("network.mihomo", ids)
        self.assertEqual(ids["network.mihomo"].status, "unknown")

    def test_known_ids_unchanged(self):
        # Existing Mihomo checks keep their ids when config is present
        checks = analyze_snapshot({"Mihomo": {
            "AppConfigPresent": True,
            "Mode": "Rule",
            "AllowLan": False,
            "TunEnabled": True,
            "StrictRoute": True,
            "DnsEnabled": True,
            "DnsMode": "fake-ip",
            "DnsHijackAny53": True,
        }})
        ids = _ids(checks)
        for check_id in ("network.mode", "network.allow_lan", "network.tun",
                         "network.strict_route", "network.dns",
                         "network.dns_mode", "network.dns_hijack"):
            self.assertIn(check_id, ids)


if __name__ == "__main__":
    unittest.main()
