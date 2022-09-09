from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime

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
