.PHONY: install lint format test check notebook

# Create the virtual environment and install the project in editable mode, so
# that a notebook can import from src/ without any path juggling.
install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev,notebook]"

# The same two commands CI runs, so a green local run means a green CI run.
lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

test:
	pytest

check: lint test

notebook:
	jupyter lab
