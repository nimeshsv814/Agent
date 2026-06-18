from __future__ import annotations

from .models import Alarm, HealthSummary, IacRequest, LogFinding, SecretValidation, SsmCheckResult, utcnow
from .policy import validate_iac_request, validate_secret_name, validate_ssm_check


class MockPlatformProvider:
    def list_active_alarms(self) -> list[Alarm]:
        return [
            Alarm(
                name="quickslot-external-alb-target-5xx",
                state="ALARM",
                reason="Target 5XX responses crossed threshold during the last 5 minutes.",
                namespace="AWS/ApplicationELB",
                metric_name="HTTPCode_Target_5XX_Count",
                updated_at=utcnow(),
            ),
            Alarm(
                name="quickslot-app-targets-unhealthy",
                state="ALARM",
                reason="Internal app target group has unhealthy targets.",
                namespace="AWS/ApplicationELB",
                metric_name="UnHealthyHostCount",
                updated_at=utcnow(),
            ),
        ]

    def summarize_health(self, service: str | None = None, az: str | None = None) -> HealthSummary:
        selected_service = service or "booking"
        selected_az = az or "AZ-1"
        findings = [
            LogFinding(
                service=selected_service,
                az=selected_az,
                message="Detected repeated HTTP 500 responses around booking confirmation flow.",
                count=42,
                latest_at=utcnow(),
            )
        ]
        return HealthSummary(
            severity="critical",
            summary=f"{selected_service.title()} service is degraded in {selected_az}; ALB 5XX and unhealthy target alarms are active.",
            alarms=self.list_active_alarms(),
            findings=findings,
            recommended_actions=[
                "Check target health for the internal app target group.",
                "Run SSM system-health on affected private instances.",
                "Inspect booking-service logs for recent deploy/config errors.",
                "Consider rolling back or scaling the affected Auto Scaling Group if saturation is confirmed.",
            ],
        )

    def run_ssm_check(self, check_name: str, target: str) -> SsmCheckResult:
        decision = validate_ssm_check(check_name)
        if not decision.allowed:
            return SsmCheckResult(check_name, target, "blocked", decision.reason)
        return SsmCheckResult(
            command=check_name,
            target=target,
            status="success",
            output="Mock SSM check passed: load average normal, disk below 70%, app ports listening.",
        )

    def validate_secret(self, secret_name: str) -> SecretValidation:
        decision = validate_secret_name(secret_name)
        findings = [] if decision.allowed else [decision.reason]
        if "prod" in secret_name.lower() and not secret_name.endswith("/current"):
            findings.append("Production secret should use a /current suffix for rotation-aware references.")
        return SecretValidation(secret_name, len(findings) == 0, findings)

    def invoke_iac(self, request: IacRequest) -> dict:
        decision = validate_iac_request(request)
        if not decision.allowed:
            return {"status": "blocked", "reason": decision.reason}
        return {
            "status": "accepted",
            "lambda": "mock",
            "request": {
                "action": request.action,
                "environment": request.environment,
                "template": request.template,
                "ttl_hours": request.ttl_hours,
                "variables": request.variables,
            },
        }
