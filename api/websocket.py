from fastapi import WebSocket, APIRouter
import time
import os

from config import settings

ws = APIRouter(tags=["websocket"])


@ws.websocket('/wslog')
async def send_server_log(websocket: WebSocket):
    await websocket.accept()
    file = await websocket.receive_text()
    logfile = os.path.join(settings.logpath, file)
    if os.path.exists(logfile):
        f = open(logfile, encoding='utf-8')
    else:
        await websocket.send_text("{} not exist!.".format(logfile))
        await websocket.close()
        return False

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