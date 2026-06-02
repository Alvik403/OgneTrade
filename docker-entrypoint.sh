#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python - <<'PY'
import os
import sys
import time

import psycopg2
from urllib.parse import unquote, urlparse

url = os.environ.get("DATABASE_URL", "")
if not url.startswith("postgresql"):
    sys.exit(0)

parsed = urlparse(url)
host = parsed.hostname or os.environ.get("POSTGRES_HOST", "db")
port = parsed.port or int(os.environ.get("POSTGRES_PORT", "5432"))
user = parsed.username or os.environ.get("POSTGRES_USER", "lids")
password = unquote(parsed.password or "") or os.environ.get("POSTGRES_PASSWORD", "")
dbname = (parsed.path or "/lids").lstrip("/") or os.environ.get("POSTGRES_DB", "lids")

last_error = None
for attempt in range(60):
    try:
        psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=3,
        )
        sys.exit(0)
    except Exception as exc:
        last_error = exc
        if attempt in (0, 29, 59):
            print(f"PostgreSQL not ready ({attempt + 1}/60): {exc}", file=sys.stderr)
        time.sleep(1)

print(f"PostgreSQL unavailable after 60 attempts: {last_error}", file=sys.stderr)
sys.exit(1)
PY
do
  sleep 1
done

echo "Running seed..."
python -m app.cli seed

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
