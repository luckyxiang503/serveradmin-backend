import logging

from fastapi import WebSocket, APIRouter
import time
import os

from config import settings

ws = APIRouter(tags=["websocket"])


@ws.websocket('/wslog')
async def send_server_log(websocket: WebSocket):
    await websocket.accept()
    # 连接建立后前端发送日志文件名称或者关闭连接信息
    text = await websocket.receive_text()
    logfile = os.path.join(settings.logpath, text)
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
            line = f.readline().replace('\n', '')
            if not line:
                time.sleep(1)
                f.seek(where)
                data = ''
            else:
                data = line
            await websocket.send_text(data)
            r = await websocket.receive_text()
            if r == 'close':
                await websocket.close()
                break
        except:
            await websocket.close()
            break

    f.close()
