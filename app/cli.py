from __future__ import annotations

import argparse
import json

from .factory import build_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="QuickSlot DevOps Co-Pilot")
    parser.add_argument("message", help="Incident report, health request, SNS payload, or platform task.")
    parser.add_argument("--json", action="store_true", help="Print the full response as JSON.")
    args = parser.parse_args()

    response = build_agent().handle(args.message)
    if args.json:
        print(json.dumps(response.__dict__, indent=2, default=str))
        return

    print(f"[{response.severity.upper()}] {response.intent}")
    print(response.message)
    if response.actions:
        print("\nRecommended actions:")
        for action in response.actions:
            print(f"- {action}")


if __name__ == "__main__":
    main()
