import uuid
from typing import Any, Dict, Optional

class HandleManager:
    """
    Manages the mapping between symbolic UUID keys (handles) and raw untrusted values.
    This serves as the isolation layer for the Dual LLM pattern.
    """

    def __init__(self):
        # Internal storage for mapping handles to data
        self._store: Dict[str, Dict[str, Any]] = {}

    def create_handle(self, value: Any, type_hint: Optional[str] = None) -> str:
        """
        Stores a raw value and returns a unique symbolic handle.
        """
        # Generate a unique key (UUID)
        key = str(uuid.uuid4())
        
        # Store the value along with metadata
        self._store[key] = {
            "value": value, 
            "type": type_hint
        }
        return key

    def resolve_handle(self, key: str) -> Any:
        """
        Retrieves the original raw value associated with a given handle.
        Raises KeyError if the handle is invalid or expired.
        """
        if key not in self._store:
            raise KeyError(f"Handle {key} does not exist in the registry.")
        
        return self._store[key]["value"]

    def clear(self) -> None:
        """Resets the storage. Useful for clearing state between episodes."""
        self._store.clear()