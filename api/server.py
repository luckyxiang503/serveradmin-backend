from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List

from core.security import get_current_user
from core.server import install_server
from schemas.server import Server, ServerRecord
from schemas.base import Response200
from crud.server import save_server_info, get_all_server_info, delete_server, get_serverinfo_by_id

server = APIRouter(tags=["服务安装相关"], dependencies=[Depends(get_current_user)])
# server = APIRouter(tags=["服务安装相关"])


@server.post("/srvsaveinfo", summary='服务信息保存')
async def save_server_to_db(server: List[Server]):
    if save_server_info(server):
        return Response200(msg="保存信息成功")
    return HTTPException(status_code=400, detail="保存服务信息失败")


@server.post("/server", summary='安装接口')
async def server_install(srvid: int, bg_tasks: BackgroundTasks):
    srv = get_serverinfo_by_id(srvid)
    if srv is None:
        return HTTPException(status_code=400, detail="服务信息未找到")
    bg_tasks.add_task(install_server, srv)
    return Response200(msg="开始安装")


@server.get("/serverlist", summary='获取服务安装记录', response_model=List[ServerRecord])
async def get_server_install_record():
    return get_all_server_info()


@server.delete("/server", summary='删除记录')
async def delete_server_record(ids: List[int]):
    if delete_server(ids):
        return Response200(msg="服务记录删除成功")
    else:
        return HTTPException(status_code=400, detail="服务记录删除失败")