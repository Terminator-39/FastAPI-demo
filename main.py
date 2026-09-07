# from urllib.request import Request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import news, user,deepseek
from config.db_conf import lifespan
from utils.exception_handler import register_exception_handlers

app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)
origins = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # allow_origins = origins
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


# 挂载路由/注册路由
app.include_router(news.router)
app.include_router(user.router)
app.include_router(deepseek.router)

