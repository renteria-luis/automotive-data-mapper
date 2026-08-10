.PHONY: install test kernel

# Create the virtual environment and install the project in editable mode, so
# that a notebook can import from src/ without any path juggling.
install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev,notebook]"

# The same command CI runs, so a green local run means a green CI run.
test:
	pytest

# Register this virtual environment as a Jupyter kernel, so a notebook opened
# from any JupyterLab can run with the project's Python and import from src/.
kernel:
	.venv/bin/python -m ipykernel install --user --name automotive-data-mapper --display-name "Python (automotive-data-mapper)"
