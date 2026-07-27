import unittest
import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from claude_shield.schema import validate_report, SchemaValidationError
from claude_shield.cli import _collector_checks

class TestPhase2(unittest.TestCase):
    def test_privacy_controls_require_value_one(self):
        checks = _collector_checks({"ClaudeCode": {
            "DisableTelemetryVars": [{"Scope": "User", "Value": "0"}],
            "DisableErrorReportingVars": [{"Scope": "User", "Value": "false"}],
            "DisableNonessentialTrafficVars": [],
        }})
        self.assertTrue(all(check.status == "unknown" for check in checks[:3]))

    def test_broad_privacy_control_covers_metrics_and_errors(self):
        checks = _collector_checks({"ClaudeCode": {"DisableNonessentialTrafficActive": True}})
        self.assertTrue(all(check.status == "pass" for check in checks[:3]))

    def test_schema_valid(self):
        report = {
            "schema_version": "1.0.0",
            "checks": [
                {
                    "id": "test",
                    "status": "pass",
                    "severity": "info",
                    "confidence": "confirmed"
                }
            ]
        }
        self.assertTrue(validate_report(report))
        
    def test_schema_missing_version(self):
        report = {"checks": []}
        with self.assertRaises(SchemaValidationError):
            validate_report(report)
            
    def test_schema_invalid_status(self):
        report = {
            "schema_version": "1.0.0",
            "checks": [{"id": "t", "status": "foo", "severity": "info", "confidence": "confirmed"}]
        }
        with self.assertRaises(SchemaValidationError):
            validate_report(report)

    def test_schema_unsupported_major(self):
        report = {"schema_version": "2.0.0"}
        with self.assertRaises(SchemaValidationError):
            validate_report(report)

    def test_cli_audit_json(self):
        # Run CLI in JSON format and check it's valid JSON and contains summary
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        result = subprocess.run(
            [sys.executable, '-m', 'claude_shield', 'audit', '--format', 'json'],
            env=env,
            capture_output=True,
            text=True
        )
        # Note: Depending on the mock, it might exit with 0 or 1 (if medium risk found)
        self.assertIn(result.returncode, (0, 1, 2))
        try:
            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "1.0.0")
            self.assertIn("summary", data)
        except Exception as e:
            self.fail(f"Failed to parse JSON output: {e}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
            
    def test_cli_doctor(self):
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        result = subprocess.run(
            [sys.executable, '-m', 'claude_shield', 'doctor'],
            env=env,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Doctor", result.stdout)

if __name__ == '__main__':
    unittest.main()
