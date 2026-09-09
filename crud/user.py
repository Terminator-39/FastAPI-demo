'''
    todo 用户 tab 类型的 crud 方法
'''
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, DateTime
from models.user import User, UserToken
from schemas.user import UserRequest, UserUpdateRequest
from utils.security import get_password_hash


async def register(db: AsyncSession, user_data: UserRequest):
    '''注册'''
    result = await db.execute(select(User).where(User.username.like(str(user_data.username))))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=404, detail=f'用户[{user_data.username}] 已存在')
    pwd = get_password_hash(user_data.password)
    user = User(username=user_data.username, password=pwd)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(db: AsyncSession, username: str, password: str):
    '''登录'''
    result = await db.execute(select(User).where(User.username.like(f'{username}%')))
    # if result is None:
    #     raise HTTPException(status_code=404, detail=f'User[{username}] is not found')
    # elif res.password != password:
    return result.scalars().first()


async def create_token(db: AsyncSession, user_id: int):
    '''创建token'''
    token = str(uuid.uuid4())
    expire_time = datetime.utcnow() + timedelta(minutes=30)
    stmt = select(UserToken).where(UserToken.user_id.like(str(user_id)))
    result = await db.execute(stmt)
    # 如果存在 token -> 更新 ；
    if result.scalar_one_or_none() is not None:
        await db.execute(
            update(UserToken).where(UserToken.user_id.like(str(user_id))).values(token=token, expire_time=expire_time))
    # 不存在 -> 新增
    else:
        await db.execute(insert(UserToken).values(user_id=user_id, token=token, expire_time=expire_time))
    await db.commit()
    return token


async def get_user_by_username(db: AsyncSession, username: str):
    '''根据用户名获取用户'''
    result = await db.execute(select(User).where(User.username.like(f'{username}%')))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int):
    '''根据用户id获取用户'''
    result = await db.get(User, user_id)
    return result


async def get_user_by_token(db: AsyncSession, token: str):
    '''根据token获取用户'''
    result = await db.execute(select(UserToken).where(UserToken.token.like(str(token))))
    res = result.scalar_one_or_none()
    if res is None or res.expire_time <= datetime.utcnow():
        return None
    res_info = await db.get(User, res.user_id)
    return res_info


async def update_user(db: AsyncSession, user_id: int, user_inf: UserUpdateRequest):
    '''更新用户信息'''
    res = await db.execute(update(User).where(User.id.like(str(user_id))).values(
        **user_inf.model_dump(exclude_unset=True, exclude_none=True)))
    await db.commit()
    if not res:
        raise HTTPException(status_code=404, detail=f'用户[{user_id}] 找不到')
    return res
