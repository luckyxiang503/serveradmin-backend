'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/11 15:59
'''
import os
import datetime
import fabric
import SimpleFunc


class fabMongodb():
    def __init__(self, pkgsdir, d):
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        mode = d['mode']
        hosts = d['host']
        self.remotepath = "/opt/pkgs/mongodb"
        self.installpath = "/usr/local/mongodb"
        self.datapath = "/opt/mongodb"
        self.logpath = "/var/log/mongodb"
        self.confpath = "/etc/mongodb"
        self.cludatapath = "/opt/mongodb-cluster"
        self.cluconfpath = "/etc/mongodb-cluster"
        self.clulogpath = "/var/log/mongod-cluster"
        self.mongopkgname = "mongodb-linux-x86_64-rhel70-5.0.10"
        self.mongoshellpkgname = "mongodb-shell-linux-x86_64-rhel70-5.0.10"
        dirpath = os.path.dirname(__file__)
        self.msgFile = os.path.join(os.path.dirname(dirpath), "ServerMsg.txt")

        self.mongodbMain(mode, hosts)

    def mongodbMain(self, mode, hosts):
        hostnum = len(hosts)
        if mode == "mongodb-single" and hostnum == 1:
            self.mongodbSingle(hosts[0])
        elif mode == "mongodb-sharding":
            self.mongodbSharding(hosts)
        else:
            print("ERROR: host num or mode is not true!")
            return 1

    def mongodbSingle(self, host):
        mongodpwd = SimpleFunc.createpasswd()
        # 日志定义
        logger = SimpleFunc.FileLog('mongodb-single', host['ip'])

        # 连接远程机器
        logger.info(">>>>>>>>>>>>>>> mongodb install start <<<<<<<<<<<<<<")
        conn = fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                 connect_kwargs={"password": host['password']}, connect_timeout=10)
        # 调用安装函数
        rcode = self.mongodbInstall(conn, logger)
        if rcode == 0:
            logger.info("mongodb install stop.")
            return
        elif rcode == 1:
            logger.error("mongodb install faild !")
            return 1
        logger.info("mongodb install success")

        # 创建用户
        logger.info("create user mongod")
        conn.run("id mongod >/dev/null 2>&1 || useradd mongod", warn=True, hide=True)
        conn.run("echo '{}' | passwd --stdin mongod".format(mongodpwd), warn=True, hide=True)
        # 创建数据目录
        logger.info("create data path...")
        conn.run("mkdir -p {} {} {} /var/run/mongodb".format(self.confpath, self.logpath, self.datapath), warn=True)
        # 拷贝文件
        logger.info("copy mongod.conf...")
        conn.run("[ -f {0}/mongod.conf ] && mv {0}/mongod.conf {0}/mongod.conf_bak_`date +%F`".format(self.confpath), warn=True)
        conn.run("cp -f {}/mongod.conf {}".format(self.remotepath, self.confpath),  warn=True)
        conn.run("cp -f {}/mongod.service /lib/systemd/system/".format(self.remotepath), warn=True)
        conn.run("chown -R mongod:mongod {} {} {} /var/run/mongodb".format(self.confpath, self.logpath, self.datapath),
                 warn=True)

        # 启动mongodb
        logger.info("mongod starting...")
        try:
            conn.run("systemctl daemon-reload")
            conn.run("systemctl start mongod")
            conn.run("systemctl enable mongod")
        except:
            logger.error("mongodb start faild!")
            return 1
        logger.info("mongodb start success.")

        logger.info("check mongod server...")
        self.mongodbCheck(conn, logger)
        # 将服务信息写入文件
        logger.info("mongodb msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  MongoDB server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("mode: single\n")
            f.write("Listen: {}:27017\n".format(host['ip']))
            f.write("system user: mongod, password: {}\n".format(mongodpwd))
            f.write("configpath: {}\n".format(self.confpath))
            f.write("logpath: {}\n".format(self.logpath))
            f.write("datapath: {}\n\n".format(self.datapath))

    def mongodbSharding(self, hosts):
        mongodpwd = SimpleFunc.createpasswd()
        shardlist, configlist, mongoslist = [], [], []
        S, C, M = [], [], []
        for host in hosts:
            role = host['role'].split(' ')
            if 'configsrv' in role:
                C.append("{}:27000".format(host['ip']))
            if 'shard' in role:
                S.append("{}:27001".format(host['ip']))
                S.append("{}:27002".format(host['ip']))
                S.append("{}:27003".format(host['ip']))
            if 'mongos' in role:
                M.append("{}:27017".format(host['ip']))
        configDB = "config/{}".format(",".join(C))

        for host in hosts:
            s = host['ip'].split('.')[-1]
            # 日志定义
            logger = SimpleFunc.FileLog('mongodb_shard_{}'.format(s), host['ip'])

            # 连接远程机器
            logger.info(">>>>>>>>>>>>>>> mongodb install start <<<<<<<<<<<<<<")
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.mongodbInstall(conn, logger)
                if rcode == 0:
                    logger.info("mongodb install stop.")
                    return
                elif rcode == 1:
                    logger.error("mongodb install faild !")
                    return 1
                logger.info("mongodb install success")

                # 创建用户
                logger.info("create user mongod")
                conn.run("id mongod >/dev/null 2>&1 || useradd mongod", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin mongod".format(mongodpwd), warn=True, hide=True)
                conn.run("mkdir -p /var/run/mongodb && chown -R mongod:mongod /var/run/mongodb", warn=True)
                # 安装组件
                role = host['role'].split(' ')
                if 'shard' in role:
                    shardlist.append(host)
                    for i in ['shard1', 'shard2', 'shard3']:
                        logger.info("crete {} path...".format(i))
                        conn.run("mkdir -p {0}/{3} {1}/{3} {2}/{3}".format(self.clulogpath, self.cluconfpath, self.cludatapath, i))
                        logger.info("copy {} mongod.conf...".format(i))
                        conn.run("cp -f {0}/mongod-shard.conf {1}/{2}/mongod.conf".format(self.remotepath, self.cluconfpath, i))
                        conn.run("sed -i 's/shard1/{1}/g' {0}/{1}/mongod.conf".format(self.cluconfpath, i), warn=True)
                    conn.run("sed -i 's/port: .*/port: 27001/' {}/shard1/mongod.conf".format(self.cluconfpath), warn=True)
                    conn.run("sed -i 's/port: .*/port: 27002/' {}/shard2/mongod.conf".format(self.cluconfpath), warn=True)
                    conn.run("sed -i 's/port: .*/port: 27003/' {}/shard3/mongod.conf".format(self.cluconfpath), warn=True)
                    conn.run("chown -R mongod:mongod {} {} {}".format(self.clulogpath, self.cludatapath, self.cluconfpath))

                    for i in ['shard1', 'shard2', 'shard3']:
                        logger.info("copy {} service file...".format(i))
                        conn.run("cp -f {}/mongod-shard.service /lib/systemd/system/mongod-{}.service".format(self.remotepath, i))
                        conn.run("sed -i 's/shard1/{0}/g' /lib/systemd/system/mongod-{0}.service".format(i), warn=True)
                        logger.info("starting shardsrv {}....".format(i))
                        try:
                            conn.run("systemctl daemon-reload")
                            conn.run("systemctl start mongod-{}".format(i))
                            conn.run("systemctl enable mongod-{}".format(i))
                        except:
                            logger.error("start shardsrv {} faild!".format(i))
                            return 1
                        logger.info("start shardsrv {} success.".format(i))
                if 'configsrv' in role:
                    configlist.append(host)
                    logger.info("create configsrv data path...")
                    conn.run("mkdir -p {0}/configsrv {1}/configsrv {2}/configsrv".format(self.clulogpath, self.cluconfpath, self.cludatapath))
                    logger.info("copy configsrv file...")
                    conn.run("cp -f {}/mongod-config.conf {}/configsrv/mongocfg.conf".format(self.remotepath, self.cluconfpath))
                    logger.info("copy configsrv service file...")
                    conn.run("cp -f {}/mongod-config.service /lib/systemd/system/mongod-config.service".format(self.remotepath))
                    conn.run("chown -R mongod:mongod {} {} {}".format(self.clulogpath, self.cludatapath, self.cluconfpath))
                    logger.info("starting configsrv....")
                    try:
                        conn.run("systemctl daemon-reload")
                        conn.run("systemctl start mongod-config")
                        conn.run("systemctl enable mongod-config")
                    except:
                        logger.error("start mongod-config faild!")
                        return 1
                    logger.info("start mongod-config success.")
                if 'mongos' in role:
                    mongoslist.append(host)
                    logger.info("create mongos path...")
                    conn.run("mkdir -p {0}/mongos {1}/mongos".format(self.clulogpath, self.cluconfpath))
                    logger.info("copy mongos configfile...")
                    conn.run(
                        "cp -f {}/mongod-mongos.conf {}/mongos/mongos.conf".format(self.remotepath, self.cluconfpath))
                    conn.run("sed -i 's#configDB:.*#configDB: {}#' {}/mongos/mongos.conf".format(configDB, self.cluconfpath))
                    logger.info("copy mongos service file...")
                    conn.run(
                        "cp -f {}/mongod-mongos.service /lib/systemd/system/mongod-mongos.service".format(self.remotepath))
                    conn.run("chown -R mongod:mongod {} {} {}".format(self.clulogpath, self.cludatapath, self.cluconfpath))

                logger.info(">>>>>>>>>>>>>>>>  check mongo server  <<<<<<<<<<<<<<<")
                self.mongodbCheck(conn, logger)


        logger = SimpleFunc.FileLog("mongodb-shard-main")
        logger.info(">>>>>>>>>>>>>>>>>>> mongodb cluster init  <<<<<<<<<<<<<<<<<<<<<<")
        # 创建config repset
        host = configlist[0]
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            logger.info("mongodb configsrv repSet...")
            members = []
            for i in range(len(configlist)):
                members.append('{{"_id":{},"host":"{}:27000"}}'.format(i+1, configlist[i]['ip']))
            cfg = 'rs.initiate({{"_id":"config", configsvr: true, "members":[{}] }})'.format(",".join(members))
            logger.info("configsrv: {}".format(cfg))
            try:
                conn.run("echo -e '{}' | mongo --port 27000".format(cfg))
            except:
                logger.error("mongodb configsrv repSet faild！")
                return 1
        # 创建shard repset
        host = shardlist[0]
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            logger.info("mongodb shardsrv repSet...")
            dc = {'shard1': 27001, 'shard2': 27002, 'shard3': 27003}
            for h in dc:
                members = []
                for i in range(len(shardlist)):
                    members.append('{{"_id":{},"host":"{}:{}"}}'.format(i + 1, shardlist[i]['ip'], dc[h]))
                cfg = 'rs.initiate({{"_id":"{}","members":[{}] }})'.format(h, ",".join(members))
                logger.info("{}: {}".format(h, cfg))
                try:
                    conn.run("echo -e '{}' | mongo --port {}".format(cfg, dc[h]))
                except:
                    logger.error("mongodb shardsrv repSet {} faild！".format(h))
                    return 1
        # mongos 服务启动与配置分片路由
        for host in mongoslist:
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                logger.info("[{}] starting mongos....".find(host['ip']))
                try:
                    conn.run("systemctl daemon-reload")
                    conn.run("systemctl start mongod-mongos")
                    conn.run("systemctl enable mongod-mongos")
                except:
                    logger.error("start mongod-mongos faild!")
                    return 1
                logger.info("start mongod-mongos success.")

                logger.info("[{}] mongodb mongos init...".format(host['ip']))
                dc = {'shard1': 27001, 'shard2': 27002, 'shard3': 27003}
                for h in dc:
                    members = []
                    for host in shardlist:
                        members.append("{}:{}".format(host['ip'], dc[h]))
                    cfg = "sh.addShard(\"{}/{}\")".format(h, ",".join(members))
                    logger.info("[{}] mongos: {}".format(host['ip'], cfg))
                    try:
                        conn.run("echo -e '{}' | mongo --port 27017".format(cfg))
                    except:
                        logger.error("mongodb mongos {} init faild！".format(h))
                        return 1
                self.mongodbCheck(conn, logger)


        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  MongoDB server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Model: mongodb-sharding\n")
            f.write("mongos: {}\n".format(";".join(M)))
            f.write("shardsrv: {}\n".format(";".join(S)))
            f.write("configsrv: {}\n".format(";".join(C)))
            f.write("system user: mongod, passwd: {}\n".format(mongodpwd))
            f.write("configpath: {}/[shard1,shard2,shard3,configsrv,mongos]\n".format(self.cluconfpath))
            f.write("logpath: {}/[shard1,shard2,shard3,configsrv,mongos]\n".format(self.clulogpath))
            f.write("datapath: {}/[shard1,shard2,shard3,configsrv]\n\n".format(self.cludatapath))

    def mongodbInstall(self, conn, logger):
        # 检查是否已经安装
        logger.info(">>>>>>>>>>>>>> check mongodb server isn't installed <<<<<<<<<<<<<")
        r = conn.run("[ -f {0}/bin/mongod ] && [ -f {0}/bin/mongos ]".format(self.installpath), warn=True, hide=True)
        if r.exited == 0:
            logger.info("mongodb server is installed, please check it.")
            return 0
        else:
            logger.info("mongodb server not install.")

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

        # 安装mongodb
        logger.info("mongodb install start...")
        try:
            with conn.cd(self.remotepath):
                conn.run("tar -xf {}.tgz".format(self.mongopkgname))
                conn.run("tar -xf {}.tgz".format(self.mongoshellpkgname))
                conn.run("mv {} {}".format(self.mongopkgname, self.installpath))
                conn.run("ln -s {}/bin/mongod /usr/local/bin/mongod".format(self.installpath), warn=True)
                conn.run("ln -s {}/bin/mongos /usr/local/bin/mongos".format(self.installpath), warn=True)
                conn.run("ln -s {}/bin/mongo /usr/local/bin/mongo".format(self.installpath), warn=True)
        except:
            logger.error("mongodb install faild!")
            return 1
        logger.info("mongodb install success.")

    def mongodbCheck(self, conn, logger):
        logger.info(">>>>>>>>>>>>>>> check mongod server <<<<<<<<<<<<<<")
        try:
            logger.info("mongod server process.")
            conn.run("ps -ef | grep mongod | grep -v grep")
            logger.info("mongod server listen port.")
            conn.run("ss -tunlp | grep mongo")
        except Exception as e:
            logger.error(e)