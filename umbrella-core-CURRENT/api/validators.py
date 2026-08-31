"""
api/validators.py — Small, reusable Pydantic field validators shared across
routers and capabilities.

Currently just player_uuid validation (master bug report finding #17,
originally fixed independently in api/routers/verification.py, then
extracted here so capabilities/verification.py's VerificationStatusParams
uses the exact same rule instead of a second, possibly-drifting copy).
"""
import uuid as uuid_lib


def validate_player_uuid(v: str) -> str:
    """Validate player_uuid is a well-formed, canonically-formatted UUID
    (standard 36-char lowercase hyphenated form: 8-4-4-4-12), matching
    Player.uuid's String(36) column and how the Minecraft plugin actually
    generates/sends it.

    FIX (master bug report #17): player_uuid was accepted as any string with
    no format check anywhere a client supplies one directly. Since
    Player.uuid is a plain String(36) column (not a native UUID type), a
    malformed value doesn't crash — it silently gets stored/queried as
    garbage data instead. This stops bad data from being written or used to
    query with invalid strings in the first place, with a clear 422 rather
    than a downstream lookup that either errors confusingly or (worse)
    silently matches nothing.

    Checked strictly against the canonical form rather than just
    `uuid.UUID(v)` succeeding: Python's uuid.UUID() is lenient — it also
    accepts a 32-char non-hyphenated hex string, braces, or mixed case, all
    of which parse to the same UUID value but would NOT string-match the
    36-char lowercase-hyphenated value already stored for the same player
    from a normal request. Accepting those forms wouldn't stop bad data, it
    would let two different string representations of the same UUID
    silently fail to `==`-match each other in every query that uses this
    value, which is arguably worse than the original gap. `str(parsed) == v`
    rejects anything that isn't already in the exact form this column has
    always used.
    """
    try:
        parsed = uuid_lib.UUID(v)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"player_uuid must be a valid UUID: {v!r}") from exc
    if str(parsed) != v:
        raise ValueError(
            f"player_uuid must be in canonical lowercase hyphenated form "
            f"(e.g. {parsed}): {v!r}"
        )
    return v
