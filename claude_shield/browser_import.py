import json
from pathlib import Path

from . import __version__
from .models import AuditReport, AuditCheck, Evidence, PlatformInfo, PrivacyMetadata
from .redaction import Redactor


_STATUSES = {"pass", "fail", "warning", "skipped", "unknown"}
_SEVERITIES = {"critical", "high", "medium", "low", "info"}
_CONFIDENCE = {"confirmed", "probable", "possible", "unknown"}


def _validate(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Browser report must be a JSON object.")

    version = data.get("version")
    if not isinstance(version, str) or version.split(".")[0] != "1":
        raise ValueError("Unsupported or missing browser report version.")
    if not isinstance(data.get("timestamp"), str):
        raise ValueError("Browser report timestamp is required.")

    findings = data.get("findings")
    checks = data.get("checks")
    if findings is not None and checks is not None:
        raise ValueError("Cannot contain both 'findings' and 'checks'.")
    raw_checks = findings if findings is not None else checks
    if not isinstance(raw_checks, list):
        raise ValueError("Browser report findings must be an array.")

    required = {"id", "title", "category", "status", "severity", "confidence"}
    for item in raw_checks:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError("Each browser finding must contain the required fields.")
        if item["status"] not in _STATUSES:
            raise ValueError(f"Invalid browser finding status: {item['status']}")
        if item["severity"] not in _SEVERITIES:
            raise ValueError(f"Invalid browser finding severity: {item['severity']}")
        if item["confidence"] not in _CONFIDENCE:
            raise ValueError(f"Invalid browser finding confidence: {item['confidence']}")
        if not isinstance(item.get("evidence", []), list):
            raise ValueError("Browser finding evidence must be an array.")

    return data


def _check_limits(obj, level=0):
    if level > 20:
        raise ValueError("JSON too deep")
    if isinstance(obj, dict):
        if len(obj) > 100:
            raise ValueError("Too many keys in object")
        for key, value in obj.items():
            if len(str(key)) > 1000:
                raise ValueError("Key too long")
            _check_limits(value, level + 1)
    elif isinstance(obj, list):
        if len(obj) > 1000:
            raise ValueError("Array too large")
        for value in obj:
            _check_limits(value, level + 1)
    elif isinstance(obj, str) and len(obj) > 10000:
        raise ValueError("String too long")


def import_browser_report(path: str) -> AuditReport:
    file_path = Path(path).resolve()
    if file_path.stat().st_size > 1024 * 1024:
        raise ValueError("Browser report file too large (max 1MB).")

    def reject_constant(value):
        raise ValueError(f"Invalid constant: {value}")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"), parse_constant=reject_constant)
        _check_limits(data)
        _validate(data)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid browser report: {exc}") from exc

    redactor = Redactor()
    raw_checks = data.get("findings", data.get("checks", []))
    checks = []
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

    for item in raw_checks:
        evidence = []
        for raw_evidence in item.get("evidence", []):
            if not isinstance(raw_evidence, dict):
                continue
            evidence.append(Evidence(
                type=str(raw_evidence.get("type", "browser")),
                description=redactor._redact_string(str(raw_evidence.get("description", ""))),
                data=redactor.scan_and_redact(raw_evidence.get("data")),
            ))

        severity = item["severity"]
        if item["category"] == "network" and item["status"] == "fail":
            severity = "high"
        check = AuditCheck(
            id=str(item["id"]),
            title=redactor._redact_string(str(item["title"])),
            category=str(item["category"]),
            status=item["status"],
            severity=severity,
            confidence=item["confidence"],
            evidence=evidence,
            explanation=redactor._redact_string(str(item.get("explanation", ""))),
            recommendation=redactor._redact_string(str(item.get("recommendation", ""))),
        )
        checks.append(check)
        summary[severity] += 1

    assessment = data.get("assessment") if isinstance(data.get("assessment"), dict) else {}
    score = assessment.get("overall")
    if not isinstance(score, int) or not 0 <= score <= 100:
        score = None
    raw_categories = assessment.get("scores") if isinstance(assessment.get("scores"), dict) else {}
    categories = {
        str(name): value
        for name, value in raw_categories.items()
        if value is None or isinstance(value, int) and 0 <= value <= 100
    }

    return AuditReport(
        schema_version=data["version"],
        tool_version=__version__,
        platform=PlatformInfo(os=f"browser-{data.get('browser_env', 'unknown')}", version="", hostname=""),
        privacy=PrivacyMetadata(redaction_enabled=True, salt_used=True),
        generated_at=data["timestamp"],
        checks=checks,
        summary=summary,
        errors=[],
        score=score,
        score_categories=categories,
    )
