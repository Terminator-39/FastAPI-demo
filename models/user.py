import datetime

from sqlalchemy import DateTime, func, String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# todo 定义模型类
class Base(DeclarativeBase):
    create_time: Mapped[datetime.datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now(),
                                                           comment='创建时间')
    update_time: Mapped[datetime.datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now(),
                                                           onupdate=func.now(),
                                                           comment='更新时间')


class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    bio: Mapped[str] = mapped_column(String(255), comment='个人简介', default='这个人很懒，什么也没留下', nullable=True)
    avatar: Mapped[str] = mapped_column(String(255), comment='头像', default='xxx', nullable=True)
    token: Mapped[str] = mapped_column(String(255), comment='用户token', default='xxx', nullable=True)
    tel: Mapped[str] = mapped_column(String(11), comment='手机号', unique=True, nullable=True, default='13892799355')

    def __repr__(self):
        return f'<User(username={self.username}, tel={self.tel})>'


class UserToken(Base):

    """
    用户令牌模型类，用于存储用户的认证令牌信息。
    继承自Base基类，使用SQLAlchemy ORM进行数据库映射。
    """
    __tablename__ = 'user_token'  # 指定数据库表名为'user_token'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 定义id字段，为主键，类型为整数
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, foreign_key='User.id')  # 定义用户ID字段，外键关联User表的id，不可为空
    token: Mapped[str] = mapped_column(String(255), nullable=False)  # 定义令牌字段，最大长度255，不可为空
    expire_time: Mapped[datetime] = mapped_column(DateTime,nullable=True, comment='过期时间')  # 定义过期时间字段
    # 以下是被注释的创建时间字段
    # created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=True,
    #                                              comment='创建时间')  # 创建时间字段，默认值为当前时间，可为空
