#!/usr/bin/env bash
# Run the project test suite with sensible defaults.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
PYTEST_ARGS=("$@")

if [[ $# -eq 0 ]]; then
  PYTEST_ARGS=("-q")
fi

export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

CMD=("${PYTHON_BIN}" "-m" "pytest")
CMD+=("${PYTEST_ARGS[@]}")

echo "Executing: ${CMD[*]}"
cd "${ROOT_DIR}"
"${CMD[@]}"
