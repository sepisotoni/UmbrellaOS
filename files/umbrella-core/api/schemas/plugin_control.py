
from pydantic import BaseModel
from typing import Literal

class PluginControlRequest(BaseModel):
    plugin_name: str
    action: Literal["reload", "toggle"]
