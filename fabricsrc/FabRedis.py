'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/4 10:28
'''
import os
import datetime
import fabric
import CommonFunc

from config import settings, redisConf


class fabRedis():
    def __init__(self, d, logger):
        self.remotepath = "{}/{}".format(settings.remotedir, d['srvname'])
        self.datapath = redisConf.data_path
        self.logpath = redisConf.log_path
        self.confpath = redisConf.conf_path
        self.cludatapath = redisConf.clu_data_path
        self.clulogpath = redisConf.clu_log_path
        self.cluconfpath = redisConf.clu_conf_path
        self.redis_version = redisConf.redis_version
        self.redis_dir = redisConf.redis_install_path
        self.msgFile = settings.serverMsgText
        self.logger = logger
        self.pkgpath = os.path.join(settings.pkgsdir, d['srvname'], "pkgs")
        self.tmplatepath = os.path.join(settings.pkgsdir, d['srvname'], "template")
        self.d = d

    def redisMain(self):
        mode = self.d['mode']
        hosts = self.d['host']
        hostnum = len(hosts)

        # 判断部署方式 1、单机 2、单机伪集群 3、三节点集群 4、六节点集群
        if mode == "redis-single" and hostnum == 1:
            if self.redisSingle(hosts[0]) is not None:
                return 1
        elif mode == "redis-cluster-one" and hostnum == 1:
            if self.redisClusterOne(hosts[0]) is not None:
                return 1
        elif mode == "redis-cluster-three" and hostnum == 3:
            if self.redisClusterThree(hosts) is not None:
                return 1
        elif mode == "redis-cluster-six" and hostnum == 6:
            if self.redisClusterSix(hosts) is not None:
                return 1
        else:
            self.logger.error("redis model and host is not match.")
            return 1

    def redisInstall(self, conn):
        '''
        :param conn: fabric连接实例
        :param self.logger: 日志实例
        :return:
        '''
        # 检查是否已经安装
        self.logger.info("Check whether redis is installed...")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/redis-server ] && [ -f {0}/bin/redis-cli ]".format(self.redis_dir),
                     warn=True, hide=True)
        if r.exited == 0:
            self.logger.info("redis server is installed, please check it.")
            return 0
        else:
            self.logger.info("redis server not install.")

        # 拷贝文件到远程主机
        self.logger.info("copy package to remothost.")
        if not os.path.exists(self.pkgpath):
            self.logger.error("local path {} not exist.".format(self.pkgpath))
            return 1
        conn.run("[ -d {0} ] && rm -rf {0}/*".format(self.remotepath), warn=True, hide=True)
        # 遍历目录文件并上传到服务器
        self.logger.info("upload {} files to remote host...".format(self.pkgpath))
        for root, dirs, files in os.walk(self.pkgpath):
            rpath = root.replace(self.pkgpath, self.remotepath).replace('\\', '/')
            conn.run("mkdir -p {}".format(rpath))
            for file in files:
                localfile = os.path.join(root, file)
                #self.logger.info("put file: {} to {}".format(localfile, rpath))
                conn.put(localfile, rpath)

        # 编译redis
        self.logger.info("tar: {}.tar.gz......".format(self.redis_version))
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}.tar.gz".format(self.redis_version), hide=True)
        self.logger.info("install redis......")
        try:
            with conn.cd("{}/{}".format(self.remotepath, self.redis_version)):
                self.logger.info("make runing, Please wait 5-10 minutes...")
                conn.run("make -j 4", hide=True)
                self.logger.info("make install runing, Please wait 3-5 minutes...")
                conn.run("make install PREFIX={}".format(self.redis_dir), hide=True)
        except:
            self.logger.error("{} make error.".format(self.redis_version))
            return 1

        try:
            conn.run("[ -f /usr/bin/redis-server ] || ln -s /usr/local/{}/bin/redis-server /usr/bin/redis-server".format(self.redis_version))
            conn.run("[ -f /usr/bin/redis-cli ] || ln -s /usr/local/{}/bin/redis-cli /usr/bin/redis-cli".format(self.redis_version))
        except:
            self.logger.error("redis bin file not exist.")
            return 1
        self.logger.info("{} make and make install success.".format(self.redis_version))

    def redisSingle(self, host):
        # 用户密码
        redispwd = CommonFunc.createpasswd()
        # redis服务密码
        spasswd = CommonFunc.createpasswd(length=10)

        # 连接远程机器
        self.logger.info("=" * 40)
        self.logger.info("[{}] redis install start......".format(host['ip']))
        self.logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 调用安装函数
            rcode = self.redisInstall(conn)
            if rcode == 0:
                self.logger.info("redis install stop.")
                return 1
            elif rcode == 1:
                self.logger.error("redis install faild !")
                return 1
            self.logger.info("redis install success")

            # 单机redis配置
            # 创建用户
            self.logger.info("add user redis...")
            conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
            self.logger.info("create data and log dir...")
            conn.run("mkdir -p {}".format(self.logpath), warn=True, hide=True)
            conn.run("mkdir -p {}".format(self.datapath), warn=True, hide=True)
            conn.run("mkdir -p {}".format(self.confpath), warn=True, hide=True)
            self.logger.info("copy redis.conf")
            conn.run("[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(self.confpath), warn=True, hide=True)

            txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis_6379.conf', datapath=self.datapath, logpath=self.logpath, redispwd=spasswd)
            conn.run("echo '{}' > {}/redis.conf".format(txt, self.confpath), hide=True)
            conn.run("chown -R redis:redis {} {} {}".format(self.confpath, self.datapath, self.logpath))

            # 服务添加与启动
            self.logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
            txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis-6379.service', redispath=self.redis_dir, confpath=self.confpath)
            conn.run("echo '{}' > /lib/systemd/system/redis.service".format(txt), hide=True)
            conn.run("systemctl daemon-reload", hide=True)
            try:
                conn.run("systemctl start redis.service", hide=True)
                conn.run("systemctl enable redis.service", hide=True)
            except:
                self.logger.error("redis server start error.")
                return 1
            self.logger.info("redis server start success.")

        # 将服务信息写入文件
        self.logger.info("redis msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis single  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Listen: {}:6379\n".format(host['ip']))
            f.write("系统用户: redis, 密码: {}\n".format(redispwd))
            f.write("Redis 服务密码: {}\n".format(spasswd))

    def redisClusterOne(self, host):
        redispwd = CommonFunc.createpasswd()
        spasswd = CommonFunc.createpasswd()

        # 连接远程机器
        self.logger.info("=" * 40)
        self.logger.info("[{}] redis install start......".format(host['ip']))
        self.logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 调用安装函数
            rcode = self.redisInstall(conn)
            if rcode == 0:
                self.logger.info("redis install stop.")
                return 1
            elif rcode == 1:
                self.logger.error("redis install faild !")
                return 1
            self.logger.info("redis install success")

            # 单机伪集群redis配置
            # 创建用户
            self.logger.info("add user redis...")
            conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
            self.logger.info("copy redis.conf")
            for i in range(7000, 7006):
                dpath = "{}/{}".format(self.cludatapath, i)
                lpath = "{}/{}".format(self.clulogpath, i)
                cpath = "{}/{}".format(self.cluconfpath, i)
                # 创建数据目录和拷贝配置文件
                self.logger.info("create {} data dir...".format(dpath))
                conn.run("mkdir -p {}".format(dpath), warn=True,hide=True)
                conn.run("mkdir -p {}".format(lpath), warn=True, hide=True)
                conn.run("mkdir -p {}".format(cpath), warn=True, hide=True)
                self.logger.info("create redis.conf".format(cpath))
                conn.run("[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(cpath), warn=True, hide=True)
                txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis_cluster.conf', datapath=dpath, logpath=lpath, redispwd=spasswd, port=i)
                conn.run("echo '{}' > {}/redis.conf".format(txt, cpath), hide=True)
            conn.run("chown -R redis:redis {} {} {}".format(self.clulogpath, self.cluconfpath, self.cludatapath))

            # 服务添加与启动
            self.logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
            for i in range(7000, 7006):
                txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis-cluster.service', redispath=self.redis_dir, confpath=self.cluconfpath, port=i)
                conn.run("echo '{}' > /lib/systemd/system/redis-{}.service".format(txt, i), hide=True)
            conn.run("systemctl daemon-reload", hide=True)
            try:
                for i in range(7000, 7006):
                    conn.run("systemctl start redis-{}.service".format(i), hide=True)
                    conn.run("systemctl enable redis-{}.service".format(i), hide=True)
            except:
                self.logger.error("redis server start error.")
                return 1
            self.logger.info("redis server start success.")

            # 集群初始化
            self.logger.info(">>>>>>>>>>>>>>> redis cluster init <<<<<<<<<<<<<<")
            try:
                r = conn.run("echo yes | {2}/bin/redis-cli --cluster create {0}:7000 {0}:7001 {0}:7002 {0}:7003 {0}:7004 {0}:7005 --cluster-replicas 1 -a '{1}'".format(host['ip'], spasswd, self.redis_dir), hide=True)
                self.logger.info(r.stdout)
            except:
                self.logger.error("redis cluster init error.")
                return 1

        # 将相关信息存入文件中
        self.logger.info("redis msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis cluster-one <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: cluster-one\n")
            f.write("Listen: {}:[7000-7005]\n".format(host['ip']))
            f.write("系统用户: redis, 密码: {}\n".format(redispwd))
            f.write("Redis 服务密码: {}\n".format(spasswd))

    def redisClusterThree(self, hosts):
        spasswd = CommonFunc.createpasswd(length=10)
        redispwd = CommonFunc.createpasswd(length=10)

        # 连接远程机器
        for host in hosts:
            self.logger.info("=" * 40)
            self.logger.info("[{}] redis install start......".format(host['ip']))
            self.logger.info("=" * 40)
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.redisInstall(conn)
                if rcode == 0:
                    self.logger.info("redis install stop.")
                    return 1
                elif rcode == 1:
                    self.logger.error("redis install faild !")
                    return 1
                self.logger.info("redis install success")

                # 三节点集群redis配置
                # 创建用户
                self.logger.info("add user redis...")
                conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
                self.logger.info("copy redis.conf")
                for i in range(7000, 7002):
                    dpath = "{}/{}".format(self.cludatapath, i)
                    lpath = "{}/{}".format(self.clulogpath, i)
                    cpath = "{}/{}".format(self.cluconfpath, i)
                    # 创建数据目录和拷贝配置文件
                    self.logger.info("create {} data dir...".format(dpath))
                    conn.run("mkdir -p {}".format(dpath), warn=True, hide=True)
                    conn.run("mkdir -p {}".format(lpath), warn=True, hide=True)
                    conn.run("mkdir -p {}".format(cpath), warn=True, hide=True)
                    self.logger.info("copy redis.conf to {}/redis.conf".format(cpath))
                    conn.run(
                        "[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(cpath),
                        warn=True, hide=True)
                    txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis_cluster.conf', datapath=dpath, logpath=lpath,
                                                  redispwd=spasswd, port=i)
                    conn.run("echo '{}' > {}/redis.conf".format(txt, cpath), hide=True)
                conn.run("chown -R redis:redis {} {} {}".format(self.clulogpath, self.cluconfpath, self.cludatapath))

                # 服务添加与启动
                self.logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
                for i in range(7000, 7002):
                    txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis-cluster.service', redispath=self.redis_dir,
                                                  confpath=self.cluconfpath, port=i)
                    conn.run("echo '{}' > /lib/systemd/system/redis-{}.service".format(txt, i), hide=True)
                conn.run("systemctl daemon-reload", hide=True)
                try:
                    for i in range(7000, 7002):
                        conn.run("systemctl start redis-{}.service".format(i), hide=True)
                        conn.run("systemctl enable redis-{}.service".format(i), hide=True)
                except:
                    self.logger.error("redis server start error.")
                    return 1
                self.logger.info("redis server start success.")

        # 集群初始化
        conn = fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                                 connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10)
        self.logger.info(">>>>>>>>>>>>>>> redis cluster init <<<<<<<<<<<<<<")
        try:
            r = conn.run(
                "echo yes | {4}/bin/redis-cli --cluster create {0}:7000 {0}:7001 {1}:7000 {1}:7001 {2}:7000 {2}:7001 --cluster-replicas 1 -a '{3}'".format(
                    hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip'], spasswd, self.redis_dir), hide=True)
            self.logger.info(r.stdout)
        except:
            self.logger.error("redis cluster init error.")
            return 1

        # 将相关信息存入文件中
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis cluster-three  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: cluster-three\n")
            f.write("Listen: {0}:7000 {0}:7001 {1}:7000 {1}:7001 {2}:7000 {2}:7001\n".format(hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip']))
            f.write("系统用户: redis, 密码: {}\n".format(redispwd))
            f.write("Redis 服务密码: {}\n".format(spasswd))

    def redisClusterSix(self, hosts):
        spasswd = CommonFunc.createpasswd(length=10)
        redispwd = CommonFunc.createpasswd(length=10)

        # 连接远程机器
        for host in hosts:
            self.logger.info("=" * 40)
            self.logger.info("[{}] redis install start......".format(host['ip']))
            self.logger.info("=" * 40)
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.redisInstall(conn)
                if rcode == 0:
                    self.logger.info("redis install stop.")
                    return
                elif rcode == 1:
                    self.logger.error("redis install faild !")
                    return 1
                self.logger.info("redis install success")

                # 六节点集群redis配置
                # 创建用户
                self.logger.info("add user redis...")
                conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
                port = 7000
                self.logger.info("copy redis.conf")
                dpath = "{}/{}".format(self.cludatapath, port)
                lpath = "{}/{}".format(self.clulogpath, port)
                cpath = "{}/{}".format(self.cluconfpath, port)
                # 创建数据目录和拷贝配置文件
                self.logger.info("create {} data dir...".format(dpath))
                conn.run("mkdir -p {}".format(dpath), warn=True, hide=True)
                conn.run("mkdir -p {}".format(lpath), warn=True, hide=True)
                conn.run("mkdir -p {}".format(cpath), warn=True, hide=True)
                self.logger.info("copy redis.conf to {}/redis.conf".format(cpath))
                conn.run("[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(cpath),
                    warn=True, hide=True)
                txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis_cluster.conf', datapath=dpath, logpath=lpath,
                                              redispwd=spasswd, port=port)
                conn.run("echo '{}' > {}/redis.conf".format(txt, cpath), hide=True)
                conn.run("chown -R redis:redis {} {} {}".format(self.clulogpath, self.cluconfpath, self.cludatapath))

                # 服务添加与启动
                self.logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
                txt = CommonFunc.FillTemplate(self.tmplatepath, 'redis-cluster.service', redispath=self.redis_dir,
                                              confpath=self.cluconfpath, port=port)
                conn.run("echo '{}' > /lib/systemd/system/redis-{}.service".format(txt, port), hide=True)
                conn.run("systemctl daemon-reload", hide=True)
                try:
                    conn.run("systemctl start redis-{}.service".format(port), hide=True)
                    conn.run("systemctl enable redis-{}.service".format(port), hide=True)
                except:
                    self.logger.error("redis server start error.")
                    return 1
                self.logger.info("redis server start success.")

        # 集群初始化
        conn = fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                                 connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10)
        self.logger.info(">>>>>>>>>>>>>>> redis cluster init <<<<<<<<<<<<<<")
        try:
            r = conn.run(
                "echo yes | {7}/bin/redis-cli --cluster create {0}:7000 {1}:7000 {2}:7000 {3}:7000 {4}:7000 {5}:7000 --cluster-replicas 1 -a '{6}'".format(
                    hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip'], hosts[3]['ip'], hosts[4]['ip'], hosts[5]['ip'], spasswd, self.redis_dir), hide=True)
            self.logger.info(r.stdout)
        except:
            self.logger.error("redis cluster init error.")
            return 1

        # 将相关信息存入文件中
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis cluster-six  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Listen: {}:7000 {}:7000 {}:7000 {}:7000 {}:7000 {}:7000\n".format(hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip'], hosts[3]['ip'], hosts[4]['ip'], hosts[5]['ip']))
            f.write("系统用户: redis, 密码: {}\n".format(redispwd))
            f.write("Redis 服务密码: {}\n".format(spasswd))


def check_redis(conn):
    r = conn.run("[ -d {0} ] && [ -f {0}/bin/redis-server ] && [ -f {0}/bin/redis-cli ]".format(redisConf.redis_install_path), warn=True, hide=True)
    if r.exited != 0:
        return "未安装"
    r = conn.run("ps -ef | grep redis | grep -v grep", warn=True, hide=True)
    if r.exited != 0:
        return "已安装，未启动服务"
    else:
        return "服务已启动"