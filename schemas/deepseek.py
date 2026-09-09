from typing import Optional

from pydantic import BaseModel, Field
from pydantic.v1 import ConfigDict


class AichatRequest(BaseModel):
    # 定义AI聊天请求的数据模型，继承自BaseModel
    prompt: str  # 用户输入的提示文本，类型为字符串
    session_id: str  # 会话ID，用于标识不同的对话会话，类型为字符串
    stream: Optional[bool] = Field(False, description='是否流式返回')  # 可选的流式返回标志，默认为False，类型为布尔值的可选类型


class AIChatStreamRequest(BaseModel):
    role: str = Field("user", description="用户或系统")
    content: str = Field(..., description="消息内容")
    session_id: Optional[str] = Field(None, description="会话ID", alias='sessionId')  # 会话ID，用于标识不同的对话会话，类型为字符串


class AichatResponse(BaseModel):
    # 定义AichatResponse类，继承自BaseModel
    session_id: str  # 会话ID，字符串类型
    text: str  # 响应文本，字符串类型
    # 配置模型，允许从属性直接创建模型实例
    model_config = ConfigDict(from_attributes=True)
