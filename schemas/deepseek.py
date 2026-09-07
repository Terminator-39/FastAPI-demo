from typing import Optional

from pydantic import BaseModel, Field
from pydantic.v1 import ConfigDict


class AichatRequest(BaseModel):
    prompt: str
    session_id: str
    stream: Optional[bool] = Field(False, description='是否流式返回')


class AIChatStreamRequest(BaseModel):
    role: str = Field("user", description="用户或系统")
    content: str = Field(..., description="消息内容")


class AichatResponse(BaseModel):
    session_id: str
    text: str
    model_config = ConfigDict(from_attributes=True)
