import os
import secrets

basedir = os.path.abspath(os.path.dirname(__file__))


class settings:
    # 数据库相关
    dbhost = '192.168.10.253'
    dbuser = 'serveradmin'
    dbpasswd = 'Admin@123'
    dbname = 'ServerAdmin'
    # dbuser = 'srvadmin'
    # dbpasswd = 'Admin@123'
    # dbhost = '127.0.0.1'
    # dbname = 'srvadmin'

    # 安全相关
    ALGORITHM = "HS256"
    SECRET_KEY = secrets.token_urlsafe(32)

    # 服务安装相关
    pkgsdir = r"E:\python\fabric\pkgs"
    logpath = os.path.join(basedir, 'logs')
    logfile = os.path.join(logpath, 'server.log')
    serverMsgText = os.path.join(logpath, "ServerMsg.txt")


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


class mysqlConf:
    datapath = "/data/mysql"


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


class nginxConf:
    nginx_version = "tengine-2.3.3"
    luajit_version = "LuaJIT-2.0.4"
    nginx_install_path = "/usr/local/nginx"


class springConf:
    jdkPkgName = "jdk-8u341-linux-x64.tar.gz"
    jdkVersion = "jdk1.8.0_341"
    tomcatpkg = "apache-tomcat-8.5.51.tar.gz"
    pinpointpkg = "pinpoint-agent-2.3.3.tar.gz"
    group = "hcapp"
    user = "spring"


class rocketmqConf:
    rocketmq_install_path = "/opt/rocketMQ"
    data_path = "/opt/rocketMQ/data"
    log_path = "/opt/rocketMQ/logs"
    pkg_name = "rocketmq-all-4.9.4-bin-release.zip"
    console_pkg_name = "rocketmq-console-ng-1.0.1.jar"
    console_install_path = "/opt/rocketMQ/console"
    # 启动内存
    xms = "1g"
    xmx = "1g"
    xmn = "512m"
    JAVAHOME = "/usr/local/jdk1.8.0_341"


class zookeeperConf:
    pkg_name = "zookeeper-3.4.14.tar.gz"
    zk_install_path = "/opt/zookeeper"


class nacosConf:
    nacos_install_path = "/opt/nacos"
    nacos_pkg_name = "nacos-server-2.1.1.tar.gz"
    JAVAHOME = "/usr/local/jdk1.8.0_341"
