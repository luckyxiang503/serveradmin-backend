# -*- coding:utf-8 -*-
# @Author: zhangxiang
# @Time: 2022/9/4 13:36
from pydantic import BaseSettings
import secrets


class Settings(BaseSettings):
    # 数据库相关
    # dbhost = '192.168.10.253'
    # dbuser = 'serveradmin'
    # dbpasswd = 'Admin@123'
    # dbname = 'ServerAdmin'
    dbuser = 'srvadmin'
    dbpasswd = 'Admin@123'
    dbhost = '127.0.0.1'
    dbname = 'srvadmin'

    # 安全相关
    ALGORITHM = "HS256"
    SECRET_KEY = secrets.token_urlsafe(32)


settings = Settings()