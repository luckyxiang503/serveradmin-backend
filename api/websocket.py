import json

from fastapi import WebSocket, APIRouter
import time
import os

from crud.server import get_serverinfo_by_id
from config import settings

ws = APIRouter(tags=["websocket"])


@ws.websocket('/wslog')
async def send_server_log(websocket: WebSocket):
    await websocket.accept()
    # 连接建立后前端发送日志文件名称或者关闭连接信息
    text = await websocket.receive_text()
    data = json.loads(text)
    if data['logfile'] == "":
        srvdb = get_serverinfo_by_id(data['id'])
        file = srvdb.logfile
        if file == "":
            print("file not exist")
            await websocket.send_text("logfile is null!!!")
            await websocket.close()
    else:
        file = data['logfile']
    logfile = os.path.join(settings.logpath, file)
    # 判断日志文件是否存在
    if os.path.exists(logfile):
        f = open(logfile, encoding='utf-8')
    else:
        await websocket.send_text("logfile not exist !!!")
        await websocket.close()
        return
    # 循环发送日志文件内容
    while True:
        try:
            where = f.tell()
            line = f.readline()
            if not line:
                time.sleep(1)
                f.seek(where)
                data = ''
            else:
                data = line.replace('\n', '')
            await websocket.send_text(data)
            r = await websocket.receive_text()
            if r == 'close':
                await websocket.close()
                break
        except:
            await websocket.close()
            break

    f.close()
