'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/5 17:35
'''
import datetime
import os
import re
import time

import fabric

import SimpleFunc
from config import settings, mysqlConf


class fabMysql():
    def __init__(self):
        self.remotepath = "/opt/pkgs/mysql"
        self.perconapath = "/opt/pkgs/mysql/percona"
        self.datapath = mysqlConf.datapath
        self.msgFile = settings.serverMsgText

    def mysqlMain(self, d, logger):
        pkgsdir = settings.pkgsdir
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        mode = d['mode']
        hosts = d['host']
        hostNum = len(hosts)

        # 判断部署方式
        if mode == "mysql-single" and hostNum == 1:
           if self.mysqlSingle(hosts[0], logger) is not None:
                return 1
        elif mode == "mysql-1M1S" and hostNum == 2:
            if self.mysql1M1S(hosts, logger) is not None:
                return 1
        else:
            logger.error("mysql host num is not true.")
            return 1

    def mysqlInstall(self, conn, logger):
        # 检查是否已经安装
        logger.info("Check whether mysql is installed...")
        r = conn.run("which mysqld >/dev/null 2>&1 && which mysql >/dev/null 2>&1", warn=True, hide=True)
        if r.exited == 0:
            logger.info("mysql server is installed, please check it.")
            return 0
        else:
            logger.info("mysql server not install.")

        # 拷贝文件到远程主机
        logger.info("copy package to remothost...")
        if not os.path.exists(self.pkgpath):
            logger.error("local path {} not exist.".format(self.pkgpath))
            return 1
        conn.run("[ -d {0} ] && rm -rf {0}/*".format(self.remotepath), warn=True, hide=True)
        # 遍历目录文件并上传到服务器
        for root, dirs, files in os.walk(self.pkgpath):
            rpath = root.replace(self.pkgpath, self.remotepath).replace('\\', '/')
            conn.run("mkdir -p {}".format(rpath))
            for file in files:
                localfile = os.path.join(root, file)
                logger.info("put file: {} to {}".format(localfile, rpath))
                conn.put(localfile, rpath)

        # 安装mysql
        logger.info("mysql install starting...")
        try:
            logger.info("remove mariadb...")
            conn.run("yum -y remove mariadb mariadb-libs", warn=True, hide=True)
            conn.run("rpm -qa | grep 'mysql-community' | xargs rpm -e", warn=True, hide=True)
            with conn.cd(self.remotepath):
                logger.info("install mysql-community, Please wait 5-10 minutes...")
                conn.run("rpm -ih *.rpm", hide=True)
        except:
            logger.error("mysql install error!")
            return 1
        logger.info("mysql install success.")

        # 安装percona
        logger.info("percona install starting...")
        try:
            with conn.cd(self.perconapath):
                logger.info("install percona...")
                conn.run("rpm -ih *.rpm", hide=True)
        except:
            logger.error("percona install error!")
            return 1
        logger.info("percona install success.")

    def mysqlInit(self, conn, serverid, logger, rootpwd, mysqlpwd):
        # 拷贝配置文件启动mysql
        conn.run("id mysql >/dev/null 2>&1 && usermod mysql -s /bin/bash || useradd mysql", warn=True, hide=True)
        conn.run("echo '{}' | passwd --stdin mysql".format(mysqlpwd), warn=True, hide=True)
        logger.info("copy my.cnf and starting mysql server...")
        conn.run("[ -f /etc/my.cnf ] && mv -f /etc/my.cnf /etc/my.cnf_bak_`date +%F`", warn=True, hide=True)
        conn.run("cp {}/my.cnf /etc/".format(self.remotepath))
        conn.run("sed -i 's/server-id=.*/server-id={}/g' /etc/my.cnf".format(serverid))
        conn.run("mkdir -p {0}/data {0}/log {0}/tmp".format(self.datapath))
        conn.run("mkdir -p  /var/run/mysqld /var/lib/mysql".format(self.datapath))
        conn.run("chown -R mysql:mysql {}".format(self.datapath))
        conn.run("chown -R mysql:mysql /var/run/mysqld /var/lib/mysql".format(self.datapath))
        try:
            conn.run("systemctl daemon-reload")
            conn.run("systemctl start mysqld")
            conn.run("systemctl enable mysqld", warn=True, hide=True)
        except:
            logger.error("mysql server starting error!")
            return 1

        # 重置密码
        updateMysqlPwd = "flush privileges;\ngrant all on *.* to 'root'@'localhost' identified by '{}' with grant option;\nflush privileges;".format(
            rootpwd)
        logger.info("reset mysql password.")
        try:
            conn.run("echo \"{}\" > /tmp/temp.sql".format(updateMysqlPwd))
            conn.run("cat /tmp/temp.sql", warn=True)
            conn.run("mysql -uroot -e \"source /tmp/temp.sql\"")
        except:
            logger.info("reset mysql password error!")
            return 1
        r = conn.run("mysql -uroot -p'{}' -e \"show databases;\"".format(rootpwd), warn=True, hide=True)
        if r.exited != 0:
            logger.error("mysql password reset faild!")
            return 1
        logger.info("mysql password reset success.")

        # 关闭无密码登录
        try:
            conn.run("sed -i 's/skip-grant-tables/#skip-grant-tables/g' /etc/my.cnf")
            conn.run("systemctl restart mysqld", hide=True)
        except:
            logger.error("mysql restart error!")
            return 1
        logger.info("mysql restart success.")

    def mysqlSingle(self, host, logger):
        # 系统用户账号密码
        mysqlpwd = SimpleFunc.createpasswd()
        # mysql用户账号密码
        rootpwd = SimpleFunc.createpasswd()
        logger.debug("mysql root passwd: {}".format(rootpwd))

        logger.info("=" * 40)
        logger.info("[{}] mysql install......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:

            # 安装mysql
            rcode = self.mysqlInstall(conn, logger)
            if rcode == 0:
                logger.info("mysql is installed.")
                return 1
            elif rcode == 1:
                logger.error("mysql install faild !")
                return 1
            # mysql初始化配置
            serverid = host['ip'].split('.')[-1]
            rcode = self.mysqlInit(conn, serverid, logger, rootpwd, mysqlpwd)
            if rcode != None:
                return 1
            logger.info("mysql install success")

        # 将服务信息写入文件
        logger.info("mysql msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  mysql single  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("server: {}:3306\n".format(host['ip']))
            f.write("系统用户: mysql, 密码: {}\n".format(mysqlpwd))
            f.write("数据库 root密码: {}\n".format(rootpwd))

    def mysql1M1S(self, hosts, logger):
        # 系统用户密码
        mysqlpwd = SimpleFunc.createpasswd()
        # mysql用户账号密码
        rootpwd = SimpleFunc.createpasswd()
        reppwd = SimpleFunc.createpasswd()

        # 判断master与slave
        if hosts[0]['role'] == 'slave' and hosts[1]['role'] == 'master':
            hosts.reverse()
        elif hosts[0]['role'] == 'master' and hosts[1]['role'] == 'slave':
            pass
        else:
            logger.error("mysql cluster need hava master and slave.")
            return 1

        logger.info("=" * 40)
        logger.info("[{}] mysql master install......".format(hosts[0]['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                               connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10) as conn:

            # 安装mysql
            rcode = self.mysqlInstall(conn, logger)
            if rcode == 0:
                logger.info("mysql install stop.")
                return 1
            elif rcode == 1:
                logger.error("mysql install faild !")
                return 1
            logger.info("mysql install success")

            # mysql初始化配置
            serverid = hosts[0]['ip'].split('.')[-1]
            rcode = self.mysqlInit(conn, serverid, logger, rootpwd, mysqlpwd)
            if rcode != None:
                return 1

            # 创建复制账号，并提取master bin-log日志信息
            logger.info("create mysql rep user.")
            try:
                conn.run(
                    "echo \"grant replication slave on *.* to 'rep'@'{}' identified by '{}';\" > /tmp/temp.sql".format(
                        hosts[1]['ip'], reppwd))
                conn.run("echo \"flush privileges;\" >> /tmp/temp.sql")
                conn.run("mysql -h127.0.0.1 -P3306 -p'{}' -e \"source /tmp/temp.sql\"".format(rootpwd), hide=True)
            except:
                logger.error("create mysql user error!")
                return 1
            finally:
                conn.run("rm -f /tmp/temp.sql", warn=True, hide=True)
            result = conn.run("mysql -h127.0.0.1 -P3306 -p'{}' -e \"show master status \\G\"".format(rootpwd),
                              warn=True, hide=True)
            s = result.stdout
            binFileg = re.search(r'File: (.*)', s)
            positiong = re.search(r"Position: (.*)", s)
            if binFileg == None or positiong == None:
                logger.error("mysql bin file get error!")
                return 1
            binFile = binFileg.group(1)
            position = positiong.group(1)
            logger.info("[{}] mysqld install sueccess.".format(hosts[0]['ip']))

        logger.info("=" * 40)
        logger.info("[{}] mysql master install......".format(hosts[1]['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=hosts[1]['ip'], port=hosts[1]['port'], user=hosts[1]['user'],
                               connect_kwargs={"password": hosts[1]['password']}, connect_timeout=10) as conn:

            # 安装mysql
            rcode = self.mysqlInstall(conn, logger)
            if rcode == 0:
                logger.info("mysql install stop.")
                return 1
            elif rcode == 1:
                logger.error("mysql install faild !")
                return 1
            logger.info("mysql install success")

            # mysql初始化配置
            serverid = hosts[1]['ip'].split('.')[-1]
            rcode = self.mysqlInit(conn, serverid, logger, rootpwd, mysqlpwd)
            if rcode != None:
                return 1

            # 启用slave
            logger.info("slave config and starting.")
            try:
                conn.run(
                    "echo \"CHANGE MASTER TO MASTER_HOST='{}', MASTER_USER='{}', MASTER_PASSWORD='{}', MASTER_LOG_FILE='{}',MASTER_LOG_POS={};\" >/tmp/temp.sql".format(
                        hosts[0]['ip'], "rep", reppwd, binFile, position))
                conn.run("echo \"start slave;\" >> /tmp/temp.sql")
                conn.run("mysql -h127.0.0.1 -P3306 -p'{}' -e \"source /tmp/temp.sql\"".format(rootpwd), hide=True)
            except:
                logger.error("slave start error!")
                return 1
            finally:
                conn.run("rm -f /tmp/temp.sql")
            logger.info("[{}] mysqld install success".format(hosts[1]['ip']))

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Mysql 1M1S  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("master: {}:3306\n".format(hosts[0]['ip']))
            f.write("slave: {}:3306\n".format(hosts[1]['ip']))
            f.write("系统用户: mysql, 密码: {}\n".format(mysqlpwd))
            f.write("数据库 root账号密码: {}\n".format(rootpwd))
            f.write("数据库 rep账号密码：{}\n".format(reppwd))


def check_mysql(conn):
    r = conn.run("which mysqld >/dev/null && rpm -ql mysql-community-server >/dev/null", warn=True, hide=True)
    if r.exited != 0:
        return "未安装"
    r = conn.run("ps -ef | grep mysql | grep -v grep", warn=True, hide=True)
    if r.exited != 0:
        return "已安装，未启动服务"
    else:
        return "服务已启动"