from ..models import AuditCheck

def check_dns_consistency():
    return AuditCheck(
        id="network.dns.consistency",
        title="DNS resolution observation",
        category="network",
        status="skipped",
        severity="info",
        confidence="unknown",
        explanation="This check only identifies DNS configuration and resolution path differences. It cannot fully prove or exclude DNS leaks."
    )
