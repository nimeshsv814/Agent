from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import load_settings
from .factory import build_agent
from .models import IacRequest


app = FastAPI(title="QuickSlot DevOps Co-Pilot", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str


class SsmRequest(BaseModel):
    check_name: str = "system-health"
    target: str


class SecretRequest(BaseModel):
    secret_name: str


class IacApiRequest(BaseModel):
    action: str
    environment: str
    template: str
    ttl_hours: int | None = None
    variables: dict[str, Any] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "quickslot-devops-copilot"}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config")
def config() -> dict[str, Any]:
    settings = load_settings()
    return {
        "mode": settings.mode,
        "region": settings.region,
        "app_name": settings.app_name,
        "iac_lambda_name": settings.iac_lambda_name,
        "default_secret_name": settings.default_secret_name,
        "log_groups": settings.log_group_names,
    }


@app.get("/alarms")
def alarms() -> dict[str, Any]:
    provider = build_agent().provider
    try:
        active_alarms = provider.list_active_alarms()
        return {
            "count": len(active_alarms),
            "alarms": jsonable_encoder(active_alarms),
            "error": None,
        }
    except Exception as exc:
        return {
            "count": 0,
            "alarms": [],
            "error": str(exc),
        }


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    return build_agent().handle(request.message).__dict__


@app.post("/sns")
def sns(payload: dict[str, Any]) -> dict[str, Any]:
    return build_agent().handle_sns_message(__import__("json").dumps(payload)).__dict__


@app.post("/ssm/check")
def ssm_check(request: SsmRequest) -> dict[str, Any]:
    provider = build_agent().provider
    return provider.run_ssm_check(request.check_name, request.target).__dict__


@app.post("/secrets/validate")
def validate_secret(request: SecretRequest) -> dict[str, Any]:
    provider = build_agent().provider
    return provider.validate_secret(request.secret_name).__dict__


@app.post("/iac/invoke")
def invoke_iac(request: IacApiRequest) -> dict[str, Any]:
    provider = build_agent().provider
    iac_request = IacRequest(
        action=request.action,  # type: ignore[arg-type]
        environment=request.environment,
        template=request.template,
        ttl_hours=request.ttl_hours,
        variables=request.variables,
    )
    return provider.invoke_iac(iac_request)
