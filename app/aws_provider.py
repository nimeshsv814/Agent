from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

from .config import Settings
from .models import Alarm, HealthSummary, IacRequest, LogFinding, SecretValidation, SsmCheckResult
from .policy import ALLOWED_SSM_COMMANDS, validate_iac_request, validate_secret_name, validate_ssm_check


class AwsPlatformProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cloudwatch = boto3.client("cloudwatch", region_name=settings.region)
        self.logs = boto3.client("logs", region_name=settings.region)
        self.ssm = boto3.client("ssm", region_name=settings.region)
        self.secrets = boto3.client("secretsmanager", region_name=settings.region)
        self.lambda_client = boto3.client("lambda", region_name=settings.region)

    def list_active_alarms(self) -> list[Alarm]:
        response = self.cloudwatch.describe_alarms(StateValue="ALARM")
        alarms = []
        for item in response.get("MetricAlarms", []):
            alarms.append(
                Alarm(
                    name=item["AlarmName"],
                    state=item["StateValue"],
                    reason=item.get("StateReason", ""),
                    namespace=item.get("Namespace"),
                    metric_name=item.get("MetricName"),
                    updated_at=item.get("StateUpdatedTimestamp"),
                )
            )
        return alarms

    def summarize_health(self, service: str | None = None, az: str | None = None) -> HealthSummary:
        alarms = self.list_active_alarms()
        findings = self._query_error_logs(service=service, az=az)
        severity = "critical" if alarms or any(f.count >= 10 for f in findings) else "info"
        target = service or "all QuickSlot services"
        summary = f"Found {len(alarms)} active alarms and {len(findings)} recent log findings for {target}."
        actions = [
            "Open the active CloudWatch alarms and confirm target group health.",
            "Run an allow-listed SSM health check on affected private instances.",
            "Validate recent configuration changes in Secrets Manager metadata.",
        ]
        return HealthSummary(severity=severity, summary=summary, alarms=alarms, findings=findings, recommended_actions=actions)

    def run_ssm_check(self, check_name: str, target: str) -> SsmCheckResult:
        decision = validate_ssm_check(check_name)
        if not decision.allowed:
            return SsmCheckResult(check_name, target, "blocked", decision.reason)

        response = self.ssm.send_command(
            InstanceIds=[target],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": [ALLOWED_SSM_COMMANDS[check_name]]},
            Comment=f"QuickSlot agent check: {check_name}",
            TimeoutSeconds=60,
        )
        command_id = response["Command"]["CommandId"]
        time.sleep(2)
        invocation = self.ssm.get_command_invocation(CommandId=command_id, InstanceId=target)
        output = invocation.get("StandardOutputContent", "") + invocation.get("StandardErrorContent", "")
        return SsmCheckResult(check_name, target, invocation.get("Status", "Unknown"), output[:4000])

    def validate_secret(self, secret_name: str) -> SecretValidation:
        decision = validate_secret_name(secret_name)
        findings = [] if decision.allowed else [decision.reason]
        try:
            metadata = self.secrets.describe_secret(SecretId=secret_name)
        except Exception as exc:
            return SecretValidation(secret_name, False, findings + [f"Unable to describe secret metadata: {exc}"])

        if not metadata.get("KmsKeyId"):
            findings.append("Secret does not report a customer-managed KMS key.")
        if not metadata.get("RotationEnabled"):
            findings.append("Secret rotation is not enabled.")
        return SecretValidation(secret_name, len(findings) == 0, findings)

    def invoke_iac(self, request: IacRequest) -> dict[str, Any]:
        decision = validate_iac_request(request)
        if not decision.allowed:
            return {"status": "blocked", "reason": decision.reason}
        payload = {
            "source": "quickslot-devops-copilot",
            "request": {
                "action": request.action,
                "environment": request.environment,
                "template": request.template,
                "ttl_hours": request.ttl_hours,
                "variables": request.variables,
            },
        }
        response = self.lambda_client.invoke(
            FunctionName=self.settings.iac_lambda_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        body = response["Payload"].read().decode("utf-8")
        return {"status": "invoked", "lambda_status": response.get("StatusCode"), "response": body}

    def _query_error_logs(self, service: str | None, az: str | None) -> list[LogFinding]:
        services = [service] if service and service in self.settings.log_group_names else list(self.settings.log_group_names)
        start_time = int((datetime.now(timezone.utc) - timedelta(minutes=self.settings.default_log_minutes)).timestamp())
        findings: list[LogFinding] = []
        for svc in services:
            log_group = self.settings.log_group_names[svc]
            query = "fields @timestamp, @message | filter @message like /ERROR|Exception|HTTP 5/ | sort @timestamp desc | limit 20"
            query_id = self.logs.start_query(logGroupName=log_group, startTime=start_time, endTime=int(time.time()), queryString=query)["queryId"]
            result = self._wait_for_query(query_id)
            for row in result[:5]:
                message = self._field(row, "@message")
                if az and az not in message:
                    continue
                findings.append(LogFinding(service=svc, az=az, message=message[:500], latest_at=datetime.now(timezone.utc)))
        return findings

    def _wait_for_query(self, query_id: str) -> list[list[dict[str, str]]]:
        for _ in range(10):
            response = self.logs.get_query_results(queryId=query_id)
            if response["status"] in {"Complete", "Failed", "Cancelled", "Timeout"}:
                return response.get("results", [])
            time.sleep(1)
        return []

    @staticmethod
    def _field(row: list[dict[str, str]], name: str) -> str:
        for item in row:
            if item.get("field") == name:
                return item.get("value", "")
        return ""
