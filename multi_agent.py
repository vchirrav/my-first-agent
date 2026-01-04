import streamlit as st
import uuid
import asyncio
import sys
import sqlite3
import json
import operator
from typing import Annotated, TypedDict, List, Union, Literal

# Pydantic
from pydantic import BaseModel, Field

# MCP Client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangChain / LangGraph Imports
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

# =============================================================================
# 🎨 UI CONFIGURATION
# =============================================================================
st.set_page_config(page_title="Multi-Agent System", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    :root { --bg-color: #f4f6f9; --sidebar-bg: #ffffff; --text-color: #1f2937; }
    .stApp { background-color: var(--bg-color); color: var(--text-color); }
    [data-testid="stSidebar"] { background-color: var(--sidebar-bg); }
    .status-tag { background-color: #eef2ff; color: #3b82f6; padding: 4px 8px; border-radius: 4px; font-size: 0.9rem; border: 1px solid #dbeafe; display: inline-block; margin: 2px; }
    .worker-tag { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; } /* Green for workers */
    .manager-tag { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; } /* Red for manager */
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🔌 MCP CLIENT ADAPTER (Same as before)
# =============================================================================
async def call_mcp_tool(tool_name, arguments):
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except: pass
    
    server_params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content: return result.content[0].text
                return "Tool executed."
    except Exception as e: return f"Error: {e}"

def create_mcp_tool(name, description, args_schema):
    def wrapped_tool(**kwargs):
        return asyncio.run(call_mcp_tool(name, kwargs))
    return StructuredTool.from_function(func=wrapped_tool, name=name, description=description, args_schema=args_schema)

# =============================================================================
# 🛠️ TOOL DEFINITIONS & SPLIT
# =============================================================================

class ListDirInput(BaseModel): pass
class FileCheckInput(BaseModel):
    filename: str = Field(..., description="Filename to check")
class CalculatorInput(BaseModel):
    expression: str = Field(..., description="Math expression")

# Worker 1 Tools: File System
file_tools = [
    create_mcp_tool("list_directory", "Lists files in folder", ListDirInput),
    create_mcp_tool("check_file_exists", "Checks file existence", FileCheckInput)
]

# Worker 2 Tools: Math
math_tools = [
    create_mcp_tool("calculator", "Calculates math expressions", CalculatorInput)
]

# =============================================================================
# 🧠 MULTI-AGENT ARCHITECTURE (The Supervisor Pattern)
# =============================================================================

# 1. State Definition
# We add 'next' to track which agent is acting
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next: str

# 2. Worker Node Factory
# This creates a standard agent node that calls tools and reports back
def create_agent_node(agent_name, tools, system_prompt):
    llm = ChatOllama(model="llama3.1", temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: AgentState):
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        result = llm_with_tools.invoke(messages)
        # We return the result, but we DO NOT set 'next' here. 
        # The graph wiring will automatically send us back to Supervisor.
        return {"messages": [result]}
    
    return agent_node

# 3. Create the Workers
file_agent_node = create_agent_node(
    "File_Agent", 
    file_tools, 
    "You are a File System Specialist. You can list directories and check files. Do not do math."
)

math_agent_node = create_agent_node(
    "Math_Agent", 
    math_tools, 
    "You are a Math Specialist. Use the calculator for everything. Do not check files."
)

# 4. The Supervisor (Manager)
# This node decides who goes next.
class Router(BaseModel):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal["File_Agent", "Math_Agent", "FINISH"]

def supervisor_node(state: AgentState):
    system_prompt = (
        "You are a Supervisor tasked with managing a conversation between the"
        " following workers: File_Agent, Math_Agent.\n\n"
        "1. File_Agent: Good for file checks, listing directories.\n"
        "2. Math_Agent: Good for calculations.\n\n"
        "Given the conversation history, decide who should act next.\n"
        "If the user's question is answered or if you need input from the user, choose 'FINISH'."
    )
    
    llm = ChatOllama(model="llama3.1", format="json", temperature=0)
    
    # We force the LLM to output structured JSON matching our Router schema
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # Simple prompting for JSON routing with Llama 3.1
    prompt = (
        "Who should act next? Respond in JSON with a single key 'next'. "
        "Options: 'File_Agent', 'Math_Agent', 'FINISH'."
    )
    messages.append(HumanMessage(content=prompt))
    
    response = llm.invoke(messages)
    try:
        decision = json.loads(response.content)
        next_step = decision.get("next", "FINISH")
    except:
        next_step = "FINISH"
        
    return {"next": next_step}

# 5. Build the Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("File_Agent", file_agent_node)
workflow.add_node("Math_Agent", math_agent_node)
workflow.add_node("File_Tools", ToolNode(file_tools))
workflow.add_node("Math_Tools", ToolNode(math_tools))

# Entry Point
workflow.add_edge(START, "Supervisor")

# Supervisor Conditional Logic
workflow.add_conditional_edges(
    "Supervisor",
    lambda x: x["next"],
    {
        "File_Agent": "File_Agent",
        "Math_Agent": "Math_Agent",
        "FINISH": END
    }
)

# Worker -> Tool Logic
def should_continue(state: AgentState):
    last_msg = state["messages"][-1]
    if last_msg.tool_calls:
        return "continue"
    return "back_to_manager"

workflow.add_conditional_edges("File_Agent", should_continue, {"continue": "File_Tools", "back_to_manager": "Supervisor"})
workflow.add_conditional_edges("Math_Agent", should_continue, {"continue": "Math_Tools", "back_to_manager": "Supervisor"})

# Tool -> Back to Worker (Standard ReAct pattern)
workflow.add_edge("File_Tools", "File_Agent")
workflow.add_edge("Math_Tools", "Math_Agent")

# Compile
conn = sqlite3.connect("multi_agent_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)

# =============================================================================
# 🖥️ MULTI-AGENT GUI
# =============================================================================

with st.sidebar:
    st.markdown("### 🏢 Agent Org Chart")
    st.markdown("---")
    st.markdown('<div class="status-tag manager-tag">👨‍💼 Supervisor</div>', unsafe_allow_html=True)
    st.markdown("⬇️ Manages")
    st.markdown('<div class="status-tag worker-tag">📂 File_Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-tag worker-tag">🧮 Math_Agent</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("Clear History", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

st.title("🤖 Multi-Agent System (A2A)")
st.markdown("A **Supervisor** delegates tasks to **Specialist Agents**.")

for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    with st.chat_message(role):
        st.markdown(content)

if prompt := st.chat_input("Example: Check files in this folder and then calculate 50 * 10"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        # CHANGED: Initialize as a list to capture multiple answers
        final_responses = []
        
        # Increased recursion limit because multi-agent hops take more steps
        config = {"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 25}
        
        with st.status("🏢 Management in progress...", expanded=True) as status:
            events = app.stream({"messages": [("user", prompt)]}, config)
            
            for event in events:
                # 1. Detect who is acting based on the key in the event
                agent_name = list(event.keys())[0]
                state_update = event[agent_name]
                
                # 2. Update Status Box
                if agent_name == "Supervisor":
                    next_worker = state_update.get("next", "FINISH")
                    if next_worker != "FINISH":
                        st.write(f"👨‍💼 **Supervisor**: Handing off to `{next_worker}`")
                    else:
                        st.write(f"👨‍💼 **Supervisor**: Task complete.")
                        
                elif agent_name in ["File_Agent", "Math_Agent"]:
                    # Check for tool calls
                    if "messages" in state_update:
                        msg = state_update["messages"][-1]
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                st.write(f"⚙️ **{agent_name}**: Calling `{tc['name']}`")
                                st.code(f"Args: {tc['args']}")
                        elif msg.content:
                            # If the worker speaks regular text, it's an answer
                            st.write(f"💬 **{agent_name}**: Reporting back.")
                            
                            # --- FIX IS HERE ---
                            # Append the message to our list instead of overwriting it
                            final_responses.append(f"**{agent_name}:** {msg.content}")

                elif agent_name.endswith("_Tools"):
                    st.write(f"🛠️ **Tool Output**: Received successfully.")

            status.update(label="Complete", state="complete", expanded=False)
        
        # Display Final Response (Combine all answers)
        if final_responses:
            full_response = "\n\n".join(final_responses)
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})