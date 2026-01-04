# Local Multi-Agent System (Supervisor Architecture)

**A secure, local-first Multi-Agent system built with LangGraph, Ollama, and Model Context Protocol (MCP).**

This project demonstrates an enterprise-grade **Supervisor-Worker Architecture**. Instead of a single generalist agent, a "Supervisor" LLM intelligently routes tasks to specialized "Worker" agents (File Specialist & Math Specialist), which execute tools via a local MCP server.

## Architecture

The system operates on a **Hub-and-Spoke** model:

1.  **Supervisor (Manager):** Analyzes the user's complex request and decides which specialist needs to act next. It maintains the global state.
2.  **Workers (Specialists):**
    * **File Agent:** Specialized prompt context. Access to `list_directory` and `check_file_exists`.
    * **Math Agent:** Specialized prompt context. Access to `calculator`.
3.  **MCP Server (Tools):** A standalone server (`mcp_server.py`) that hosts the actual Python functions, decoupled from the agents.
4.  **Orchestration:** **LangGraph** manages the state transitions (Supervisor → Worker → Tool → Supervisor).

## Prerequisites

Before running the system, ensure you have the following installed:

1.  **Python 3.11+**
2.  **[uv](https://github.com/astral-sh/uv)** (Fast Python package installer) or standard `pip`.
3.  **[Ollama](https://ollama.com/)** running locally.

### Setup Local Model
You must have the `llama3.1` model pulled.

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
    
    # Install required packages
    uv pip install langchain langchain-community langchain-ollama langgraph langsmith langgraph-checkpoint-sqlite streamlit fastmcp mcp pydantic
    ```

## Usage

Ensure Ollama is running in the background (`ollama serve`).

### 1. Run the Multi-Agent GUI
This launches the Supervisor system. The GUI will visualize the hand-offs between the Manager and the Workers.

```bash
streamlit run multi_agent.py
```
* **Note:** The application will automatically connect to the local MCP server for tools.

### 2. (Optional) Run Single-Agent Mode
If you want to test the simpler, single-agent version:

```bash
streamlit run gui.py
```

### Example Multi-Agent Interactions
Try compound queries that require both specialists to collaborate:
* *"List the files in this directory, and then calculate 500 * 5 based on what you find."*
* *"Check if 'data.csv' exists, and if not, calculate how much disk space I need for 1GB."*

## Security Guardrails

* **Role Separation:** The Math Agent cannot access file tools, and the File Agent cannot access math tools.
* **Supervisor Validation:** The Supervisor can decide to `FINISH` the conversation if a request is unsafe or off-topic.
* **MCP Isolation:** Tools run in a separate process (`mcp_server.py`), ensuring a clean boundary between the LLM reasoning and code execution.

## Project Structure

```text
my-first-agent/
├── multi_agent.py        # SUPERVISOR SYSTEM (Multi-Agent Logic)
├── gui.py                # Single-Agent Interface (Legacy)
├── mcp_server.py         # Shared MCP Server (Tools Host)
├── mcp_client.py         # MCP Client utilities
├── multi_agent_memory.sqlite # Memory DB for Multi-Agent sessions
├── .venv/                # Virtual environment
└── README.md             # Project documentation
```

## Observability (Optional)

To trace the Supervisor's decision-making process with **LangSmith**, set these environment variables:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-api-key"
```