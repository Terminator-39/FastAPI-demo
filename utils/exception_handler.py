# 导入必要的库和模块
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from utils.response import BaseResp

# 创建日志记录器
logger = logging.getLogger(__name__)


def _error_response(status_code: int, message: str, data: Any = None, headers=None):
    """
    通用的错误响应函数
    Args:
        status_code: HTTP状态码
        message: 错误信息
        data: 响应数据
        headers: 响应头
    Returns:
        JSONResponse: 格式化的错误响应
    """
    body = BaseResp(code=status_code, message=message, data=data)
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body.model_dump()),
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP异常处理器
    Args:
        request: FastAPI请求对象
        exc: HTTP异常对象
    Returns:
        JSONResponse: 格式化的错误响应
    """
    message = exc.detail if isinstance(exc.detail, str) else '请求处理失败'
    data = None if isinstance(exc.detail, str) else exc.detail
    return _error_response(exc.status_code, message, data, exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    请求参数校验异常处理器
    Args:
        request: FastAPI请求对象
        exc: 请求参数校验异常对象
    Returns:
        JSONResponse: 格式化的错误响应
    """
    errors = [
        {'loc': error.get('loc'), 'msg': error.get('msg'), 'type': error.get('type')}
        for error in exc.errors()
    ]
    return _error_response(422, '请求参数校验失败', errors)


async def integrity_exception_handler(request: Request, exc: IntegrityError):
    """
    数据完整性约束异常处理器
    Args:
        request: FastAPI请求对象
        exc: 数据完整性约束异常对象
    Returns:
        JSONResponse: 格式化的错误响应
    """
    logger.warning('数据完整性约束异常: %s', exc)
    return _error_response(409, '数据完整性约束冲突')


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    数据库异常处理器
    Args:
        request: FastAPI请求对象
        exc: 数据库异常对象
    Returns:
        JSONResponse: 格式化的错误响应
    """
    logger.exception('数据库操作异常')
    return _error_response(500, '数据库操作失败')


async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    未处理异常处理器
    Args:
        request: FastAPI请求对象
        exc: 通用异常对象
    Returns:
        JSONResponse: 格式化的错误响应
    """
    logger.exception('未处理的服务器异常')
    return _error_response(500, '服务器内部错误')


def register_exception_handlers(app: FastAPI):
    """
    注册异常处理器
    Args:
        app: FastAPI应用实例
    Returns:
        None
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
