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


class Category(Base):
    __tablename__ = 'news_category'  # 对应表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment='新闻分类id')
    name: Mapped[str] = mapped_column(String(50), comment='新闻分类名称', unique=True, nullable=False)

    def __repr__(self):
        return f'<Category(id={self.id}, name={self.name})>'


class News(Base):
    __tablename__ = 'news'  # 对应表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment='新闻id')
    title: Mapped[str] = mapped_column(String(100), comment='新闻标题', unique=True, nullable=False)
    abstract: Mapped[str] = mapped_column(String(100), comment='新闻摘要', nullable=False)
    type: Mapped[str] = mapped_column(Integer, comment='新闻分类id', unique=True, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, comment='浏览量')

    def __repr__(self):
        return f'<News(id={self.id}, title={self.title}, views={self.views}, type={self.type})>'
