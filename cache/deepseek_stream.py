import json
from typing import Any

from config.cache_conf import redis_client

STREAM_EXPIRE = 3600


def _meta_key(request_id: str) -> str:
    return f"deepseek:stream:{request_id}:meta"


def _events_key(request_id: str) -> str:
    return f"deepseek:stream:{request_id}:events"


def _next_id_key(request_id: str) -> str:
    return f"deepseek:stream:{request_id}:next_id"


async def create_request(request_id: str, session_id: str, owner_id: int) -> bool:
    """原子登记一次生成请求，避免断线重连重复启动 DeepSeek 请求。"""
    meta = json.dumps(
        {"session_id": session_id, "owner_id": owner_id, "status": "running"},
        ensure_ascii=False,
    )
    return bool(await redis_client.set(_meta_key(request_id), meta, ex=STREAM_EXPIRE, nx=True))


async def get_request(request_id: str) -> dict[str, Any] | None:
    """
    根据请求ID从Redis中获取请求数据
    Args:
        request_id: 请求的唯一标识符
    Returns:
        dict: 如果找到数据，返回解析后的JSON字典
        None: 如果未找到数据，返回None
    """
    # 从Redis中获取指定request_id的值
    value = await redis_client.get(_meta_key(request_id))
    # 如果value存在，则解析JSON并返回；否则返回None
    return json.loads(value) if value else None


async def set_request_status(request_id: str, status: str) -> None:
    meta = await get_request(request_id) or {}
    meta["status"] = status
    await redis_client.set(
        _meta_key(request_id),
        json.dumps(meta, ensure_ascii=False),
        ex=STREAM_EXPIRE,
    )


async def append_event(request_id: str, data: str) -> int:
    """为每个 SSE data 分配单调递增 ID，并把完整事件保存到 Redis。"""
    event_id = int(await redis_client.incr(_next_id_key(request_id)))
    event = json.dumps({"id": event_id, "data": data}, ensure_ascii=False)
    await redis_client.rpush(_events_key(request_id), event)
    await redis_client.expire(_events_key(request_id), STREAM_EXPIRE)
    await redis_client.expire(_next_id_key(request_id), STREAM_EXPIRE)
    return event_id


async def get_events_after(request_id: str, last_event_id: int) -> list[dict[str, Any]]:
    """Redis list 的第 N 项对应 event id N+1，因此从 last_event_id 开始读取。"""
    values = await redis_client.lrange(_events_key(request_id), last_event_id, -1)
    return [json.loads(value) for value in values]
