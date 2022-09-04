'''
    @Project   : ServerAdmin
    @Author    : xiang
    @CreateTime: 2022/8/29 14:51
'''
from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    is_admin: bool = True
    email: str = None

    class Config:
        orm_mode = True

class User(UserBase):
    password: str

class TokenModel(UserBase):
    token: str
