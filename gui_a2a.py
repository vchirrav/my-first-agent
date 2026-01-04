import streamlit as st
import asyncio
import json
import uuid

# Official A2A Client Imports
from a2a.client import ClientFactory
from a2a.types import Message, TextPart 

# LangChain Imports
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama

# =============================================================================
# 🎨 UI CONFIGURATION
# =============================================================================
st.set_page_config(page_title="A2A Network", page_icon="📡", layout="wide")

st.markdown("""
<style>
    :root { --bg-color: #f4f6f9; --text-color: #1f2937; }
    .stApp { background-color: var(--bg-color); color: var(--text-color); }
    .status-tag { padding: 4px 8px; border-radius: 4px; border: 1px solid #ddd; display: inline-block; margin-right: 5px; font-size: 0.9rem; }
    .agent-server { background-color: #d1fae5; color: #065f46; border-color: #a7f3d0; } 
    .agent-client { background-color: #eff6ff; color: #1e40af; border-color: #bfdbfe; } 
    .stChatMessage { background-color: transparent; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 📡 A2A NETWORK LAYER
# =============================================================================

async def query_remote_agent(port: int, query: str) -> str:
    endpoint = f"http://localhost:{port}"
    try:
        # 1. Connect
        client = await ClientFactory.connect(endpoint)
        
        # 2. Construct Message
        msg = Message(
            messageId=str(uuid.uuid4()),        
            role="user", 
            parts=[TextPart(text=str(query))]
        )
        
        # 3. Send & Stream Response
        final_text = ""
        async for response in client.send_message(msg):
            # Robust extraction for all A2A SDK versions
            if hasattr(response, 'parts') and response.parts:
                part = response.parts[0]
                if hasattr(part, 'text') and part.text:
                    final_text = part.text
                elif hasattr(part, 'model_dump'):
                    data = part.model_dump()
                    final_text = data.get('text', '')
                elif hasattr(part, 'dict'):
                    data = part.dict()
                    final_text = data.get('text', '')
                else:
                    final_text = str(part)

        return final_text if final_text else "✅ Task completed (No text returned)."

    except Exception as e:
        return f"ERROR: {str(e)}"

# =============================================================================
# 🧠 SUPERVISOR LOGIC
# =============================================================================

def get_next_step(history):
    llm = ChatOllama(model="llama3.1", format="json", temperature=0)
    
    # --- PROMPT: Explicit Anti-Hallucination Rules ---
    system_prompt = (
        "You are the Supervisor of an Agent Network.\n"
        "AGENTS:\n"
        "1. FileAgent: 'list', 'check <filename>'\n"
        "2. MathAgent: Math expressions (e.g. '5 * 5')\n\n"
        "RULES:\n"
        "1. If the LAST message (from Assistant) answers the User, return 'next': 'FINISH'.\n"
        "2. If listing files, DO NOT call MathAgent, even if file names look like math.\n"
        "3. DO NOT output commands like 'history', 'status', or empty strings.\n"
        "4. Output JSON: {'next': 'AgentName', 'query': 'StrictCommand'}"
    )
    
    messages = [SystemMessage(content=system_prompt)] + history
    messages.append(HumanMessage(content="Analyze history. Is the task done? Return JSON."))
    
    try:
        res = llm.invoke(messages)
        return json.loads(res.content)
    except Exception as e:
        return {"next": "FINISH", "error": str(e)}

# =============================================================================
# 🖥️ GUI LOOP
# =============================================================================

with st.sidebar:
    st.markdown("### 📡 Network Topology")
    st.markdown("**Supervisor Node**")
    st.markdown('<div class="status-tag agent-client">GUI Client (You)</div>', unsafe_allow_html=True)
    st.markdown("**Worker Nodes**")
    st.markdown('<div class="status-tag agent-server">📂 FileAgent :8001</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-tag agent-server">🧮 MathAgent :8002</div>', unsafe_allow_html=True)
    if st.button("Clear Network History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🌐 Agent-to-Agent (A2A) Network")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ex: List files here and calculate 100/4"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        container = st.empty()
        full_log = []
        executed_actions = set() 
        
        for step in range(5):
            # 1. Build History (User vs AI)
            history_msgs = []
            for m in st.session_state.messages:
                if m["role"] == "user":
                    history_msgs.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    history_msgs.append(AIMessage(content=m["content"]))
            
            # 2. Get AI Decision
            decision = get_next_step(history_msgs)
            target = decision.get("next")
            payload = decision.get("query", "")
            
            # --- STRICT VALIDATOR (Prevents Bad Calls) ---
            should_stop = False
            
            # A. Check Target Validity
            if target not in ["FileAgent", "MathAgent"]:
                should_stop = True # Invalid agent name or FINISH
            
            # B. Check Payload Logic
            elif target == "MathAgent":
                # If MathAgent is called without numbers, it's a hallucination (like "history")
                if not any(char.isdigit() for char in payload):
                     interaction_log = "**System**: Blocked invalid MathAgent call (no numbers found). Finishing."
                     full_log.append(interaction_log)
                     st.session_state.messages.append({"role": "assistant", "content": interaction_log})
                     container.markdown("\n\n".join(full_log))
                     should_stop = True

            elif target == "FileAgent":
                # FileAgent must have a valid command keyword
                if "list" not in payload.lower() and "check" not in payload.lower():
                     should_stop = True

            # C. Check for Loops
            action_signature = f"{target}:{payload}"
            if action_signature in executed_actions:
                should_stop = True
            
            if should_stop:
                break
            
            executed_actions.add(action_signature)
            # ---------------------------------------------

            # 3. Execute
            port = 8001 if target == "FileAgent" else 8002
            
            with st.status(f"📡 Hop {step+1}: Contacting **{target}**...", expanded=False) as status:
                st.write(f"**Target:** `{target}` (:{port})")
                st.write(f"**Payload:** `{payload}`")
                
                response_text = asyncio.run(query_remote_agent(port, payload))
                st.write(f"**Response:** {response_text}")
                
                if response_text.startswith("ERROR:"):
                    status.update(label=f"❌ Connection Failed to {target}", state="error")
                    st.error(f"Network Error: {response_text}")
                    break
                else:
                    status.update(label=f"✅ {target} Responded", state="complete")
                
            interaction_log = f"**{target}**: {response_text}"
            full_log.append(interaction_log)
            st.session_state.messages.append({"role": "assistant", "content": interaction_log})
            container.markdown("\n\n".join(full_log))

        if not full_log:
             container.markdown("✅ Task complete.")