from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from crud import user
from config.db_conf import get_db
from crud.user import create_token, get_user_by_token, update_user
from schemas.user import UserRequest, UserAuthResp, UserInfoResp, LoginInfoResp, UserInfoBase, UserUpdateRequest
from utils.auth import get_current_user
from utils.response import BaseResp, success_resp
from utils.security import verify_password

router = APIRouter(prefix="/api/user", tags=["user"])


@router.post('/register', response_model=BaseResp)
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    # todo 检查是否存在 -> 处理是否新增用户信息
    res = await user.register(db, user_data)
    token = await create_token(db, res.id)
    resp_data = UserAuthResp(token=token, user_info=UserInfoResp.model_validate(res))
    return success_resp(message='注册成功', data=resp_data)
    # return {
    #     'code': 200,
    #     'message': '注册成功',
    #     'data': {
    #         'token': token,
    #         "user_info": {
    #             'id': res.id,
    #             'username': res.username,
    #             'bio': res.bio,
    #             'avatar': res.avatar
    #         }
    #     }
    # }


@router.get('/login', response_model=BaseResp)
async def login(username: str, password: str, db: AsyncSession = Depends(get_db)):
    res = await user.get_user_by_username(db, username)
    if not res:
        raise HTTPException(status_code=404, detail=f'用户[{username}] 找不到')
    if not verify_password(password, res.password):
        raise HTTPException(status_code=401, detail='密码错误')
    token = await create_token(db, res.id)
    resp_data = UserAuthResp(token=token, user_info=UserInfoResp.model_validate(res))
    # return {'code': 200, 'message': '登录成功', 'data': resp_data}
    return success_resp(message='登录成功', data=resp_data)


@router.get('/info', response_model=BaseResp)
async def get_user_info(user=Depends(get_current_user)):
    '''获取用户信息'''
    # if not user:
    #     raise HTTPException(status_code=404, detail=f'用户[{user.user_id}] 找不到')
    resp_data = UserInfoBase.model_validate(user)
    return success_resp(message='获取用户信息成功', data=resp_data)


@router.post('/update', response_model=BaseResp)
async def update_user_info(user_info: UserUpdateRequest, user=Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    '''更新用户信息'''
    # 验证 token -> 更新字段 -> 返回
    res = await update_user(db, user.id, user_info)
    resp_data = UserInfoBase.model_validate(res)
    return success_resp(message='更新用户信息成功', data=resp_data)
