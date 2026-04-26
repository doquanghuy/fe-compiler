.PHONY: install dev fix typecheck test deadcode clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

fix:
	ruff check . --fix
	ruff format .

typecheck:
	pyright

test:
	pytest -q

deadcode:
	vulture src/fe_compiler --min-confidence 70 || true

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .pyright_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
