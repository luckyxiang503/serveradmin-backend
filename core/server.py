from datetime import datetime
from myfabric import SimpleFunc

from config import settings
from myfabric import *
from crud.server import update_server
from schemas.server import ServerInstall


def install_server(srv: ServerInstall):
    if not os.path.exists(settings.logpath):
        os.mkdir(settings.logpath)
    if srv.logfile == '':
        logfile = "{}id{}_{}.log".format(srv.srvname, srv.id, datetime.now().strftime("%Y%m%d%H%M%S"))
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
    logger = SimpleFunc.FileLog(name="{}_{}".format(srv.srvname, srv.id), logfile=srv.logfile)
    pkgsdir = settings.pkgsdir
    s = srv.dict()
    try:
        if srv.srvname == 'base':
            BaseTools.base(pkgsdir, s, logger)
        elif srv.srvname == "redis":
            FabRedis.fabRedis(pkgsdir, s, logger)
        elif srv.srvname == "mysql":
            FabMysql.fabMysql(pkgsdir, s, logger)
        elif srv.srvname == 'rocketmq':
            FabRocketMq.fabRocketmq(pkgsdir, s, logger)
        elif srv.srvname == 'jdk':
            FabSpring.jdkMain(pkgsdir, s, logger)
        elif srv.srvname == 'app':
            FabSpring.appinit(pkgsdir, s, logger)
        elif srv.srvname == 'nginx':
            FabTengine.fabTengine(pkgsdir, s, logger)
        elif srv.srvname == 'mongodb':
            FabMongodb.fabMongodb(pkgsdir, s, logger)
        elif srv.srvname == 'nacos':
            FabNacos.fabNacos(pkgsdir, s, logger)
        elif srv.srvname == 'zookeeper':
            FabZookeeper.fabZookeeper(pkgsdir, s, logger)
        elif srv.srvname == 'fdfs':
            FabFastdfs.fabFastdfs(pkgsdir, s, logger)
        else:
            raise "srvname not true"
    except Exception as e:
        logger.error("ERROR: {}".format(e))
        return False
    logger.info("=" * 40)
    logger.info("{} install finished.".format(srv.srvname))
    logger.info("=" * 40)
    return True

