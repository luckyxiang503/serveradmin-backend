from fastapi import APIRouter


host = APIRouter(tags=["主机相关"])


@host.get("/host", summary="主机信息")
async def user_info():
    pass

@host.post("/host", summary="新增主机")
async def user_update():
    pass

@host.put("/host", summary="修改信息")
async def user_update():
    pass

@host.delete("/host", summary="删除主机")
async def user_update():
    pass