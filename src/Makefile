run_php:
	uv run main.py build-data --ecosystem php

format:
	uv format

analyze:
	uv run ruff check

types:
	uv run ty check

install_dev:
	python3 -m pip install --upgrade pip build wheel
	python3 -m build
	pip install dist/*.whl --force-reinstall
