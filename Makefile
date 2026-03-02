.PHONY: dev api mcp fe ingest kill

API_PORT ?= 9000
MCP_PORT ?= 9001

dev:
	@echo "Starting MCP (port $(MCP_PORT)), API (port $(API_PORT)), Frontend (3000)..."
	@bash scripts/dev.sh

ingest:
	@. .venv/bin/activate && python -m rag.ingest

kill:
	@bash scripts/kill.sh