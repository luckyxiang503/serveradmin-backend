'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/22 11:35
'''
import os
import datetime
import fabric
import SimpleFunc

jdkPkgName = "jdk-8u341-linux-x64.tar.gz"
jdkVersion = "jdk1.8.0_341"

def jdkMain(pkgsdir, d):
    hosts = d['host']
    for host in hosts:
        # 连接远程机器
        s = host['ip'].split('.')[-1]
        logger = SimpleFunc.FileLog("jdk_{}".format(s), host['ip'])
        logger.info(">>>>>>>>>>>>>>>>> [{}] jdk install <<<<<<<<<<<<<<<<<<".format(host['ip']))
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            rcode = jdkInstall(pkgsdir, conn, logger)
            if rcode != None:
                logger.error("jdk install faild!")
                return 1
            logger.info("jdk install success.")

def jdkInstall(pkgsdir, conn, logger):
    pkgpath = os.path.join(pkgsdir, "tools")
    localpkg = os.path.join(pkgpath, jdkPkgName)
    remotepath = "/opt/pkgs/tools"
    # 判断本地文件
    if not os.path.exists(localpkg):
        print("{} is not exists".format(localpkg))
        return 1

    # 判断是否已经安装java以及java版本
    logger.info("check java isn't installed.")
    r = conn.run("[ -d /usr/local/{0} ] && /usr/local/{0}/bin/java -version 2>&1 | grep version".format(jdkVersion), warn=True, hide=True)
    if r.exited == 0:
        javav = r.stdout.split("\"")[-2]
        logger.info("java is isntalled, version: {}".format(javav))
        return
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
        conn.run("echo \"PATH=\$PATH:\$JAVA_HOME/bin\" >> /etc/profile")
    conn.run("source /etc/profile")
    logger.info(">>>>>>>>>>>>>>>>>> jdk check <<<<<<<<<<<<<<<<")
    try:
        conn.run("/usr/local/{}/bin/java -version".format(jdkVersion), hide=True)
    except:
        logger.error("java install faild!")
        return 1
    logger.info("jdk install success.")


def appinit(pkgsdir, d):
    hosts = d['host']
    pkgpath = os.path.join(pkgsdir, "tools")
    remotepath = "/opt/pkgs/tools"
    tomcatpkg = "apache-tomcat-8.5.51.tar.gz"
    pinpointpkg = "pinpoint-agent-2.3.3.tar.gz"
    group = "hcapp"
    user = "spring"
    upasswd = SimpleFunc.createpasswd()

    for host in hosts:
        # 连接远程机器
        s = host['ip'].split('.')[-1]
        logger = SimpleFunc.FileLog("app_{}".format(s), host['ip'])
        logger.info(">>>>>>>>>>>>>>>>> app init <<<<<<<<<<<<<<<<<<".format(host['ip']))
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            r = conn.run("[ -d /usr/local/{0} ] && [ -f /usr/local/{0}/bin/java ]".format(jdkVersion), warn=True, hide=True)
            if r.exited != 0:
                logger.info("jdk not installed.")
                rcode = jdkInstall(pkgsdir, conn, logger)
                if rcode != None:
                    logger.error("jdk install faild!")
                    return 1
                logger.info("jdk install success.")

            # 创建用户和目录
            logger.info("add system user...")
            conn.run("groupadd {}".format(group), warn=True, hide=True)
            conn.run("id -u {0} >/dev/null && usermod -g {1} {0} || useradd -g {1} {0}".format(user, group), warn=True, hide=True)
            conn.run("echo '{}' | passwd --stdin {}".format(upasswd, user), warn=True, hide=True)

            # 拷贝文件到远程主机
            logger.info("copy package to remothost.")
            if not os.path.exists(pkgpath):
                logger.error("local path {} not exist.".format(pkgpath))
                return 1
            conn.run("[ -d {0} ] && rm -rf {0}/*".format(remotepath), warn=True, hide=True)
            # 遍历目录文件并上传到服务器
            for root, dirs, files in os.walk(pkgpath):
                rpath = root.replace(pkgpath, remotepath).replace('\\', '/')
                conn.run("mkdir -p {}".format(rpath))
                for file in files:
                    localfile = os.path.join(root, file)
                    logger.info("put file: {} to {}".format(localfile, rpath))
                    conn.put(localfile, rpath)

            # 解压tomcat包
            r = conn.run("[ -d /usr/local/{} ]".format(tomcatpkg), hide=True, warn=True)
            if r.exited != 0:
                logger.info("tar xf {}".format(tomcatpkg))
                conn.run("tar -xf {}/{} -C /usr/local/".format(remotepath, tomcatpkg), hide=True)
            # 解压pinpoint包
            r = conn.run("[ -d /home/{0}/pinpoint ]".format(user), hide=True, warn=True)
            if r.exited != 0:
                logger.info("tar xf {}".format(pinpointpkg))
                conn.run("tar -xf {}/{} -C /home/{}".format(remotepath, pinpointpkg, user), hide=True)
                conn.run("mv /home/{0}/{1} /home/{0}/pinpoint".format(user, pinpointpkg), hide=True)

            conn.run("mkdir -p /logs", warn=True, hide=True)
            conn.run("chown -R {0}:{1} /logs /home/{0}".format(user, group), warn=True, hide=True)

            logger.info("app init finished.")