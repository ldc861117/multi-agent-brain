PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/python -m pip
PYTEST := $(VENV_BIN)/pytest

.PHONY: install run-network studio milvus-lite clean test test-fast cov cov-html verify-tests

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
	scripts/verify_tests.py

test: install
	PYTHONPATH=. $(PYTEST) -q

test-fast: install
	PYTHONPATH=. $(PYTEST) -q -m "not slow and not integration"

cov: install
	PYTHONPATH=. $(PYTEST) --cov-config=.coveragerc --cov=agents --cov=utils --cov-report=term-missing --cov-report=xml --cov-report=html

cov-html: cov
