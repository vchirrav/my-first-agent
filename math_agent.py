import asyncio
import math
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.utils import new_agent_text_message

class MathAgentExecutor(AgentExecutor):
    async def execute(self, context, event_queue) -> None:
        user_text = ""
        msg_obj = None
        
        # 1. Safe Message Location
        if hasattr(context, 'message'):
            msg_obj = context.message
        elif hasattr(context, 'request') and hasattr(context.request, 'message'):
            msg_obj = context.request.message

        # 2. Robust Text Extraction
        if msg_obj and hasattr(msg_obj, 'parts') and msg_obj.parts:
            part = msg_obj.parts[0]
            if hasattr(part, 'text') and part.text:
                user_text = part.text
            elif hasattr(part, 'model_dump'):
                data = part.model_dump()
                user_text = data.get('text', '')
            elif hasattr(part, 'dict'):
                data = part.dict()
                user_text = data.get('text', '')
            else:
                user_text = str(part)
        
        print(f"[MathAgent] Processing: {user_text}")
        
        try:
            expression = user_text.replace("calculate", "").strip()
            safe_dict = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            result = eval(expression, {"__builtins__": None}, safe_dict)
            response = str(result)
        except Exception as e:
            response = f"Math Error: {e}"

        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(self, task_id: str) -> None:
        print(f"Cancellation requested for {task_id}")

card = AgentCard(
    id="math-agent",
    name="Math Specialist",
    description="I calculate numbers.",
    version="0.0.1",
    url="http://localhost:8002",
    capabilities=AgentCapabilities(),
    defaultInputModes={"text"},
    defaultOutputModes={"text"},
    skills=[
        AgentSkill(id="math", name="Calculator", description="Eval math expressions", tags=[])
    ]
)

task_store = InMemoryTaskStore()
handler = DefaultRequestHandler(
    agent_executor=MathAgentExecutor(), 
    task_store=task_store
)

app_wrapper = A2AStarletteApplication(
    agent_card=card,
    http_handler=handler
)

app = app_wrapper.build()

if __name__ == "__main__":
    print("🧮 Starting Math Agent on :8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)