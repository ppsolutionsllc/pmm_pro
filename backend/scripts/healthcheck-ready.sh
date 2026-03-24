#!/usr/bin/env sh
set -eu

python - <<'PY'
import sys
import urllib.request

request = urllib.request.Request("http://127.0.0.1:8000/readyz", headers={"User-Agent": "pmm-healthcheck/1.0"})

try:
    with urllib.request.urlopen(request, timeout=3) as response:
        status = getattr(response, "status", response.getcode())
        if int(status) != 200:
            raise RuntimeError(f"unexpected status: {status}")
except Exception as exc:
    print(f"backend readiness check failed: {exc}", file=sys.stderr)
    sys.exit(1)
PY
