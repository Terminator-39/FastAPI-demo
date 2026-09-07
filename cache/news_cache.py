'''
    新闻相关的读取/写入缓存方法
    key-value
'''
from typing import List, Dict, Any

from config.cache_conf import redis_getJsonCache, redis_setCache

CATEGORIES_KEY = 'news:categories'


async def get_cache_categories():
    '''获取新闻分类缓存'''
    return await redis_getJsonCache(CATEGORIES_KEY)


async def set_cache_categories(data: List[Dict[str, Any]], expire: int = 3600):
    '''设置新闻分类缓存'''
    return await redis_setCache(CATEGORIES_KEY, data, expire)


async def set_cache_news(category_id: str, no: int, size: int, data: List[Dict[str, Any]], expire: int = 3600):
    '''设置新闻列表缓存'''
    return await redis_setCache(f'news_list:{category_id}:{no}:{size}', data, expire)

async def get_cache_news(category_id: str, no: int, size: int):
    '''获取新闻列表缓存'''
    return await redis_getJsonCache(f'news_list:{category_id}:{no}:{size}')
