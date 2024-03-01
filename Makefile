format:
	isort . -m HANGING_INDENT -l 120

dev: format
	uvicorn appinspector.app:app --reload --port 20242
