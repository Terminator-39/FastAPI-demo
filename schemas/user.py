from typing import Optional

from pydantic import BaseModel, Field
from pydantic.v1 import ConfigDict


class UserRequest(BaseModel):
    username: str
    password: str


class UserInfoBase(BaseModel):
    username: Optional[str] = Field(None, description='用户名', max_length=50)
    bio: Optional[str] = Field(None, description='个人简介', max_length=100)
    avatar: Optional[str] = Field(None, description='头像', max_length=255)


class UserInfoResp(UserInfoBase):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class UserAuthResp(BaseModel):
    token: str
    user_info: UserInfoResp = Field(..., alias="userInfo")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class LoginInfoBase(BaseModel):
    '''登录信息响应基类'''
    username: Optional[str] = Field(None, description='用户名', max_length=50)
    bio: Optional[str] = Field(None, description='个人简介', max_length=100)
    avatar: Optional[str] = Field(None, description='头像', max_length=255)

class LoginInfoResp(LoginInfoBase):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class UserInfoBase(BaseModel):
    username: Optional[str] = Field(None, description='用户名', max_length=50)
    bio: Optional[str] = Field(None, description='个人简介', max_length=100)
    avatar: Optional[str] = Field(None, description='头像', max_length=255)
    tel: Optional[str] = Field(None, description='手机号', max_length=11)


class UserUpdateRequest(BaseModel):
    '''更新信息模型类'''
    username: Optional[str] = Field(None, description='用户名', max_length=50)
    bio: Optional[str] = Field(None, description='个人简介', max_length=100)
    avatar: Optional[str] = Field(None, description='头像', max_length=255)
    tel: Optional[str] = Field(None, description='手机号', max_length=11)