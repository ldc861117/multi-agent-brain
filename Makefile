PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/python -m pip
PYTEST := $(VENV_BIN)/pytest

.PHONY: install run-network studio milvus-lite clean test test-fast cov cov-html verify-tests quick-verify lint format ci

$(VENV_BIN)/python:
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/python -m ensurepip --upgrade
	$(PIP) install --upgrade pip

install: $(VENV_BIN)/python
	$(VENV_BIN)/python -m ensurepip --upgrade
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run-network: install
	$(VENV_BIN)/openagents network http --config config.yaml

studio: install
	$(VENV_BIN)/openagents studio --config config.yaml

milvus-lite:
	docker run --rm -it \
	    -p 19530:19530 \
	    -p 9091:9091 \
	    -v "$(PWD)/.milvus:/var/lib/milvus" \
	    milvusdb/milvus:v2.4.4-liteserve

clean:
	rm -rf $(VENV) .milvus coverage.xml htmlcov

verify-tests:
	$(PYTHON) scripts/quick_verify.py

quick-verify: install
	PYTHON=$(VENV_BIN)/python scripts/quick_verify.py --run

lint: install
	PYTHON=$(VENV_BIN)/python scripts/lint.sh

format: install
	PYTHON=$(VENV_BIN)/python scripts/format.sh

test: install
	PYTHON=$(VENV_BIN)/python scripts/run_tests.sh

test-fast: install
	PYTHON=$(VENV_BIN)/python scripts/run_tests.sh -q -m "not slow and not integration"

cov: install
	PYTHON=$(VENV_BIN)/python scripts/run_tests.sh --cov-config=.coveragerc --cov=agents --cov=utils --cov-report=term-missing --cov-report=xml --cov-report=html

cov-html: cov

ci: install
	PYTHON=$(VENV_BIN)/python scripts/lint.sh
	PYTHON=$(VENV_BIN)/python scripts/run_tests.sh --cov-config=.coveragerc --cov=agents --cov=utils --cov-report=term-missing --cov-report=xml
