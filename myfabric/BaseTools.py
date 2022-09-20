'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/8 16:18
'''
import contextlib
import os
import datetime
import fabric
import SimpleFunc

dirpath = os.path.dirname(__file__)
msgFile = os.path.join(os.path.dirname(dirpath), "ServerMsg.txt")


def base(pkgsdir, d):
    pkgpath = os.path.join(pkgsdir, "base")
    pypkgpath = os.path.join(pkgsdir, 'pypi')
    remotepath = '/opt/pkgs/base'
    pyremotepath = '/opt/pkgs/pypi'
    hosts = d['host']

    repotools = ['tsar', 'netdata', 'sysstat', 'iotop', 'iftop', 'dstat', 'net-tools', 'clamav']
    piptools = ['glances', 'asciinema']

    res = []

    # 日志定义
    logfile = d['logfile']
    logger = SimpleFunc.FileLog(logfile=logfile)
    for host in hosts:
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 拷贝文件到远程主机
            logger.info(">>>>>>>>>>>>>>>>> copy package to remothost <<<<<<<<<<<<<<<<")
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

            # 拷贝pypi文件到远程主机
            logger.info(">>>>>>>>>>>>>>>>> copy pypkgs to remothost <<<<<<<<<<<<<<<<")
            if not os.path.exists(pypkgpath):
                logger.error("local path {} not exist.".format(pypkgpath))
                return 1
            conn.run("[ -d {0} ] && rm -rf {0}/*".format(pyremotepath), warn=True, hide=True)
            # 遍历目录文件并上传到服务器
            for root, dirs, files in os.walk(pypkgpath):
                rpath = root.replace(pypkgpath, pyremotepath).replace('\\', '/')
                conn.run("mkdir -p {}".format(rpath))
                for file in files:
                    localfile = os.path.join(root, file)
                    logger.info("put file: {} to {}".format(localfile, rpath))
                    conn.put(localfile, rpath)

            # 系统基线修改
            rcode = sysbaseline(remotepath, conn, logger)
            if rcode != None:
                logger.error("systemctl baseline faild!")
                return 1

            # 安装工具
            logger.info(">>>>>>>>>>>>>>> create local repos <<<<<<<<<<<<<<<<<")
            rcode = createLocalRepo(pkgsdir, conn, logger)
            if rcode != None:
                logger.error("create local repos faild!")
                return 1

            logger.info(">>>>>>>>>>>>>>>>>> install tools <<<<<<<<<<<<<<<<<<<<<<")
            result = {
                'host': host['ip'],
                'succ': [],
                'fail': []
            }
            logger.info("install tar unzip gcc make net-tools...")
            conn.run("yum -y install tar unzip gcc make net-tools", warn=True, hide=True)
            r = conn.run("which python3 >/dev/null && which pip3 >/dev/null", warn=True, hide=True)
            if r != 0:
                logger.info("install python3")
                r = conn.run("yum -y install python3", warn=True, hide=True)
                if r.exited != 0:
                    logger.error("python install faild!")
                else:
                    conn.run("pip3 install --upgrade --index-url=file://{}/simple pip".format(pyremotepath), hide=True, warn=True)
                    conn.run("pip3 install --upgrade --index-url=file://{}/simple setuptools".format(pyremotepath), hide=True, warn=True)

            for tool in repotools:
                logger.info("check {} isn't installed.".format(tool))
                r = conn.run("rpm -qa | grep {}".format(tool), warn=True, hide=True)
                if r.exited == 0:
                    logger.info("{} is installed.".format(tool))
                    result['succ'].append(tool)
                    continue

                logger.info("install {}.......".format(tool))
                r = conn.run("yum -y install {}".format(tool), warn=True, hide=True)
                if r.exited != 0:
                    logger.error("{} install faild!".format(tool))
                    result['fail'].append(tool)
                else:
                    logger.info("{} install success".format(tool))
                    result['succ'].append(tool)

            for tool in piptools:
                logger.info("install {}.......".format(tool))
                r = conn.run("pip3 install --index-url=file://{}/simple {}".format(pyremotepath, tool), warn=True, hide=True)
                if r.exited != 0:
                    logger.error("{} install faild!".format(tool))
                    result['fail'].append(tool)
                else:
                    logger.info("{} install success".format(tool))
                    result['succ'].append(tool)
            res.append(result)

    with open(msgFile, 'a+', encoding='utf-8') as f:
        dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  base tools  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
        f.write("time: {}\n".format(dtime))
        for r in res:
            f.write("{}\n".format(r['host']))
            f.write("    install success: {}\n".format(" ".join(r['succ'])))
            f.write("    install faild: {}\n".format(" ".join(r['fail'])))


def createLocalRepo(pkgsdir, conn, logger):
    #判断是否已有本地yum源
    logger.info(">>>>>>>>>>>>>  check local repos  <<<<<<<<<<<<<<")
    r = conn.run("yum repolist | grep -E \"^local\ +\"", warn=True, hide=True)
    if r.exited == 0:
        logger.info("yum local repos is installed.")
        return
    # 安装本地yum源
    localrepo = os.path.join(pkgsdir, 'yumrepos')
    logger.info(">>>>>>>>>>>>  create yum local repos. <<<<<<<<<<<")
    remoterepo = "/opt/yumrepos"
    # 拷贝文件到远程主机
    logger.info("copy repopkgs to remothost.")
    if not os.path.exists(localrepo):
        logger.error("local path {} not exist.".format(localrepo))
        return 1
    conn.run("[ -d {0} ] && rm -rf {0}/*".format(remoterepo), warn=True, hide=True)
    # 遍历目录文件并上传到服务器
    for root, dirs, files in os.walk(localrepo):
        repopath = root.replace(localrepo, remoterepo).replace('\\', '/')
        conn.run("mkdir -p {}".format(repopath))
        for file in files:
            localfile = os.path.join(root, file)
            logger.info("put file: {} to {}".format(localfile, repopath))
            conn.put(localfile, repopath)

    logger.info("create local.repo")
    repofile = '[local]\nname=local repository\nbaseurl=file://{}\ngpgcheck=0\nenabled=1'.format(remoterepo)
    conn.run("echo '{}' > /etc/yum.repos.d/local.repo".format(repofile))
    conn.run("yum makecache", hide=True, warn=True)
    logger.info("yum local repos create success.")

def sysbaseline(remotepath, conn, logger):
    logger.info(">>>>>>>>>>>>>>>>>>> system base line <<<<<<<<<<<<<<<<<<<<")
    logger.info("selinux...")
    conn.run("setenforce 0", hide=True, warn=True)
    conn.run("sed -i 's/= *enforcing/=permissive/g' /etc/selinux/config", warn=True, hide=True)
    logger.info("selinu finish.")

    logger.info("limit nofile ...")
    r = conn.run("grep -E \"^*[ ]+(soft|hard)[ ]+nofile[ ]+65535\" /etc/security/limits.conf", warn=True, hide=True)
    if r.exited != 0:
        conn.run("cp -f /etc/security/limits.conf /etc/security/limits.conf_`date +%F-%H%M%S`", warn=True)
        conn.run("echo \"*          soft    nofile     65535\" >> /etc/security/limits.conf", warn=True)
        conn.run("echo \"*          hard    nofile     65535\" >> /etc/security/limits.conf", warn=True)
    logger.info("limit nofile finish.")

    logger.info("ssh config...")
    conn.run("cp -f /etc/ssh/sshd_config /etc/ssh/sshd_config_`date +%F-%H%M%S`", warn=True)
    conn.run("cp -f {}/sshd_config /etc/ssh/".format(remotepath), warn=True)
    conn.run("cp -f {}/ssh_banner /etc/".format(remotepath), warn=True)
    try:
        conn.run("systemctl restart sshd".format(remotepath))
    except:
        logger.error("sshd restart faild!")
        return 1
    logger.info("ssh config finish.")