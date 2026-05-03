#!/usr/bin/env bash
set -euo pipefail

docker compose -f docker-compose.copilot.yml up --build
