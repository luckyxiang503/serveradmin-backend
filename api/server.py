from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List

from core.security import get_current_user
from core.server import install_server
from schemas.server import Server, ServerRecord
from schemas.base import Response200
from crud.server import save_server_info, get_all_server_info, delete_server, chage_server_status

server = APIRouter(tags=["服务安装相关"], dependencies=[Depends(get_current_user)])
# server = APIRouter(tags=["服务安装相关"])


@server.post("/server", summary='服务安装接口')
async def server_install(server: List[Server], bg_tasks: BackgroundTasks):
    if save_server_info(server):
        bg_tasks.add_task(install_server)
        return Response200(msg="保存信息成功，正在安装中。")
    return HTTPException(status_code=400, detail="保存服务信息失败")


@server.post("/reinstall", summary='重新安装接口')
async def server_install(ids: List[int], bg_tasks: BackgroundTasks):
    if chage_server_status(ids):
        bg_tasks.add_task(install_server)
        return Response200(msg="重新安装中。")
    return HTTPException(status_code=400, detail="更改失败")


@server.get("/serverlist", summary='获取服务安装记录', response_model=List[ServerRecord])
async def get_server_install_record():
    return get_all_server_info()


@server.delete("/server", summary='删除记录')
async def delete_server_record(id: int):
    if delete_server(id):
        return Response200(msg="服务记录删除成功")
    else:
        return HTTPException(status_code=400, detail="服务记录删除失败")