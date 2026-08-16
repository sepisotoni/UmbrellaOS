"""
services/moderation_intelligence/heuristics.py — Ported from Moo-assistant's
bot/moderation/heuristics.py.

Adaptation from the source: Moo keys its sliding windows by (guild_id, user_id)
since one bot process can serve multiple guilds. umbrella-core has no
multi-tenant concept (see models/moderation_intelligence.py's module
docstring) - one deployment is one Discord community, so SpamDetector keys
by user_id alone and RaidDetector tracks a single global join window.

Both detectors are deliberately in-memory, process-local, and hold no DB
state - they exist to cheaply flag "this looks like it might be spam/a
raid" for a ModerationReport to be created from, not to be an audit trail
themselves. The report + AI analysis that follows is what gets persisted.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from config import get_settings


class SpamDetector:
    """Flags a user once they've sent `spam_message_threshold`+ messages
    within a `spam_window_seconds` sliding window."""

    def __init__(self) -> None:
        self._recent_messages: dict[str, deque[float]] = defaultdict(deque)

    def record_message(self, user_id: str) -> bool:
        """Records a message from user_id and returns True if this message
        pushed them over the spam threshold."""
        settings = get_settings()
        now = time.monotonic()
        window = self._recent_messages[user_id]
        window.append(now)

        cutoff = now - settings.spam_window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        return len(window) >= settings.spam_message_threshold

    def reset(self, user_id: str) -> None:
        """Clears a user's window - called after a report is created for
        them, so the same burst of messages doesn't generate a second
        report on the very next message."""
        self._recent_messages.pop(user_id, None)


class RaidDetector:
    """Flags a possible raid once `raid_join_threshold`+ members have
    joined within a `raid_window_seconds` sliding window."""

    def __init__(self) -> None:
        self._recent_joins: deque[float] = deque()

    def record_join(self) -> bool:
        """Records a join and returns True if this join pushed the server
        over the raid threshold."""
        settings = get_settings()
        now = time.monotonic()
        self._recent_joins.append(now)

        cutoff = now - settings.raid_window_seconds
        while self._recent_joins and self._recent_joins[0] < cutoff:
            self._recent_joins.popleft()

        return len(self._recent_joins) >= settings.raid_join_threshold

    def reset(self) -> None:
        self._recent_joins.clear()
