#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for DB..."
python manage.py wait_for_db 2>/dev/null || true

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
