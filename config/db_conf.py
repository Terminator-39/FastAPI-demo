'''
    todo 配置数据库会话&手动建表
'''
import datetime
from sqlalchemy import DateTime, func, String, Text, Index, ForeignKey, Integer
from contextlib import asynccontextmanager
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi import FastAPI

ADMIN_DATABASE_URL = 'mysql+aiomysql://fastapi_app_demo:fanshou98chuizi.@localhost:3306/fastapi_app_demo?charset=utf8'
# 数据库引擎
async_engine = create_async_engine(
    ADMIN_DATABASE_URL,
    echo=True,  # todo 可选：输出日志
    pool_size=10,  # todo 允许连接池中保持的持久连接数
    max_overflow=20,  # todo 允许额外创建的连接数
)


class Base(DeclarativeBase):
    create_time: Mapped[datetime.datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now(),
                                                           comment='创建时间')
    update_time: Mapped[datetime.datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now(),
                                                           onupdate=func.now(),
                                                           comment='更新时间')


class User(Base):
    '''用户表'''
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment='用户id')
    username: Mapped[str] = mapped_column(String(255), comment='用户名称')
    password: Mapped[str] = mapped_column(String(255), comment='用户密码')
    tel: Mapped[str] = mapped_column(String(255), comment='联系方式')
    bio: Mapped[str] = mapped_column(String(255), comment='个人简介')
    avatar: Mapped[str] = mapped_column(String(255), comment='头像')
    token: Mapped[str] = mapped_column(String(255), comment='用户token')


class UserToken(Base):
    '''用户token表'''
    __tablename__ = 'user_token'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment='用户tokenid')
    user_id: Mapped[int] = mapped_column(Integer, comment='用户id', foreign_key='User.id')
    token: Mapped[str] = mapped_column(String(255), comment='用户token')
    expire_time: Mapped[datetime.datetime] = mapped_column(DateTime, comment='过期时间')
    # create_at: Mapped[datetime.datetime] = mapped_column(DateTime, comment='创建时间')


class News(Base):
    '''新闻表'''
    __tablename__ = 'news'
    # 创建索引：提升查询速度
    # __table_args__ = (
    #     Index('idx_news_idx', 'type'),  # 高频查询场景
    #     Index('idx_create_time', 'create_time')
    # )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment='新闻id')
    title: Mapped[str] = mapped_column(String(255), comment='新闻标题')
    abstract: Mapped[str] = mapped_column(String(150), comment='新闻摘要')
    content: Mapped[str] = mapped_column(Text, comment='新闻内容')
    author: Mapped[str] = mapped_column(String(255), comment='作者')
    views: Mapped[int] = mapped_column(Integer, default=0, comment='浏览量')
    type: Mapped[str] = mapped_column(String(255),
                                      # ForeignKey('news_category.id'),
                                      comment='新闻分类')  # ForeignKey 外键约束


class NewsCategory(Base):
    '''新闻分类表'''
    __tablename__ = 'news_category'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment='新闻分类id')
    name: Mapped[str] = mapped_column(String(50), comment='新闻分类标题')


# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,  # 绑定数据库引擎
    class_=AsyncSession,  # 指定会话类
    expire_on_commit=False  # 提交后会话不过期，不用重新查询数据库
)


# todo 获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session  # 正常则返回数据库会话
            await session.commit()  # 进行提交事务
        except Exception as e:
            await session.rollback()  # 错误则回滚数据库会话
            raise e  # 抛出异常
        finally:
            await session.close()  # 关闭会话


# todo 3. 建表：定义建表函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await async_engine.dispose()
