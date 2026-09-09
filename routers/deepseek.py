from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from crud.deepseek import check_rate_limit, get_ai_response, get_ai_response_stream
from schemas.deepseek import AichatResponse, AichatRequest, AIChatStreamRequest

# from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix='/api/chat/deepseek', tags=['DeepSeek'])


@router.post('/start_chat', response_model=AichatResponse)
async def start_chat(user_input: AichatRequest):
    res = await get_ai_response(user_input.prompt, user_input.session_id)
    return res


@router.post('/stream_chat')
async def stream_chat(
        messages: list[AIChatStreamRequest],
        session_id: str | None = Query(None, alias='sessionId')
):
    session_id = session_id or (messages[-1].session_id if messages else None)
    if not session_id:
        raise HTTPException(status_code=422, detail='缺少 sessionId')
    # 检查当前会话的速率限制
    await check_rate_limit(session_id)
    return StreamingResponse(
        get_ai_response_stream(messages, session_id),
        media_type="text/event-stream"
    )
