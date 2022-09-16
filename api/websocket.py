from fastapi import WebSocket, APIRouter
import time

from config import settings

ws = APIRouter(tags=["websocket"])


@ws.websocket('/wslog')
async def send_server_log(websocket: WebSocket):
    await websocket.accept()
    file = settings.logfile
    f = open(file)

    while True:
        where = f.tell()
        line = f.readline().replace('\n', '')
        if not line:
            time.sleep(1)
            f.seek(where)
            data = ''
        else:
            data = line
        await websocket.send_text(data)
        r = await websocket.receive_text()
        if r == "close":
            await websocket.close()
            break
