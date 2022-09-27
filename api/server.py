from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List

from core.security import get_current_user
from core.server import install_server, delete_logfile, host_srv_check
from schemas.server import Server, ServerRecord, ServerCheck
from schemas.host import Host
from schemas.base import Response200
from crud.server import save_server_info, get_all_server_info, delete_server, get_serverinfo_by_id
from crud.host import get_host_by_ip

# server = APIRouter(tags=["服务安装相关"], dependencies=[Depends(get_current_user)])
server = APIRouter(tags=["服务安装相关"])


@server.post("/srvsaveinfo", summary='服务信息保存')
async def save_server_to_db(server: List[Server]):
    if save_server_info(server):
        return Response200(msg="保存信息成功")
    raise HTTPException(status_code=400, detail="保存服务信息失败")


@server.post("/server", summary='安装接口')
async def server_install(srvid: int, bg_tasks: BackgroundTasks):
    srv = get_serverinfo_by_id(srvid)
    if srv is None or len(srv.host) == 0:
        raise HTTPException(status_code=400, detail="服务信息出错")
    bg_tasks.add_task(install_server, srv)
    return Response200(msg="开始安装")


@server.get("/serverlist", summary='获取服务安装记录', response_model=List[ServerRecord])
async def get_server_install_record():
    return get_all_server_info()


@server.delete("/server", summary='删除记录')
async def delete_server_record(ids: List[int]):
    for id in ids:
        srv = get_serverinfo_by_id(id)
        if srv is None:
            continue
        if not delete_server(ids):
            raise HTTPException(status_code=400, detail="srvname: {}, id: {} 删除失败".format(srv.srvname, srv.id))
        delete_logfile(srv.logfile)
    return Response200(msg="服务记录删除成功")


@server.post("/servercheck", summary="主机服务检查")
async def server_check(srvcheckinfo: ServerCheck):
    host: Host = get_host_by_ip(srvcheckinfo.host)
    if host is None:
        return HTTPException(status_code=404, detail="主机不存在")
    if data := host_srv_check(host):
        srvcheckinfo.status = '正常'
        srvcheckinfo.result = data
    else:
        srvcheckinfo.status = "连接失败"
    return srvcheckinfo