from db import models
from db.database import SessionLocal
from schemas.user import User, UserBase


def get_user_by_name(username: str):
    """
    通过用户名获取用户信息
    :param db: 数据库连接
    :param username: 用户名
    :return: 用户信息
    """
    with SessionLocal() as db:
        db_user = db.query(models.User).filter(models.User.username == username).first()
    return db_user


def create_user(user: User):
    """
    添加用户
    :param db: 数据库连接
    :param user: 用户信息
    :return: 数据库存入信息
    """
    db_user = models.User(**user.dict())
    with SessionLocal() as db:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    return db_user


def update_user(user: User):
    """
    更新信息
    :param db: 数据库连接
    :param user: 用户信息
    :return: 数据库存入信息
    """
    with SessionLocal() as db:
        data = db.query(models.User).filter(models.User.username == user.username).first()
        if data:
            for k, v in user:
                setattr(data, k, v)
            db.add(data)
            db.commit()
            return True


def get_users(skip: int = 0, limit: int = 100):
    """
    批量获取用户信息
    :param db:
    :param skip: 起始点
    :param limit: 数据条数
    :return: 用户列表
    """
    with SessionLocal() as db:
        users = db.query(models.User).offset(skip).limit(limit).all()
    return users

def get_all_users():
    """
    批量获取用户信息
    :param db:
    :return: 用户列表
    """
    with SessionLocal() as db:
        users = db.query(models.User).all()
    return users

def delete_user(username: str):
    """
    删除用户
    :param db: 数据库连接
    :param username: 用户名
    :return: 用户信息
    """
    with SessionLocal() as db:
        db.query(models.User).filter(models.User.username == username).delete()
        db.commit()
        return True