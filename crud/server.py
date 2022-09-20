from typing import List
from datetime import datetime

from db.models import Server, ServerHost, Host
from db.database import SessionLocal
from schemas import server


def save_server_info(servers: List[server.Server]):
    """
    添加安装服务信息
    :param servers: 安装服务列表
    :return: bool
    """
    db = SessionLocal()
    try:
        for s in servers:
            s_obj = Server(srvname=s.srvname, mode=s.mode, createtime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           updatetime=None, status=0, logfile='')
            hostlist = []
            for host in s.host:
                host_obj = db.query(Host).filter(Host.host == host.ip).first()
                hostlist.append(ServerHost(host_id=host_obj.id, role=host.role))
            s_obj.serverhost = hostlist
            db.add(s_obj)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(e)
        return False
    finally:
        db.close()


def get_uninstall_server():
    """
    获取所有server信息
    :return: List[ServerInstall]
    """
    serverlist = []
    with SessionLocal() as db:
        servers = db.query(Server).filter_by(status=0).all()
        for s in servers:
            hosts = []
            for host in s.serverhost:
                hosts.append(server.Host(ip=host.hosts.host,
                                         port=host.hosts.port,
                                         user=host.hosts.user,
                                         password=host.hosts.password,
                                         role=host.role))
            d = server.ServerInstall(id=s.id,
                                     srvname=s.srvname,
                                     mode=s.mode,
                                     host=hosts,
                                     logfile=s.logfile)
            serverlist.append(d)
        return serverlist


def get_all_server_info():
    """
    获取未安装服务信息
    :return: List[ServerRecord]
    """
    serverlist = []
    with SessionLocal() as db:
        servers = db.query(Server).order_by(Server.createtime.desc()).all()
        for s in servers:
            hosts = []
            for host in s.serverhost:
                hosts.append(server.HostBase(ip=host.hosts.host, role=host.role))
            d = server.ServerRecord(id=s.id,
                                    srvname=s.srvname,
                                    mode=s.mode,
                                    host=hosts,
                                    createtime=str(s.createtime),
                                    updatetime=str(s.updatetime),
                                    status=s.status,
                                    logfile=s.logfile)
            serverlist.append(d)
        return serverlist


def update_server(id: int, status: int, logfile: str = None):
    db = SessionLocal()
    try:
        s_obj = db.query(Server).filter(Server.id == id).first()
        s_obj.updatetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s_obj.status = status
        if logfile:
            s_obj.logfile = logfile
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(e)
        return False
    finally:
        db.close()


def delete_server(id: int):
    """
    删除主机
    :param db: 数据库连接
    :param host: 主机名
    :return: bool
    """
    db = SessionLocal()
    try:
        db.query(ServerHost).filter(ServerHost.server_id == id).delete()
        db.query(Server).filter(Server.id == id).delete()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(e)
        return False
    finally:
        db.close()


def chage_server_status(ids: List[int]):
    """
    将server状态重置为未安装
    :param ids: id 列表
    :return: bool
    """
    db = SessionLocal()
    try:
        for id in ids:
            s_obj = db.query(Server).filter(Server.id == id).first()
            s_obj.updatetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            s_obj.status = 0
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(e)
        return False
    finally:
        db.close()