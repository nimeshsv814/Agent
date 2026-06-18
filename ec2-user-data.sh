#!/bin/bash
set -euo pipefail

APP_USER="ubuntu"
APP_DIR="/opt/quickslot-agent"
AGENT_DIR="$APP_DIR"

REPO_URL="https://github.com/nimeshsv814/Agent.git"

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y git nginx python3 python3-pip python3-venv

if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR"
  git pull --ff-only
fi

cd "$AGENT_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > "$AGENT_DIR/.env" <<EOF
QUICKSLOT_AGENT_MODE=aws
AWS_REGION=us-east-1
QUICKSLOT_APP_NAME=quickslot
QUICKSLOT_IAC_LAMBDA_NAME=quickslot-iac-runner
QUICKSLOT_ALLOWED_INSTANCE_TAG=Application=smart-parking
QUICKSLOT_DEFAULT_SECRET_NAME=quickslot-05
QUICKSLOT_DEFAULT_LOG_MINUTES=30
EOF

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

cat > /etc/systemd/system/quickslot-agent.service <<EOF
[Unit]
Description=QuickSlot DevOps Co-Pilot Agent
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=$AGENT_DIR
EnvironmentFile=$AGENT_DIR/.env
ExecStart=$AGENT_DIR/.venv/bin/uvicorn app.api:app --host 127.0.0.1 --port 8010
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/quickslot-agent <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/quickslot-agent /etc/nginx/sites-enabled/quickslot-agent
nginx -t

systemctl daemon-reload
systemctl enable quickslot-agent
systemctl restart quickslot-agent
systemctl enable nginx
systemctl restart nginx

sleep 5
systemctl --no-pager status quickslot-agent || true
curl -fsS http://127.0.0.1/health || true
