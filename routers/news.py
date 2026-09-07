'''
    todo 接口实现流程
        --- 1. 模块化路由
        --- 2. 去 models 层定义模型类
        --- 3. 在 crud 里创建文件，封装操作数据库的方法
        --- 4. 在路由函数里调用crud的方法，返回响应结果
'''
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from cache.news_cache import get_cache_categories, set_cache_categories
from crud import news
from config.db_conf import get_db

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories")
async def get_categories(page_size: int = 20, page_no: int = 1, db: AsyncSession = Depends(get_db)):
    '''查看新闻分类'''
    # todo 旁路缓存策略：
    cache_data = await get_cache_categories()
    if cache_data:
        return {'code': 200, 'data': cache_data, 'message': '查询分类成功'}
    # todo 查询数据库 -> 定义模型类 -> 封装查询数据的方法(crud)
    res = await news.get_categories(db, page_size, page_no)
    # todo 设置缓存
    if res:
        cache_data = jsonable_encoder(res)
        await set_cache_categories(cache_data)
    return {'code': 200, 'data': res, 'message': '查询分类成功'}


@router.get('/list')
async def get_list(category_id: str, page_size: int = Query(20, alias='pageSize', le=100),
                   page_no: int = Query(1, alias='pageNo', le=100), db: AsyncSession = Depends(get_db)):
    '''根据分类 id 查看新闻列表'''
    list = await news.get_list(db, category_id, page_size, page_no)
    total = await news.get_total(db, category_id)
    total = len(total)
    has_more = True if total > page_size * page_no else False
    return {'code': 200,
            'data': {'list': list
                , 'total': total
                , 'hasMore': has_more},
            'message': '查询列表成功'}


@router.get('/detail')
async def get_detail(news_id: int, db: AsyncSession = Depends(get_db)):
    '''根据新闻 id 查看新闻详情'''
    detail = await news.get_detail(db, news_id)
    if not detail:
        return {'code': 200, 'data': [], 'message': '新闻不存在'}
    return {'code': 200, 'data': detail, 'message': '查询详情成功'}
