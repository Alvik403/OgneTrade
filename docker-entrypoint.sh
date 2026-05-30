#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import os, sys, time
import psycopg2
url = os.environ.get('DATABASE_URL', '')
if not url.startswith('postgresql'):
    sys.exit(0)
parts = url.replace('postgresql://', '').split('@')
userpass, hostdb = parts[0], parts[1]
user, password = userpass.split(':')
host, rest = hostdb.split(':')
port, dbname = rest.split('/')
for i in range(30):
    try:
        psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
"; do
  sleep 1
done

echo "Running seed..."
python -m app.cli seed

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
