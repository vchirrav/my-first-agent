# Local Multi-Agent Systems: Supervisor Architectures

**A secure, local-first exploration of Multi-Agent patterns using LangGraph, Agent-to-Agent (A2A), MCP, and Ollama.**

This repository demonstrates two distinct enterprise-grade architectures for building Supervisor-Worker systems locally:
1.  **LangGraph + MCP:** A centralized "Hub-and-Spoke" model where agents are logical nodes sharing a tool server.
2.  **A2A (Agent-to-Agent):** A distributed "Network" model where agents are independent micro-services communicating via HTTP/JSON-RPC.

---

## Prerequisites & Installation

Before running either system, ensure you have the following:
1.  **Python 3.11+**
2.  **[uv](https://github.com/astral-sh/uv)** (Fast Python package installer) or standard `pip`.
3.  **[Ollama](https://ollama.com/)** running locally with the `llama3.1` model.

### 1. Setup Local Model
```bash
ollama pull llama3.1
```

### 2. Clone & Install
```bash
git clone [https://github.com/vchirrav/my-first-agent.git](https://github.com/vchirrav/my-first-agent.git)
cd my-first-agent

# Create Virtual Environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install ALL dependencies (for both architectures)
uv pip install langchain langchain-community langchain-ollama langgraph langsmith langgraph-checkpoint-sqlite streamlit fastmcp mcp pydantic a2a uvicorn
```

---

## Architecture 1: LangGraph + MCP (Centralized)

This system operates on a **Hub-and-Spoke** model. A single Supervisor LLM routes tasks to Worker nodes that execute tools via a shared local Model Context Protocol (MCP) server.

### Components
* **Supervisor:** Maintains global state and orchestrates the workflow.
* **Workers:** Specialized agents (File & Math) with restricted permissions.
* **MCP Server:** A standalone server (`mcp_server.py`) hosting the actual Python functions.
* **Orchestration:** **LangGraph** manages state transitions.

### 🚀 How to Run

Ensure Ollama is running (`ollama serve`).

**1. Run the Multi-Agent GUI**
This launches the Supervisor system visualizing the hand-offs.
```bash
streamlit run multi_agent.py
```
*(Note: The app will automatically connect to the local MCP server).*

**2. (Optional) Single-Agent Mode**
For a simpler, tool-calling test:
```bash
streamlit run gui.py
```

### Security Guardrails
* **Role Separation:** The Math Agent cannot access file tools, and vice-versa.
* **Supervisor Validation:** The Supervisor can `FINISH` conversations deemed unsafe.
* **MCP Isolation:** Tools run in a separate process (`mcp_server.py`).

---

## Architecture 2: Agent-to-Agent Network (Distributed)

This system demonstrates a **Distributed Micro-Service** model using the **Agent2Agent (A2A) Protocol**. Instead of a shared graph, agents are independent servers listening on different ports.

### Components
| Role | Component | Port | Description |
| :--- | :--- | :--- | :--- |
| **Supervisor** | `gui_a2a.py` | `:8501` | The Client GUI. Translates natural language into strict agent commands. |
| **Worker A** | `file_agent.py` | `:8001` | **File Specialist**. Independent server for file ops. |
| **Worker B** | `math_agent.py` | `:8002` | **Math Specialist**. Independent server for calculations. |

### How to Run

You must run the components in **three separate terminal windows**.

**1. Start the File Agent (Terminal 1)**
```bash
python file_agent.py
# Output: 📂 Starting File Agent on :8001...
```

**2. Start the Math Agent (Terminal 2)**
```bash
python math_agent.py
# Output: 🧮 Starting Math Agent on :8002...
```

**3. Start the Supervisor GUI (Terminal 3)**
```bash
streamlit run gui_a2a.py
```

### A2A Features
* **Smart Translation:** Supervisor translates fuzzy requests (e.g., *"Do I have secrets?"*) into strict syntax (`check secrets.txt`).
* **Loop Breaker:** "Hard Loop Breaker" logic physically prevents the AI from repeating commands.
* **Strict Validators:** Anti-hallucination guards prevent sending invalid payloads (like text to the math agent).

---

## Unified Project Structure

```text
my-first-agent/
├── .venv/                      # Virtual environment
├── README.md                   # This file
│
├── # --- ARCHITECTURE 1 (LangGraph + MCP) ---
├── multi_agent.py              # Supervisor Logic (LangGraph)
├── gui.py                      # Single-Agent Interface (Legacy)
├── mcp_server.py               # Shared MCP Server (Tools Host)
├── mcp_client.py               # MCP Client utilities
├── multi_agent_memory.sqlite   # Memory DB for LangGraph sessions
│
└── # --- ARCHITECTURE 2 (A2A Network) ---
    ├── gui_a2a.py              # Supervisor Client (Streamlit + A2A SDK)
    ├── file_agent.py           # Independent File Agent Server (:8001)
    ├── math_agent.py           # Independent Math Agent Server (:8002)
```

## Observability

To trace the decision-making process (especially for the LangGraph implementation), set these environment variables for **LangSmith**:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-api-key"
```

## Troubleshooting

* **A2A Connection Errors?** Ensure `file_agent.py` and `math_agent.py` are running in separate terminals before starting the GUI.
* **Context Attributes Missing?** If using A2A, ensure you are using the updated agent code with "Safe Message Extraction" logic to handle the SDK version differences.
* **Ollama Errors?** Ensure `ollama run llama3.1` works in your terminal before running any scripts.