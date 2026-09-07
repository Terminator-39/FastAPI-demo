'''
    todo 新闻 tab 类型的 crud 方法
'''
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.exc import SQLAlchemyError

from cache.news_cache import get_cache_news, set_cache_news
from models.news import Category, News


async def get_categories(db: AsyncSession, page_size: int = 20, page_no: int = 1):
    '''查看新闻分类'''
    stmt = select(Category).offset((page_no - 1) * page_size).limit(page_size)
    res = await db.execute(stmt)
    if not res:
        return HTTPException(status_code=404, detail='获取新闻分类失败,请检查数据库!')
    return res.scalars().all()


async def get_list(db: AsyncSession, category_id: str, page_size: int = 20, page_no: int = 1):
    '''获取新闻信息分页列表'''
    cache_news = await get_cache_news(category_id, page_no, page_size)
    print('走Redis-----------------------------------------------------------------------------')
    if cache_news:
        # return [News(**news) for news in cache_news]
        return cache_news
    stmt = select(News).where(News.type.like(f'{category_id}%')).offset((page_no - 1) * page_size).limit(page_size)
    res = await db.execute(stmt)
    print('走请求-----------------------------------------------------------------------------')
    if not res:
        return HTTPException(status_code=404, detail='获取新闻列表失败,请检查数据库!')
    cache_news = res.scalars().all()
    if cache_news:
        res_cache_news = jsonable_encoder(cache_news)
        await set_cache_news(category_id, page_no, page_size,res_cache_news)
    return cache_news


async def get_total(db: AsyncSession, category_id: str):
    '''获取新闻数据总数'''
    stmt = select(News).where(News.type.like(f'{category_id}%'))
    res = await db.execute(stmt)
    if not res:
        return HTTPException(status_code=404, detail='获取新闻数据总数失败,请检查数据库!')
    return res.scalars().all()


async def get_detail(db: AsyncSession, news_id: int):
    '''获取新闻详情'''
    try:
        result = await db.execute(select(News).where(News.id.like(f'{news_id}')))
        detail = result.scalar_one_or_none()
        if detail is None:
            raise HTTPException(status_code=404, detail='新闻不存在')

        if not await increment_view(db, news_id):
            raise HTTPException(status_code=500, detail='浏览量更新失败')
        detail.views = (detail.views or 0) + 1
        return detail
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail='获取新闻详情失败') from exc

async def increment_view(db: AsyncSession, news_id: int):
    '''浏览量+1'''
    stmt = update(News).where(News.id.like(f'{news_id}')).values(views=News.views + 1)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0 if hasattr(res, 'rowcount') else False
