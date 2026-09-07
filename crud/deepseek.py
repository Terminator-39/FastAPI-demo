import httpx
import requests
from fastapi import HTTPException

from schemas.deepseek import AIChatStreamRequest

# 配置
url = "https://api.deepseek.com/v1/chat/completions"
BASE_URL = "https://api.deepseek.com/v1/chat/completions"
api_key = 'sk-7d7a697d53ff487db84128d2c429af37'
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}


async def get_ai_response(prompt, session_id):
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
async def get_ai_response_stream(messages: list[AIChatStreamRequest]):
    '''异步流式请求ds'''
    # 检查 API Key 是否已配置
    if not api_key:
        raise HTTPException(status_code=500, detail="未配置 DEEPSEEK_API_KEY")

    payload = {
        "model": "deepseek-chat",
        "messages": [message.model_dump() for message in messages],
        "temperature": 0.7,
        "stream": True
        # "max_tokens": 10000
    }

    # 使用 httpx 异步客户端发送流式请求
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
                yield chunk
