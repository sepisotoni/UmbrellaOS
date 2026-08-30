"""
capabilities/shared.py — Shared Pydantic models used across multiple
capability modules.

FIX (#72): NoParams was defined independently in investigation.py,
memory.py, and knowledge.py — three identical one-liner classes with no
shared source of truth. Centralised here; each module now imports from
this file instead of defining its own copy.
"""
from pydantic import BaseModel


class NoParams(BaseModel):
    """Empty params model for capabilities that take no input."""
    pass
