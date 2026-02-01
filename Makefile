# ClimABC Index - Makefile
# Common development tasks using uv

.PHONY: help install sync test test-cov test-ci lint fmt check clean update-docs

# Default target
help:
	@echo "ClimABC Index - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    Install dependencies"
	@echo "  make sync       Sync dependencies with lock file"
	@echo ""
	@echo "Testing:"
	@echo "  make test       Run all tests"
	@echo "  make test-cov   Run tests with coverage"
	@echo "  make test-ci    Run tests (CI mode - fail fast)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint       Run linter (ruff)"
	@echo "  make fmt        Format code (ruff)"
	@echo "  make check      Run lint + fmt + test"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean      Clean cache and temp files"
	@echo "  make update-docs  Update documentation"

# Setup
install:
	uv sync

sync:
	uv sync --locked

# Testing
test:
	uv run pytest -v

test-cov:
	uv run pytest -v --cov=climabc --cov-report=term-missing --cov-report=html

test-ci:
	uv run pytest -x --tb=short

# Code Quality
lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

fmt:
	uv run ruff check --select I --fix src tests
	uv run ruff format src tests

check: lint test
	@echo "✓ All checks passed"

# Maintenance
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned cache and temp files"

# Fetch data (for testing)
fetch-psl:
	uv run python -c "import asyncio; from test_psl import *; asyncio.run(test_psl_fetcher())"

# Development helpers
run:
	uv run climabc $(ARGS)

# CI/CD simulation
ci: sync lint test-ci
	@echo "✓ CI checks passed"
