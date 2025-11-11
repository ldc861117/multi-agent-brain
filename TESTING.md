# Testing Guide

This repository ships with several test layers to keep development fast while preserving reliability. All suites run offline – no external APIs or vector stores are contacted during the smoke checks – which keeps CI stable even when networking is unavailable.

## Quick smoke verification

Use the lightweight smoke suite when you need a fast confidence boost (runs in under a minute on a typical laptop):

```bash
pytest tests/smoke -q
```

These tests validate module imports, configuration loading overrides, and the coordination happy-path using fully mocked dependencies.

## Full test suite with coverage

For pre-commit or CI parity run the full suite with coverage enabled:

```bash
pytest --cov=agents --cov=utils \
       --cov-report=term-missing --cov-report=xml --cov-report=html \
       --cov-fail-under=60
```

The command above respects `.coveragerc`, outputs both HTML (`htmlcov/`) and XML (`coverage.xml`) reports, and enforces a 60% minimum coverage gate.

## Continuous Integration notes

GitHub Actions executes the same coverage command across Python 3.10 and 3.11. Coverage artifacts (`coverage.xml` and `htmlcov/`) are uploaded for pull-request annotations. If the coverage threshold drops below 60%, the CI job will fail, ensuring regressions are caught early.
