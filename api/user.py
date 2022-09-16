from typing import List
from fastapi import HTTPException, APIRouter, Depends

from crud.user import get_user_by_name, create_user, get_users, delete_user, update_user, get_all_users
from schemas.user import User, UserBase
from schemas.base import Response200
from core.security import get_hash_password, get_current_user


user = APIRouter(tags=['用户相关'], dependencies=[Depends(get_current_user)])
# user = APIRouter(tags=['用户相关'])


@user.get("/user", summary='用户信息', response_model=UserBase)
async def get_user_info(username: str):
    if db_user := get_user_by_name(username):
        return db_user
    raise HTTPException(status_code=404, detail="用户不存在")


@user.get("/users", response_model=List[UserBase], summary='用户列表',)
async def read_users(skip: int = 0, limit: int = 10):
    users = get_users(skip=skip, limit=limit)
    if users is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return users


@user.get("/alluser", response_model=List[UserBase], summary='所有用户',)
async def get_all_user():
    users = get_all_users()
    if users is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return users


@user.post("/user", summary='添加用户', response_model=UserBase)
async def add_user(user: User):
    if get_user_by_name(username=user.username):
        raise HTTPException(status_code=400, detail="用户已存在")
    hash_password = get_hash_password(user.password)
    user.password = hash_password
    return create_user(user=user)


@user.put("/user", summary="修改信息")
async def user_update(user: User):
    hash_password = get_hash_password(user.password)
    user.password = hash_password
    if update_user(user=user):
        return Response200(msg="用户更新成功")
    raise HTTPException(status_code=400, detail="用户更新失败")


@user.delete("/user", summary="删除用户")
async def user_delete(username: str):
    if get_user_by_name(username=username):
        if delete_user(username):
            return Response200(msg="用户删除成功")
    raise HTTPException(status_code=400, detail="用户删除失败")