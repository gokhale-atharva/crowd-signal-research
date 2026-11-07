.PHONY: setup replay live test report

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -e ".[dev]"

replay:
	crowd-signal replay

live:
	crowd-signal run-all --exchange ALL

test:
	$(PYTHON) -m pytest
	$(PYTHON) -m ruff check src tests

report:
	crowd-signal report

