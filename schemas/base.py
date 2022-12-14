from pydantic import BaseModel, Field
from enum import Enum
from typing import Any


class CodeEnum(int, Enum):
    """业务状态码"""
    SUCCESS = 200
    FAIL = 400


class ResponseBasic(BaseModel):
    code: CodeEnum = Field(default=CodeEnum.SUCCESS, description="业务状态码 200 是成功, 400 是失败")
    data: Any = Field(default=None, description="数据结果")
    msg: str = Field(default="请求成功", description="提示")


class Response200(ResponseBasic):
    pass


class ResponseToken(BaseModel):
    token: str
    token_type: str = Field(default="bearer")


class Response400(ResponseBasic):
    code: CodeEnum = CodeEnum.FAIL
    msg: str = "请求失败"