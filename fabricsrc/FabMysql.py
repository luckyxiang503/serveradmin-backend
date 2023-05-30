'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/5 17:35
'''
import datetime
import os
import re
import fabric

import CommonFunc
from config import settings, mysqlConf


class fabMysql:
    def __init__(self, d, logger):
        self.msgFile = settings.serverMsgText
        self.env = settings.env
        self.tmplatepath = os.path.join(settings.pkgsdir, d['srvname'], "template")
        self.logger = logger
        # mysql相关路径
        self.datadir = mysqlConf.data_path
        self.logdir = mysqlConf.log_path
        self.d = d

    def mysqlMain(self):
        mode = self.d['mode']
        hosts = self.d['host']
        hostNum = len(hosts)

        # 判断部署方式
        if mode == "mysql-single" and hostNum == 1:
           if self.mysqlSingle(hosts[0]) is not None:
                return 1
        elif mode == "mysql-1M1S" and hostNum == 2:
            if self.mysql1M1S(hosts) is not None:
                return 1
        else:
            self.logger.error("mysql host num is not true.")
            return 1

    def mysqlInstall(self, conn):
        # 检查是否已经安装
        self.logger.info("Check whether mysql is installed...")
        r = conn.run("which mysqld >/dev/null 2>&1 && which mysql >/dev/null 2>&1", warn=True, hide=True)
        if r.exited == 0:
            self.logger.info("mysql server is installed, please check it.")
            return 0

        self.createyumrepos(conn)

        # 安装mysql
        self.logger.info("mysql install starting...")
        try:
            self.logger.info("remove mariadb...")
            conn.run("yum -y remove mariadb mariadb-libs", warn=True, hide=True)
            self.logger.info("install mysql-community, Please wait 5-10 minutes...")
            # conn.run("yum -y install mysql-community-server mysql-community-client --disablerepo=\"*\" --enablerepo=\"local\"", hide=True)
            conn.run("yum -y install mysql-community-server mysql-community-client", hide=True)
        except:
            self.logger.error("mysql install error!")
            return 1
        self.logger.info("mysql install success.")

        # 安装percona
        self.logger.info("install percona-xtrabackup...")
        r = conn.run("rpm -ql percona-xtrabackup", warn=True, hide=True)
        if r.exited == 0:
            return
        try:
            conn.run("yum -y install percona-xtrabackup", hide=True)
        except:
            self.logger.error("percona install error!")
        self.logger.info("percona install success.")

    def mysqlInit(self, conn, serverid, mysqlpwd, rootpwd):
        self.logger.info("mysql init...")
        # 拷贝配置文件启动mysql
        conn.run("id mysql >/dev/null 2>&1 && usermod mysql -s /bin/bash || useradd mysql", warn=True, hide=True)
        conn.run("echo '{}' | passwd --stdin mysql".format(mysqlpwd), warn=True, hide=True)
        conn.run("[ -f /etc/my.cnf ] && mv -f /etc/my.cnf /etc/my.cnf_bak_`date +%F`", warn=True, hide=True)
        txt = CommonFunc.FillTemplate(self.tmplatepath, 'my.cnf', datadir=self.datadir, logdir=self.logdir, serverid=serverid)
        conn.run("echo '{}' > /etc/my.cnf".format(txt))
        # 创建相关目录
        conn.run("mkdir -p {} {} /data/mysql/tmp /var/run/mysqld".format(self.logdir, self.datadir))
        conn.run("chown -R mysql:mysql {} {} /data/mysql/tmp /var/run/mysqld".format(self.logdir, self.datadir))
        try:
            conn.run("systemctl daemon-reload")
            conn.run("systemctl start mysqld")
            conn.run("systemctl enable mysqld", warn=True, hide=True)
        except:
            self.logger.error("mysql server starting error!")
            return 1

        # 获取初始密码
        r = conn.run("grep -Eo \"root@localhost: .*\" {}/mysqld.log | cut -d ' ' -f2".format(self.logdir), hide=True)
        roottmppwd = r.stdout.replace('\n', '')

        # 重置密码
        self.logger.info("reset mysql password.")
        try:
            conn.run("mysql -uroot -p'{}' --connect-expired-password -e \"set password='{}'\"".format(roottmppwd, rootpwd))
            self.logger.info("mysql password reset success.")
        except:
            self.logger.info("reset mysql password error!")
            return 1

    def mysqlSingle(self, host):
        # 系统用户账号密码
        mysqlpwd = CommonFunc.createpasswd()
        # mysql用户账号密码
        rootpwd = CommonFunc.createpasswd()

        self.logger.debug("mysql root passwd: {}".format(rootpwd))
        self.logger.info("=" * 40)
        self.logger.info("[{}] mysql install......".format(host['ip']))
        self.logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:

            # 安装mysql
            rcode = self.mysqlInstall(conn)
            if rcode == 0:
                self.logger.info("mysql is installed.")
            elif rcode == 1:
                self.logger.error("mysql install faild !")
                return 1
            # mysql初始化配置
            serverid = host['ip'].split('.')[-1]
            rcode = self.mysqlInit(conn, serverid, mysqlpwd, rootpwd)
            if rcode != None:
                return 1
            self.logger.info("mysql install success")
            conn.run("echo \"{}\n\" > /root/.cb.cfg".format(rootpwd), warn=True)

            # 创建应用账号
            if self.env == "dev":
                try:
                    admpwd = CommonFunc.createpasswd()
                    apppwd = CommonFunc.createpasswd()
                    conn.run("echo \"grant all on *.* to 'sqladm'@'192.168.%' identified by '{}';\" > /tmp/tmp.sql".format(admpwd))
                    conn.run("echo \"grant select,update,delete,insert on *.* to 'sqlapp'@'192.168.%' identified by '{}';\" >> /tmp/tmp.sql".format(apppwd))
                    conn.run("echo \"flush privileges;\" >> /tmp/tmp.sql")
                    conn.run("mysql -p'{}' -e \"source /tmp/tmp.sql\"".format(rootpwd), hide=True)
                    conn.run("echo \"sqladm {}\nsqlapp {}\n\" >> /root/.cb.cfg".format(admpwd, apppwd), warn=True)
                except Exception as e:
                    self.logger.error("create db user error: {}".format(e))
                    return 1
                finally:
                    conn.run("rm -f /tmp/temp.sql", warn=True, hide=True)
            elif self.env == "pro":
                pass

        # 将服务信息写入文件
        self.logger.info("mysql msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  mysql single  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("server: {}:3306\n".format(host['ip']))
            f.write("系统用户: mysql, 密码: {}\n".format(mysqlpwd))
            f.write("数据库 root密码: {}\n".format(rootpwd))
            if self.env == "dev":
                f.write("数据库 sqladm密码: {}\n".format(admpwd))
                f.write("数据库 sqlapp: {}\n".format(apppwd))

    def mysql1M1S(self, hosts):
        # 系统用户密码
        mysqlpwd = CommonFunc.createpasswd()
        # mysql用户账号密码
        rootpwd = CommonFunc.createpasswd()
        reppwd = CommonFunc.createpasswd()

        # 判断master与slave
        if hosts[0]['role'] == 'slave' and hosts[1]['role'] == 'master':
            hosts.reverse()
        elif hosts[0]['role'] == 'master' and hosts[1]['role'] == 'slave':
            pass
        else:
            self.logger.error("mysql cluster need hava master and slave.")
            return 1

        self.logger.info("=" * 40)
        self.logger.info("[{}] mysql master install......".format(hosts[0]['ip']))
        self.logger.info("=" * 40)
        with fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                               connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10) as conn:

            # 安装mysql
            rcode = self.mysqlInstall(conn)
            if rcode == 0:
                self.logger.info("mysql install stop.")
                return 1
            elif rcode == 1:
                self.logger.error("mysql install faild !")
                return 1
            self.logger.info("mysql install success")

            # mysql初始化配置
            serverid = hosts[0]['ip'].split('.')[-1]
            rcode = self.mysqlInit(conn, serverid, mysqlpwd, rootpwd)
            if rcode != None:
                return 1

            # 创建复制账号，并提取master bin-log日志信息
            self.logger.info("create mysql rep user.")
            try:
                conn.run(
                    "echo \"grant replication slave on *.* to 'rep'@'{}' identified by '{}';\" > /tmp/temp.sql".format(
                        hosts[1]['ip'], reppwd))
                conn.run("echo \"flush privileges;\" >> /tmp/temp.sql")
                conn.run("mysql -p'{}' -e \"source /tmp/temp.sql\"".format(rootpwd), hide=True)
            except:
                self.logger.error("create mysql user error!")
                return 1
            finally:
                conn.run("rm -f /tmp/temp.sql", warn=True, hide=True)
            result = conn.run("mysql -h127.0.0.1 -P3306 -p'{}' -e \"show master status \\G\"".format(rootpwd),
                              warn=True, hide=True)
            s = result.stdout
            binFileg = re.search(r'File: (.*)', s)
            positiong = re.search(r"Position: (.*)", s)
            if binFileg == None or positiong == None:
                self.logger.error("mysql bin file get error!")
                return 1
            binFile = binFileg.group(1)
            position = positiong.group(1)
            self.logger.info("[{}] mysqld install sueccess.".format(hosts[0]['ip']))

        self.logger.info("=" * 40)
        self.logger.info("[{}] mysql slave install......".format(hosts[1]['ip']))
        self.logger.info("=" * 40)
        with fabric.Connection(host=hosts[1]['ip'], port=hosts[1]['port'], user=hosts[1]['user'],
                               connect_kwargs={"password": hosts[1]['password']}, connect_timeout=10) as conn:

            # 安装mysql
            rcode = self.mysqlInstall(conn)
            if rcode == 0:
                self.logger.info("mysql install stop.")
                return 1
            elif rcode == 1:
                self.logger.error("mysql install faild !")
                return 1
            self.logger.info("mysql install success")

            # mysql初始化配置
            serverid = hosts[1]['ip'].split('.')[-1]
            rcode = self.mysqlInit(conn, serverid, mysqlpwd, rootpwd)
            if rcode != None:
                return 1

            # 启用slave
            self.logger.info("slave config and starting.")
            try:
                conn.run(
                    "echo \"CHANGE MASTER TO MASTER_HOST='{}', MASTER_USER='{}', MASTER_PASSWORD='{}', MASTER_LOG_FILE='{}',MASTER_LOG_POS={};\" >/tmp/temp.sql".format(
                        hosts[0]['ip'], "rep", reppwd, binFile, position))
                conn.run("echo \"start slave;\" >> /tmp/temp.sql")
                conn.run("cat /tmp/temp.sql", warn=True)
                conn.run("mysql -h127.0.0.1 -P3306 -p'{}' -e \"source /tmp/temp.sql\"".format(rootpwd), hide=True)
            except:
                self.logger.error("slave start error!")
                return 1
            finally:
                conn.run("rm -f /tmp/temp.sql")
            self.logger.info("[{}] mysqld install success".format(hosts[1]['ip']))

            conn.run("echo \"{}\n\" > /root/.cb.cfg".format(rootpwd), warn=True)

        # 创建应用账号
        with fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                               connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10) as conn:
            if self.env == "dev":
                try:
                    admpwd = CommonFunc.createpasswd()
                    apppwd = CommonFunc.createpasswd()
                    conn.run(
                        "echo \"grant all on *.* to 'sqladm'@'192.168.%' identified by '{}';\" > /tmp/tmp.sql".format(
                            admpwd))
                    conn.run(
                        "echo \"grant select,update,delete,insert on *.* to 'sqlapp'@'192.168.%' identified by '{}';\" >> /tmp/tmp.sql".format(
                            apppwd))
                    conn.run("echo \"flush privileges;\" >> /tmp/tmp.sql")
                    conn.run("mysql -p'{}' -e \"source /tmp/tmp.sql\"".format(rootpwd), hide=True)
                    conn.run("echo \"sqladm {}\nsqlapp {}\n\" >> /root/.cb.cfg".format(admpwd, apppwd), warn=True)
                except Exception as e:
                    self.logger.error("create db user error: {}".format(e))
                    return 1
                finally:
                    conn.run("rm -f /tmp/temp.sql", warn=True, hide=True)
            elif self.env == "pro":
                pass

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
            if self.env == "dev":
                f.write("数据库 sqladm密码: {}\n".format(admpwd))
                f.write("数据库 sqlapp: {}\n".format(apppwd))

    def createyumrepos(self, conn):
        # 安装本地yum源
        self.logger.info("check local repos, Please wait 5-10 minutes...")
        r = conn.run("yum repolist | grep -E \"^local\ +\"", warn=True, hide=True)
        if r.exited == 0:
            self.logger.info("yum local repos is installed.")
            return
        localrepo = "{}/yumrepos".format(settings.pkgsdir)
        self.logger.info("create yum local repos, Please wait 3-5 minutes...")
        remoterepo = "/opt/yumrepos"
        # 拷贝文件到远程主机
        self.logger.info("copy repopkgs to remothost.")
        if not os.path.exists(localrepo):
            self.logger.error("local path {} not exist.".format(localrepo))
            return 1
        conn.run("[ -d {0} ] && rm -rf {0}/*".format(remoterepo), warn=True, hide=True)
        # 遍历目录文件并上传到服务器
        for root, dirs, files in os.walk(localrepo):
            repopath = root.replace(localrepo, remoterepo).replace('\\', '/')
            conn.run("mkdir -p {}".format(repopath))
            for file in files:
                localfile = os.path.join(root, file)
                conn.put(localfile, repopath)
        self.logger.info("create local.repo...")
        repofile = '[local]\nname=local repository\nbaseurl=file://{}\ngpgcheck=0\nenabled=1'.format(remoterepo)
        conn.run("echo '{}' > /etc/yum.repos.d/local.repo".format(repofile))
        self.logger.info("yum makecache...")
        conn.run("yum makecache", hide=True, warn=True)
        self.logger.info("yum local repos create success.")


def check_mysql(conn):
    r = conn.run("which mysqld >/dev/null && rpm -ql mysql-community-server >/dev/null", warn=True, hide=True)
    if r.exited != 0:
        return "未安装"
    r = conn.run("ps -ef | grep mysql | grep -v grep", warn=True, hide=True)
    if r.exited != 0:
        return "已安装，未启动服务"
    else:
        return "服务已启动"