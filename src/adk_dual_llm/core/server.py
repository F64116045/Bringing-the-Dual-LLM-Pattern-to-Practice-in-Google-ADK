import os
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from .quarantined_agent import QuarantinedAgent

def create_app(model: str = "gemini-2.0-flash"):
    """
    Creates the FastAPI app for the Q-LLM agent.
    """
    # Instantiate the agent
    agent = QuarantinedAgent(model=model)
    
    # Convert ADK Agent to A2A FastAPI App
    # This automatically creates endpoints like /agent-card, /chat, etc.
    app = to_a2a(agent)
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