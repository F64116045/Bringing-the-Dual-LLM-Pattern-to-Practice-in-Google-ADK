import os
from urllib.parse import urlparse
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from .quarantined_agent import QuarantinedAgent

def create_app(model: str | None = None):
    """
    Creates the FastAPI app for the Q-LLM agent.
    """
    if model is None:
        model = os.environ.get("QLLM_MODEL", "gemini-2.0-flash")

    # Instantiate the agent
    agent = QuarantinedAgent(model=model)
    
    # Build agent-card URL host/port from QLLM_URL so RemoteA2aAgent
    # can call back the correct endpoint instead of default localhost:8000.
    parsed = urlparse(os.environ.get("QLLM_URL", "http://localhost:8001"))
    card_host = parsed.hostname or "localhost"
    card_port = parsed.port or 8001

    # Convert ADK Agent to A2A FastAPI App
    # This automatically creates endpoints like /agent-card, /chat, etc.
    app = to_a2a(agent, host=card_host, port=card_port)
    return app

# This block allows running directly with `python src/.../server.py`
# But usually, you run it with `uvicorn` command.
if __name__ == "__main__":
    # Allow port configuration via environment variable
    port = int(os.environ.get("QLLM_PORT", 8001))
    
    print(f"Starting Q-LLM Server on port {port}...")
    
    # Run the server
    # Note: 'src.adk_dual_llm.core.server:create_app' is the factory path
    uvicorn.run(
        "src.adk_dual_llm.core.server:create_app", 
        host="0.0.0.0", 
        port=port, 
        factory=True,
        reload=True
    )
