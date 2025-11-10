#!/usr/bin/env bash
# Apply formatting using the best available tool.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if command -v ruff >/dev/null 2>&1; then
  echo "Running ruff format"
  ruff format .
  exit 0
fi

if command -v black >/dev/null 2>&1; then
  echo "Running black"
  black .
  exit 0
fi

echo "No formatter (ruff or black) found; nothing to format."
exit 0
