from datetime import datetime
import fabric

from config import settings
from fabricsrc import *
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
        if s['srvname'] == 'base':
            rcode = BaseTools.base(s, logger)
        elif s['srvname'] == "redis":
            redis = FabRedis.fabRedis(s, logger)
            rcode = redis.redisMain()
        elif s['srvname'] == "mysql":
            mysql = FabMysql.fabMysql(s, logger)
            rcode = mysql.mysqlMain()
        elif s['srvname'] == 'rocketmq':
            rocketmq = FabRocketMq.fabRocketmq()
            rcode = rocketmq.rocketmqMain(s, logger)
        elif s['srvname'] == 'jdk':
            rcode = FabApp.jdkMain(s, logger)
        elif s['srvname'] == 'app':
            rcode = FabApp.appinit(s, logger)
        elif s['srvname'] == 'consul':
            rcode = FabConsul.consulMain(s, logger)
        elif s['srvname'] == 'nginx':
            nginx = FabTengine.fabTengine(s, logger)
            rcode = nginx.tengineMain()
        elif s['srvname'] == 'mongodb':
            mongod = FabMongodb.fabMongodb()
            rcode = mongod.mongodbMain(s, logger)
        elif s['srvname'] == 'nacos':
            nacos = FabNacos.fabNacos()
            rcode = nacos.nacosMain(s, logger)
        elif s['srvname'] == 'zookeeper':
            zookeeper = FabZookeeper.fabZookeeper()
            rcode = zookeeper.zookeeperMain(s, logger)
        else:
            raise "srvname not ture,please check it!"
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
        r = FabApp.check_spring(conn)
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
