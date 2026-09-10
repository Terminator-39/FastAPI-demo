import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from starlette.responses import StreamingResponse

from cache.deepseek_stream import (
    create_request,
    ensure_session_owner,
    get_session_history,
    get_session_meta,
    get_session_owner,
    get_events_after,
    get_request,
    list_sessions,
)
from crud.deepseek import check_rate_limit, get_ai_response
from crud.deepseek_stream import run_ai_response_stream
from schemas.deepseek import AichatResponse, AichatRequest, AIChatStreamRequest
from utils.auth import get_current_user

# from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix='/api/chat/deepseek', tags=['DeepSeek'])


@router.get('/conversations')
async def get_conversations(user=Depends(get_current_user)):
    """返回当前用户的最近会话摘要，不读取完整消息内容。"""
    return await list_sessions(user.id)


@router.get('/conversations/{session_id}')
async def get_conversation(session_id: str, user=Depends(get_current_user)):
    """校验会话归属后读取指定会话的完整历史消息。"""
    owner_id = await get_session_owner(session_id)
    if owner_id != user.id:
        raise HTTPException(status_code=404, detail='会话不存在')
    meta = await get_session_meta(session_id)
    return {
        "id": session_id,
        "title": meta.get("title", "新的对话") if meta else "新的对话",
        "messages": await get_session_history(session_id),
    }


@router.post('/start_chat', response_model=AichatResponse)
async def start_chat(user_input: AichatRequest):
    """调用非流式聊天服务，返回一次性完整回答。"""
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
    """创建或恢复一个可断点续传的聊天 SSE 流。

    首次请求会校验并绑定会话归属、创建后台模型任务；断线重连只读取
    Redis 中尚未消费的事件，不会重复启动上游模型请求。
    """
    # 如果没有提供session_id，则使用最后一条消息的session_id
    session_id = session_id or (messages[-1].session_id if messages else None)
    if not session_id:
        raise HTTPException(status_code=422, detail='缺少 sessionId')  # 如果没有session_id，抛出422错误

    title = next(
        # (message.content.strip()[:22] for message in reversed(messages) if message.content.strip()),
        (stripped[:22] for message in reversed(messages) if (stripped := message.content.strip())),
        "新的对话",
    )

    # requestId 只负责一次生成请求的断点续传，不能用它代替会话权限校验。
    # 先锁定 sessionId 的用户归属，再读取历史和创建流请求，防止跨用户复用会话 ID。
    if not await ensure_session_owner(session_id, user.id, title):
        raise HTTPException(status_code=403, detail='无权访问该会话')

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

        # 创建一个异步任务并调度执行
        # asyncio.create_task() 用于将一个协程包装成任务(Task)，并安排其尽快在事件循环中执行
        # monitor_task() 是一个协程函数，将被包装成任务并在后台执行
        asyncio.create_task(monitor_task())
        # asyncio.create_task(run_ai_response_stream(messages, session_id, request_id))

    # 返回一个流式响应对象，用于服务器推送事件流
    return StreamingResponse(
        # 调用stream_saved_events函数生成事件流，传入请求ID和最后事件ID（如果未提供则默认为0）
        stream_saved_events(request_id, last_event_id or 0),
        # 设置媒体类型为text/event-stream，这是SSE（Server-Sent Events）的标准媒体类型
        media_type="text/event-stream",
        # 设置响应头，确保流式响应正确工作
        headers={
            "Cache-Control": "no-cache",  # 禁用缓存，确保实时性
            "Connection": "keep-alive",  # 保持连接活跃，持续接收数据
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲，确保实时推送
        },
    )


async def stream_saved_events(request_id: str, last_event_id: int):
    """持续发送指定 SSE ID 之后的事件，直到后台任务完成或失败。

    客户端断开只会结束当前响应，不会取消独立运行的后台模型任务。
    """
    cursor = max(last_event_id, 0)
    while True:
        # 获取指定请求ID和游标之后的事件列表
        # 使用异步方式获取事件数据
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
