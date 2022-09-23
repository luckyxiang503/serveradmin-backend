'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/9/1 11:43
'''
import os
import datetime
import time
import fabric

import SimpleFunc
from config import settings


class fabFastdfs():
    def __init__(self, pkgsdir, d, logger):
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        self.remotepath = "/opt/pkgs/fdfs"
        self.datapath = "/data/fdfs"
        self.confpath = "/etc/fdfs"
        self.libfastcommon_v = "libfastcommon-1.0.42"
        self.fastdfs_v = "fastdfs-5.12"
        self.msgFile = settings.serverMsgText

        self.fdfsMain(d, logger)

    def fdfsMain(self, d, logger):
        hosts = d['host']
        upasswd = SimpleFunc.createpasswd()
        tracker, storage = [], []
        T, S = [], []
        for host in hosts:
            role = host['role'].split(' ')
            if 'tracker' in role:
                tracker.append(host)
                T.append(host['ip'])
            elif 'storage' in role:
                storage.append(host)
                S.append(host['ip'])

        for host in hosts:
            # 连接远程机器
            logger.info("=" * 40)
            logger.info("[{}] fdfs install start......".format(host['ip']))
            logger.info("=" * 40)
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                # 调用安装函数
                rcode = self.fdfsInstall(conn, logger)
                if rcode == 0:
                    logger.info("fdfs install stop.")
                    return
                elif rcode == 1:
                    logger.error("fdfs install faild !")
                    return 1
                logger.info("fdfs install success")

            # 创建fdfs用户
            logger.info("create user fdfs...")
            conn.run("id -u fdfs >/dev/null 2>&1 || useradd fdfs", warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin fdfs".format(upasswd), warn=True, hide=True)

            # 创建数据目录
            logger.info("create data path...")
            conn.run("mkdir -p /data/fdfs/storage /data/fdfs/tracker", warn=True, hide=True)
            conn.run("chown -R fdfs:fdfs /data/fdfs", warn=True, hide=True)

            # 拷贝文件
            logger.info("copy config file...")
            conn.run("[ -f {0}/storage.conf ] && mv {0}/storage.conf {0}/storage.conf_`date +%F%H%M%S`".format(
                self.confpath), warn=True)
            conn.run("[ -f {0}/tracker.conf ] && mv {0}/tracker.conf {0}/tracker.conf_`date +%F%H%M%S`".format(
                self.confpath), warm=True)
            conn.run("cp -f {}/storage.conf {}".format(self.remotepath, self.confpath))
            conn.run("cp -f {}/tracker.conf {}".format(self.remotepath, self.confpath))

            logger.info("rewrite storage conf file...")
            for t in tracker:
                try:
                    conn.run("sed -i '/^#tracker_server=/atracker_server={}:22122'".format(t['ip']), hide=True)
                except:
                    logger.info("rewrite conf file faild!")
                    return 1

            logger.info("copy service file...")
            systempath = "/lib/systemd/system"
            conn.run(
                "[ -f {0}/fdfs_storaged.service ] && mv {0}/fdfs_storaged.service {0}/fdfs_storaged.service_`date +%F%H%M%S`".format(
                    systempath), warn=True)
            conn.run(
                "[ -f {0}/fdfs_trackerd.service ] && mv {0}/fdfs_trackerd.service {0}/fdfs_trackerd.service_`date +%F%H%M%S`".format(
                    systempath), warn=True)
            conn.run("cp -f {}/fdfs_storaged.service {}".format(self.remotepath, systempath))
            conn.run("cp -f {}/fdfs_trackerd.service {}".format(self.remotepath, systempath))

        for host in tracker:
            # 连接远程机器
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                logger.info(">>>>> systemctl start fdfs_trackerd <<<<<")
                try:
                    conn.run("systemctl daemon-reload", hide=True)
                    conn.run("systemctl start fdfs_trackerd", hide=True)
                    conn.run("systemctl enable fdfs_trackerd", hide=True)
                except:
                    logger.info("fdfs_trackerd start faild!")
                    time.sleep(5)

        for host in storage:
            # 连接远程机器
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                logger.info(">>>>> systemctl start fdfs_storaged <<<<<<")
                try:
                    conn.run("systemctl daemon-reload", hide=True)
                    conn.run("systemctl start fdfs_storaged", hide=True)
                    conn.run("systemctl enable fdfs_storaged", hide=True)
                except:
                    logger.info("fdfs_storaged start faild!")
                    time.sleep(5)

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>> fdfs server <<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("system user: fdfs password: {}\n".format(upasswd))
            f.write("tracker server: {}:22122\n".format(":22122 ".join(T)))
            f.write("storage server: {}:23000\n\n".format(":23000 ".join(S)))

    def fdfsInstall(self, conn, logger):
        # 检查是否已经安装
        logger.info(">>>>> check fdfs server isn't installed <<<<<")
        r = conn.run("which fdfs_trackerd && which fdfs_storaged", warn=True, hide=True)
        if r.exited == 0:
            logger.info("fdfs is installed, please check it.")
            return 0
        else:
            logger.info("fdfs not install.")

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

        # 安装fdfs
        logger.info(">>>>> start install fdfs <<<<<")
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}/{}.tar.gz".format(self.remotepath, self.libfastcommon_v), hide=True)
            conn.run("tar -xf {}/{}.tar.gz".format(self.remotepath, self.fastdfs_v), hide=True)

        logger.info("install libfastcommon...")
        try:
            with conn.cd(os.path.join(self.remotepath, self.libfastcommon_v)):
                logger.info("libfastcommon make...")
                conn.run("./make.sh", hide=True)
                logger.info("libfastcommon make install...")
                conn.run("./make.sh install", hide=True)
        except Exception as e:
            logger.error("libfastcommon install faild!, {}".format(e))
            return 1

        logger.info("install fdfs...")
        try:
            with conn.cd(os.path.join(self.remotepath, self.fastdfs_v)):
                logger.info("fdfs make...")
                conn.run("./make.sh", hide=True)
                logger.info("fdfs make install...")
                conn.run("./make.sh install", hide=True)
        except Exception as e:
            logger.error("fdfs install faild!, {}".format(e))
            return 1
