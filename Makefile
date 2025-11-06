PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip

.PHONY: install run-network studio milvus-lite clean

$(VENV_BIN)/python:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install: $(VENV_BIN)/python
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
	rm -rf $(VENV) .milvus
