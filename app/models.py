from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Severity = Literal["info", "warning", "critical"]


@dataclass(frozen=True)
class Alarm:
    name: str
    state: str
    reason: str
    namespace: str | None = None
    metric_name: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class LogFinding:
    service: str
    message: str
    count: int = 1
    az: str | None = None
    latest_at: datetime | None = None


@dataclass(frozen=True)
class HealthSummary:
    severity: Severity
    summary: str
    alarms: list[Alarm] = field(default_factory=list)
    findings: list[LogFinding] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SsmCheckResult:
    command: str
    target: str
    status: str
    output: str


@dataclass(frozen=True)
class SecretValidation:
    name: str
    compliant: bool
    findings: list[str]


@dataclass(frozen=True)
class IacRequest:
    action: Literal["plan", "apply", "destroy"]
    environment: str
    template: str
    ttl_hours: int | None = None
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResponse:
    intent: str
    message: str
    severity: Severity = "info"
    actions: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
