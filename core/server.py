
from config import settings
from myfabric import *


def install_server(server):
    pkgsdir = settings.pkgsdir
    if len(server) == 0:
        return False
    for srv in server:
        s = srv.dict()
        if s['srvname'] == 'base':
            BaseTools.base(pkgsdir, s)
        elif s['srvname'] == "redis":
            FabRedis.fabRedis(pkgsdir, s)
        elif s['srvname'] == "mysql":
            FabMysql.fabMysql(pkgsdir, s)
        elif s['srvname'] == 'rocketmq':
            FabRocketMq.fabRocketmq(pkgsdir, s)
        elif s['srvname'] == 'jdk':
            FabSpring.jdkMain(pkgsdir, s)
        elif s['srvname'] == 'app':
            FabSpring.appinit(pkgsdir, s)
        elif s['srvname'] == 'nginx':
            FabTengine.fabTengine(pkgsdir, s)
        elif s['srvname'] == 'mongodb':
            FabMongodb.fabMongodb(pkgsdir, s)
        elif s['srvname'] == 'nacos':
            FabNacos.fabNacos(pkgsdir, s)
        elif s['srvname'] == 'zookeeper':
            FabZookeeper.fabZookeeper(pkgsdir, s)
        elif s['srvname'] == 'fdfs':
            FabZookeeper.fabZookeeper(pkgsdir, s)
        else:
            return False