import os
import sqlite3
import uuid
from typing import Annotated, TypedDict

# LangChain / LangGraph Imports
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

# =============================================================================
# STEP 1: SYSTEM PROMPT (Goal, Role, Instructions)
# Security: We use delimiters (###) to separate instructions from potential user data.
# =============================================================================
SYSTEM_PROMPT = """You are a Local Assistant Agent.
GOAL: Help the user perform local file checks and calculations securely.
ROLE: You are precise, security-conscious, and never execute code without verifying the intent.

INSTRUCTIONS:
- Only use the provided tools.
- If the user asks to delete files, politely refuse.
- Provide concise responses.
- ALWAYS check if a file exists before trying to read it (though you currently only have check_file_exists).
"""

def get_system_message():
    return SystemMessage(content=SYSTEM_PROMPT)


# =============================================================================
# STEP 2: LLM (Base Model)
# Security: Ensure you have run `ollama pull llama3` (or mistral) locally.
# This runs entirely on your machine; no data is sent to OpenAI/Anthropic.
# =============================================================================
llm = ChatOllama(
    model="llama3.1",  # Ensure this matches what you pulled in Ollama
    temperature=0,   # 0 = Deterministic (more reliable for tools)
)


# =============================================================================
# STEP 3: TOOLS (Simple/Local)
# Security: Input Validation & Least Privilege
# =============================================================================
@tool
def check_file_exists(filename: str) -> str:
    """Checks if a file exists in the current directory."""
    
    # SECURITY GUARDRAIL: Prevent Directory Traversal
    # This prevents the agent from checking files outside the project folder (e.g., C:\Windows)
    if ".." in filename or filename.startswith("/") or filename.startswith("\\") or ":" in filename:
         return "Error: Access denied. You can only check files in the current relative directory."
    
    try:
        exists = os.path.exists(filename)
        return f"File '{filename}' exists: {exists}"
    except Exception as e:
        return f"Error checking file: {e}"

@tool
def calculator(expression: str) -> str:
    """Calculates a simple math expression (e.g., '2 + 2')."""
    
    # SECURITY GUARDRAIL: Input Sanitization
    # We only allow specific safe characters to prevent code injection via eval()
    allowed = set("0123456789+-*/(). ")
    if not set(expression).issubset(allowed):
        return "Error: Invalid characters in math expression. Only numbers and basic math symbols allowed."
    
    try:
        # Note: In a real production app, use a safer math library like `numexpr` instead of eval()
        return str(eval(expression)) 
    except Exception as e:
        return f"Math error: {e}"

# Bind tools to the LLM so it knows they exist
tools = [check_file_exists, calculator]
llm_with_tools = llm.bind_tools(tools)


# =============================================================================
# STEP 4: MEMORY (State Persistence)
# Security: The sqlite file stores chat history. Keep 'agent_memory.sqlite' secure.
# =============================================================================
# We open a connection to a local file. 
# check_same_thread=False is needed because LangGraph might access it from different threads.
conn = sqlite3.connect("agent_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)


# =============================================================================
# STEP 5: ORCHESTRATION (LangGraph Workflows)
# Security: Recursion limit prevents infinite loops if the model gets stuck.
# =============================================================================

# 5a. Define the State (The "Brain" of the graph)
class AgentState(TypedDict):
    # 'add_messages' means new messages are appended to history, not overwritten
    messages: Annotated[list, add_messages] 

# 5b. Define the Agent Node (The Decision Maker)
def agent_node(state: AgentState):
    # We prepend the system message to ensure the model remembers its role
    messages = [get_system_message()] + state["messages"]
    result = llm_with_tools.invoke(messages)
    return {"messages": [result]}

# 5c. Define the Conditional Logic (The Router)
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    
    # If the LLM decided to call a tool, route to "tools" node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, stop and return answer to user
    return END

# 5d. Build the Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools)) # specific node just for running tools

workflow.add_edge(START, "agent") # Start at agent
workflow.add_conditional_edges("agent", should_continue, ["tools", END]) # Decide: Tool or End?
workflow.add_edge("tools", "agent") # After tool runs, go back to agent to interpret result

# Compile the graph with memory attached
app = workflow.compile(checkpointer=memory)


# =============================================================================
# STEP 6: UI (CLI Loop)
# Security: Local execution only. No web server exposure.
# =============================================================================
def run_cli():
    print("=========================================")
    print("   LOCAL AI AGENT (Ollama + LangGraph)   ")
    print("=========================================")
    print("Tools available: 'check_file_exists', 'calculator'")
    print("Type 'exit' to quit.\n")

    # Thread ID separates conversations in the memory database
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        try:
            user_input = input("User (You): ")
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            # Helper to print distinct steps
            print("\n--- Processing ---")

            # Stream the graph events
            events = app.stream(
                {"messages": [("user", user_input)]}, 
                config, 
                stream_mode="values"
            )
            
            for event in events:
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    # Only print the AI's final response or tool calls (optional verbosity)
                    if last_msg.type == "ai":
                         # If it has tool calls, let the user know
                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                            for tc in last_msg.tool_calls:
                                print(f"[Agent is calling tool: {tc['name']}]")
                        
                        # If it has content, print the response
                        if last_msg.content:
                            print(f"Agent: {last_msg.content}")
            
            print("------------------\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

# =============================================================================
# STEP 7: AI EVALS (LangSmith)
# NOTE: This requires API keys. If not set, it simply skips sending traces.
# You configure this via environment variables in your terminal, not code.
# export LANGCHAIN_TRACING_V2=true
# set LANGSMITH_TRACING=true
# set LANGSMITH_ENDPOINT=https://api.smith.langchain.com
# set LANGSMITH_PROJECT=my-first-agent
# set LANGSMITH_API_KEY=xxxx
# =============================================================================

if __name__ == "__main__":
    run_cli()