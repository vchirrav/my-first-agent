# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local-first multi-agent system demonstrating two enterprise-grade Supervisor-Worker architectures using LangChain, LangGraph, Ollama (llama3.1), and Streamlit. All inference runs locally via Ollama.

## Two Architectures

### Architecture 1: LangGraph + MCP (Centralized)
All agents are nodes within a single LangGraph workflow. A supervisor node routes tasks to specialist worker nodes (File Agent, Math Agent). Tools are served via a shared FastMCP server (`mcp_server.py`). Communication is in-process.

- `multi_agent.py` — Full supervisor + workers system with Streamlit UI (primary entry point)
- `gui.py` — Single-agent mode with MCP tools (legacy)
- `mcp_server.py` — FastMCP tool server hosting list_directory, check_file_exists, calculator
- `main.py` — Basic CLI agent (foundation demo, no MCP)

### Architecture 2: A2A Network (Distributed)
Independent agents run as separate HTTP/JSON-RPC servers using the A2A SDK protocol. A supervisor client routes requests to worker servers over HTTP.

- `gui_a2a.py` (port 8501) — Supervisor Streamlit client with LLM-driven routing
- `file_agent.py` (port 8001) — File operations worker server
- `math_agent.py` (port 8002) — Math computation worker server

## Running the Project

**Prerequisites:** Python 3.12+, Ollama running (`ollama serve`) with llama3.1 pulled (`ollama pull llama3.1`).

```bash
# Install dependencies
uv venv
.venv\Scripts\activate  # Windows
uv pip install langchain langchain-community langchain-ollama langgraph langsmith langgraph-checkpoint-sqlite streamlit fastmcp mcp pydantic a2a uvicorn
```

**Architecture 1 (single process):**
```bash
streamlit run multi_agent.py
```

**Architecture 2 (three terminals):**
```bash
python file_agent.py    # Terminal 1
python math_agent.py    # Terminal 2
streamlit run gui_a2a.py  # Terminal 3
```

**CLI mode (basic agent, no UI):**
```bash
python main.py
```

There is no test suite or linter configured for this project.

## Key Design Patterns

- **Supervisor routing:** A central LLM-based supervisor decides which specialist agent handles each request, or returns FINISH
- **ReAct loop:** Agents reason, call tools, process results, and repeat via LangGraph's conditional edges and `should_continue()` functions
- **MCP protocol:** Tools are isolated in a separate FastMCP server process; agents connect as MCP clients
- **A2A protocol:** Loose coupling via HTTP/JSON-RPC between independent agent processes
- **SQLite checkpointing:** Conversation state persists across tool calls via `langgraph-checkpoint-sqlite` (files: `agent_memory.sqlite`, `multi_agent_memory.sqlite`)

## Security Guardrails

These are baked into the tool implementations and should be preserved when modifying tools:

- Directory traversal prevention: rejects paths containing `..`, `/`, `\`, `:`
- Calculator input sanitization: whitelist of `0-9+-*/()., ` and math function names only
- Role separation: File Agent cannot access math tools and vice versa
- A2A anti-hallucination: loop breaker tracking executed actions, payload validation preventing invalid agent calls

## Optional: LangSmith Observability

Set environment variables for tracing:
```bash
set LANGCHAIN_TRACING_V2=true
set LANGCHAIN_API_KEY=your-api-key
```
