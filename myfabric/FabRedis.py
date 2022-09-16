'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/4 10:28
'''
import os
import datetime
import fabric
import SimpleFunc


class fabRedis():
    def __init__(self, pkgsdir, d):
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        mode = d['mode']
        hosts = d['host']
        self.remotepath = "/opt/pkgs/redis"
        self.datapath = "/opt/redis/data"
        self.logpath = "/var/log/redis"
        self.confpath = "/etc/redis"
        self.cludatapath = "/opt/redis-cluster"
        self.clulogpath = "/var/log/redis-cluster"
        self.cluconfpath = "/etc/redis-cluster"
        self.redis_version = "redis-6.2.7"
        self.redis_dir = "/usr/local/{}".format(self.redis_version)
        dirpath = os.path.dirname(__file__)
        self.msgFile = os.path.join(os.path.dirname(dirpath), "ServerMsg.txt")

        self.redisMain(mode, hosts)

    def redisMain(self, mode, hosts):
        hostnum = len(hosts)

        # 判断部署方式 1、单机 2、单机伪集群 3、三节点集群 4、六节点集群
        if mode == "redis-single" and hostnum == 1:
            self.redisSingle(hosts[0])
        elif mode == "redis-cluster-one" and hostnum == 1:
            self.redisClusterOne(hosts[0])
        elif mode == "redis-cluster-three" and hostnum == 3:
            self.redisClusterThree(hosts)
        elif mode == "redis-cluster-six" and hostnum == 6:
            self.redisClusterSix(hosts)
        else:
            print("ERROR: redis model and host is not match.")
            return 1

    def redisInstall(self, conn, logger):
        '''
        :param conn: fabric连接实例
        :param logger: 日志实例
        :return:
        '''
        # 检查是否已经安装
        logger.info(">>>>>>>>>>>>>> check redis server isn't installed <<<<<<<<<<<<<")
        r = conn.run("[ -d {0} ] && [ -f {0}/bin/redis-server ] && [ -f {0}/bin/redis-cli ]".format(self.redis_dir),
                     warn=True, hide=True)
        if r.exited == 0:
            logger.info("redis server is installed, please check it.")
            return 0
        else:
            logger.info("redis server not install.")

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

        # 编译redis
        logger.info("tar: {}.tar.gz......".format(self.redis_version))
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}.tar.gz".format(self.redis_version), hide=True)
        logger.info("install redis......")
        try:
            with conn.cd("{}/{}".format(self.remotepath, self.redis_version)):
                logger.info("make runing......")
                conn.run("make -j 4", hide=True)
                logger.info("make install runing......")
                conn.run("make install PREFIX={}".format(self.redis_dir), hide=True)
        except:
            logger.error("{} make error.".format(self.redis_version))
            return 1

        try:
            conn.run("[ -f /usr/bin/redis-server ] || ln -s /usr/local/{}/bin/redis-server /usr/bin/redis-server".format(self.redis_version))
            conn.run("[ -f /usr/bin/redis-cli ] || ln -s /usr/local/{}/bin/redis-cli /usr/bin/redis-cli".format(self.redis_version))
        except:
            logger.error("redis bin file not exist.")
            return 1
        logger.info("{} make and make install success.".format(self.redis_version))

    def checkRedis(self, conn, logger, port=(6379,)):
        '''
        :param conn: fabric连接实例
        :param logger: 日志实例
        :param port: 端口列表
        :return:
        '''
        logger.info(">>>>>>>>>>>>>>> check redis server <<<<<<<<<<<<<<")
        try:
            logger.info("redis server process.")
            conn.run("ps -ef | grep redis | grep -v grep")
            logger.info("redis server listen port.")
            for p in port:
                conn.run("ss -tunlp | grep redis | grep {}".format(p))
        except Exception as e:
            logger.error(e)

    def redisSingle(self, host):
        # 日志定义
        logger = SimpleFunc.FileLog("redis_single", host['ip'])
        # 用户密码
        redispwd = SimpleFunc.createpasswd()
        # redis服务密码
        spasswd = SimpleFunc.createpasswd(length=10)

        # 连接远程机器
        logger.info(">>>>>>>>>>>>>>> redis install start <<<<<<<<<<<<<<")
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 调用安装函数
            rcode = self.redisInstall(conn, logger)
            if rcode == 0:
                logger.info("redis install stop.")
                return
            elif rcode == 1:
                logger.error("redis install faild !")
                return 1
            logger.info("redis install success")

            # 单机redis配置
            # 创建用户
            logger.info("add user redis...")
            conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
            logger.info("create data and log dir...")
            conn.run("mkdir -p {}".format(self.logpath), warn=True, hide=True)
            conn.run("mkdir -p {}".format(self.datapath), warn=True, hide=True)
            conn.run("mkdir -p {}".format(self.confpath), warn=True, hide=True)
            logger.info("copy redis.conf")
            conn.run("[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(self.confpath), warn=True, hide=True)
            conn.run("cp {}/redis_6379.conf {}/redis.conf".format(self.remotepath, self.confpath))
            conn.run("chown -R redis:redis {} {} {}".format(self.confpath, self.datapath, self.logpath))
            conn.run("sed -i 's/^requirepass .*/requirepass {}/' {}/redis.conf".format(spasswd, self.confpath), warn=True, hide=True)

            # 服务添加与启动
            logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
            conn.run("cp -f {}/redis-6379.service /lib/systemd/system/".format(self.remotepath), warn=True, hide=True)
            conn.run("systemctl daemon-reload", hide=True)
            try:
                conn.run("systemctl start redis-6379.service")
                conn.run("systemctl enable redis-6379.service")
            except:
                logger.error("redis server start error.")
                return 1
            logger.info("redis server start success.")

            # 检查服务
            self.checkRedis(conn, logger)
            conn.close()

        # 将服务信息写入文件
        logger.info("redis msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Model: single\n")
            f.write("Listen: {}:6379\n".format(host['ip']))
            f.write("system user: redis, password: {}\n".format(redispwd))
            f.write("Redis server password: {}\n".format(spasswd))
            f.write("configpath: {}\n".format(self.confpath))
            f.write("logpath: {}\n".format(self.logpath))
            f.write("datapath: {}\n\n".format(self.datapath))

    def redisClusterOne(self, host):
        remotepath = self.remotepath
        datapath = self.datapath
        redispwd = SimpleFunc.createpasswd()
        spasswd = SimpleFunc.createpasswd()
        # 日志定义
        logger = SimpleFunc.FileLog("rediscluster1", host['ip'])

        # 连接远程机器
        logger.info(">>>>>>>>>>>>>>> redis install start <<<<<<<<<<<<<<")
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 调用安装函数
            rcode = self.redisInstall(conn, logger)
            if rcode == 0:
                logger.info("redis install stop.")
                return
            elif rcode == 1:
                logger.error("redis install faild !")
                return 1
            logger.info("redis install success")

            # 单机伪集群redis配置
            # 创建用户
            logger.info("add user redis...")
            conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
            logger.info("copy redis.conf")
            for i in range(7000, 7006):
                dpath = "{}/{}".format(self.cludatapath, i)
                lpath = "{}/{}".format(self.clulogpath, i)
                cpath = "{}/{}".format(self.cluconfpath, i)
                # 创建数据目录和拷贝配置文件
                logger.info("create {} data dir...".format(dpath))
                conn.run("mkdir -p {}".format(dpath), warn=True,hide=True)
                conn.run("mkdir -p {}".format(lpath), warn=True, hide=True)
                conn.run("mkdir -p {}".format(cpath), warn=True, hide=True)
                logger.info("copy redis.conf to {}/redis.conf".format(cpath))
                conn.run("[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(cpath), warn=True, hide=True)
                conn.run("cp {}/redis_cluster.conf {}/redis.conf".format(remotepath, cpath))
                conn.run("sed -i 's/^masterauth.*/masterauth {}/' {}/redis.conf".format(spasswd, cpath), warn=True, hide=True)
                conn.run("sed -i 's/^requirepass.*/requirepass {}/' {}/redis.conf".format(spasswd, cpath), warn=True, hide=True)
                conn.run("sed -i 's/7000/{}/g' {}/redis.conf".format(i, cpath), warn=True, hide=True)
            conn.run("chown -R redis:redis {} {} {}".format(self.clulogpath, self.cluconfpath, self.cludatapath))

            # 服务添加与启动
            logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
            for i in range(7000, 7006):
                conn.run("cp -f {}/redis-cluster.service /lib/systemd/system/redis-{}.service".format(remotepath, i), warn=True, hide=True)
                conn.run("sed -i 's/7000/{0}/g' /lib/systemd/system/redis-{0}.service".format(i), warn=True, hide=True)
            conn.run("systemctl daemon-reload", hide=True)
            try:
                for i in range(7000, 7006):
                    conn.run("systemctl start redis-{}.service".format(i))
                    conn.run("systemctl enable redis-{}.service".format(i))
            except:
                logger.error("redis server start error.")
                return 1
            logger.info("redis server start success.")

            # 集群初始化
            logger.info(">>>>>>>>>>>>>>> redis cluster init <<<<<<<<<<<<<<")
            try:
                conn.run("echo yes | {2}/bin/redis-cli --cluster create {0}:7000 {0}:7001 {0}:7002 {0}:7003 {0}:7004 {0}:7005 --cluster-replicas 1 -a '{1}'".format(host['ip'], spasswd, self.redis_dir))
            except:
                logger.error("redis cluster init error.")
                return 1

            # 检查服务
            self.checkRedis(conn, logger, port=(7000, 7001, 7002, 7003, 7004, 7005))

        # 将相关信息存入文件中
        logger.info("redis msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis server <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: cluster-one\n")
            f.write("Listen: {}:[7000-7005]\n".format(host['ip']))
            f.write("system user: redis, password: {}\n".format(redispwd))
            f.write("Redis server password: {}\n".format(spasswd))
            f.write("configpath: {}/[7000-7005]\n".format(self.cluconfpath))
            f.write("logpath: {}/[7000-7005]\n".format(self.clulogpath))
            f.write("datapath: {}/[7000-7005]\n\n".format(self.cludatapath))

    def redisClusterThree(self, hosts):
        spasswd = SimpleFunc.createpasswd(length=10)
        redispwd = SimpleFunc.createpasswd(length=10)

        # 连接远程机器
        for host in hosts:
            s = host['ip'].split('.')[-1]
            logger = SimpleFunc.FileLog("rediscluster3_{}".format(s), host['ip'])
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.redisInstall(conn, logger)
                if rcode == 0:
                    logger.info("redis install stop.")
                    return
                elif rcode == 1:
                    logger.error("redis install faild !")
                    return 1
                logger.info("redis install success")

                # 三节点集群redis配置
                # 创建用户
                logger.info("add user redis...")
                conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
                logger.info("copy redis.conf")
                for i in range(7000, 7002):
                    dpath = "{}/{}".format(self.cludatapath, i)
                    lpath = "{}/{}".format(self.clulogpath, i)
                    cpath = "{}/{}".format(self.cluconfpath, i)
                    # 创建数据目录和拷贝配置文件
                    logger.info("create {} data dir...".format(dpath))
                    conn.run("mkdir -p {}".format(dpath), warn=True, hide=True)
                    conn.run("mkdir -p {}".format(lpath), warn=True, hide=True)
                    conn.run("mkdir -p {}".format(cpath), warn=True, hide=True)
                    logger.info("copy redis.conf to {}/redis.conf".format(cpath))
                    conn.run(
                        "[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(cpath),
                        warn=True, hide=True)
                    conn.run("cp {}/redis_cluster.conf {}/redis.conf".format(self.remotepath, cpath))
                    conn.run("sed -i 's/^masterauth.*/masterauth {}/' {}/redis.conf".format(spasswd, cpath), warn=True,
                             hide=True)
                    conn.run("sed -i 's/^requirepass.*/requirepass {}/' {}/redis.conf".format(spasswd, cpath),
                             warn=True, hide=True)
                    conn.run("sed -i 's/7000/{}/g' {}/redis.conf".format(i, cpath), warn=True, hide=True)
                conn.run("chown -R redis:redis {} {} {}".format(self.clulogpath, self.cluconfpath, self.cludatapath))

                # 服务添加与启动
                logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
                for i in range(7000, 7002):
                    conn.run("cp -f {}/redis-cluster.service /lib/systemd/system/redis-{}.service".format(self.remotepath, i),
                             warn=True, hide=True)
                    conn.run("sed -i 's/7000/{0}/g' /lib/systemd/system/redis-{0}.service".format(i), warn=True, hide=True)
                conn.run("systemctl daemon-reload", hide=True)
                try:
                    for i in range(7000, 7002):
                        conn.run("systemctl start redis-{}.service".format(i))
                        conn.run("systemctl enable redis-{}.service".format(i))
                except:
                    logger.error("redis server start error.")
                    return 1
                logger.info("redis server start success.")

                # 检查服务
                self.checkRedis(conn, logger, port=(7000, 7001))

        # 集群初始化
        logger = SimpleFunc.FileLog("redis_cluster_three")
        conn = fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                                 connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10)
        logger.info(">>>>>>>>>>>>>>> redis cluster init <<<<<<<<<<<<<<")
        try:
            conn.run(
                "echo yes | {4}/bin/redis-cli --cluster create {0}:7000 {0}:7001 {1}:7000 {1}:7001 {2}:7000 {2}:7001 --cluster-replicas 1 -a '{3}'".format(
                    hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip'], spasswd, self.redis_dir))
        except:
            logger.error("redis cluster init error.")
            return 1

        # 将相关信息存入文件中
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: cluster-three\n")
            f.write("Listen: {0}:7000 {0}:7001 {1}:7000 {1}:7001 {2}:7000 {2}:7001\n".format(hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip']))
            f.write("system user: redis, password: {}\n".format(redispwd))
            f.write("Redis server password: {}\n".format(spasswd))
            f.write("configpath: {}/[7000-7001]\n".format(self.cluconfpath))
            f.write("logpath: {}/[7000-7001]\n".format(self.clulogpath))
            f.write("datapath: {}/[7000-7001]\n\n".format(self.cludatapath))

    def redisClusterSix(self, hosts):
        remotepath = self.remotepath
        datapath = self.datapath
        spasswd = SimpleFunc.createpasswd(length=10)
        redispwd = SimpleFunc.createpasswd(length=10)

        # 连接远程机器
        for host in hosts:
            s = host['ip'].split('.')[-1]
            logger = SimpleFunc.FileLog("rediscluster6_{}".format(s), host['ip'])
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.redisInstall(conn, logger)
                if rcode == 0:
                    logger.info("redis install stop.")
                    return
                elif rcode == 1:
                    logger.error("redis install faild !")
                    return 1
                logger.info("redis install success")

                # 六节点集群redis配置
                # 创建用户
                logger.info("add user redis...")
                conn.run("id -u redis >/dev/null 2>&1 || useradd redis", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin redis".format(redispwd), warn=True, hide=True)
                port = 7000
                logger.info("copy redis.conf")
                dpath = "{}/{}".format(self.cludatapath, port)
                lpath = "{}/{}".format(self.clulogpath, port)
                cpath = "{}/{}".format(self.cluconfpath, port)
                # 创建数据目录和拷贝配置文件
                logger.info("create {} data dir...".format(dpath))
                conn.run("mkdir -p {}".format(dpath), warn=True, hide=True)
                conn.run("mkdir -p {}".format(lpath), warn=True, hide=True)
                conn.run("mkdir -p {}".format(cpath), warn=True, hide=True)
                logger.info("copy redis.conf to {}/redis.conf".format(cpath))
                conn.run(
                    "[ -f {0}/redis.conf ] && mv -f {0}/redis.conf {0}/redis.conf_bak_`date +%F`".format(cpath),
                    warn=True, hide=True)
                conn.run("cp {}/redis_cluster.conf {}/redis.conf".format(remotepath, cpath))
                conn.run("sed -i 's/^masterauth.*/masterauth {}/' {}/redis.conf".format(spasswd, cpath), warn=True, hide=True)
                conn.run("sed -i 's/^requirepass.*/requirepass {}/' {}/redis.conf".format(spasswd, cpath), warn=True, hide=True)
                conn.run("sed -i 's/7000/{}/g' {}/redis.conf".format(port, cpath), warn=True, hide=True)
                conn.run("chown -R redis:redis {} {} {}".format(self.clulogpath, self.cluconfpath, self.cludatapath))

                # 服务添加与启动
                logger.info(">>>>>>>>>>>>>>> starting redis server <<<<<<<<<<<<<<")
                conn.run("cp -f {}/redis-cluster.service /lib/systemd/system/redis-{}.service".format(remotepath, port),
                         warn=True, hide=True)
                conn.run("sed -i 's/7000/{0}/g' /lib/systemd/system/redis-{0}.service".format(port), warn=True, hide=True)
                conn.run("systemctl daemon-reload", hide=True)
                try:
                    conn.run("systemctl start redis-{}.service".format(port))
                    conn.run("systemctl enable redis-{}.service".format(port))
                except:
                    logger.error("redis server start error.")
                    return 1
                logger.info("redis server start success.")

                # 检查服务
                self.checkRedis(conn, logger, port=(7000,))

        # 集群初始化
        logger = SimpleFunc.FileLog("redis_cluster_six")
        conn = fabric.Connection(host=hosts[0]['ip'], port=hosts[0]['port'], user=hosts[0]['user'],
                                 connect_kwargs={"password": hosts[0]['password']}, connect_timeout=10)
        logger.info(">>>>>>>>>>>>>>> redis cluster init <<<<<<<<<<<<<<")
        try:
            conn.run(
                "echo yes | {7}/bin/redis-cli --cluster create {0}:7000 {1}:7000 {2}:7000 {3}:7000 {4}:7000 {5}:7000 --cluster-replicas 1 -a '{6}'".format(
                    hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip'], hosts[3]['ip'], hosts[4]['ip'], hosts[5]['ip'], spasswd, self.redis_dir))
        except:
            logger.error("redis cluster init error.")
            return 1

        # 将相关信息存入文件中
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Redis server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Mode: cluster-six\n")
            f.write("Listen: {}:7000 {}:7000 {}:7000 {}:7000 {}:7000 {}:7000\n".format(hosts[0]['ip'], hosts[1]['ip'], hosts[2]['ip'], hosts[3]['ip'], hosts[4]['ip'], hosts[5]['ip']))
            f.write("system user: redis, password: {}\n".format(redispwd))
            f.write("Redis server password: {}\n".format(spasswd))
            f.write("configpath: {}/7000\n".format(self.cluconfpath))
            f.write("logpath: {}/7000\n".format(self.clulogpath))
            f.write("datapath: {}/7000\n\n".format(self.cludatapath))