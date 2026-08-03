import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestProbesSmoke(unittest.TestCase):
    """Smoke tests for the retained probes package (live network checks)."""

    def test_probes_importable(self):
        from claude_shield.probes.base import run_probes
        self.assertTrue(callable(run_probes))

    def test_probes_offline_run_returns_list(self):
        # run_probes with a short timeout and no endpoint should not crash;
        # results may be empty or unknown on restricted networks.
        from claude_shield.probes.base import run_probes
        try:
            results = run_probes(None, timeout=3)
            self.assertIsInstance(results, list)
        except Exception as exc:
            # Network unreachable is acceptable; hard crashes are not.
            self.fail(f"run_probes raised unexpected {type(exc).__name__}: {exc}")

    def test_endpoints_known(self):
        from claude_shield.probes import endpoints
        eps = endpoints.get_all_endpoints()
        self.assertIsInstance(eps, list)
        self.assertTrue(any(e.get("id") == "cloudflare-trace" for e in eps))


if __name__ == "__main__":
    unittest.main()
