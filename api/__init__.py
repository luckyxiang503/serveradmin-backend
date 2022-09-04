'''
    @Project   : ServerAdmin
    @Author    : xiang
    @CreateTime: 2022/8/29 15:22
'''
from fastapi import APIRouter, FastAPI

from .user import user
from db.database import engine, Base

api = APIRouter()

api.include_router(user, prefix='/user')

app = FastAPI()
app.include_router(api, prefix='/api')


@app.on_event("startup")
async def init():
    Base.metadata.create_all(bind=engine)
