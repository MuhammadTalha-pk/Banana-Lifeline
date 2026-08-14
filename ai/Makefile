PY := .venv/Scripts/python.exe
ifeq ($(OS),)
	PY := .venv/bin/python
endif

.PHONY: help setup audit split cache data test lint typecheck check clean-cache

help:
	@echo "setup      create the 3.11 venv and install the package"
	@echo "audit      fingerprint the corpus and write reports/data_audit.md"
	@echo "split      generate leakage-free + comparison manifests and the review sheet"
	@echo "cache      build the 512px training cache"
	@echo "data       audit + split + cache, in order"
	@echo "test       run the test suite"
	@echo "check      lint + typecheck + test"

setup:
	py -3.11 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

audit:
	$(PY) -m banana_lifeline.cli audit

split:
	$(PY) -m banana_lifeline.cli split

cache:
	$(PY) -m banana_lifeline.cli cache --variant clean

data: audit split cache

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

typecheck:
	$(PY) -m mypy

check: lint typecheck test

clean-cache:
	rm -rf data/cache
