from typing import List
from fastapi import HTTPException, APIRouter, Depends

from db.crud import get_user_by_name, create_user, get_users
from schemas.user import User
from schemas.base import Response200
from core.security import get_hash_password, get_current_user


user = APIRouter(tags=['用户相关'], dependencies=[Depends(get_current_user)])


@user.get("/user", summary='获取用户信息')
async def get_user_info(userinfo: User = Depends(get_current_user)):
    return Response200(data=userinfo, msg="用户信息查询成功")


@user.get("/users", response_model=List[User], summary='用户列表',)
async def read_users(skip: int = 0, limit: int = 10):
    users = get_users(skip=skip, limit=limit)
    if users is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return users


@user.post("/user", summary='添加用户')
async def add_user(user: User):
    if get_user_by_name(username=user.username):
        raise HTTPException(status_code=400, detail="用户已存在")
    hash_password = get_hash_password(user.password)
    user.password = hash_password
    return create_user(user=user)


@user.put("/user", summary="修改信息")
async def user_update():
    pass


@user.delete("/user", summary="删除用户")
async def user_update():
    pass