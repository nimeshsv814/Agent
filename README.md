# QuickSlot DevOps Co-Pilot

An incident responder and platform engineering agent for the QuickSlot AWS stack.

The app is intentionally self-contained in this `Agent` folder. It can run in mock mode for local demos, or use `boto3` in AWS mode to read CloudWatch alarms/logs, receive SNS alert payloads, run guarded SSM health checks, validate Secrets Manager configuration without printing secret values, and trigger an IaC Lambda action.

## What It Can Do

- Summarize active CloudWatch health issues for QuickSlot.
- Triage natural-language incidents such as `QuickSlot is seeing a spike in booking errors in AZ-1`.
- Parse SNS alarm notifications and produce operator-friendly summaries.
- Run allow-listed SSM Session Manager checks on private instances.
- Validate secret metadata and naming/KMS policy expectations without exposing credentials.
- Trigger a Terraform/CDK provisioning Lambda through a Bedrock action group compatible handler.

## Project Layout

```text
Agent/
  app/
    agent.py              # Intent routing and incident workflows
    api.py                # FastAPI app
    aws_provider.py       # boto3-backed AWS integration
    cli.py                # Local command-line interface
    config.py             # Environment-driven settings
    lambda_handler.py     # Bedrock action group / Lambda handler
    mock_provider.py      # Demo provider with deterministic incidents
    models.py             # Shared dataclasses
    policy.py             # Safety rules for SSM, secrets, and IaC
    provider.py           # Provider interface
  tests/
  .env.example
  bedrock-action-group-openapi.yaml
  iam-policy-example.json
  requirements.txt
```

## Quick Start

```powershell
cd Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.cli "QuickSlot is seeing a spike in booking errors in AZ-1"
```

By default, `QUICKSLOT_AGENT_MODE=mock`, so no AWS calls are made.

## Run The API

```powershell
cd Agent
uvicorn app.api:app --reload --port 8010
```

Example request:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8010/chat `
  -ContentType "application/json" `
  -Body '{"message":"summarize active system health issues"}'
```

## AWS Mode

Set these values in the environment or copy `.env.example` to `.env` for your own runner:

```powershell
$env:QUICKSLOT_AGENT_MODE="aws"
$env:AWS_REGION="ap-south-1"
$env:QUICKSLOT_IAC_LAMBDA_NAME="quickslot-iac-runner"
```

The agent expects IAM permissions for read-only CloudWatch/Logs/SNS metadata, guarded SSM command execution, Secrets Manager metadata inspection, and Lambda invoke for the configured IaC runner.

`iam-policy-example.json` is a starting point for the Lambda execution role. Tighten resource ARNs for your account, region, log groups, SSM document, and instance tags before production use.

## Bedrock Action Group

Use `bedrock-action-group-openapi.yaml` as the action schema and `app.lambda_handler.handler` as the Lambda entry point. The handler supports:

- `/health/summary`
- `/ssm/check`
- `/secrets/validate`
- `/iac/environment`

## Safety Defaults

- SSM commands are allow-listed in `app/policy.py`.
- Secrets Manager reads only metadata by default and never returns secret values.
- IaC requests require an explicit environment, action, and TTL for temporary dev environments.
- Destructive infrastructure actions are blocked by policy.
