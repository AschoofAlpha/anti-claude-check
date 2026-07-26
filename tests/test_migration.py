import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from claude_shield.schema import validate_report, SchemaValidationError

class TestSchemaMigration(unittest.TestCase):
    def test_findings_migration(self):
        report = {
            "schema_version": "1.0.0",
            "tool_version": "1.0.0",
            "generated_at": "2026-07-25T00:00:00Z",
            "platform": {"os": "mock", "version": "1", "hostname": "mock"},
            "privacy": {"redaction_enabled": True, "salt_used": True},
            "findings": [
                {
                    "id": "test",
                    "title": "test",
                    "category": "test",
                    "status": "pass",
                    "severity": "info",
                    "confidence": "confirmed"
                }
            ],
            "summary": {"info": 1},
            "errors": []
        }
        
        # Validates and mutates
        self.assertTrue(validate_report(report))
        self.assertNotIn('findings', report)
        self.assertIn('checks', report)
        
    def test_findings_and_checks_conflict(self):
        report = {
            "schema_version": "1.0.0",
            "findings": [],
            "checks": []
        }
        with self.assertRaises(SchemaValidationError) as ctx:
            validate_report(report)
        self.assertIn("Cannot contain both", str(ctx.exception))
        
    def test_unknown_field(self):
        report = {
            "schema_version": "1.0.0",
            "tool_version": "1.0.0",
            "generated_at": "2026-07-25T00:00:00Z",
            "platform": {"os": "mock", "version": "1", "hostname": "mock"},
            "privacy": {"redaction_enabled": True, "salt_used": True},
            "checks": [],
            "summary": {"info": 1},
            "errors": [],
            "unknown_field_123": True
        }
        with self.assertRaises(SchemaValidationError) as ctx:
            validate_report(report)
        self.assertIn("Unknown root field: unknown_field_123", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
