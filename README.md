# My First AI Agent

**A secure, local-first AI agent template built with LangGraph, Ollama, and SQLite.**

This project demonstrates a structured **7-layer architectural framework** for building stateful, autonomous agents that run entirely on your local machine. It uses Llama 3.1 for reasoning and **Model Context Protocol (MCP)** for tool execution.

## Architecture (The 7 Steps)

This agent is built following a strict 7-step process defined for enterprise-grade AI development:

1.  **System Prompt:** Defines the agent's goal, role, and security constraints.
2.  **LLM (Local):** Uses **Llama 3.1** via Ollama for privacy and offline capability.
3.  **Tools (MCP):** Tools are decoupled into a standalone **MCP Server** (`mcp_server.py`) using `fastmcp`.
4.  **Memory:** Persistent conversation history using **SQLite**.
5.  **Orchestration:** **LangGraph** manages the cyclic workflow (Agent → Tool → Agent).
6.  **UI:** Dual interface support: **Command Line Interface (CLI)** and **Streamlit Web GUI**.
7.  **Evals:** Hooks for LangSmith (optional) for analyzing and improving performance.

## Prerequisites

Before running the agent, ensure you have the following installed:

1.  **Python 3.11+**
2.  **[uv](https://github.com/astral-sh/uv)** (Fast Python package installer) or standard `pip`.
3.  **[Ollama](https://ollama.com/)** running locally.

### Setup Local Model
You must have the `llama3.1` model pulled, as it supports tool calling natively.

```bash
ollama pull llama3.1
```

## Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/vchirrav/my-first-agent.git](https://github.com/vchirrav/my-first-agent.git)
    cd my-first-agent
    ```

2.  **Create Virtual Environment & Install Dependencies**
    Using `uv` (recommended):
    ```bash
    uv venv
    
    # Activate the virtual environment
    # Windows:
    .venv\Scripts\activate
    # Mac/Linux:
    source .venv/bin/activate
    
    # Install packages (Now includes 'fastmcp' and 'mcp')
    uv pip install langchain langchain-community langchain-ollama langgraph langsmith langgraph-checkpoint-sqlite streamlit fastmcp mcp pydantic
    ```

## Usage

Ensure Ollama is running in the background (`ollama serve`).

### Option 1: Run the Web GUI (MCP Enabled)
Launch the agent in a browser. The GUI automatically connects to the local MCP server to access tools.

```bash
streamlit run gui.py
```
* **Architecture:** The GUI acts as an **MCP Client**.
* **Features:** Visual chat history, real-time tool logs, sidebar controls, and independent memory (`gui_memory.sqlite`).
* **Tools Available:** File Checker, Directory Lister, Calculator.

### Option 2: Run the CLI (Classic)
Run the agent directly in your terminal (uses internal tool definitions).

```bash
python main.py
```

### Example Interactions
The agent supports natural language queries. Try these examples:
* *"What files are in this directory?"*
* *"Does the file mcp_server.py exist?"*
* *"Calculate log 10 base 10."*
* *"Calculate 25 * 40 + 10."*

## Security Guardrails

This project implements specific security measures at the code level:
* **Prompt Hardening:** System prompts use delimiters to separate instructions from user input.
* **Path Traversal Protection:** The file tool blocks access to parent directories (`..`) or absolute paths.
* **Input Sanitization:** The calculator tool prevents code injection by restricting characters.
* **Strict Schemas:** Tools use **Pydantic** schemas to prevent hallucinated arguments.
* **Local Execution:** No data leaves your machine (unless you explicitly enable LangSmith tracing).

## Project Structure

```text
my-first-agent/
├── main.py               # CLI Agent code (Classic Mode)
├── gui.py                # Streamlit Web Interface (MCP Client)
├── mcp_server.py         # Standalone MCP Server (Tools Host)
├── agent_memory.sqlite   # Memory DB for CLI session
├── gui_memory.sqlite     # Memory DB for GUI session (auto-created)
├── .venv/                # Virtual environment
└── README.md             # Project documentation
```

## Observability (Optional)

To trace the agent's decision-making process with **LangSmith**, set these environment variables before running:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-api-key"
```