"""
models/feature_flag.py — Simple boolean feature-flag registry.

Design decisions:
- Flags are identified by name (e.g. "anticheat.enabled") — unique,
  indexed, human-readable — rather than an opaque integer ID. The REST
  router and the service use name as the natural key everywhere.
- enabled defaults False so a newly-inserted flag is always off until
  explicitly toggled — safe default for any infrastructure feature.
- No caching here; FeatureFlagService.get_flag does a direct DB read
  every call. Simple, correct, and easy to reason about.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database.engine import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<FeatureFlag name={self.name!r} enabled={self.enabled}>"
