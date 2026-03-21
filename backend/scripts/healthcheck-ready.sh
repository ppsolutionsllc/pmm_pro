#!/usr/bin/env sh
set -eu

python - <<'PY'
import os
import sys
import urllib.request

host = os.getenv("HEALTHCHECK_HOST", "pmm.66br.pp.ua").strip() or "pmm.66br.pp.ua"
request = urllib.request.Request(
    "http://127.0.0.1:8000/ready",
    headers={
        "Host": host,
        "User-Agent": "pmm-healthcheck/1.0",
    },
)

try:
    with urllib.request.urlopen(request, timeout=3) as response:
        status = getattr(response, "status", response.getcode())
        if int(status) != 200:
            raise RuntimeError(f"unexpected status: {status}")
except Exception as exc:
    print(f"backend readiness check failed: {exc}", file=sys.stderr)
    sys.exit(1)
PY
