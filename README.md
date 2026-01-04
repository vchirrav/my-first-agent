# My First AI Agent

**A secure, local-first AI agent template built with LangGraph, Ollama, and SQLite.**

This project demonstrates a structured **7-layer architectural framework** for building stateful, autonomous agents that run entirely on your local machine. It uses Llama 3.1 for tool calling and reasoning, orchestrated by LangGraph.

## Architecture (The 7 Steps)

This agent is built following a strict 7-step process defined for enterprise-grade AI development:

1.  **System Prompt:** Defines the agent's goal, role, and security constraints.
2.  **LLM (Local):** Uses **Llama 3.1** via Ollama for privacy and offline capability.
3.  **Tools:** Custom Python tools with input validation (File System Check, Calculator).
4.  **Memory:** Persistent conversation history using **SQLite**.
5.  **Orchestration:** **LangGraph** manages the cyclic workflow (Agent → Tool → Agent).
6.  **UI:** Simple Command Line Interface (CLI) for interaction.
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
    
    # Install packages
    uv pip install langchain langchain-community langchain-ollama langgraph langsmith langgraph-checkpoint-sqlite
    ```

## Usage

1.  **Start Ollama**
    Ensure Ollama is running in the background (`ollama serve`).

2.  **Run the Agent**
    ```bash
    python main.py
    ```

3.  **Interact**
    The agent supports natural language queries. Try these examples:
    * *"Is there a file called main.py in this folder?"*
    * *"Calculate 25 * 40 + 10."*
    * *"Check if secret.txt exists."*

## Security Guardrails

This project implements specific security measures at the code level:
* **Prompt Hardening:** System prompts use delimiters to separate instructions from user input.
* **Path Traversal Protection:** The file tool blocks access to parent directories (`..`) or absolute paths.
* **Input Sanitization:** The calculator tool only accepts mathematical characters to prevent code injection.
* **Local Execution:** No data leaves your machine (unless you explicitly enable LangSmith tracing).

## Project Structure

```text
my-first-agent/
├── main.py                # Complete agent code (Steps 1-7)
├── agent_memory.sqlite    # Local database for conversation history (created on run)
├── .venv/                 # Virtual environment
└── README.md              # Project documentation
```

## Observability (Optional)

To trace the agent's decision-making process with **LangSmith**, set these environment variables before running:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-api-key"
```

---