#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
echo "=== Contingut de staticfiles_build/static/ ==="
find staticfiles_build/static/ -type f | head -40
