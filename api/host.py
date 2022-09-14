from typing import List
from fastapi import APIRouter, Depends, HTTPException

from crud.host import get_hosts, update_host, delete_host, get_host_by_ip, add_host, get_all_hosts
from schemas.host import Host
from schemas.base import Response200
from core.security import get_current_user


host = APIRouter(tags=["主机相关"], dependencies=[Depends(get_current_user)])
# host = APIRouter(tags=["主机相关"])


@host.get("/hosts", summary="主机信息", response_model=List[Host])
async def host_list(skip: int = 0, limit: int = 10):
    hosts = get_hosts(skip=skip, limit=limit)
    if hosts is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    return hosts


@host.get("/allhost", summary="主机信息", response_model=List[Host])
async def all_hosts():
    hosts = get_all_hosts()
    if hosts is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    return hosts


@host.post("/host", summary='添加主机', response_model=Host)
async def host_create(host: Host):
    if get_host_by_ip(host=host.host):
        raise HTTPException(status_code=400, detail="主机已存在")
    if add_host(host):
        return Response200(msg="主机添加成功")
    else:
        HTTPException(status_code=400, detail="主机添加失败")


@host.put("/host", summary="修改信息")
async def host_update(host: Host):
    if update_host(host=host):
        return Response200(msg="主机更新成功")
    raise HTTPException(status_code=400, detail="主机更新失败")


@host.delete("/host", summary="删除主机")
async def host_delete(host: str):
    if get_host_by_ip(host=host):
        if delete_host(host):
            return Response200(msg="主机删除成功")
    raise HTTPException(status_code=400, detail="主机删除失败")