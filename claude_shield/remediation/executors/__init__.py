from .base import RemediationExecutor
from .gitignore import GitIgnoreExecutor
from .permissions import PermissionsExecutor
from .quarantine import QuarantineExecutor
from .git_unstage import GitUnstageExecutor
from .env_template import EnvTemplateExecutor
from .report_redaction import ReportRedactionExecutor
from .browser_profile import BrowserProfileRemediationExecutor

EXECUTORS = {
    "gitignore": GitIgnoreExecutor(),
    "permissions": PermissionsExecutor(),
    "quarantine": QuarantineExecutor(),
    "git-unstage": GitUnstageExecutor(),
    "env-template": EnvTemplateExecutor(),
    "redact-report": ReportRedactionExecutor(),
    "browser-profile-reset": BrowserProfileRemediationExecutor()
}

def get_executor(executor_id: str) -> RemediationExecutor:
    return EXECUTORS.get(executor_id)
