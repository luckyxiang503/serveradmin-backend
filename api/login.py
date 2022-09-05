from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from db.crud import get_user_by_name
from core.security import verify_password, create_access_token
from schemas.base import ResponseToken

login = APIRouter(tags=["认证相关"])


@login.post("/login", summary='登录')
async def user_login(form_data: OAuth2PasswordRequestForm = Depends()):
    db_user = get_user_by_name(username=form_data.username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if verify_password(form_data.password, db_user.password):
        token = create_access_token(data={"sub": db_user.username})
        return ResponseToken(data={"token": f"bearer {token}"}, access_token=token)
    else:
        raise HTTPException(status_code=400, detail="密码错误")


@login.put("/logout", summary="注销")
async def user_logout():
    pass