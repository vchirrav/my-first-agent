import asyncio
import os
import uvicorn

# Official A2A SDK Imports
from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.utils import new_agent_text_message

class FileAgentExecutor(AgentExecutor):
    async def execute(self, context, event_queue) -> None:
        user_text = ""
        msg_obj = None
        
        # --- FIX 1: Safe Message Location (Fixes 'RequestContext has no attribute task') ---
        if hasattr(context, 'message'):
            msg_obj = context.message
        elif hasattr(context, 'request') and hasattr(context.request, 'message'):
            msg_obj = context.request.message

        # --- FIX 2: Robust Text Extraction (Fixes 'Part has no attribute text') ---
        if msg_obj and hasattr(msg_obj, 'parts') and msg_obj.parts:
            # We grab the first part of the message
            part = msg_obj.parts[0]
            
            # We try multiple ways to get the text, as SDK versions vary
            if hasattr(part, 'text') and part.text:
                user_text = part.text
            elif hasattr(part, 'model_dump'): # Pydantic v2
                data = part.model_dump()
                user_text = data.get('text', '')
            elif hasattr(part, 'dict'):       # Pydantic v1
                data = part.dict()
                user_text = data.get('text', '')
            else:
                # Last resort fallback
                user_text = str(part)
        
        # LOWERCASE the input for easier matching
        user_text = user_text.lower()
        print(f"[FileAgent] Processing: {user_text}")
        
        response = ""
        if "list" in user_text:
            files = os.listdir(".")
            response = f"Files: {', '.join(files)}"
        elif "check" in user_text:
            words = user_text.split()
            # Simple cleanup: remove ? or . at the end if user typed "secrets.txt?"
            filename = words[-1].strip("?.,") if words else ""
            exists = os.path.exists(filename)
            response = f"File '{filename}' exists: {exists}"
        else:
            response = "I can only [list] files or [check] if a file exists."

        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(self, task_id: str) -> None:
        print(f"Cancellation requested for {task_id}")

# --- Configuration ---
card = AgentCard(
    id="file-agent",
    name="File Specialist",
    description="I handle file system operations.",
    version="0.0.1",
    url="http://localhost:8001",
    capabilities=AgentCapabilities(), 
    defaultInputModes={"text"},
    defaultOutputModes={"text"},
    skills=[
        AgentSkill(id="fs", name="FileSystem", description="List/Check files", tags=[])
    ]
)

task_store = InMemoryTaskStore()
handler = DefaultRequestHandler(
    agent_executor=FileAgentExecutor(), 
    task_store=task_store
)

app_wrapper = A2AStarletteApplication(
    agent_card=card,
    http_handler=handler
)

app = app_wrapper.build()

if __name__ == "__main__":
    print("📂 Starting File Agent on :8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)