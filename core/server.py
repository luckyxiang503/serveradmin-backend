from datetime import datetime
import fabric

from config import settings
from myfabric import *
from crud.server import update_server
from schemas.server import ServerInstall
from schemas.host import Host


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
    s = srv.dict()
    try:
        if srv.srvname == 'base':
            rcode = BaseTools.base(s, logger)
        elif srv.srvname == "redis":
            redis = FabRedis.fabRedis()
            rcode = redis.redisMain(s, logger)
        elif srv.srvname == "mysql":
            mysql = FabMysql.fabMysql()
            rcode = mysql.mysqlMain(s, logger)
        elif srv.srvname == 'rocketmq':
            rocketmq = FabRocketMq.fabRocketmq()
            rcode = rocketmq.rocketmqMain(s, logger)
        elif srv.srvname == 'jdk':
            rcode = FabSpring.jdkMain(s, logger)
        elif srv.srvname == 'spring':
            rcode = FabSpring.springinit(s, logger)
        elif srv.srvname == 'nginx':
            nginx = FabTengine.fabTengine()
            rcode = nginx.tengineMain(s, logger)
        elif srv.srvname == 'mongodb':
            mongod = FabMongodb.fabMongodb()
            rcode = mongod.mongodbMain(s, logger)
        elif srv.srvname == 'nacos':
            nacos = FabNacos.fabNacos()
            rcode = nacos.nacosMain(s, logger)
        elif srv.srvname == 'zookeeper':
            zookeeper = FabZookeeper.fabZookeeper()
            rcode = zookeeper.zookeeperMain(s, logger)
        else:
            raise "srvname not true"
    except Exception as e:
        logger.error(e)
        return False
    finally:
        logger.info("=" * 40)
        logger.info("{} install finished.".format(srv.srvname))
        logger.info("=" * 40)

    if rcode is None:
        return True
    else:
        return False


def delete_logfile(file):
    if file == "":
        return
    logfile = os.path.join(settings.logpath, file)
    if os.path.exists(logfile):
        os.remove(logfile)


def host_srv_check(host: Host):
    result = []
    with fabric.Connection(host=host.host, port=host.port, user=host.user,
                           connect_kwargs={"password": host.password}, connect_timeout=5) as conn:
        try:
            conn.run("echo \"test\"", hide=True)
        except:
            return False

        # 系统基础工具
        r = BaseTools.check_base_tools(conn)
        result.append("Base: {}".format(r))
        # mongodb
        r = FabMongodb.check_mongodb(conn)
        result.append("Mongodb: {}".format(r))
        # mysql
        r = FabMysql.check_mysql(conn)
        result.append("Mysql: {}".format(r))
        # redis
        r = FabRedis.check_redis(conn)
        result.append("Redis: {}".format(r))
        # nginx
        r = FabTengine.check_nginx(conn)
        result.append("Nginx: {}".format(r))
        # spring
        r = FabSpring.check_spring(conn)
        result.append("Spring: {}".format(r))
        # rocketmq
        r = FabRocketMq.check_rocketmq(conn)
        result.append("RocketMQ: {}".format(r))
        # rocketmq
        r = FabZookeeper.check_zookeeper(conn)
        result.append("Zookeeper: {}".format(r))
        # nacos
        r = FabNacos.check_nacos(conn)
        result.append("Nacos: {}".format(r))

        return result
