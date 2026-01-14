import uvicorn
import os
import sys


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    print(" Starting Q-LLM Server on http://0.0.0.0:8001 ...")
    

    uvicorn.run(
        "src.adk_dual_llm.core.server:create_app", 
        host="0.0.0.0", 
        port=8001, 
        factory=True,
        reload=True
    )