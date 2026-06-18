from __future__ import annotations

from typing import Protocol

from .models import Alarm, HealthSummary, IacRequest, SecretValidation, SsmCheckResult


class PlatformProvider(Protocol):
    def list_active_alarms(self) -> list[Alarm]:
        ...

    def summarize_health(self, service: str | None = None, az: str | None = None) -> HealthSummary:
        ...

    def run_ssm_check(self, check_name: str, target: str) -> SsmCheckResult:
        ...

    def validate_secret(self, secret_name: str) -> SecretValidation:
        ...

    def invoke_iac(self, request: IacRequest) -> dict:
        ...
