#!/usr/bin/env bash
# Run static analysis helpers if available, otherwise fall back to bytecode checks.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
cd "${ROOT_DIR}"

ran_tool=false

run_if_available() {
  local tool="$1"
  shift || true
  if command -v "${tool}" >/dev/null 2>&1; then
    echo "Running ${tool} $*"
    "${tool}" "$@"
    ran_tool=true
  fi
}

run_if_available ruff check .
run_if_available flake8 .

if [[ "${ran_tool}" == false ]]; then
  echo "No lint-specific tool found; running bytecode compilation as a safety net."
  "${PYTHON_BIN}" -m compileall agents utils
fi
