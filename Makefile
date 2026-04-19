
lint:
	ruff check --fix .
	black .
	mypy .

check:
	ruff check .
	black --check .
	mypy .

install:
	python -m pip install -e .

dev-deps:
	python -m pip install ruff black mypy
