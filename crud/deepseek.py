import json

import httpx
import requests
from fastapi import HTTPException

from config.cache_conf import redis_client, redis_getJsonCache, redis_setCache
from schemas.deepseek import AIChatStreamRequest

# 配置
url = "https://api.deepseek.com/v1/chat/completions"
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
api_key = 'sk-7d7a697d53ff487db84128d2c429af37'
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
RATE_LIMIT = 5
RATE_LIMIT_WINDOW = 60
SESSION_HISTORY_EXPIRE = 3600


async def check_rate_limit(session_id: str):
    """
    检查指定会话的请求频率是否超过限制。
    Args:
        session_id (str): 当前聊天会话 ID，用于隔离限流计数
    Returns:
        None: 如果请求频率在限制范围内，正常返回
    Raises:
        HTTPException: 当请求频率超过限制时，抛出429状态码的异常
    """
    # 构建Redis键，使用session_id作为标识
    key = f"deepseek:rate_limit:{session_id}"
    # 使用Redis的incr命令增加计数器，如果键不存在则创建并设置为1
    count = await redis_client.incr(key)
    # 如果计数器为1，说明是第一次请求，设置过期时间
    if count == 1:
        await redis_client.expire(key, RATE_LIMIT_WINDOW)
    # 如果计数器超过预设的限制值，抛出异常
    if count > RATE_LIMIT:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")


async def get_ai_response(prompt, session_id):
    """调用非流式模型接口并返回完整 assistant 文本。"""
    await check_rate_limit(session_id)
    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        # "max_tokens": 100000
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        # print(response.json()["choices"][0]["message"]["content"])
        res = response.json()["choices"][0]["message"]["content"]
        return {"session_id": session_id, "text": res}

    else:
        print(f"错误：{response.status_code} - {response.text}")
        raise HTTPException(status_code=500, detail="API请求失败")


# 异步流式请求 DeepSeek API
async def get_ai_response_stream(messages: list[AIChatStreamRequest], session_id: str):
    """调用旧版非持久化流式接口并逐块转发上游响应。

    当前主聊天链路使用 crud.deepseek_stream.run_ai_response_stream；
    该函数保留给旧接口，历史上下文仍按 session_id 存取。
    """
    # 检查 API Key 是否已配置
    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    history_key = f"deepseek:chat_history:{session_id}"
    history = await redis_getJsonCache(history_key) or []
    history.extend({"role": message.role, "content": message.content} for message in messages)
    await redis_setCache(history_key, history, SESSION_HISTORY_EXPIRE)

    payload = {
        "model": "deepseek-chat",
        "messages": history,
        "temperature": 0.7,
        "stream": True
        # "max_tokens": 10000
    }

    # 使用 httpx 异步客户端发送流式请求
    assistant_content = []
    # 初始化一个空的bytes对象，用于存储待处理的数据
    pending = b""

    async with httpx.AsyncClient(timeout=None) as client:

        async with client.stream(
                "POST",
                BASE_URL,
                json=payload,
                headers=headers
        ) as resp:
            # 检查响应状态码，若非 2xx 则抛出异常
            resp.raise_for_status()
            # 异步迭代读取流式响应的字节块并逐块返回
            async for chunk in resp.aiter_bytes():
                pending += chunk
                lines = pending.split(b"\n")
                pending = lines.pop()
                for line in lines:
                    data = line.removeprefix(b"data:").strip()
                    if data and data != b"[DONE]":
                        try:
                            content = json.loads(data)["choices"][0]["delta"].get("content")
                            if content:
                                assistant_content.append(content)
                        except (KeyError, IndexError, json.JSONDecodeError):
                            pass
                yield chunk

    # 检查pending内容是否以"data:"开头
    if pending.startswith(b"data:"):
        try:
            # 尝试解析JSON数据，提取assistant的回复内容
            # 首先去除"data:"前缀，然后解析JSON，获取choices数组的第一个元素
            # 再获取delta对象中的content字段
            content = json.loads(pending[5:].strip())["choices"][0]["delta"].get("content")
            # 如果content存在，则添加到assistant_content列表中
            if content:
                assistant_content.append(content)
        # 捕获可能出现的异常：KeyIndex(键不存在)、IndexError(索引越界)、JSONDecodeError(JSON解析错误)
        except (KeyError, IndexError, json.JSONDecodeError):
            pass
    # 如果assistant_content列表不为空，说明有assistant的回复内容
    if assistant_content:
        # 将assistant的回复内容合并成一个字符串，添加到对话历史中
        history.append({"role": "assistant", "content": "".join(assistant_content)})
        # 将更新后的对话历史保存到Redis缓存中，设置过期时间
        await redis_setCache(history_key, history, SESSION_HISTORY_EXPIRE)
