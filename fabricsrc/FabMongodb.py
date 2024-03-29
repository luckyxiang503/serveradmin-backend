'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/11 15:59
'''
import os
import datetime
import fabric
import CommonFunc

from config import settings, mongoConf


class fabMongodb:
    def __init__(self):
        self.remotepath = "/opt/pkgs/mongodb"
        self.installpath = mongoConf.install_path
        self.datapath = mongoConf.data_path
        self.logpath = mongoConf.log_path
        self.confpath = mongoConf.conf_path
        self.cludatapath = mongoConf.clu_data_path
        self.cluconfpath = mongoConf.clu_conf_path
        self.clulogpath = mongoConf.clu_log_path
        self.mongopkgname = mongoConf.mongo_pkg_name
        self.mongoshellpkgname = mongoConf.mongoShell_pkg_name
        self.msgFile = settings.serverMsgText

    def mongodbMain(self, d, logger):
        pkgsdir = settings.pkgsdir
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        mode = d['mode']
        hosts = d['host']
        hostnum = len(hosts)

        if mode == "mongodb-single" and hostnum == 1:
            if self.mongodbSingle(hosts[0], logger) is not None:
                return 1
        elif mode == "mongodb-sharding" and hostnum == 3:
            if self.mongodbSharding(hosts, logger) is not None:
                return 1
        else:
            logger.error("host num or mode is not true!")
            return 1

    def mongodbSingle(self, host, logger):
        mongodpwd = CommonFunc.createpasswd()

        # 连接远程机器
        logger.info("=" * 40)
        logger.info("[{}] mongodb install......".format(host['ip']))
        logger.info("=" * 40)
        conn = fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                 connect_kwargs={"password": host['password']}, connect_timeout=10)
        # 调用安装函数
        rcode = self.mongodbInstall(conn, logger)
        if rcode == 0:
            logger.error("mongodb is installed !")
            return 1
        elif rcode == 1:
            logger.error("mongodb install faild !")
            return 1
        logger.info("mongodb install success")

        # 创建用户
        logger.info("Create System User: mongod")
        conn.run("id mongod >/dev/null 2>&1 || useradd mongod", warn=True, hide=True)
        conn.run("echo '{}' | passwd --stdin mongod".format(mongodpwd), warn=True, hide=True)
        # 创建数据目录
        logger.info("Create data path...")
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

        # 将服务信息写入文件
        logger.info("mongodb msg write to ServerMsg.txt")
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  MongoDB single  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Listen: {}:27017\n".format(host['ip']))
            f.write("系统用户: mongod, 密码: {}\n".format(mongodpwd))

    def mongodbSharding(self, hosts, logger):
        mongodpwd = CommonFunc.createpasswd()

        H, C = [], []
        for host in hosts:
            H.append(host['ip'])
            C.append("{}:27000".format(host['ip']))
        configDB = "config/{}".format(",".join(C))

        for host in hosts:
            # 连接远程机器
            logger.info("=" * 40)
            logger.info("[{}] mongodb install......".format(host['ip']))
            logger.info("=" * 40)
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.mongodbInstall(conn, logger)
                if rcode == 0:
                    logger.error("mongodb is installed !")
                    return 1
                elif rcode == 1:
                    logger.error("mongodb install faild !")
                    return 1
                logger.info("mongodb install success")

                # 创建用户
                logger.info("create user mongod")
                conn.run("id mongod >/dev/null 2>&1 || useradd mongod", warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin mongod".format(mongodpwd), warn=True, hide=True)
                conn.run("mkdir -p /var/run/mongodb && chown -R mongod:mongod /var/run/mongodb", warn=True)

                # mongodb shard
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
                    conn.run("cp -f {}/mongod-shard.service /lib/systemd/system/mongod-{}.service".format(self.remotepath, i), warn=True)
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

                # mongodb config
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

                # mongodb mongos
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

        logger.info(">>>>>>>>>>>>>>>>>>> mongodb cluster init  <<<<<<<<<<<<<<<<<<<<<<")
        # 创建config repset
        host = hosts[0]
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            logger.info("mongodb configsrv repSet...")
            members = []
            for i in range(len(hosts)):
                members.append('{{"_id":{},"host":"{}:27000"}}'.format(i+1, hosts[i]['ip']))
            cfg = 'rs.initiate({{"_id":"config", configsvr: true, "members":[{}] }})'.format(",".join(members))
            logger.info("configsrv: {}".format(cfg))
            try:
                conn.run("echo -e '{}' | mongo --port 27000".format(cfg))
            except:
                logger.error("mongodb configsrv repSet faild！")
                return 1

            logger.info("mongodb shardsrv repSet...")
            dc = {'shard1': 27001, 'shard2': 27002, 'shard3': 27003}
            for h in dc:
                members = []
                for i in range(len(hosts)):
                    members.append('{{"_id":{},"host":"{}:{}"}}'.format(i + 1, hosts[i]['ip'], dc[h]))
                cfg = 'rs.initiate({{"_id":"{}","members":[{}] }})'.format(h, ",".join(members))
                logger.info("{}: {}".format(h, cfg))
                try:
                    conn.run("echo -e '{}' | mongo --port {}".format(cfg, dc[h]))
                except:
                    logger.error("mongodb shardsrv repSet {} faild！".format(h))
                    return 1

        # mongos 服务启动与配置分片路由
        for host in hosts:
            logger.info("=" * 40)
            logger.info("[{}] mongodb install......".format(host['ip']))
            logger.info("=" * 40)
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
                    for host in hosts:
                        members.append("{}:{}".format(host['ip'], dc[h]))
                    cfg = "sh.addShard(\"{}/{}\")".format(h, ",".join(members))
                    logger.info("[{}] mongos: {}".format(host['ip'], cfg))
                    try:
                        conn.run("echo -e '{}' | mongo --port 27017".format(cfg))
                    except:
                        logger.error("mongodb mongos {} init faild！".format(h))
                        return 1

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  MongoDB sharding  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("ip: {}\n".format(";".join(H)))
            f.write("port: 27000,27001,27002,27003,27017\n")
            f.write("系统用户: mongod, 密码: {}\n".format(mongodpwd))

    def mongodbInstall(self, conn, logger):
        # 检查是否已经安装
        logger.info("Check whether mongodb is installed...")
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
        logger.info("upload {} files to remote host...".format(self.pkgpath))
        for root, dirs, files in os.walk(self.pkgpath):
            rpath = root.replace(self.pkgpath, self.remotepath).replace('\\', '/')
            conn.run("mkdir -p {}".format(rpath))
            for file in files:
                localfile = os.path.join(root, file)
                # logger.info("put file: {} to {}".format(localfile, rpath))
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


def check_mongodb(conn):
    r = conn.run("[ -f {0}/bin/mongod ] && [ -f {0}/bin/mongos ]".format(mongoConf.install_path), warn=True, hide=True)
    if r.exited != 0:
        return "未安装"
    r = conn.run("ps -ef | grep mongo | grep -v grep", warn=True, hide=True)
    if r.exited != 0:
        return "已安装，未启动服务"
    else:
        return "服务已启动"