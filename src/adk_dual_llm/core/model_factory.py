from typing import Union

from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLlm


def resolve_model(model_name: str) -> Union[str, BaseLlm]:
    """Return an ADK-compatible model config.

    - Plain Gemini names (e.g. gemini-2.0-flash) are returned as-is.
    - Provider-prefixed names (e.g. openai/gpt-4o-mini) use LiteLlm.
    """
    if "/" in model_name:
        return LiteLlm(model=model_name)
    return model_name

