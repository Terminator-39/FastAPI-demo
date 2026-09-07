import json
from typing import Any

import redis.asyncio as redis

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
# REDIS_PASSWORD = '123456'

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    # password=REDIS_PASSWORD,
    db=REDIS_DB,
    decode_responses=True
)


async def redis_getCache(key: str):
    '''获取str缓存'''
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(e, '获取str缓存失败')
        raise None


async def redis_getJsonCache(key: str):
    '''获取json缓存[{}]'''
    try:
        res = await redis_client.get(key)
        if res:
            return json.loads(res)
        return None
    except Exception as e:
        print(e, '获取json缓存失败')
        raise None


async def redis_setCache(key: str, value: Any, expire_time: int = 3600):
    '''设置缓存'''
    try:
        if isinstance(value,(dict,list)):
            value = json.dumps(value, ensure_ascii=False) # json格式化 保留中文
        await redis_client.setex(key, expire_time, value)
        return True
    except Exception as e:
        print(e, '设置缓存失败')
        raise None


async def redis_deleteCache(key: str):
    return await redis_client.delete(key)


async def redis_exists(key: str):
    return await redis_client.exists(key)
