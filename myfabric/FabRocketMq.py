'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/8 17:39
'''
import os
import time, datetime
import fabric
import SimpleFunc, FabSpring

class fabRocketmq():
    def __init__(self, pkgsdir, d):
        self.pkgsdir = pkgsdir
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        mode = d['mode']
        hosts = d['host']
        self.remotepath = "/opt/pkgs/rocketmq"
        self.rocketmqPath = "/opt/rocketMQ"
        self.datapath = "/opt/rocketMQ/data"
        self.logpath = "/opt/rocketMQ/logs"
        self.zippkgname = "rocketmq-all-4.9.4-bin-release.zip"
        self.consolepkgname = "rocketmq-console-ng-1.0.1.jar"
        self.consolepath = "/opt/rocketMQ/console"
        self.xms = "1g"
        self.xmx = "1g"
        self.xmn = "512m"
        self.JAVAHOME = "/usr/local/jdk1.8.0_341"
        dirpath = os.path.dirname(__file__)
        self.msgFile = os.path.join(os.path.dirname(dirpath), "ServerMsg.txt")

        self.rocketmqMain(mode, hosts)

    def rocketmqMain(self, mode, hosts):
        hostnum = len(hosts)

        if mode == 'rocketmq-single' and hostnum == 1:
            self.rocketmqSingle(hosts[0])
        elif mode == 'rocketmq-nM' and hostnum > 1:
            self.rocketmqnM(hosts)
        else:
            print("ERROR: rocketMQ mode is not true.")
            return 1

    def rocketmqInstall(self, conn, logger):
        # 判断是否已经安装
        logger.info("check rocketMQ isn't installed.")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/runserver.sh ]".format(self.rocketmqPath), warn=True, hide=True)
        if r.exited == 0:
            logger.warn("rocketMQ is installed, please check it.")
            return 0

        # 检查java环境
        logger.info("check JAVA_HOME...")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/java ]".format(self.JAVAHOME), hide=True, warn=True)
        if r.exited != 0:
            logger.error("not JAVA_HOME,start install jdk...")
            rcode = FabSpring.jdkInstall(self.pkgsdir, conn, logger)
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
        for root, dirs, files in os.walk(self.pkgpath):
            rpath = root.replace(self.pkgpath, self.remotepath).replace('\\', '/')
            conn.run("mkdir -p {}".format(rpath))
            for file in files:
                localfile = os.path.join(root, file)
                logger.info("put file: {} to {}".format(localfile, rpath))
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

        # 修改日志目录
        conn.run("sed -i 's#{}/logs/rocketmqlogs#{}#g' {}/conf/logback_*.xml".format("\${user.home}", self.logpath,self.rocketmqPath), warn=True)

    def checkRocketmq(self, conn, logger, port=(30911, 9876, 8080)):
        logger.info("check rocketMQ server...")
        try:
            conn.run("ps -ef | grep rocketmq | grep -v grep")
            for p in port:
                conn.run("ss -tunlp | grep {}".format(p))
        except:
            logger.error("rocketMQ check fiald!")

    def rocketmqSingle(self, host):
        # 日志定义
        logger = SimpleFunc.FileLog('rocketSingle', host['ip'])

        logger.info(">>>>>>>>>>>>>>>>>>>> [{}] rocketmq start install <<<<<<<<<<<<<<<<<<<".format(host['ip']))
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            rcode = self.rocketmqInstall(conn, logger)
            if rcode == 0:
                logger.info("rocketmq install stop.")
                return
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
            conn.run("[ -d {0} ] || mkdir -p {0}".format(self.logpath), warn=True, hide=True)
            # 拷贝配置文件和启动脚本
            logger.info("copy conf file...")
            conn.run("[ -d {0}/conf/broker.conf ] && mv {0}/conf/broker.conf {0}/conf/broker.conf_bak_`date +%F`".format(self.rocketmqPath), warn=True)
            conn.run("cp -f {}/broker.conf {}/conf/".format(self.remotepath, self.rocketmqPath), warn=True)
            conn.run("chown -R rocketmq:rocketmq {} {} {}".format(self.rocketmqPath, self.logpath, self.datapath))

            logger.info("copy service file...")
            conn.run("cp -f {}/rocketmq-console.service /lib/systemd/system/".format(self.remotepath), warn=True)
            conn.run("cp -f {}/rocketmq-broker.service /lib/systemd/system/".format(self.remotepath), warn=True)
            conn.run("cp -f {}/rocketmq-namesrv.service /lib/systemd/system/".format(self.remotepath), warn=True)

            # 启动服务
            logger.info("rocketMQ server starting...")
            conn.run("systemctl daemon-reload", hide=True, warn=True)
            try:
                conn.run("systemctl start rocketmq-namesrv")
                conn.run("systemctl enable rocketmq-namesrv")
                time.sleep(5)
                conn.run("systemctl start rocketmq-broker")
                conn.run("systemctl enable rocketmq-broker")
                time.sleep(5)
                conn.run("systemctl start rocketmq-console")
                conn.run("systemctl enable rocketmq-console")
            except:
                logger.error("rocketMQ server start faild!")
                return 1

            self.checkRocketmq(conn, logger)
        # 将相关信息存入文件中
        logger.info("redis msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  RoceketMQ server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: single\n")
            f.write("rocketmq namesrv: {}:9876\n".format(host['ip']))
            f.write("rocketmq broker: {}:10911\n".format(host['ip']))
            f.write("System user: rocketmq, password: {}\n".format(upasswd))
            f.write("configpath: {}/conf\n".format(self.rocketmqPath))
            f.write("logpath: {}\n".format(self.logpath))
            f.write("datapath: {}\n\n".format(self.datapath))

    def rocketmqnM(self, hosts):
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
            logger = SimpleFunc.FileLog('rocketmq_{}'.format(s), host['ip'])

            logger.info(">>>>>>>>>>>>>>>>>>>> [{}] rocketmq start install <<<<<<<<<<<<<<<<<<<".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                rcode = self.rocketmqInstall(conn, logger)
                if rcode == 0:
                    logger.info("rocketmq install stop.")
                    return
                elif rcode == 1:
                    logger.error("rocketmq install faild !")
                    return 1
                logger.info("rocketmq install success")

                # 创建用户和数据目录
                logger.info("create rocketmq user...")
                conn.run("id -u rocketmq >/dev/null 2>&1 || useradd rocketmq", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin rocketmq".format(upasswd), warn=True, hide=True)
                conn.run("[ -d {0} ] || mkdir -p {0}".format(self.datapath), warn=True, hide=True)
                conn.run("[ -d {0} ] || mkdir -p {0}".format(self.logpath), warn=True, hide=True)
                # 拷贝配置文件和启动脚本
                logger.info("copy broker.conf file to {}/conf/...".format(self.rocketmqPath))
                conn.run("[ -d {0}/conf/broker.conf ] && mv {0}/conf/broker.conf {0}/conf/broker.conf_bak_`date +%F_%H%M%S`".format(self.rocketmqPath), warn=True)
                conn.run("cp -f {}/broker.conf {}/conf/".format(self.remotepath, self.rocketmqPath), warn=True)
                conn.run("sed -i 's/\\(namesrvAddr=\\).*/\\1{}/' {}/conf/broker.conf".format(namesrvaddr, self.rocketmqPath), warn=True)
                conn.run("sed -i 's/\\(brokerName=\\).*/\\1broker-{}/' {}/conf/broker.conf".format(s, self.rocketmqPath), warn=True)
                conn.run("sed -i 's/\\(dLegerGroup=\\).*/\\1broker-{}/' {}/conf/broker.conf".format(s, self.rocketmqPath), warn=True)
                conn.run("sed -i 's/\\(dLegerPeers=\\).*/\\1{}/' {}/conf/broker.conf".format(dLegerPeer, self.rocketmqPath), warn=True)
                conn.run("sed -i 's/\\(dLegerSelfId=\\).*/\\1n{}/' {}/conf/broker.conf".format(host['SelfId'], self.rocketmqPath), warn=True)
                conn.run("chown -R rocketmq:rocketmq {} {} {}".format(self.rocketmqPath, self.datapath, self.logpath))

                logger.info("copy service file...")
                conn.run("cp -f {}/rocketmq-console.service /lib/systemd/system/".format(self.remotepath), warn=True)
                conn.run("cp -f {}/rocketmq-broker.service /lib/systemd/system/".format(self.remotepath), warn=True)
                conn.run("cp -f {}/rocketmq-namesrv.service /lib/systemd/system/".format(self.remotepath), warn=True)

                # 启动服务
                logger.info("rocketMQ server starting...")
                conn.run("systemctl daemon-reload", hide=True, warn=True)
                try:
                    conn.run("systemctl start rocketmq-namesrv")
                    conn.run("systemctl enable rocketmq-namesrv")
                    time.sleep(5)
                    conn.run("systemctl start rocketmq-broker")
                    conn.run("systemctl enable rocketmq-broker")
                    time.sleep(5)
                    conn.run("systemctl start rocketmq-console")
                    conn.run("systemctl enable rocketmq-console")
                except:
                    logger.error("rocketMQ server start faild!")
                    return 1
                time.sleep(5)

                self.checkRocketmq(conn, logger)
                # 将相关信息存入文件中

        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  RoceketMQ server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: rocketmq-nM\n")
            f.write("rocketmq namesrv: {}\n".format(namesrvaddr))
            f.write("rocketmq broker: {}\n".format(brokeraddr))
            f.write("System user: rocketmq, password: {}\n".format(upasswd))
            f.write("configpath: {}/conf\n".format(self.rocketmqPath))
            f.write("logpath: {}\n".format(self.logpath))
            f.write("datapath: {}\n\n".format(self.datapath))
