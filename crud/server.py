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
                hostlist.append(ServerHost(host_id=host_obj.id, role=host.role, appname=host.appname, tag=host.tag))
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


def get_serverinfo_by_id(srvid: int):
    """
    获取server信息
    :return: ServerInstall
    """
    with SessionLocal() as db:
        s = db.query(Server).filter_by(id=srvid).first()
        hosts = []
        for host in s.serverhost:
            hosts.append(server.Host(ip=host.hosts.host,
                                     port=host.hosts.port,
                                     user=host.hosts.user,
                                     password=host.hosts.password,
                                     role=host.role,
                                     appname=host.appname,
                                     tag=host.tag,
                                     sys_version=host.hosts.sys_version))
        srv = server.ServerInstall(id=s.id,
                                 srvname=s.srvname,
                                 mode=s.mode,
                                 host=hosts,
                                 logfile=s.logfile)
        return srv


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
                hosts.append(server.HostBase(ip=host.hosts.host, role=host.role, appname=host.appname, tag=host.tag))
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


def update_server(srvid: int, status: int, logfile: str = None):
    db = SessionLocal()
    try:
        s_obj = db.query(Server).filter(Server.id == srvid).first()
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


def delete_server(srvid: int):
    db = SessionLocal()
    try:
        db.query(Server).filter(Server.id == srvid).delete()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(e)
        return False
    finally:
        db.close()
