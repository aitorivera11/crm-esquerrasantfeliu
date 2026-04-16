#!/usr/bin/env bash
set -euo pipefail

mkdir -p audits/reports/code

echo "==> Ruff check"
ruff check . | tee audits/reports/code/ruff.txt

echo "==> Ruff format check"
ruff format --check . | tee audits/reports/code/ruff-format.txt

echo "==> Bandit"
bandit -r . -x .venv,node_modules,migrations,staticfiles \
  -f txt -o audits/reports/code/bandit.txt || true

echo "==> pip-audit"
pip-audit -r requirements.txt | tee audits/reports/code/pip-audit.txt || true

echo "OK"
