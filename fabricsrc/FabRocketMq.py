'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/8 17:39
'''
import datetime
import os
import time
import fabric

import FabApp
import SimpleFunc
from config import settings, rocketmqConf


class fabRocketmq:
    def __init__(self):
        self.remotepath = "/opt/pkgs/rocketmq"
        self.rocketmqPath = rocketmqConf.rocketmq_install_path
        self.confpath = rocketmqConf.conf_path
        self.datapath = rocketmqConf.data_path
        self.zippkgname = rocketmqConf.pkg_name
        self.consolepkgname = rocketmqConf.console_pkg_name
        self.consolepath = rocketmqConf.console_install_path
        self.xms = rocketmqConf.xms
        self.xmx = rocketmqConf.xmx
        self.xmn = rocketmqConf.xmn
        self.JAVAHOME = rocketmqConf.JAVAHOME
        self.msgFile = settings.serverMsgText

    def rocketmqMain(self, d, logger):
        self.pkgsdir = settings.pkgsdir
        self.pkgpath = os.path.join(self.pkgsdir, d['srvname'])
        mode = d['mode']
        hosts = d['host']
        hostnum = len(hosts)

        if mode == 'rocketmq-single' and hostnum == 1:
            if self.rocketmqSingle(hosts[0], logger) is not None:
                return 1
        elif mode == 'rocketmq-1M2S' and hostnum > 1:
            if self.rocketmq1M2S(hosts, logger) is not None:
                return 1
        else:
            print("ERROR: rocketMQ mode is not true.")
            return 1

    def rocketmqInstall(self, conn, logger):
        # 判断是否已经安装
        logger.info("Check whether RocketMQ is installed...")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/runserver.sh ]".format(self.rocketmqPath), warn=True, hide=True)
        if r.exited == 0:
            logger.warn("rocketMQ is installed, please check it.")
            return 0

        # 检查java环境
        logger.info("check JAVA_HOME...")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/java ]".format(self.JAVAHOME), hide=True, warn=True)
        if r.exited != 0:
            logger.error("No JAVA_HOME,start install jdk...")
            rcode = FabApp.jdkInstall(conn, logger)
            if rcode != None:
                logger.info("jdk install faild!")
                return 1
        logger.info("java is installed.")

        logger.info("check unzip...")
        r = conn.run("which unzip >/dev/null 2>&1", warn=True, hide=True)
        if r.exited != 0:
            logger.error("unzip is not install,please install it.")
            return 1

        # 拷贝文件到远程主机
        logger.info("copy package to remothost.")
        if not os.path.exists(self.pkgpath):
            logger.error("local path {} not exist.".format(self.pkgpath))
            return 1
        conn.run("[ -d {0} ] && rm -rf {0}/*".format(self.remotepath), warn=True, hide=True)
        # 遍历目录文件并上传到服务器
        logger.info("upload {} files to remote host...".format(self.pkgpath))
        for root, dirs, files in os.walk(self.pkgpath):
            rpath = root.replace(self.pkgpath, self.remotepath).replace('\\', '/')
            conn.run("mkdir -p {}".format(rpath))
            for file in files:
                localfile = os.path.join(root, file)
                # logger.info("put file: {} to {}".format(localfile, rpath))
                conn.put(localfile, rpath)

        # 解压
        pkgname = self.zippkgname.split('.zip')[0]
        logger.info("unzip {}".format(self.zippkgname))
        try:
            with conn.cd(self.remotepath):
                conn.run("unzip {}".format(self.zippkgname), hide=True)
                conn.run("mv {} {}".format(pkgname, self.rocketmqPath))
        except:
            logger.error("unzip {} faild!".format(self.zippkgname))
            return 1

        # 拷贝console包
        logger.info("copy rocketmq-console...")
        conn.run("mkdir -p {}".format(self.consolepath), warn=True)
        try:
            conn.run("mv {}/{} {}".format(self.remotepath, self.consolepkgname, self.consolepath))
        except:
            logger.error("copy rocketmq-console faild!")
            return 1

        # 修改启动内存
        logger.info("chage server jvm...")
        with conn.cd("{}/bin".format(self.rocketmqPath)):
            conn.run("sed -i 's/Xms[0-9]g/Xms{}/g' runserver.sh".format(self.xms), warn=True, hide=True)
            conn.run("sed -i 's/Xmx[0-9]g/Xmx{}/g' runserver.sh".format(self.xmx), warn=True, hide=True)
            conn.run("sed -i 's/Xmn[0-9]g/Xmn{}/g' runserver.sh".format(self.xmn), warn=True, hide=True)
            conn.run("sed -i 's/Xms[0-9]g/Xms{}/g' runbroker.sh".format(self.xms), warn=True, hide=True)
            conn.run("sed -i 's/Xmx[0-9]g/Xmx{}/g' runbroker.sh".format(self.xmx), warn=True, hide=True)
            conn.run("sed -i 's/Xmn[0-9]g/Xmn{}/g' runbroker.sh".format(self.xmn), warn=True, hide=True)


    def rocketmqSingle(self, host, logger):
        logger.info("=" * 40)
        logger.info("[{}] rocketMQ install start......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            rcode = self.rocketmqInstall(conn, logger)
            if rcode == 0:
                logger.info("rocketmq install stop.")
                return 1
            elif rcode == 1:
                logger.error("rocketmq install faild !")
                return 1
            logger.info("rocketmq install success")

            # 创建用户和数据目录
            logger.info("create rocketmq user...")
            conn.run("id -u rocketmq >/dev/null 2>&1 || useradd rocketmq", warn=True, hide=True)
            upasswd = SimpleFunc.createpasswd()
            conn.run("echo '{}' | passwd --stdin rocketmq".format(upasswd), warn=True, hide=True)
            conn.run("[ -d {0} ] || mkdir -p {0}".format(self.datapath), warn=True, hide=True)
            conn.run("chown -R rocketmq:rocketmq {}".format(self.datapath), warn=True, hide=True)
            conn.run("chown -R rocketmq:rocketmq {}".format(self.rocketmqPath), warn=True, hide=True)
            # 拷贝配置文件和启动脚本
            logger.info("copy conf file...")
            conn.run("[ -d {0}/conf/broker.conf ] && mv {0}/conf/broker.conf {0}/conf/broker.conf_bak_`date +%F`".format(self.rocketmqPath), warn=True)
            conn.run("cp -f {}/broker.conf {}/conf/".format(self.remotepath, self.rocketmqPath), warn=True)

            logger.info("copy service file...")
            conn.run("cp -f {}/rocketmq-console.service /lib/systemd/system/".format(self.remotepath), warn=True)
            conn.run("cp -f {}/rocketmq-broker.service /lib/systemd/system/".format(self.remotepath), warn=True)
            conn.run("cp -f {}/rocketmq-namesrv.service /lib/systemd/system/".format(self.remotepath), warn=True)

            # 启动服务
            logger.info("rocketMQ server starting...")
            conn.run("systemctl daemon-reload", hide=True, warn=True)
            try:
                conn.run("systemctl start rocketmq-namesrv", hide=True)
                conn.run("systemctl enable rocketmq-namesrv", hide=True)
                time.sleep(5)
                conn.run("systemctl start rocketmq-broker", hide=True)
                conn.run("systemctl enable rocketmq-broker", hide=True)
                time.sleep(5)
                conn.run("systemctl start rocketmq-console", hide=True)
                conn.run("systemctl enable rocketmq-console", hide=True)
            except:
                logger.error("rocketMQ server start faild!")
                return 1

        # 将相关信息存入文件中
        logger.info("redis msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  RoceketMQ single  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("rocketmq namesrv: {}:9876\n".format(host['ip']))
            f.write("rocketmq broker: {}:10911\n".format(host['ip']))
            f.write("系统用户: rocketmq, 密码: {}\n".format(upasswd))

    def rocketmq1M2S(self, hosts, logger):
        upasswd = SimpleFunc.createpasswd()
        namesrvaddr = ""
        brokeraddr = ""
        dLegerPeer = ""
        m = 0
        for host in hosts:
            namesrvaddr += "{}:9876;".format(host['ip'])
            brokeraddr += "{}:10911;".format(host['ip'])
            dLegerPeer += "n{}-{}:40911;".format(m, host['ip'])
            host['SelfId'] = m
            m += 1

        for host in hosts:
            s = host['ip'].split('.')[-1]
            logger.info("=" * 40)
            logger.info("[{}] rocketMQ install start......".format(host['ip']))
            logger.info("=" * 40)
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                rcode = self.rocketmqInstall(conn, logger)
                if rcode == 0:
                    logger.info("rocketmq install stop.")
                    return 1
                elif rcode == 1:
                    logger.error("rocketmq install faild !")
                    return 1
                logger.info("rocketmq install success")

                # 创建用户和数据目录
                logger.info("create rocketmq user...")
                conn.run("id -u rocketmq >/dev/null 2>&1 || useradd rocketmq", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin rocketmq".format(upasswd), warn=True, hide=True)
                conn.run("[ -d {0} ] || mkdir -p {0}".format(self.datapath), warn=True, hide=True)
                conn.run("chown -R rocketmq:rocketmq {}".format(self.datapath), warn=True, hide=True)
                conn.run("chown -R rocketmq:rocketmq {}".format(self.rocketmqPath), warn=True, hide=True)
                # 拷贝配置文件和启动脚本
                logger.info("copy broker.conf file to {}/conf/...".format(self.rocketmqPath))

                conn.run("cp -f {}/broker.conf {}/brokerA.conf".format(self.remotepath, self.confpath), warn=True)
                conn.run("sed -i 's/\\(namesrvAddr=\\).*/\\1{}/' {}/brokerA.conf".format(namesrvaddr, self.confpath), warn=True)
                conn.run("sed -i 's/\\(dLegerPeers=\\).*/\\1{}/' {}/brokerA.conf".format(dLegerPeer, self.confpath), warn=True)
                conn.run("sed -i 's/\\(dLegerSelfId=\\).*/\\1n{}/' {}/brokerA.conf".format(host['SelfId'], self.confpath), warn=True)

                logger.info("copy service file...")
                conn.run("cp -f {}/rocketmq-console.service /lib/systemd/system/".format(self.remotepath), warn=True)
                conn.run("cp -f {}/rocketmq-broker.service /lib/systemd/system/".format(self.remotepath), warn=True)
                conn.run("cp -f {}/rocketmq-namesrv.service /lib/systemd/system/".format(self.remotepath), warn=True)

                # 启动服务
                logger.info("rocketMQ server starting...")
                conn.run("systemctl daemon-reload", hide=True, warn=True)
                try:
                    conn.run("systemctl start rocketmq-namesrv", hide=True)
                    conn.run("systemctl enable rocketmq-namesrv", hide=True)
                    time.sleep(5)
                    conn.run("systemctl start rocketmq-broker", hide=True)
                    conn.run("systemctl enable rocketmq-broker", hide=True)
                    time.sleep(5)
                    if host['SelfId'] == 0:
                        conn.run("systemctl start rocketmq-console", hide=True)
                        conn.run("systemctl enable rocketmq-console", hide=True)
                except:
                    logger.error("rocketMQ server start faild!")
                    return 1
                time.sleep(5)

        # 将相关信息存入文件中
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  RoceketMQ rocketmq-nM  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("rocketmq namesrv: {}\n".format(namesrvaddr))
            f.write("rocketmq broker: {}\n".format(brokeraddr))
            f.write("系统用户: rocketmq, 密码: {}\n".format(upasswd))


def check_rocketmq(conn):
    r = conn.run("[ -d {0} ] && [ -f {0}/bin/runserver.sh ]".format(rocketmqConf.rocketmq_install_path), warn=True, hide=True)
    if r.exited != 0:
        return "未安装"
    r = conn.run("ps -ef | grep rocketmq | grep -v grep", warn=True, hide=True)
    if r.exited != 0:
        return "已安装，未启动服务"
    else:
        return "服务已启动"
