#!/usr/bin/env bash
set -euo pipefail

curl -sS http://localhost:8050/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Resume las anomalías de la última sesión","role":"crew_chief"}'
