'''根据 token 查询用户'''
from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud.user import get_user_by_token


async def get_current_user(db: AsyncSession = Depends(get_db), authorization: str = Header(..., alias="Authorization")):
    '''根据 token 查询用户'''
    token = authorization.split(' ')[1]
    if not token:
        raise HTTPException(
            status_code=401,
            detail='Authorization 格式应为 Bearer <token>'
        )

    user = await get_user_by_token(db, token)
    if not user:
        raise Exception('用户不存在或令牌已过期')
    return user
