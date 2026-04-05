"""TG PRO QUANTUM - State Manager for cross-tab synchronization"""
from typing import Callable, Dict, List, Any
from .utils import log


class StateManager:
    """Manage state changes across tabs"""

    _callbacks: Dict[str, List[Callable]] = {}
    _state: Dict[str, Any] = {}

    @classmethod
    def on_state_change(cls, event_type: str, callback: Callable):
        """Register callback for state changes"""
        if event_type not in cls._callbacks:
            cls._callbacks[event_type] = []
        if callback not in cls._callbacks[event_type]:
            cls._callbacks[event_type].append(callback)

    @classmethod
    def off_state_change(cls, event_type: str, callback: Callable):
        """Unregister callback for state changes"""
        if event_type in cls._callbacks:
            try:
                cls._callbacks[event_type].remove(callback)
            except ValueError:
                pass

    @classmethod
    def emit_state_change(cls, event_type: str, data: dict = None):
        """Emit state change to all listeners"""
        if data is None:
            data = {}
        cls._state[event_type] = data
        callbacks = cls._callbacks.get(event_type, [])
        for cb in list(callbacks):
            try:
                cb(data)
            except Exception as e:
                log(f"StateManager callback error ({event_type}): {e}", "error")

    @classmethod
    def get_state(cls, event_type: str) -> Any:
        """Get last state for event_type"""
        return cls._state.get(event_type)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get state value with optional default"""
        return cls._state.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a state value directly"""
        cls._state[key] = value

    @classmethod
    def refresh_all(cls):
        """Emit refresh_all to all listeners"""
        cls.emit_state_change("refresh_all", {})

    @classmethod
    def clear(cls):
        """Clear all callbacks and state"""
        cls._callbacks.clear()
        cls._state.clear()


# Global instance
state_manager = StateManager()

__all__ = ["StateManager", "state_manager"]
