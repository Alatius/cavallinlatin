#!/bin/bash
# Triggered by GitHub Actions over SSH (forced via the deploy user's
# authorized_keys command="..." restriction). Pulls master, rebuilds, and
# restarts the backend service.

set -euo pipefail

cd /var/www/cavallinlatin

echo "==> git pull"
git pull --ff-only

echo "==> backend deps"
editor/backend/.venv/bin/pip install -e editor --quiet

echo "==> frontend build"
cd editor/frontend
npm ci --silent
npm run build

echo "==> restart service"
sudo /usr/bin/systemctl restart cavallinlatin.service

echo "==> deployed"
