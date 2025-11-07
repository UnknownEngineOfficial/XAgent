# Makefile for X-Agent

.PHONY: help install install-dev test lint format clean docker-build docker-up docker-down run-api run-ws run-cli

help:
	@echo "X-Agent Development Commands"
	@echo "============================"
	@echo "make install      - Install production dependencies"
	@echo "make install-dev  - Install development dependencies"
	@echo "make test         - Run tests"
	@echo "make lint         - Run linters"
	@echo "make format       - Format code"
	@echo "make clean        - Clean build artifacts"
	@echo "make docker-build - Build Docker images"
	@echo "make docker-up    - Start Docker services"
	@echo "make docker-down  - Stop Docker services"
	@echo "make run-api      - Run REST API"
	@echo "make run-ws       - Run WebSocket Gateway"
	@echo "make run-cli      - Run CLI interface"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	PYTHONPATH=src pytest tests/ -v

test-cov:
	PYTHONPATH=src pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src/
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	ruff check --fix src/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

run-api:
	PYTHONPATH=src uvicorn xagent.api.rest:app --host 0.0.0.0 --port 8000 --reload

run-ws:
	PYTHONPATH=src uvicorn xagent.api.websocket:app --host 0.0.0.0 --port 8001 --reload

run-cli:
	PYTHONPATH=src python -m xagent.cli.main

run-agent:
	PYTHONPATH=src python -m xagent.core.agent
