from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime

from db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(20), index=True, comment="用户名")
    password = Column(String(255), comment="用户密码")
    is_admin = Column(Boolean, comment="是否为管理员")
    email = Column(String(30), comment="邮箱")

    def __repr__(self):
        return "{{'user': {}, 'is_admin': {}, 'email': {}}}".format(self.username, self.is_admin, self.email)