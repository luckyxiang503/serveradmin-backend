import time

from config import settings
from src import FabRedis, FabMysql, FabRocketMq, FabSpring, FabTengine, FabMongodb, FabNacos, BaseTools, FabZookeeper


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


def read_server_log():
    file = settings.logfile
    f = open(file)
    while True:
        where = f.tell()
        line = f.readline()
        if not line:
            time.sleep(1)
            f.seek(where)
        else:
            print(line)