.PHONY: check lint test coverage typecheck audit build clean

PYTHON ?= ./.venv/bin/python
PIP_AUDIT ?= ./.venv/bin/pip-audit

check: lint typecheck test coverage audit build

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest -q

coverage:
	$(PYTHON) -m coverage run -m pytest -q
	$(PYTHON) -m coverage report

typecheck:
	$(PYTHON) -m mypy src tests

audit:
	PIPAPI_PYTHON_LOCATION=$(PYTHON) $(PIP_AUDIT) --skip-editable

build: clean
	$(PYTHON) -m build

clean:
	rm -rf dist build *.egg-info
