from __future__ import annotations

from dataclasses import dataclass

from .models import IacRequest


ALLOWED_SSM_COMMANDS = {
    "system-health": "uptime && df -h && free -m",
    "app-port-check": "ss -tulpn | grep -E ':80|:8080|:3000' || true",
    "docker-health": "docker ps --format '{{.Names}} {{.Status}}'",
    "cloud-init-status": "cloud-init status --long",
}

BLOCKED_IAC_ACTIONS = {"destroy"}
ALLOWED_IAC_TEMPLATES = {"quickslot-dev", "quickslot-prod-like-dev", "quickslot-observability"}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


def validate_ssm_check(check_name: str) -> PolicyDecision:
    if check_name not in ALLOWED_SSM_COMMANDS:
        return PolicyDecision(False, f"SSM check '{check_name}' is not allow-listed.")
    return PolicyDecision(True, "Allowed SSM health check.")


def validate_secret_name(secret_name: str) -> PolicyDecision:
    normalized = secret_name.lower()
    if not normalized.startswith(("quickslot/", "quickslot-", "smart-parking/", "smart-parking-")):
        return PolicyDecision(False, "Secret must be scoped under quickslot or smart-parking naming.")
    return PolicyDecision(True, "Secret scope is valid.")


def validate_iac_request(request: IacRequest) -> PolicyDecision:
    if request.action in BLOCKED_IAC_ACTIONS:
        return PolicyDecision(False, f"IaC action '{request.action}' is blocked by policy.")
    if request.template not in ALLOWED_IAC_TEMPLATES:
        return PolicyDecision(False, f"IaC template '{request.template}' is not approved.")
    if request.environment != "dev" and request.ttl_hours is not None:
        return PolicyDecision(False, "TTL-based temporary environments must target dev.")
    if request.environment == "dev" and request.ttl_hours is None:
        return PolicyDecision(False, "Temporary dev environments require ttl_hours.")
    if request.ttl_hours is not None and not 1 <= request.ttl_hours <= 72:
        return PolicyDecision(False, "ttl_hours must be between 1 and 72.")
    return PolicyDecision(True, "IaC request satisfies safety policy.")
