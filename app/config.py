from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mode: str = "aws"
    region: str = "us-east-1"
    app_name: str = "quickslot"
    iac_lambda_name: str = "quickslot-iac-runner"
    allowed_instance_tag: str = "Application=smart-parking"
    default_secret_name: str = "quickslot-05"
    default_log_minutes: int = 30

    @property
    def log_group_names(self) -> dict[str, str]:
        return {
            "auth": "/quickslot/app/auth-service",
            "parking": "/quickslot/app/parking-service",
            "booking": "/quickslot/app/booking-service",
            "payment": "/quickslot/app/payment-service",
            "scheduler": "/quickslot/app/scheduler-service",
            "notification": "/quickslot/app/notification-service",
        }


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        mode=os.getenv("QUICKSLOT_AGENT_MODE", "aws").lower(),
        region=os.getenv("AWS_REGION", "us-east-1"),
        app_name=os.getenv("QUICKSLOT_APP_NAME", "quickslot"),
        iac_lambda_name=os.getenv("QUICKSLOT_IAC_LAMBDA_NAME", "quickslot-iac-runner"),
        allowed_instance_tag=os.getenv("QUICKSLOT_ALLOWED_INSTANCE_TAG", "Application=smart-parking"),
        default_secret_name=os.getenv("QUICKSLOT_DEFAULT_SECRET_NAME", "quickslot-05"),
        default_log_minutes=int(os.getenv("QUICKSLOT_DEFAULT_LOG_MINUTES", "30")),
    )
