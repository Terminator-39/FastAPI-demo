import json

import httpx

from cache.deepseek_stream import append_event, set_request_status
from config.cache_conf import redis_client, redis_getJsonCache, redis_setCache
from schemas.deepseek import AIChatStreamRequest
import os
from dotenv import load_dotenv

# 加在环境变量
load_dotenv()

# BASE_URL = "https://api.deepseek.com/v1/chat/completions"
# api_key = 'sk-7d7a697d53ff487db84128d2c429af37'
api_key = os.getenv('API_KEY')
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
SESSION_HISTORY_EXPIRE = 3600


async def run_ai_response_stream(
        messages: list[AIChatStreamRequest],
        session_id: str,
        request_id: str,
):
    """后台生成模型回复，并把每个上游 SSE 事件持久化到 Redis。

    这个函数不直接向浏览器 yield。HTTP 连接断开后，后台任务仍继续消费
    DeepSeek，并把事件写入 Redis，后续连接可按 Last-Event-ID 重放。
    """
    if not api_key:
        await append_event(
            request_id,
            json.dumps({"error": "未配置 DEEPSEEK_API_KEY"}, ensure_ascii=False),
        )
        await set_request_status(request_id, "failed")
        return

    history_key = f"deepseek:chat_history:{session_id}"
    history = await redis_getJsonCache(history_key) or []
    history.extend({"role": message.role, "content": message.content} for message in messages)
    await redis_setCache(history_key, history, SESSION_HISTORY_EXPIRE)

    payload = {
        "model": "deepseek-chat",
        "messages": history,
        "temperature": 0.7,
        "stream": True,
    }
    assistant_content: list[str] = []

    try:
        # 生成任务独立于 HTTP 连接；浏览器断开后它仍会继续消费上游并写 Redis。
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                    "POST",
                    os.getenv('BASE_URL'),
                    json=payload,
                    headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for data in _iter_sse_data(resp):
                    await append_event(request_id, data)
                    if data == "[DONE]":
                        break
                    try:
                        content = json.loads(data)["choices"][0]["delta"].get("content")
                        if content:
                            assistant_content.append(content)
                    except (KeyError, IndexError, json.JSONDecodeError):
                        pass

        if assistant_content:
            history.append({"role": "assistant", "content": "".join(assistant_content)})
            await redis_setCache(history_key, history, SESSION_HISTORY_EXPIRE)
        # 将请求状态设置为已完成
        # 使用await关键字等待异步函数set_request_status执行完成
        # 传入两个参数：request_id（请求ID）和"completed"（状态值）
        await set_request_status(request_id, "completed")
    except Exception:
        # 错误也写入事件队列，所有重连客户端都能收到同一个失败结果。
        await append_event(
            request_id,
            json.dumps({"error": "模型服务暂时不可用"}, ensure_ascii=False),
        )
        await set_request_status(request_id, "failed")


async def _iter_sse_data(resp: httpx.Response):
    """按空行拆分上游 SSE，避免把被网络切开的原始 bytes 直接转发给前端。"""
    data_lines: list[str] = []
    async for line in resp.aiter_lines():
        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        yield "\n".join(data_lines)
