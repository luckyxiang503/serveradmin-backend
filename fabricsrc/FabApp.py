'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/22 11:35
'''
import os
import datetime
import fabric
import SimpleFunc
from config import settings, springConf

msgFile = settings.serverMsgText
jdkPkgName = springConf.jdkPkgName
jdkVersion = springConf.jdkVersion
pkgsdir = settings.pkgsdir
pkgpath = os.path.join(pkgsdir, "tools")
remotepath = "/opt/pkgs/tools"


def jdkMain(d, logger):
    hosts = d['host']
    for host in hosts:
        # 连接远程机器
        logger.info("=" * 40)
        logger.info("[{}] jdk install start......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            rcode = jdkInstall(conn, logger)
            if rcode is not None:
                logger.error("jdk install faild!")
                return 1
            logger.info("jdk install success.")


def jdkInstall(conn, logger):
    localpkg = os.path.join(pkgpath, jdkPkgName)
    # 判断本地文件
    if not os.path.exists(localpkg):
        print("{} is not exists".format(localpkg))
        return 1

    # 判断是否已经安装java以及java版本
    logger.info("Check whether jdk is installed...")
    r = conn.run("[ -d /usr/local/{0} ] && /usr/local/{0}/bin/java -version 2>&1 | grep version".format(jdkVersion), warn=True, hide=True)
    if r.exited == 0:
        javav = r.stdout.split("\"")[-2]
        logger.info("java is isntalled, version: {}".format(javav))
        return 0
    else:
        logger.info("java not installed.")

    logger.info("copy package to remothost.")
    try:
        conn.run("mkdir -p {}".format(remotepath), warn=True, hide=True)
        logger.info("put file: {}".format(localpkg))
        conn.put(localpkg, remotepath)
    except:
        logger.error("put file error!")
        return 1

    # 卸载老版本jdk
    logger.info("remove old jdk...")
    conn.run("yum -y remove java", warn=True, hide=True)
    conn.run("rpm -qa | grep openjdk | xargs rpm -e", warn=True, hide=True)

    logger.info("tar -xf {} -C /usr/local/".format(jdkPkgName))
    try:
        with conn.cd(remotepath):
            conn.run("tar -xf {} -C /usr/local/".format(jdkPkgName), hide=True)
    except:
        logger.error("tar {} faild!".format(jdkPkgName))
        return 1
    logger.info("export JAVA_HOME...")
    r = conn.run("grep -E \"JAVA_HOME\" /etc/profile", hide=True, warn=True)
    if r.exited == 0:
        conn.run("sed -i s#^JAVA_HOME.*#JAVA_HOME=/usr/local/{}#g /etc/profile".format(jdkVersion), warn=True)
    else:
        conn.run("echo \"JAVA_HOME=\\\"/usr/local/{}\\\"\" >> /etc/profile".format(jdkVersion))
        conn.run("echo \"export PATH=\$PATH:\$JAVA_HOME/bin\" >> /etc/profile")
    conn.run("source /etc/profile")
    logger.info(">>>>>>>>>>>>>>>>>> jdk check <<<<<<<<<<<<<<<<")
    try:
        conn.run("/usr/local/{}/bin/java -version".format(jdkVersion), hide=True)
    except:
        logger.error("java install faild!")
        return 1
    logger.info("jdk install success.")


def appinit(d, logger):
    hosts = d['host']
    tomcatpkg = springConf.tomcatpkg
    tomcatv = tomcatpkg.replace(".tar.gz", "")
    pinpointpkg = springConf.pinpointpkg
    pinpointv = pinpointpkg.replace(".tar.gz", "")
    group = 'hcapp'
    # l = []

    for host in hosts:
        users = host['appname'].split(',')

        # l.append(host['ip'])
        # 连接远程机器
        logger.info("=" * 40)
        logger.info("[{}] spring init......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            r = conn.run("[ -d /usr/local/{0} ] && [ -f /usr/local/{0}/bin/java ]".format(jdkVersion), warn=True, hide=True)
            if r.exited != 0:
                logger.info("jdk not installed.")
                rcode = jdkInstall(conn, logger)
                if rcode is not None:
                    logger.error("jdk install faild!")
                    return 1
                logger.info("jdk install success.")

            # 拷贝文件到远程主机
            logger.info("copy package to remothost.")
            if not os.path.exists(pkgpath):
                logger.error("local path {} not exist.".format(pkgpath))
                return 1
            conn.run("[ -d {0} ] && rm -rf {0}/*".format(remotepath), warn=True, hide=True)
            # 遍历目录文件并上传到服务器
            logger.info("upload {} files to remote host...".format(pkgpath))
            for root, dirs, files in os.walk(pkgpath):
                rpath = root.replace(pkgpath, remotepath).replace('\\', '/')
                conn.run("mkdir -p {}".format(rpath))
                for file in files:
                    localfile = os.path.join(root, file)
                    # logger.info("put file: {} to {}".format(localfile, rpath))
                    conn.put(localfile, rpath)

            # 解压tomcat包
            r = conn.run("[ -d /usr/local/{} ]".format(tomcatv), hide=True, warn=True)
            if r.exited != 0:
                logger.info("tar xf {}".format(tomcatpkg))
                conn.run("tar -xf {}/{} -C /usr/local/".format(remotepath, tomcatpkg), hide=True)

            # 创建用户和目录
            userinfo = []
            for user in users:
                upasswd = SimpleFunc.createpasswd()
                logger.info("Create user {}...".format(user))
                conn.run("groupadd {}".format(group), warn=True, hide=True)
                conn.run("id -u {0} >/dev/null && usermod -g {1} {0} || useradd -g {1} {0}".format(user, group), warn=True, hide=True)
                conn.run("echo '{}' | passwd --stdin {}".format(upasswd, user), warn=True, hide=True)
                userinfo.append((user, upasswd))

                # 解压pinpoint包
                r = conn.run("[ -d /home/{0}/pinpoint ]".format(user), hide=True, warn=True)
                if r.exited != 0:
                    logger.info("tar xf {}".format(pinpointpkg))
                    conn.run("tar -xf {}/{} -C /home/{}".format(remotepath, pinpointpkg, user), hide=True, warn=True)
                    conn.run("mv /home/{0}/{1} /home/{0}/pinpoint".format(user, pinpointv), hide=True, warn=True)
                    conn.run("cp {}/hip.sh /home/{}/".format(remotepath, user), hide=True, warn=True)

                # 添加免密
                ver36_keys = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDZ8NAezDqe+WjuKJN5SjkETska5NzSpVkZr9rRg+lzCw3x1WQfhIPOspqK6uwv2ZbXmg5oju0gRcBtc0iEzjeHOLyFmwdjJ2FnWGw+96jkDDS4itQ7kRIctwudCK3sX2E2MsPErVBzEB2EOpdypyelje1yhs5dUG/YPboSx8krJDnbQzRazYJ01vrR7tvP4SnHudyfxD+hyQDido5LAjsgUsYcPPPKpNiqBBDUJU+ZJT77zh9HXWHLzmr7vx30gv/d3Xzi27Z5yoJPORhBDFWVI7QKyFeOFxEZhw4lxedx30reCK8YpIDGkaPRsWtJGmCMTR2lIHJjgZZXeVjGPtlh ver@ver36.gzhc.local"
                with conn.cd("/home/{}".format(user)):
                    conn.run("[ -d .ssh ] || mkdir .ssh", hide=True, warn=True)
                    conn.run("chown {}:{} .ssh && chmod 700 .ssh".format(user, group))
                    r = conn.run("[ -f .ssh/authorized_keys ] && grep 'ver@ver36.gzhc.local' .ssh/authorized_keys", hide=True, warn=True)
                    if r.exited != 0:
                        conn.run("echo \"{}\" >> .ssh/authorized_keys".format(ver36_keys))
                        conn.run("chown {}:{} .ssh/authorized_keys && chmod 600 .ssh".format(user, group))

                logger.info("appname: {} init finished.".format(user))

            conn.run("mkdir -p /logs", warn=True, hide=True)
            conn.run("chown -R {0}:{1} /logs /home/{0} && chmod -R 775 /logs".format(users[0], group), warn=True, hide=True)

        # 将服务信息写入文件
        with open(msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>> [{}] app init  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n".format(host['ip']))
            f.write("time: {}\n".format(dtime))
            f.write("Host: {}\n".format(host['ip']))
            for u in userinfo:
                f.write("系统用户: {}, 密码： {}\n".format(u[0], u[1]))


def check_spring(conn):
    r = conn.run("[ -d /usr/local/{0} ] && [ -f /usr/local/{0}/bin/java ]".format(jdkVersion), warn=True, hide=True)
    if r.exited != 0:
        return "jdk未安装"
    # r = conn.run("id -u {} >/dev/null && [ -d /usr/local/{} ]".format(springConf.tomcatpkg.replace(".tar.gz", "")),
    #              warn=True, hide=True)
    # if r.exited != 0:
    #     return "jdk已安装，未初始化"
    # else:
    #     return "jdk已安装，已初始化"