from __future__ import annotations

import json
from typing import Any

from .factory import build_agent
from .models import IacRequest


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point compatible with Bedrock action group payloads."""
    agent = build_agent()
    action = event.get("actionGroup") or event.get("operation") or event.get("apiPath", "chat")
    parameters = _parameters(event)

    if "health" in str(action):
        response = agent.handle(parameters.get("message", "summarize active system health issues"))
        body = response.__dict__
    elif "ssm" in str(action):
        result = agent.provider.run_ssm_check(parameters.get("check_name", "system-health"), parameters["target"])
        body = result.__dict__
    elif "secret" in str(action):
        result = agent.provider.validate_secret(parameters["secret_name"])
        body = result.__dict__
    elif "iac" in str(action) or "environment" in str(action):
        request = IacRequest(
            action=parameters.get("action", "plan"),
            environment=parameters.get("environment", "dev"),
            template=parameters.get("template", "quickslot-prod-like-dev"),
            ttl_hours=int(parameters.get("ttl_hours", 24)),
            variables=parameters.get("variables", {}),
        )
        body = agent.provider.invoke_iac(request)
    else:
        response = agent.handle(parameters.get("message", json.dumps(event)))
        body = response.__dict__

    return _bedrock_response(event, body)


def _parameters(event: dict[str, Any]) -> dict[str, Any]:
    if "parameters" in event and isinstance(event["parameters"], list):
        return {item["name"]: item.get("value") for item in event["parameters"]}
    if "requestBody" in event:
        content = event["requestBody"].get("content", {})
        for media in content.values():
            if "properties" in media:
                return {item["name"]: item.get("value") for item in media["properties"]}
    return event.get("parameters", {}) if isinstance(event.get("parameters"), dict) else {}


def _bedrock_response(event: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "quickslot-devops-copilot"),
            "apiPath": event.get("apiPath", "/chat"),
            "httpMethod": event.get("httpMethod", "POST"),
            "httpStatusCode": 200,
            "responseBody": {"application/json": {"body": json.dumps(body, default=str)}},
        },
    }
