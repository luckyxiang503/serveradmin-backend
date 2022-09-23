'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/22 16:55
'''
import datetime
import os
import fabric

import FabSpring
import SimpleFunc
from config import settings


class fabZookeeper():
    def __init__(self, pkgsdir, d, logger):
        self.pkgsdir = pkgsdir
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        self.remotepath = '/opt/pkgs/zookeeper'
        mode = d['mode']
        hosts = d['host']
        self.zkversion = "zookeeper-3.4.14"
        self.pkgname = "zookeeper-3.4.14.tar.gz"
        self.zkpath = "/opt/zookeeper"
        self.msgFile = settings.serverMsgText

        self.zookeeperMain(mode, hosts, logger)

    def zookeeperMain(self, mode, hosts, logger):
        hostnum = len(hosts)

        if mode == 'zookeeper-single' and hostnum == 1:
            self.zookeeperSingle(hosts[0], logger)
        elif mode == 'zookeeper-cluster' and hostnum >= 3:
            self.zookeeperCluster(hosts, logger)
        else:
            print("ERROR: rocketMQ mode is not true.")
            return 1

    def zookeeperSingle(self, host, logger):
        upasswd = SimpleFunc.createpasswd()

        logger.info(">>>>>>>>>>>>>>> [{}] zookeeper install start <<<<<<<<<<<<<<".format(host['ip']))
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 调用安装函数
            rcode = self.zookeeperInstall(conn, logger)
            if rcode == 0:
                logger.info("zookeeper install stop.")
                return
            elif rcode == 1:
                logger.error("zookeeper install faild !")
                return 1
            logger.info("zookeeper install success")

            # 创建数据和日志目录
            logger.info("create data and log dir...")
            conn.run("mkdir -p {0}/data".format(self.zkpath), hide=True, warn=True)
            # 创建用户
            logger.info("add user zookeeper...")
            conn.run("id -u zookeeper >/dev/null 2>&1 || useradd zookeeper", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin zookeeper".format(upasswd), warn=True, hide=True)
            conn.run("chown -R zookeeper:zookeeper {}".format(self.zkpath))
            logger.info("copy conf file...")
            conn.run("mv -f {0}/conf/zoo.cfg {0}/conf/zoo.cfg_bak_`date +%F`".format(self.zkpath), warn=True, hide=True)
            conn.run("cp -f {}/zoo.cfg {}/conf/".format(self.remotepath, self.zkpath), warn=True, hide=True)
            logger.info("copy service file...")
            conn.run("cp -f {}/zookeeper.service /lib/systemd/system/".format(self.remotepath), warn=True)

            # 启动服务
            logger.info("start zookeeper server...")
            try:
                conn.run("systemctl daemon-reload")
                conn.run("systemctl start zookeeper")
                conn.run("systemctl enable zookeeper")
            except:
                logger.error("zookeeper server start faild!")
                return 1
            logger.info("start zookeeper server success.")
            # 检查服务
            # self.zookeeperCheck(conn, logger)

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  zookeeper server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Model: zookeeper-single\n")
            f.write("listen: {}:2181\n".format(host['ip']))
            f.write("system user: zookeeper, password: {}\n".format(upasswd))
            f.write("zookeeper path: {}\n\n".format(self.zkpath))


    def zookeeperCluster(self, hosts, logger):
        upasswd = SimpleFunc.createpasswd()
        m = 1
        n = []
        lst = []
        for host in hosts:
            n.append(":2181".format(host['ip']))
            k = {
                'ip': host['ip'],
                'id': m
            }
            lst.append(k)
            m += 1
        # m为myid, 重置写入文件中
        m = 1

        for host in hosts:
            logger.info(">>>>>>>>>>>>>>> [{}] zookeeper install start <<<<<<<<<<<<<<".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.zookeeperInstall(conn, logger)
                if rcode == 0:
                    logger.info("zookeeper install stop.")
                    return
                elif rcode == 1:
                    logger.error("zookeeper install faild !")
                    return 1

                # 创建数据和日志目录
                logger.info("create data and log dir...")
                conn.run("mkdir -p {0}/data".format(self.zkpath), hide=True, warn=True)
                # 创建用户
                logger.info("add user zookeeper...")
                conn.run("id -u zookeeper >/dev/null 2>&1 || useradd zookeeper", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin zookeeper".format(upasswd), warn=True, hide=True)
                # 配置文件
                logger.info("copy conf file...")
                conn.run("mv -f {0}/conf/zoo.cfg {0}/conf/zoo.cfg_bak_`date +%F-%H%M%S`".format(self.zkpath), warn=True, hide=True)
                conn.run("cp -f {}/zoo.cfg {}/conf/".format(self.remotepath, self.zkpath), warn=True, hide=True)
                for l in lst:
                    conn.run("echo \"server.{}={}:2888:3888\" >> {}/conf/zoo.cfg".format(l['id'], l['ip'], self.zkpath), warn=True)
                conn.run("echo \"{0}\" > {1}/data/myid".format(m, self.zkpath), warn=True)
                m += 1
                conn.run("chown -R zookeeper:zookeeper {}".format(self.zkpath))
                # 服务启动脚本
                logger.info("copy service file...")
                conn.run("cp -f {}/zookeeper.service /lib/systemd/system/".format(self.remotepath), warn=True)

                # 启动服务
                logger.info("start zookeeper server...")
                try:
                    conn.run("systemctl daemon-reload")
                    conn.run("systemctl start zookeeper")
                    conn.run("systemctl enable zookeeper")
                except:
                    logger.error("zookeeper server start faild!")
                    return 1
                logger.info("start zookeeper server success.")
                # 检查服务
                self.zookeeperCheck(conn, logger)

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  zookeeper server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Model: zookeeper-cluster\n")
            f.write("cluster: {}\n".format(", ".join(n)))
            f.write("system user: zookeeper, password: {}\n".format(upasswd))
            f.write("zookeeper path: {}\n\n".format(self.zkpath))

    def zookeeperInstall(self, conn, logger):
        # 检查zookeeper是否已经安装
        logger.info("check zookeeper isn't installed...")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/zkServer.sh ]".format(self.zkpath), warn=True, hide=True)
        if r.exited == 0:
            logger.warn("zookeeper is installed, please check it.")
            return 0
        logger.info("zookeeper not installed, start install...")

        # java环境检查
        logger.info("check java...")
        r = conn.run("which java >/dev/null 2>&1 && java -version", warn=True, hide=True)
        if r.exited != 0:
            logger.error("java is not install,please install it.")
            rcode = FabSpring.jdkInstall(self.pkgsdir, conn, logger)
            if rcode != None:
                return 1
        else:
            logger.info("java installed.")

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

        # 安装
        logger.info("tar {} ......".format(self.pkgname))
        with conn.cd(self.remotepath):
            try:
                conn.run("tar -xf {}".format(self.pkgname), hide=True)
                conn.run("mv {} {}".format(self.zkversion, self.zkpath), hide=True)
            except:
                logger.error("tar {} faild!".format(self.pkgname))
                return 1

        # init
        logger.info("Add env PATH....")
        r = conn.run("grep '/opt/zookeeper/bin' /etc/profile", hide=True, warn=True)
        if r.exited != 0:
            conn.run("echo \"export PATH=/opt/zookeeper/bin:$PATH\" >> /etc/profile")

    def zookeeperCheck(self, conn, logger):
        logger.info(">>>>>>>>>>>>>>> check zookeeper server <<<<<<<<<<<<<<")
        try:
            logger.info("zookeeper server process.")
            conn.run("ps -ef | grep zookeeper | grep -v grep")
            logger.info("zookeeper server listen port.")
            conn.run("ss -tunlp | grep 2181")
        except:
            logger.error("zookeeper server is not start!")