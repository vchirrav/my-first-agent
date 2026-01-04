import streamlit as st
import uuid
import os
import sqlite3
from typing import Annotated, TypedDict

# Reuse your existing imports
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

# =============================================================================
# 🎨 UI CONFIGURATION (Clean Light Theme)
# =============================================================================
st.set_page_config(page_title="Agent-1", page_icon="🛡️", layout="wide")

# Custom CSS for High Contrast Light Theme
st.markdown("""
<style>
    /* --- Global Colors --- */
    :root {
        --bg-color: #f4f6f9;       /* Light Gray Background */
        --sidebar-bg: #ffffff;     /* White Sidebar */
        --text-color: #1f2937;     /* Dark Gray Text */
        --accent-color: #3b82f6;   /* Blue Accent */
        --border-color: #e5e7eb;   /* Light Border */
    }
    
    /* Force Background Color */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: var(--sidebar-bg);
        border-right: 1px solid var(--border-color);
    }
    
    /* Sidebar Text Fixes */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        color: var(--text-color) !important;
    }

    /* Headers & Text */
    h1, h2, h3 {
        color: var(--text-color) !important;
        font-family: 'Segoe UI', sans-serif;
    }
    p, li {
        color: #4b5563 !important;
    }

    /* Chat Input Styling */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        color: var(--text-color);
        border: 1px solid var(--border-color);
        border-radius: 20px;
    }

    /* Chat Messages - Make background transparent to blend */
    .stChatMessage {
        background-color: transparent;
    }
    
    /* Status Tags in Sidebar (CSS Classes) */
    .status-tag {
        background-color: #eef2ff;
        color: #3b82f6;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.9rem;
        border: 1px solid #dbeafe;
        display: inline-block;
        margin-bottom: 10px;
        font-family: sans-serif;
    }
    
    .status-indicator {
        height: 10px;
        width: 10px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    
    /* Adjust Streamlit spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 🧠 AGENT LOGIC (Unchanged)
# =============================================================================

# 1. System Prompt
SYSTEM_PROMPT = """You are a Local Assistant Agent.
GOAL: Help the user perform local file checks and calculations securely.
ROLE: You are precise, security-conscious, and never execute code without verifying the intent.
INSTRUCTIONS:
- Only use the provided tools.
- If the user asks to delete files, politely refuse.
- Provide concise responses.
"""

def get_system_message():
    return SystemMessage(content=SYSTEM_PROMPT)

# 2. LLM
llm = ChatOllama(model="llama3.1", temperature=0)

# 3. Tools
@tool
def check_file_exists(filename: str) -> str:
    """Checks if a file exists in the current directory."""
    if ".." in filename or filename.startswith(("/", "\\")) or ":" in filename:
         return "Error: Access denied. Directory traversal detected."
    try:
        exists = os.path.exists(filename)
        return f"File '{filename}' exists: {exists}"
    except Exception as e:
        return f"Error: {e}"

@tool
def calculator(expression: str) -> str:
    """Calculates a simple math expression."""
    allowed = set("0123456789+-*/(). ")
    if not set(expression).issubset(allowed):
        return "Error: Invalid characters."
    try:
        return str(eval(expression)) 
    except Exception as e:
        return f"Error: {e}"

tools = [check_file_exists, calculator]
llm_with_tools = llm.bind_tools(tools)

# 4. Graph Setup
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def agent_node(state: AgentState):
    messages = [get_system_message()] + state["messages"]
    result = llm_with_tools.invoke(messages)
    return {"messages": [result]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

# Initialize Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

# Memory Setup
conn = sqlite3.connect("gui_memory.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)

# =============================================================================
# 🖥️ GUI INTERACTION LOOP (Updated UI Elements)
# =============================================================================

# Sidebar
with st.sidebar:
    st.markdown("### 🛡️ Agent Control")
    st.markdown("---")
    
    st.markdown("**Status**")
    st.markdown('<div><span class="status-indicator"></span><span style="color:#1f2937">Online</span></div>', unsafe_allow_html=True)
    st.caption("") # Spacer
    
    st.markdown("**Model**")
    st.markdown('<div class="status-tag">llama3.1</div>', unsafe_allow_html=True)
    
    st.markdown("**Memory**")
    st.markdown('<div class="status-tag">SQLite</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("Clear History", use_container_width=True):
        # Reset thread ID to start fresh
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# Initialize Session State
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []

# Header
st.title("🤖 Local AI Agent")
st.markdown("Your secure, offline assistant for local tasks.")
st.markdown("---")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask me to check a file or calculate something..."):
    # 1. Add User Message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Run Agent
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Helper to show a spinner while thinking
        with st.spinner("Agent is thinking..."):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            
            # Stream the events
            final_response = ""
            events = app.stream(
                {"messages": [("user", prompt)]}, 
                config, 
                stream_mode="values"
            )
            
            for event in events:
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    
                    # Show Tool Usage (Intermediate Steps)
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            with st.status(f"🛠️ Executing: {tc['name']}", expanded=False):
                                st.write(f"Args: {tc['args']}")
                    
                    # Capture Final AI Response
                    if last_msg.type == "ai" and last_msg.content:
                        final_response = last_msg.content

            # Display Final Response
            message_placeholder.markdown(final_response)
            
    # 3. Save AI Message to History
    st.session_state.messages.append({"role": "assistant", "content": final_response})