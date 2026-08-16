"""
services/events — the outbox event bus package (Phase 7, Decision 1).

Importing this package registers every built-in subscriber
(services/events/subscribers.py) as a side effect, mirroring
capabilities/__init__.py's pattern. main.py imports this once at startup,
before the dispatcher loop starts, so no event can be dispatched before
its subscribers exist.
"""
from . import subscribers  # noqa: F401
from .bus import EventBus  # noqa: F401
from .dispatcher import EventDispatcher, run_event_dispatcher_loop  # noqa: F401

__all__ = ["EventBus", "EventDispatcher", "run_event_dispatcher_loop"]
