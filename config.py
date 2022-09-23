import os
from pydantic import BaseSettings
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))

class Settings(BaseSettings):
    # 数据库相关
    dbhost = '192.168.10.253'
    dbuser = 'serveradmin'
    dbpasswd = 'Admin@123'
    dbname = 'ServerAdmin'
    # dbuser = 'srvadmin'
    # dbpasswd = 'Admin@123'
    # dbhost = '127.0.0.1'
    # dbname = 'srvadmin'

    # 安全相关
    ALGORITHM = "HS256"
    SECRET_KEY = secrets.token_urlsafe(32)

    # 服务安装相关
    pkgsdir = r"E:\python\fabric\pkgs"

    logpath = os.path.join(basedir, 'logs')
    logfile = os.path.join(logpath, 'server.log')

    serverMsgText = os.path.join(logpath, "ServerMsg.txt")


settings = Settings()