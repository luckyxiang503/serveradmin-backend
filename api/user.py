'''
    @Project   : ServerAdmin
    @Author    : xiang
    @CreateTime: 2022/8/29 15:22
'''
from typing import List, Union
from fastapi import HTTPException, APIRouter, Form, Header

from core.user import get_user_by_name, create_user, get_users
from core.security import verify_password, create_access_token
from core.schemas import User

user = APIRouter(tags=['用户相关'])


@user.post("/login", summary='登录')
async def user_login(username: str = Form(...), password: str = Form(...)):
    db_user = get_user_by_name(username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户名错误!")
    if verify_password(password, db_user.password):
        token = create_access_token(data={"sub": db_user.username})
        return {'username': db_user.username, 'token': token}
    else:
        raise HTTPException(status_code=404, detail="密码错误!")


@user.post("/create", summary='添加用户')
def add_user(user: User):
    db_user = get_user_by_name(username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户已存在")
    return create_user(user=user)


@user.get("/info", summary='获取用户信息')
def get_user_info(username: str):
    db_user = get_user_by_name(username=username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@user.get("/users", response_model=List[User], summary='用户列表',)
def read_users(skip: int = 0, limit: int = 10):
    users = get_users(skip=skip, limit=limit)
    if users is None:
        raise HTTPException(status_code=404, detail="Users not found")
    return users

@user.get("/items/")
async def read_items(accept: Union[str, None] = Header(default=None)):
    return {"accept": accept}