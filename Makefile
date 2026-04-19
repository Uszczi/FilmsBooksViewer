
lint:
	ruff check --fix .
	black .
	mypy .

check:
	ruff check .
	black --check .
	mypy .

dev-deps:
	python -m pip install ruff black mypy
