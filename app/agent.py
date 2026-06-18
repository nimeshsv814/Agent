from __future__ import annotations

import json
import re
from typing import Any

from .config import Settings, load_settings
from .models import AgentResponse, IacRequest
from .provider import PlatformProvider


class DevOpsCopilot:
    def __init__(self, provider: PlatformProvider, settings: Settings | None = None):
        self.provider = provider
        self.settings = settings or load_settings()

    def handle(self, message: str) -> AgentResponse:
        normalized = message.lower()
        if "sns" in normalized or "alarmname" in normalized:
            return self.handle_sns_message(message)
        if "secret" in normalized or "kms" in normalized:
            secret_name = self._extract_secret_name(message)
            validation = self.provider.validate_secret(secret_name)
            if validation.compliant:
                return AgentResponse("validate_secret", f"{validation.name} is compliant. No secret values were read.")
            return AgentResponse("validate_secret", f"{validation.name} has policy findings.", "warning", validation.findings)
        if "temporary" in normalized or "spin up" in normalized or "dev environment" in normalized:
            request = IacRequest(action="plan", environment="dev", template="quickslot-prod-like-dev", ttl_hours=24)
            result = self.provider.invoke_iac(request)
            severity = "warning" if result.get("status") == "blocked" else "info"
            return AgentResponse("provision_environment", self._format_iac_result(result), severity, raw=result)
        if "ssm" in normalized or "health check" in normalized:
            target = self._extract_instance_id(message)
            result = self.provider.run_ssm_check("system-health", target)
            severity = "warning" if result.status == "blocked" else "info"
            return AgentResponse("ssm_health_check", f"{result.status}: {result.output}", severity, raw=result.__dict__)

        service = self._extract_service(message)
        az = self._extract_az(message)
        health = self.provider.summarize_health(service=service, az=az)
        lines = [health.summary]
        if health.alarms:
            lines.append("Active alarms: " + ", ".join(alarm.name for alarm in health.alarms))
        if health.findings:
            lines.append("Top finding: " + health.findings[0].message)
        return AgentResponse("incident_triage", " ".join(lines), health.severity, health.recommended_actions)

    def handle_sns_message(self, message: str) -> AgentResponse:
        payload = self._json_or_text(message)
        if isinstance(payload, dict):
            alarm_name = payload.get("AlarmName") or payload.get("alarmName") or "unknown alarm"
            state = payload.get("NewStateValue") or payload.get("state") or "UNKNOWN"
            reason = payload.get("NewStateReason") or payload.get("reason") or "No reason supplied."
            text = f"SNS alarm {alarm_name} is {state}: {reason}"
            actions = ["Correlate this alarm with current ALB target health and recent service logs."]
            return AgentResponse("sns_alert", text, "critical" if state == "ALARM" else "info", actions, payload)
        return AgentResponse("sns_alert", "Received SNS-style alert text; summarize active health to correlate it.", "warning")

    def _extract_service(self, message: str) -> str | None:
        normalized = message.lower()
        for service in self.settings.log_group_names:
            if service in normalized:
                return service
        if "booking" in normalized:
            return "booking"
        return None

    @staticmethod
    def _extract_az(message: str) -> str | None:
        match = re.search(r"\b(az[-\s]?\d+|[a-z]{2}-[a-z]+-\d[a-z])\b", message, re.IGNORECASE)
        return match.group(1).replace(" ", "-").upper() if match else None

    @staticmethod
    def _extract_instance_id(message: str) -> str:
        match = re.search(r"\bi-[a-f0-9]{8,17}\b", message)
        return match.group(0) if match else "i-mockquickslot01"

    def _extract_secret_name(self, message: str) -> str:
        match = re.search(r"(quickslot|smart-parking)[A-Za-z0-9_./-]*", message)
        return match.group(0) if match else self.settings.default_secret_name

    @staticmethod
    def _json_or_text(message: str) -> dict[str, Any] | str:
        try:
            return json.loads(message)
        except json.JSONDecodeError:
            return message

    @staticmethod
    def _format_iac_result(result: dict[str, Any]) -> str:
        if result.get("status") == "blocked":
            return f"IaC request blocked: {result.get('reason')}"
        return "IaC request accepted for a 24-hour prod-like dev environment."
