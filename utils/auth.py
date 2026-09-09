'''根据 token 查询用户'''
import logging

from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud.user import get_user_by_token


async def get_current_user(db: AsyncSession = Depends(get_db), authorization: str = Header(..., alias="Authorization")):
    '''根据 token 查询用户'''
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1]:
        raise HTTPException(
            status_code=401,
            detail='Authorization 格式应为 Bearer <token>'
        )
    token = parts[1]
    print(token,logging.info(f'token: {token}===================================='))
    user = await get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail='用户不存在或令牌已过期')
    return user
