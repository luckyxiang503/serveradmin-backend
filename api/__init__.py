from fastapi import APIRouter, FastAPI

from .user import user
from .login import login
from .host import host
from db.database import engine, Base

api = APIRouter()

api.include_router(login)
api.include_router(user)
api.include_router(host)

app = FastAPI()
app.include_router(api, prefix='/api')


@app.on_event("startup")
async def init():
    Base.metadata.create_all(bind=engine)
