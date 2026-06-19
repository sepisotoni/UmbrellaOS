
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from ..database import Base

class PluginCommand(Base):
    __tablename__ = "plugin_commands"

    id = Column(Integer, primary_key=True, index=True)
    plugin_name = Column(String, index=True)
    action = Column(String)
    status = Column(String, default="pending") # pending, completed, failed
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
