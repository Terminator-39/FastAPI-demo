import json
import time
from typing import Any

from config.cache_conf import redis_client

STREAM_EXPIRE = 3600


def _meta_key(request_id: str) -> str:
    """生成流式请求元数据的 Redis 键。"""
    return f"deepseek:stream:{request_id}:meta"


def _events_key(request_id: str) -> str:
    """生成流式 SSE 事件列表的 Redis 键。"""
    return f"deepseek:stream:{request_id}:events"


def _next_id_key(request_id: str) -> str:
    """生成流式 SSE 事件自增序号的 Redis 键。"""
    return f"deepseek:stream:{request_id}:next_id"


def _session_owner_key(session_id: str) -> str:
    """生成会话归属键，用于校验会话所属用户。"""
    return f"deepseek:conversation:{session_id}:owner"


def _session_meta_key(session_id: str) -> str:
    """生成会话摘要元数据键。"""
    return f"deepseek:conversation:{session_id}:meta"


def _user_sessions_key(owner_id: int) -> str:
    """生成用户最近会话有序集合的 Redis 键。"""
    return f"deepseek:conversations:user:{owner_id}"


async def _save_session_meta(
    session_id: str,  # 会话ID，字符串类型
    owner_id: int,   # 所有者ID，整数类型
    title: str,      # 会话标题，字符串类型
    updated_at: float,  # 更新时间，浮点数类型
) -> None:  # 函数返回类型为None
    """
    保存会话元数据到Redis数据库
    该函数执行以下操作：
    1. 将会话元数据以JSON格式存储到Redis中
    2. 在用户的有序集合中添加会话ID，以更新时间为分数
    3. 设置用户会话集合的过期时间
    参数:
        session_id: 会话的唯一标识符
        owner_id: 会话所有者的用户ID
        title: 会话的标题
        updated_at: 会话的最后更新时间戳
    """
    # 将会话元数据保存到Redis，使用session_id作为键
    await redis_client.set(
        _session_meta_key(session_id),  # 获取会话元数据的键
        json.dumps(  # 将数据转换为JSON字符串
            {"id": session_id, "title": title, "updated_at": updated_at},  # 要保存的数据
            ensure_ascii=False,  # 确保非ASCII字符正确保存
        ),
        ex=STREAM_EXPIRE,  # 设置过期时间
    )
    # 在用户的有序集合中添加会话，以updated_at作为分数
    await redis_client.zadd(
        _user_sessions_key(owner_id),  # 获取用户会话集合的键
        {session_id: updated_at},  # 添加会话ID和更新时间
    )
    # 设置用户会话集合的过期时间
    await redis_client.expire(_user_sessions_key(owner_id), STREAM_EXPIRE)


async def ensure_session_owner(
    session_id: str,
    owner_id: int,
    title: str = "新的对话",
) -> bool:
    """确保会话只属于一个用户。

    首次使用会话时原子写入所有者；后续请求必须匹配同一个用户。
    Redis 的 NX 保证并发首次请求不会互相覆盖归属，避免仅凭 session_id
    读取或写入其他用户的聊天历史。
    """
    owner_key = _session_owner_key(session_id)
    created = await redis_client.set(
        owner_key,
        str(owner_id),
        ex=STREAM_EXPIRE,
        nx=True,
    )
    if created:
        await _save_session_meta(session_id, owner_id, title, time.time())
        return True

    saved_owner_id = await redis_client.get(owner_key)
    if str(saved_owner_id) != str(owner_id):
        return False

    # 会话每次被合法访问时续期，使归属 TTL 与聊天历史 TTL 保持一致。
    await redis_client.expire(owner_key, STREAM_EXPIRE)
    meta = await redis_client.get(_session_meta_key(session_id))
    if not meta:
        # 兼容新增元数据前已经存在的旧历史会话。
        await _save_session_meta(session_id, owner_id, title, time.time())
    else:
        saved_meta = json.loads(meta)
        await _save_session_meta(
            session_id,
            owner_id,
            saved_meta.get("title", title),
            time.time(),
        )
    return True


async def get_session_owner(session_id: str) -> int | None:
    """读取会话所属用户 ID；会话不存在时返回 None。"""
    value = await redis_client.get(_session_owner_key(session_id))
    return int(value) if value is not None else None


async def get_session_meta(session_id: str) -> dict[str, Any] | None:
    """读取会话标题和更新时间等摘要元数据。"""
    value = await redis_client.get(_session_meta_key(session_id))
    return json.loads(value) if value else None


async def list_sessions(owner_id: int) -> list[dict[str, Any]]:
    """按最近使用时间返回当前用户的会话摘要，不读取完整聊天内容。"""
    session_ids = await redis_client.zrevrange(_user_sessions_key(owner_id), 0, -1)
    sessions: list[dict[str, Any]] = []
    for session_id in session_ids:
        raw_meta = await redis_client.get(_session_meta_key(session_id))
        if raw_meta:
            sessions.append(json.loads(raw_meta))
    return sessions


async def get_session_history(session_id: str) -> list[dict[str, str]]:
    """读取一个会话的历史消息；权限校验由路由层先完成。"""
    history_key = f"deepseek:chat_history:{session_id}"
    return await _get_json_cache(history_key) or []


async def _get_json_cache(key: str) -> Any:
    """读取并反序列化 JSON 字符串缓存。"""
    value = await redis_client.get(key)
    return json.loads(value) if value else None


async def create_request(request_id: str, session_id: str, owner_id: int) -> bool:
    """原子登记一次生成请求，避免断线重连重复启动 DeepSeek 请求。"""
    meta = json.dumps(
        {"session_id": session_id, "owner_id": owner_id, "status": "running"},
        ensure_ascii=False,
    )
    return bool(await redis_client.set(_meta_key(request_id), meta, ex=STREAM_EXPIRE, nx=True))


async def get_request(request_id: str) -> dict[str, Any] | None:
    """
    根据 request_id 读取流式请求状态和权限元数据。
    Args:
        request_id: 一次模型生成请求的唯一 ID
    Returns:
        解析后的请求元数据；请求不存在时返回 None
    """
    # 从Redis中获取指定request_id的值
    value = await redis_client.get(_meta_key(request_id))
    # 如果value存在，则解析JSON并返回；否则返回None
    return json.loads(value) if value else None


async def set_request_status(request_id: str, status: str) -> None:
    """更新后台模型任务状态，并保留原请求的会话和用户信息。"""
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
    """读取指定 SSE ID 之后的事件，供断线重连按游标继续消费。"""
    values = await redis_client.lrange(_events_key(request_id), last_event_id, -1)
    return [json.loads(value) for value in values]
