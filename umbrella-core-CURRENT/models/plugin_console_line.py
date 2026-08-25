"""Plugin console line buffer — stores recent console output from connected servers."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class PluginConsoleLine(Base):
    __tablename__ = "plugin_console_lines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False, index=False)
    line: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
