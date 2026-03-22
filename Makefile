run_php:
	uv run main.py build-data --ecosystem php

format:
	uv format

analyze:
	uv run ruff check

types:
	uv run ty check

install_dev:
	uv pip install -e . --group dev

build:
	rm -rf dist/
	uv build

release:
	rm -rf dist/
	uv build
	uv run twine check dist/*
	uv run twine upload dist/*
