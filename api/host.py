from typing import List
from fastapi import APIRouter, Depends, HTTPException

from crud.host import get_hosts, update_host, delete_host, get_host_by_ip, add_host
from schemas.host import Host, HostBase
from schemas.base import Response200


#host = APIRouter(tags=["主机相关"], dependencies=[Depends(get_current_user)])
host = APIRouter(tags=["主机相关"])


@host.get("/hosts", summary="主机信息", response_model=List[HostBase])
async def host_list(skip: int = 0, limit: int = 10):
    hosts = get_hosts(skip=skip, limit=limit)
    if hosts is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    return hosts


@host.post("/host", summary='添加主机', response_model=HostBase)
async def host_create(host: Host):
    if get_host_by_ip(host=host.host):
        raise HTTPException(status_code=400, detail="主机已存在")
    return add_host(host)


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