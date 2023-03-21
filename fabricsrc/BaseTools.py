'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/8 16:18
'''
import os
import datetime
import fabric
from config import settings

msgFile = settings.serverMsgText
pkgsdir = settings.pkgsdir


def base(d, logger):
    pkgpath = os.path.join(pkgsdir, "base")
    pypkgpath = os.path.join(pkgsdir, 'pypi')
    remotepath = '/opt/pkgs/base'
    pyremotepath = '/opt/pkgs/pypi'
    hosts = d['host']

    repotools = ['tsar', 'netdata', 'sysstat', 'iotop', 'iftop', 'dstat', 'net-tools', 'clamav']
    piptools = ['glances', 'asciinema']

    res = []

    for host in hosts:
        logger.info("=" * 40)
        logger.info("[{}] base install......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            # 拷贝文件到远程主机
            logger.info("copy package to remothost......")
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
                    #logger.info("put file: {} to {}".format(localfile, rpath))
                    conn.put(localfile, rpath)

            # 拷贝pypi文件到远程主机
            if not os.path.exists(pypkgpath):
                logger.error("local path {} not exist.".format(pypkgpath))
                return 1
            conn.run("[ -d {0} ] && rm -rf {0}/*".format(pyremotepath), warn=True, hide=True)
            # 遍历目录文件并上传到服务器
            logger.info("copy python package to remothost...")
            for root, dirs, files in os.walk(pypkgpath):
                rpath = root.replace(pypkgpath, pyremotepath).replace('\\', '/')
                conn.run("mkdir -p {}".format(rpath))
                for file in files:
                    localfile = os.path.join(root, file)
                    #logger.info("put file: {} to {}".format(localfile, rpath))
                    conn.put(localfile, rpath)

            # 系统基线修改
            rcode = sysbaseline(conn, logger)
            if rcode is not None:
                logger.error("systemctl baseline faild!")
                return 1

            # 安装工具
            logger.info("Create local yum repos,Please wait 5-10 minutes...")
            rcode = createyumrepos(conn, logger)
            if rcode is not None:
                logger.error("create local yum repos faild!")
                return 1

            logger.info("Start installing tools......")
            result = {
                'host': host['ip'],
                'succ': [],
                'fail': []
            }
            logger.info("installing wget tar unzip gcc make net-tools iptables-services...")
            conn.run("yum -y install wget tar unzip gcc make net-tools iptables-services", warn=True, hide=True)
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
                logger.info("Check whether {} is installed...".format(tool))
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
                if tool == 'netdata':
                    conn.run("sed -i 's/\(bind to =\).*/\\1 0.0.0.0/' /etc/netdata/netdata.conf", warn=True, hide=True)
                    r = conn.run("systemctl start netdata && systemctl enable netdata")
                    if r.exited == 0:
                        logger.info("netdata server start success.")
                    else:
                        logger.error("netdata server start filad.")

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
            f.write("install success: {}\n".format(" ".join(r['succ'])))
            f.write("install faild: {}\n".format(" ".join(r['fail'])))


def sysbaseline(conn, logger):
    logger.info(">>>>> system base line <<<<<")
    logger.info("selinux ......")
    conn.run("setenforce 0", hide=True, warn=True)
    conn.run("sed -i 's/= *enforcing/=permissive/g' /etc/selinux/config", warn=True, hide=True)
    logger.info("selinu finish.")
    logger.info("stop firewalld")
    conn.run("systemctl stop firewalld && systemctl disable firewalld", warn=True, hide=True)
    logger.info("finish.")

    logger.info("system passwd rules ......")
    conn.run("sed -i  's/^\(PASS_MAX_DAYS\).*/\\1   90/' /etc/login.defs", warn=True, hide=True)
    conn.run("sed -i   's/^\(PASS_MIN_DAYS\).*/\\1   3/'  /etc/login.defs", warn=True, hide=True)
    conn.run("ssed -i  's/^\(PASS_MIN_LEN\).*/\\1   10/'  /etc/login.defs", warn=True, hide=True)
    conn.run("sed -i   's/^\(PASS_WARN_AGE\).*/\\1   10/'  /etc/login.defs", warn=True, hide=True)
    r = conn.run("grep \"^SU_WHEEL_ONLY\" /etc/login.defs", warn=True, hide=True)
    if r.exited != 0:
        conn.run("sed -i '/UMASK/a\SU_WHEEL_ONLY     yes' /etc/login.defs", warn=True, hide=True)
    r = conn.run("grep -E \"^auth\ +required\ +pam_tally2.so\ +deny=3\ +unlock_time=300\" /etc/pam.d/sshd", warn=True, hide=True)
    if r.exited != 0:
        conn.run("sed -i '/#%PAM-1.0/aauth required pam_tally2.so deny=3 unlock_time=300 root_unlock_time=10' /etc/pam.d/sshd", warn=True, hide=True)
    r = conn.run("grep -E \"^password\ +requisite\ +pam_cracklib.so retry=3 difok=3 minlen=10 ucredit=-1 lcredit=-2 dcredit=-1 ocredit=-1\" /etc/pam.d/system-auth", warn=True, hide=True)
    if r.exited != 0:
        conn.run("sed -i '/password    required      pam_deny.so/apassword    requisite    pam_cracklib.so retry=3 difok=3 minlen=10 ucredit=-1 lcredit=-2 dcredit=-1 ocredit=-1' /etc/pam.d/system-auth", warn=True, hide=True)
    r = conn.run("grep -E \"^password\ +sufficient.*remember=.*\"  /etc/pam.d/system-auth", warn=True, hide=True)
    if r.exited != 0:
        conn.run("sed -i 's/\(password    sufficient    pam_unix.so.*\)/\\1 remember=5/' /etc/pam.d/system-auth", warn=True, hide=True)

    logger.info("limit nofile ......")
    r = conn.run("grep -E \"^*[ ]+(soft|hard)[ ]+nofile[ ]+65535\" /etc/security/limits.conf", warn=True, hide=True)
    if r.exited != 0:
        conn.run("cp -f /etc/security/limits.conf /etc/security/limits.conf_`date +%F-%H%M%S`", warn=True)
        conn.run("echo \"*          soft    nofile     65535\" >> /etc/security/limits.conf", warn=True)
        conn.run("echo \"*          hard    nofile     65535\" >> /etc/security/limits.conf", warn=True)
    logger.info("limit nofile finish.")


def createyumrepos(conn, logger):
    # 安装本地yum源
    logger.info("check local repos, Please wait 5-10 minutes...")
    r = conn.run("yum repolist | grep -E \"^local\ +\"", warn=True, hide=True)
    if r.exited == 0:
        logger.info("yum local repos is installed.")
        return
    localrepo = "{}/yumrepos".format(pkgsdir)
    logger.info("create yum local repos, Please wait 3-5 minutes...")
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
            # logger.info("put file: {} to {}".format(localfile, repopath))
            conn.put(localfile, repopath)
    logger.info("create local.repo...")
    repofile = '[local]\nname=local repository\nbaseurl=file://{}\ngpgcheck=0\nenabled=1'.format(remoterepo)
    conn.run("echo '{}' > /etc/yum.repos.d/local.repo".format(repofile))
    logger.info("yum makecache...")
    conn.run("yum makecache", hide=True, warn=True)
    logger.info("yum local repos create success.")


def check_base_tools(conn):
    s, f = [], []
    for t in ['tsar', 'netdata', 'sysstat', 'iotop', 'iftop', 'dstat', 'net-tools', 'clamav']:
        r = conn.run("rpm -ql {} &> /dev/null".format(t), warn=True, hide=True)
        if r.exited != 0:
            f.append(t)
        else:
            s.append(t)

    for t in ['glances', 'asciinema']:
        r = conn.run("which {} &> /dev/null".format(t), warn=True, hide=True)
        if r.exited != 0:
            f.append(t)
        else:
            s.append(t)

    if len(f) != 0:
        return "未安装"
    else:
        return "已安装"
