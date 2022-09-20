from datetime import datetime

from config import settings
from myfabric import *
from crud.server import get_uninstall_server, update_server


def install_server():
    # 获取未安装服务信息
    servers = get_uninstall_server()

    if len(servers) == 0:
        return False

    for srv in servers:
        if srv.logfile == '':
            logfile = "id{}{}{}.log".format(srv.id, srv.srvname, datetime.now().strftime("%Y%m%d%H%M%S"))
            srv.logfile = logfile
            update_server(srv.id, status=1, logfile=logfile)
        else:
            update_server(srv.id, status=1)
        # 调用安装函数
        if fabric_install(srv):
            update_server(srv.id, status=2)
        else:
            update_server(srv.id, status=3)


def fabric_install(srv):
    pkgsdir = settings.pkgsdir
    s = srv.dict()
    try:
        if srv.srvname == 'base':
            rcode = BaseTools.base(pkgsdir, s)
        elif srv.srvname == "redis":
            rcode = FabRedis.fabRedis(pkgsdir, s)
        elif srv.srvname == "mysql":
            rcode = FabMysql.fabMysql(pkgsdir, s)
        elif srv.srvname == 'rocketmq':
            rcode = FabRocketMq.fabRocketmq(pkgsdir, s)
        elif srv.srvname == 'jdk':
            rcode = FabSpring.jdkMain(pkgsdir, s)
        elif srv.srvname == 'app':
            rcode = FabSpring.appinit(pkgsdir, s)
        elif srv.srvname == 'nginx':
            rcode = FabTengine.fabTengine(pkgsdir, s)
        elif srv.srvname == 'mongodb':
            rcode = FabMongodb.fabMongodb(pkgsdir, s)
        elif srv.srvname == 'nacos':
            rcode = FabNacos.fabNacos(pkgsdir, s)
        elif srv.srvname == 'zookeeper':
            rcode = FabZookeeper.fabZookeeper(pkgsdir, s)
        elif srv.srvname == 'fdfs':
            rcode = FabZookeeper.fabZookeeper(pkgsdir, s)
        else:
            raise "srvname not true"
    except:
        return False

    if rcode == None:
        return True
    else:
        return False
