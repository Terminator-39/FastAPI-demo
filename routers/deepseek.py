import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from starlette.responses import StreamingResponse

from cache.deepseek_stream import create_request, get_events_after, get_request
from crud.deepseek import check_rate_limit, get_ai_response
from crud.deepseek_stream import run_ai_response_stream
from schemas.deepseek import AichatResponse, AichatRequest, AIChatStreamRequest
from utils.auth import get_current_user

# from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix='/api/chat/deepseek', tags=['DeepSeek'])


@router.post('/start_chat', response_model=AichatResponse)
async def start_chat(user_input: AichatRequest):
    res = await get_ai_response(user_input.prompt, user_input.session_id)
    return res


@router.post('/stream_chat')
async def stream_chat(
        messages: list[AIChatStreamRequest],  # 聊天消息列表
        session_id: str | None = Query(None, alias='sessionId'),  # 会话ID，可选参数
        request_id: str = Query(..., alias='requestId'),  # 请求ID，必需参数
        last_event_id: int | None = Header(None, alias='Last-Event-ID'),  # 最后事件ID，从请求头获取
        user=Depends(get_current_user),  # 当前用户，依赖注入获取
):
    # 如果没有提供session_id，则使用最后一条消息的session_id
    session_id = session_id or (messages[-1].session_id if messages else None)
    if not session_id:
        raise HTTPException(status_code=422, detail='缺少 sessionId')  # 如果没有session_id，抛出422错误
    # 获取现有请求
    existing = await get_request(request_id)
    if existing and (
            existing.get('owner_id') != user.id  # 检查请求所有者是否为当前用户
            or existing.get('session_id') != session_id  # 检查请求的session_id是否匹配
    ):
        raise HTTPException(status_code=403, detail='无权访问该流式请求')  # 如果不匹配，抛出403错误

    # 只有第一次请求计入速率限制、创建后台生成任务；重连只读取已有事件。
    if not existing:
        await check_rate_limit(session_id)
    # 检查是否为新的请求
    # 调用create_request异步函数，传入请求ID、会话ID和用户ID
    # 并将返回结果存储在is_new_request变量中
    is_new_request = await create_request(request_id, session_id, user.id)
    if is_new_request:
        task = asyncio.create_task(run_ai_response_stream(messages, session_id, request_id))

        # 使用 asyncio.create_task 后，如果不需要等待，但需要处理异常，可以添加以下逻辑
        async def monitor_task():
            try:
                await task
            except Exception as e:
                # 记录异常或进行其他处理
                print(f"Background task failed: {e}")

        asyncio.create_task(monitor_task())
        # asyncio.create_task(run_ai_response_stream(messages, session_id, request_id))

    return StreamingResponse(
        stream_saved_events(request_id, last_event_id or 0),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def stream_saved_events(request_id: str, last_event_id: int):
    """持续发送 Redis 中尚未收到的事件；客户端断开不会影响后台生成任务。"""
    cursor = max(last_event_id, 0)
    while True:
        events = await get_events_after(request_id, cursor)
        for event in events:
            event_id = int(event['id'])
            yield f"id: {event_id}\ndata: {event['data']}\n\n"
            cursor = event_id

        meta = await get_request(request_id)
        if meta is None:
            return
        if meta.get('status') in {'completed', 'failed'} and not events:
            return

        # 短轮询让重连延迟低；生产部署还应由代理关闭响应缓冲。
        await asyncio.sleep(0.2)
