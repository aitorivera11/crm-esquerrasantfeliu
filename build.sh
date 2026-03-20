#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
echo "BUILD DONE: $(find staticfiles_build/static -type f | wc -l) ficheros estàtics"
