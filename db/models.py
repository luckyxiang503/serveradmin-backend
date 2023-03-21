from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(20), unique=True, index=True, comment="用户名")
    password = Column(String(255), comment="用户密码")
    is_admin = Column(Boolean, comment="是否为管理员")
    email = Column(String(30), comment="邮箱")


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    host = Column(String(20), unique=True, index=True, comment="ip")
    port = Column(Integer(), comment="端口")
    user = Column(String(20), comment="用户")
    password = Column(String(100), comment="密码")
    sys_version = Column(String(10), comment="系统版本")


class Server(Base):
    __tablename__ = "server"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    srvname = Column(String(20), comment="服务名")
    mode = Column(String(20), comment="安装模式")
    createtime = Column(DateTime, comment="创建时间")
    updatetime = Column(DateTime, comment="更新时间")
    status = Column(Integer, comment="状态, 0: 未安装,1: 安装中,2: 安装成功,3: 安装失败")
    logfile = Column(String(255), comment="安装日志文件")

    serverhost = relationship('ServerHost', backref="server")


class ServerHost(Base):
    __tablename__ = "serverhost"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    host_id = Column(Integer, ForeignKey('hosts.id', ondelete='CASCADE'))
    server_id = Column(Integer, ForeignKey('server.id', ondelete='CASCADE'))
    role = Column(String(20), comment="主机角色")
    appname = Column(String(20), comment="app账号")
    tag = Column(String(20), comment="consul组名")

    hosts = relationship('Host', uselist=False, backref="serverhost")

