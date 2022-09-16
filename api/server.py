from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List

from core.server import install_server
from core.security import get_current_user
from schemas.server import Server
from schemas.base import Response200


server = APIRouter(tags=["服务安装相关"], dependencies=[Depends(get_current_user)])


@server.post("/server", summary='服务安装接口')
async def server_install(server: List[Server], bg_tasks: BackgroundTasks):
    bg_tasks.add_task(install_server, server)
    return Response200(msg="开始安装")