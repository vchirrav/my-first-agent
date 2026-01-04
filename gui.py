import streamlit as st
import uuid
import asyncio
import sys
import sqlite3
import json
from typing import Annotated, TypedDict

# Pydantic for strict data validation (Fixes hallucinations)
from pydantic import BaseModel, Field

# MCP Client Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangChain Imports
from langchain_core.messages import SystemMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

# =============================================================================
# 🎨 UI CONFIGURATION
# =============================================================================
st.set_page_config(page_title="Agent-1 (MCP)", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    :root { --bg-color: #f4f6f9; --sidebar-bg: #ffffff; --text-color: #1f2937; --accent-color: #3b82f6; --border-color: #e5e7eb; }
    .stApp { background-color: var(--bg-color); color: var(--text-color); }
    [data-testid="stSidebar"] { background-color: var(--sidebar-bg); border-right: 1px solid var(--border-color); }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p { color: var(--text-color) !important; }
    h1, h2, h3 { color: var(--text-color) !important; font-family: 'Segoe UI', sans-serif; }
    p, li { color: #4b5563 !important; }
    .stTextInput > div > div > input { background-color: #ffffff; color: var(--text-color); border: 1px solid var(--border-color); border-radius: 20px; }
    .stChatMessage { background-color: transparent; }
    .status-tag { background-color: #eef2ff; color: #3b82f6; padding: 4px 8px; border-radius: 4px; font-size: 0.9rem; border: 1px solid #dbeafe; display: inline-block; margin-bottom: 10px; font-family: sans-serif; }
    .status-indicator { height: 10px; width: 10px; background-color: #10b981; border-radius: 50%; display: inline-block; margin-right: 8px; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🔌 MCP CLIENT ADAPTER
# =============================================================================

async def call_mcp_tool(tool_name, arguments):
    """Connects to mcp_server.py, runs the tool, and returns the result."""
    
    # Safety: Ensure arguments are a dict. Some models output stringified JSON.
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            pass # Pass raw string if it's not JSON (server might handle it)

    server_params = StdioServerParameters(
        command=sys.executable, 
        args=["mcp_server.py"], 
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.content:
                    return result.content[0].text
                return "Tool executed but returned no content."
    except Exception as e:
        return f"MCP Connection Error: {str(e)}"

# =============================================================================
# 🛠️ ROBUST TOOL DEFINITIONS (Pydantic Schemas)
# =============================================================================

# 1. Define Explicit Schemas 
# This tells the LLM EXACTLY what arguments are required.

class ListDirInput(BaseModel):
    pass # No arguments needed for listing directory

class FileCheckInput(BaseModel):
    filename: str = Field(
        ..., 
        description="The full name or path of the file to check. Example: 'data.txt'"
    )

class CalculatorInput(BaseModel):
    expression: str = Field(
        ..., 
        description="The mathematical expression to evaluate. Example: '2 + 2' or 'log(10, 10)'"
    )

# 2. Wrapper Function
def create_langchain_tool_from_mcp(name, description, args_schema):
    """Wraps MCP tool with strict Pydantic validation."""
    
    def wrapped_tool(**kwargs):
        # The args_schema ensures kwargs are valid before we get here
        return asyncio.run(call_mcp_tool(name, kwargs))
    
    return StructuredTool.from_function(
        func=wrapped_tool,
        name=name,
        description=description,
        args_schema=args_schema # <--- Enforces structure
    )

# 3. Create Tool List
tools = [
    create_langchain_tool_from_mcp(
        name="list_directory", 
        description="Lists all files and folders in the current directory.", 
        args_schema=ListDirInput
    ),
    create_langchain_tool_from_mcp(
        name="check_file_exists", 
        description="Checks if a specific file exists on the local system.", 
        args_schema=FileCheckInput
    ),
    create_langchain_tool_from_mcp(
        name="calculator", 
        description="Calculates math expressions.", 
        args_schema=CalculatorInput
    )
]

# =============================================================================
# 🧠 AGENT LOGIC
# =============================================================================

# Strict Prompt to prevent chatting and looping
SYSTEM_PROMPT = """You are a precise Local Assistant.
GOAL: Use tools to answer questions.
RULES:
1. If you have the answer from a tool, STOP and output the answer immediately.
2. Do not "chat" about the tool calls. Just call them.
3. If a file exists, say "Yes, it exists". If not, say "No".
"""

def get_system_message():
    return SystemMessage(content=SYSTEM_PROMPT)

llm = ChatOllama(model="llama3.1", temperature=0)
llm_with_tools = llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def agent_node(state: AgentState):
    messages = [get_system_message()] + state["messages"]
    result = llm_with_tools.invoke(messages)
    return {"messages": [result]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        # Loop Protection: If history is getting too long, force stop
        if len(state["messages"]) > 12:
            return END
        return "tools"
    return END

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

conn = sqlite3.connect("gui_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)

# =============================================================================
# 🖥️ GUI INTERACTION LOOP
# =============================================================================

with st.sidebar:
    st.markdown("### 🛡️ Agent Control")
    st.markdown("---")
    st.markdown('<div><span class="status-indicator"></span><span style="color:#1f2937">Online</span></div>', unsafe_allow_html=True)
    st.caption("") 
    st.markdown("**Model**")
    st.markdown('<div class="status-tag">llama3.1</div>', unsafe_allow_html=True)
    st.markdown("**Architecture**")
    st.markdown('<div class="status-tag">MCP Client</div>', unsafe_allow_html=True)
    st.markdown("---")
    if st.button("Clear History", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

st.title("🤖 Local AI Agent")
st.markdown("Powered by **Llama 3.1** and **FastMCP**.")
st.markdown("---")

# Render History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input Handling
if prompt := st.chat_input("Ask me to check a file or calculate something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("Thinking..."):
            # Set recursion limit to hard stop infinite loops
            config = {
                "configurable": {"thread_id": st.session_state.thread_id},
                "recursion_limit": 10 
            }
            final_response = ""
            
            try:
                events = app.stream({"messages": [("user", prompt)]}, config, stream_mode="values")
                
                for event in events:
                    if "messages" in event:
                        last_msg = event["messages"][-1]
                        
                        # Show Tool Status (but don't print "It seems I need to..." text)
                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                            for tc in last_msg.tool_calls:
                                with st.status(f"🛠️ MCP Tool: {tc['name']}", expanded=False):
                                    st.write(f"Args: {tc['args']}")
                        
                        # Capture Final Answer
                        elif last_msg.type == "ai" and last_msg.content:
                            final_response = last_msg.content

                # Display Result
                if final_response:
                    message_placeholder.markdown(final_response)
                    st.session_state.messages.append({"role": "assistant", "content": final_response})
                else:
                    st.warning("Agent completed the task but returned no text summary.")
                    
            except Exception as e:
                # Catch recursion errors or connection errors gracefully
                if "recursion" in str(e).lower():
                    st.error("🛑 Stopped: The agent got stuck in a loop.")
                else:
                    st.error(f"Error: {e}")