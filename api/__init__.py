import time
from fastapi import APIRouter, FastAPI
import logging

from .user import user
from .login import login
from .host import host
from .server import server
from .websocket import ws

from schemas.user import User
from core.security import get_hash_password
from db.database import engine, Base
from crud.user import get_user_by_name, create_user


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")
api = APIRouter()

api.include_router(login)
api.include_router(user)
api.include_router(host)
api.include_router(server)

app = FastAPI()
app.include_router(api, prefix='/api')
app.include_router(ws, prefix='/websocket')


@app.on_event("startup")
async def init():
    while True:
        try:
            Base.metadata.create_all(bind=engine)
            if not get_user_by_name("admin"):
                hash_password = get_hash_password("admin")
                user = User(username="admin", password=hash_password)
                create_user(user=user)
            break
        except Exception as e:
            logging.error(e)
            time.sleep(10)

