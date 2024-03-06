format:
	poetry run isort . -m HANGING_INDENT -l 120

test:
	poetry run pytest -v tests

cov:
	poetry run pytest --cov=. --cov-report xml --cov-report term

dev: format
	poetry run appinspector --reload --port 20242

mock:
	poetry run appinspector --mock --port 20242 --reload
