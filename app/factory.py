from __future__ import annotations

from .agent import DevOpsCopilot
from .config import load_settings
from .mock_provider import MockPlatformProvider


def build_agent() -> DevOpsCopilot:
    settings = load_settings()
    if settings.mode == "aws":
        from .aws_provider import AwsPlatformProvider

        provider = AwsPlatformProvider(settings)
    else:
        provider = MockPlatformProvider()
    return DevOpsCopilot(provider, settings)
