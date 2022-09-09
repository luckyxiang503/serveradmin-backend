from db import models
from db.database import SessionLocal
from schemas.host import Host


def get_host_by_ip(host: str):
    """
    :param db: 数据库连接
    :param host: ip
    :return: 主机信息
    """
    with SessionLocal() as db:
        data = db.query(models.Host).filter(models.Host.host == host).first()
    return data


def get_hosts(skip: int = 0, limit: int = 100):
    """
    批量获取用户信息
    :param db:
    :param skip: 起始点
    :param limit: 数据条数
    :return: 主机列表
    """
    with SessionLocal() as db:
        hosts = db.query(models.Host).order_by(models.Host.host).offset(skip).limit(limit).all()
    return hosts


def add_host(host: Host):
    """
    添加主机
    :param db: 数据库连接
    :param user: 主机信息
    :return: 数据库存入信息
    """
    db_host = models.Host(**host.dict())
    with SessionLocal() as db:
        db.add(db_host)
        db.commit()
        db.refresh(db_host)
    return db_host


def update_host(host: Host):
    """
    更新信息
    :param db: 数据库连接
    :param user: 主机信息
    :return: 数据库存入信息
    """
    with SessionLocal() as db:
        data = db.query(models.Host).filter(models.Host.host == host.host).first()
        if data:
            for k, v in host:
                setattr(data, k, v)
            db.add(data)
            db.commit()
            return True


def delete_host(host: str):
    """
    删除主机
    :param db: 数据库连接
    :param host: 主机名
    :return: bool
    """
    with SessionLocal() as db:
        db.query(models.Host).filter(models.Host.host == host).delete()
        db.commit()
        return True