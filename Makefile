
lint:
	ruff check --fix .
	black .
	mypy .

check:
	ruff check .
	black --check .
	mypy .

