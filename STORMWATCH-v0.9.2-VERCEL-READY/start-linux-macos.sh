#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
python -m pip install -r apps/api/requirements.txt
export PYTHONPATH="$PWD/apps/api"
exec python -m uvicorn stormwatch.main:app --host 127.0.0.1 --port 8000
