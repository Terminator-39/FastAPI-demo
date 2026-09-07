from fastapi import APIRouter
from starlette.responses import StreamingResponse

from crud.deepseek import get_ai_response, get_ai_response_stream
from schemas.deepseek import AichatResponse, AichatRequest, AIChatStreamRequest

# from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix='/api/chat/deepseek', tags=['DeepSeek'])


@router.post('/start_chat', response_model=AichatResponse)
async def start_chat(user_input: AichatRequest):
    res = await get_ai_response(user_input.prompt, user_input.session_id)
    return res


@router.post('/stream_chat')
async def stream_chat(messages: list[AIChatStreamRequest]):
    return StreamingResponse(
        get_ai_response_stream(messages),
        media_type="text/event-stream"
    )
