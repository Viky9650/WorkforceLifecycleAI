# ======================================================
# WorkforceLifecycleAI Makefile
#
# Common development commands for running and managing
# the WorkforceLifecycleAI project.
#
# Usage:
#   make help     -> show available commands
#   make dev      -> start full development stack
#   make ingest   -> rebuild the RAG index
#   make clean    -> remove Python cache files
#   make reset    -> full project reset
#   make kill     -> stop running services
# ======================================================

.PHONY: help dev ingest kill clean reset

API_PORT ?= 9000
MCP_PORT ?= 9001


# -----------------------
# Show available commands
# -----------------------
help:
	@echo ""
	@echo "WorkforceLifecycleAI Development Commands"
	@echo "-----------------------------------------"
	@echo "make dev      Start MCP server, API, and frontend"
	@echo "make ingest   Build or rebuild the RAG vector index"
	@echo "make clean    Remove Python cache and temporary files"
	@echo "make reset    Stop services, clean caches, rebuild RAG index"
	@echo "make kill     Stop running development services"
	@echo ""


# -----------------------
# Start development stack
# -----------------------
dev:
	@echo "Starting MCP (port $(MCP_PORT)), API (port $(API_PORT)), Frontend (3000)..."
	@bash scripts/dev.sh


# -----------------------
# Rebuild RAG index
# -----------------------
ingest:
	@echo "Building RAG index..."
	@. .venv/bin/activate && python -m rag.ingest


# -----------------------
# Kill running processes
# -----------------------
kill:
	@echo "Stopping running services..."
	@bash scripts/kill.sh


# -----------------------
# Clean cache files
# -----------------------
clean:
	@echo "Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache .mypy_cache .ruff_cache
	@find . -name ".DS_Store" -delete
	@echo "Cache cleanup complete."


# -----------------------
# Reset project
# -----------------------
reset: kill clean
	@echo "Removing RAG index..."
	@rm -rf rag_index
	@echo "Rebuilding RAG index..."
	@. .venv/bin/activate && python -m rag.ingest
	@echo "Project reset complete."