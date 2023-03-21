import os
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))


class settings:
    # 数据库相关
    dbhost = '192.168.10.100:13306'
    dbuser = 'root'
    dbpasswd = 'Hc_2023!'
    dbname = 'hcsadb'

    # 安全相关
    ALGORITHM = "HS256"
    SECRET_KEY = secrets.token_urlsafe(32)

    # 本地文件目录
    pkgsdir = os.path.join(basedir, "files")
    # 安装机器包上传目录
    remotedir = "/opt/pkgs"
    # 日志
    logpath = os.path.join(basedir, 'logs')
    logfile = os.path.join(logpath, 'server.log')
    serverMsgText = os.path.join(logpath, "ServerMsg.txt")

    # 开发环境: dev   生产环境：pro  其他：无
    env = ""


class mysqlConf:
    log_path = "/data/mysql/log"
    data_path = "/var/lib/mysql"


class redisConf:
    redis_version = "redis-6.2.7"
    redis_install_path = "/usr/local/{}".format(redis_version)
    # 单机配置
    data_path = "/opt/redis/data"
    log_path = "/var/log/redis"
    conf_path = "/etc/redis"
    #集群配置
    clu_data_path = "/opt/redis-cluster"
    clu_log_path = "/var/log/redis-cluster"
    clu_conf_path = "/etc/redis-cluster"


class mongoConf:
    mongo_pkg_name = "mongodb-linux-x86_64-rhel70-5.0.10"
    mongoShell_pkg_name = "mongodb-shell-linux-x86_64-rhel70-5.0.10"
    install_path = "/usr/local/mongodb"
    # 单机路径
    data_path = "/opt/mongodb"
    log_path = "/var/log/mongodb"
    conf_path = "/etc/mongodb"
    # 集群路径
    clu_data_path = "/opt/mongodb-cluster"
    clu_conf_path = "/etc/mongodb-cluster"
    clu_log_path = "/var/log/mongod-cluster"


class nginxConf:
    nginx_version = "tengine-2.3.3"
    luajit_version = "LuaJIT-2.0.4"
    nginx_install_path = "/usr/local/nginx"


class springConf:
    jdkPkgName = "jdk-8u341-linux-x64.tar.gz"
    jdkVersion = "jdk1.8.0_341"
    tomcatpkg = "apache-tomcat-8.5.51.tar.gz"
    pinpointpkg = "pinpoint-agent-2.3.3.tar.gz"


class rocketmqConf:
    rocketmq_install_path = "/opt/rocketMQ"
    conf_path = "/opt/rocketMQ/conf/dledger"
    data_path = "/home/rocketmq/rmqstore"
    pkg_name = "rocketmq-all-4.9.4-bin-release.zip"
    console_pkg_name = "rocketmq-console-ng-1.0.1.jar"
    console_install_path = "/opt/rocketMQ/console"
    # 启动内存
    xms = "2g"
    xmx = "2g"
    xmn = "1g"
    JAVAHOME = "/usr/local/jdk1.8.0_341"


class zookeeperConf:
    pkg_name = "zookeeper-3.4.14.tar.gz"
    zk_install_path = "/opt/zookeeper"
    JAVAHOME = "/usr/local/jdk1.8.0_341"


class nacosConf:
    nacos_install_path = "/opt/nacos"
    nacos_pkg_name = "nacos-server-2.1.1.tar.gz"
    JAVAHOME = "/usr/local/jdk1.8.0_341"


class consulConf:
    consul_version = "1.13.3"
    consul_template_version = "0.29.5"