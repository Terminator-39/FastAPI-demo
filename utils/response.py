from pydantic import BaseModel
from typing import Optional, Any
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

class BaseResp(BaseModel):
    '''响应模型'''
    code: int = 200
    message: str = 'success'
    data: Optional[Any] = None


def success_resp(data: Any = None, message: str = 'success'):
    '''成功响应的函数'''
    content = {
        'code': 200,
        'message': message,
        'data': data
    }
    # return BaseResp(data=data, message=message)
    return JSONResponse(content=jsonable_encoder(content))

def fail_resp(code: int = 500, message: str = 'fail') -> BaseResp:
    '''失败响应的函数'''
    return BaseResp(code=code, message=message)


def not_found_resp(message: str = 'not found') -> BaseResp:
    '''未找到响应的函数'''
    return BaseResp(code=404, message=message)


def bad_request_resp(message: str = 'bad request') -> BaseResp:
    '''错误请求响应的函数'''
    return BaseResp(code=400, message=message)


def internal_server_error_resp(message: str = 'internal server error') -> BaseResp:
    '''服务器内部错误响应的函数'''
    return BaseResp(code=500, message=message)


def unauthorized_resp(message: str = 'unauthorized') -> BaseResp:
    '''未授权响应的函数'''
    return BaseResp(code=401, message=message)


def forbidden_resp(message: str = 'forbidden') -> BaseResp:
    '''禁止响应的函数'''
    return BaseResp(code=403, message=message)
