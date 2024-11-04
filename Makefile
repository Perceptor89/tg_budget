PHONY: run style

VENV_BIN_PATH = ./.venv/bin
PYTHONPATH = $(shell pwd)

run:
	$(VENV_BIN_PATH)/python3 -m Scripts.run

style:
	poetry run flake8 app/
