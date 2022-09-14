from fastapi import APIRouter, FastAPI

from .user import user
from .login import login
from .host import host
from .server import server
from .websocket import ws
from db.database import engine, Base

api = APIRouter()

api.include_router(login)
api.include_router(user)
api.include_router(host)
api.include_router(server)
api.include_router(ws)

app = FastAPI()
app.include_router(api, prefix='/api')


@app.on_event("startup")
async def init():
    Base.metadata.create_all(bind=engine)
