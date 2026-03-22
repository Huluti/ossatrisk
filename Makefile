format:
	uv format

analyze:
	uv run ruff check

types:
	uv run ty check

install_dev:
	uv pip install -e . --group dev

build:
	rm -rf .venv dist
	uv build

release:
	rm -rf .venv dist
	uv build
	uv run twine check dist/*
	uv run twine upload dist/*
