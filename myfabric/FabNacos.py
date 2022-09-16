'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/15 16:47
'''
import logging
import os
import datetime
import time

import fabric
import SimpleFunc, FabSpring


class fabNacos():
    def __init__(self, pkgsdir, d):
        self.pkgsdir = pkgsdir
        hosts = d['host']
        mode = d['mode']
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        self.remotepath = "/opt/pkgs/nacos"
        self.nacospath = "/opt/nacos"
        self.nacospkgname = "nacos-server-2.1.1.tar.gz"
        self.JAVAHOME = "/usr/local/jdk1.8.0_341"
        dirpath = os.path.dirname(__file__)
        self.msgFile = os.path.join(os.path.dirname(dirpath), "ServerMsg.txt")

        self.nacosMain(mode, hosts)

    def nacosMain(self, mode, hosts):
        hostnum = len(hosts)
        if mode == 'nacos-single' and hostnum == 1:
            self.nacosSingle(hosts[0])
        elif mode == 'nacos-cluster' and hostnum >= 3:
            self.nacosCluster(hosts)
        else:
            print("ERROR: nacos mode or host num not true!")
            return 1

    def nacosSingle(self, host):
        # 日志
        logger = SimpleFunc.FileLog("nacos-single", host['ip'])
        logger.info(">>>>>>>>>>>>>>> [{}] nacos install start <<<<<<<<<<<<<<".format(host['ip']))
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 调用安装函数
            rcode = self.nacosInstall(conn, logger)
            if rcode == 0:
                logger.info("nacos install stop.")
                return
            elif rcode == 1:
                logger.error("nacos install faild !")
                return 1
            logger.info("nacos install success")

            # 创建用户
            logger.info("add user nacos...")
            upasswd = SimpleFunc.createpasswd()
            conn.run("id -u nacos >/dev/null 2>&1 || useradd nacos", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin nacos".format(upasswd), warn=True, hide=True)
            conn.run("chown -R nacos:nacos {}".format(self.nacospath))
            # 拷贝文件
            logger.info("copy conf/application.properties...")
            conn.run("[ -f {0}/conf/application.properties ] && mv -f {0}/conf/application.properties {0}/conf/application.properties_`date +%F`".format(self.nacospath), warn=True)
            conn.run("cp {}/application.properties {}/conf/".format(self.remotepath, self.nacospath), warn=True)
            logger.info("copy nacos.service...")
            conn.run("cp -f {}/nacos-standalone.service /lib/systemd/system/nacos.service".format(self.remotepath), warn=True)
            conn.run("sed -i 's#^Environment=.*#Environment=\"JAVA_HOME={}\"#' /lib/systemd/system/nacos.service".format(self.JAVAHOME), warn=True)
            # 启动服务
            logger.info("start nacos server...")
            try:
                conn.run("systemctl daemon-reload")
                conn.run("systemctl start nacos")
                conn.run("systemctl enable nacos")
            except:
                logger.error("nacos server start faild!")
                return 1
            logger.info("start nacos server success.")
            # 检查服务
            self.nacosCheck(conn, logger)

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  nacos standalone  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Model: nacos-single\n")
            f.write("listen: {}:8848\n".format(host['ip']))
            f.write("system user: nacos, password: {}\n".format(upasswd))
            f.write("nacos path: {}\n".format(self.nacospath))


    def nacosCluster(self, hosts):
        l = []
        upasswd = SimpleFunc.createpasswd()
        for host in hosts:
            l.append(host['ip'])
        for host in hosts:
            s = host['ip'].split('.')[-1]
            # 日志
            logger = SimpleFunc.FileLog("nacoscluster-{}".format(s), host['ip'])
            logger.info(">>>>>>>>>>>>>>> [{}] nacos install start <<<<<<<<<<<<<<".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.nacosInstall(conn, logger)
                if rcode == 0:
                    logger.info("nacos install stop.")
                    return
                elif rcode == 1:
                    logger.error("nacos install faild !")
                    return 1
                logger.info("nacos install success")

                # 创建用户
                logger.info("add user nacos...")
                conn.run("id -u nacos >/dev/null 2>&1 || useradd nacos", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin nacos".format(upasswd), warn=True, hide=True)
                conn.run("chown -R nacos:nacos {}".format(self.nacospath))
                # 拷贝文件
                conn.run("[ -f {0}/conf/application.properties ] && mv -f {0}/conf/application.properties {0}/conf/application.properties_`date +%F`".format(self.nacospath), warn=True)
                conn.run("[ -f {0}/conf/cluster.conf ] && rm -f {0}/conf/cluster.conf".format(self.nacospath), warn=True)
                conn.run("cp {}/application.properties {}/conf/".format(self.remotepath, self.nacospath), warn=True)
                for i in l:
                    conn.run("echo \"{}:8848\" >> {}/conf/cluster.conf".format(i, self.nacospath))
                conn.run("cp -f {}/nacos-cluster.service /lib/systemd/system/nacos.service".format(self.remotepath), warn=True)
                conn.run("sed -i 's#^Environment=.*#Environment=\"JAVA_HOME={}\"#' /lib/systemd/system/nacos.service".format(self.JAVAHOME), warn=True)
                # 启动服务
                logger.info("start nacos server...")
                try:
                    conn.run("systemctl daemon-reload")
                    conn.run("systemctl start nacos")
                    conn.run("systemctl enable nacos")
                except:
                    logger.error("nacos server start faild!")
                    return 1
                logger.info("start nacos server success.")
                # 检查服务
                self.nacosCheck(conn, logger)

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  nacos server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Model: nacos-cluster\n")
            f.write("cluster: {}:8848\n".format(":8848;".join(l)))
            f.write("system user: nacos, password: {}\n".format(upasswd))
            f.write("nacos path: {}\n\n".format(self.nacospath))

    def nacosInstall(self, conn, logger):
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

        # 检查是否已经安装
        logger.info(">>>>>>>>>>>>>> check nacos server isn't installed <<<<<<<<<<<<<")
        r = conn.run("[ -d {0} ] && [ -f {0}/target/nacos-server.jar ]".format(self.nacospath), warn=True, hide=True)
        if r.exited == 0:
            logger.warn("nacos server is installed, please check it.")
            return 0
        logger.info("nacos server not install.")

        # 安装nacos
        logger.info("tar {}...".format(self.nacospkgname))
        try:
            with conn.cd(self.remotepath):
                conn.run("tar -xf {} -C /opt".format(self.nacospkgname))
        except:
            logger.info("tar {} faild !".format(self.nacospkgname))
            return 1
        logger.info("nacos install success.")

    def nacosCheck(self, conn, logger, port=8848):
        logger.info(">>>>>>>>>>>>>>> check nacos server <<<<<<<<<<<<<<")
        try:
            logger.info("nacos server process.")
            conn.run("ps -ef | grep nacos | grep -v grep")
        except:
            logger.error("nacos server is not start!")