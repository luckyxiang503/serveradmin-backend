import os
import re
import datetime
import time
import fabric
from config import settings, consulConf

msgFile = settings.serverMsgText
pkgsdir = settings.pkgsdir
pkgpath = os.path.join(pkgsdir, "consul")
remotepath = "/opt/pkgs/consul"
consul_v = consulConf.consul_version
consul_template_v = consulConf.consul_template_version


def consulMain(d, logger):
    hosts = d['host']
    hostnum = len(hosts)
    consulenv = d['consulEnv']

    print("nacos需要先安装mysql，暂不支持！")
    return 1
    if d['mode'] == 'server' and hostnum == 3:
        if install_server(hosts, logger) is not None:
            return 1
    elif d['mode'] == 'client':
        join_server = d["join"]
        token = d['token']
        if install_client(hosts, join_server, token, consulenv, logger) is not None:
            return 1
    else:
        logger.error("host num or mode is not true!")
        return 1


def install_server(hosts, logger):
    join_server = []
    for host in hosts:
        join_server.append(host['ip'])

    for host in hosts:
        s = host['ip'].split('.')
        sname = "server-{}-{}".format(s[-2], s[-1])
        # 连接远程机器
        logger.info("=" * 40)
        logger.info("[{}] consul install start......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            rcode = consul_install(conn, logger)
            if rcode is not None:
                logger.error("consul install faild!")
                return 1
            logger.info("consul install success.")

            # 拷贝配置文件并启动服务
            logger.info("copy consul conf file...")
            conn.run("[ -d /var/lib/consul ] || mkdir /var/lib/consul", hide=True, warn=True)
            conn.run("[ -d /var/log/consul ] || mkdir /var/log/consul", hide=True, warn=True)
            conn.run("[ -d /etc/consul-template ] && mv /etc/consul-template /etc/consul-template_{}".format(
                time.strftime("%Y%m%d%H%M%S")), hide=True, warn=True)
            conn.run("[ -d /etc/consul.d ] && mv /etc/consul.d /etc/consul.d_{}".format(time.strftime("%Y%m%d%H%M%S")),
                     hide=True, warn=True)
            conn.run("mkdir /etc/consul-template", hide=True, warn=True)
            conn.run("mkdir /etc/consul.d", hide=True, warn=True)

            with conn.cd(remotepath):
                conn.run("cp -r consul.d/consul-server.json /etc/consul.d/", hide=True)
                conn.run("cp -r consul-template /etc/", hide=True)
                conn.run("cp -f consul.service /lib/systemd/system/", hide=True)
                conn.run("cp -f consul-template.service /lib/systemd/system/", hide=True)

            conn.run("sed -i 's#\"node_name\":\"\"#\"node_name\":\"{}\"#g' /etc/consul.d/consul-server.json".format(sname), hide=True)
            conn.run("sed -i 's#\"bind_addr\":\"\"#\"bind_addr\":\"{}\"#g' /etc/consul.d/consul-server.json".format(host['ip']), hide=True)
            conn.run("sed -i 's#\"retry_join\":\[\]#\"retry_join\":[\"{}\"]#g' /etc/consul.d/consul-server.json".format("\",\"".join(join_server)), hide=True)

            # 服务添加与启动
            logger.info("starting consul server...")
            conn.run("systemctl daemon-reload", hide=True)
            try:
                conn.run("systemctl start consul", hide=True)
                conn.run("systemctl enable consul", hide=True)
            except:
                logger.error("consul server start error.")
                return 1
            logger.info("consul server start success.")

    time.sleep(5)
    host = hosts[0]
    with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
        # 创建master token
        logger.info("create Bootstrap token...")
        r = conn.run("/usr/bin/consul acl bootstrap", hide=True, warn=True)
        if r.exited != 0:
            logger.error("Token create faild.")
            return 1
        s1 = r.stdout.replace("\n", ";")
        s2 = re.search(r"SecretID:.*?;", s1).group()
        Bootstrap_token = s2.split(" ")[-1].replace(";", "")
        logger.info("Bootstrap token: {}".format(Bootstrap_token))

        # 创建agent token
        logger.info("create kv-read token...")
        s = '''
key_prefix  {  
    policy = \\"read\\"
}
'''
        conn.run("echo \"{}\" > /etc/consul.d/kv-read.hcl".format(s), warn=True)
        # 创建policy
        r = conn.run("/usr/bin/consul acl policy create -name kv-read-policy -rules=@/etc/consul.d/kv-read.hcl -token=\'{}\'".format(Bootstrap_token), warn=True, hide=True)
        if r.exited != 0:
            logger.error("policy create faild.")
            return 1
        # 创建token
        r = conn.run("/usr/bin/consul acl token create -description \"kv-read-token\" -policy-name kv-read-policy  -token=\'{}\'".format(Bootstrap_token), warn=True, hide=True)
        if r.exited != 0:
            logger.error("Token create faild.")
            return 1
        s1 = r.stdout.replace("\n", ";")
        s2 = re.search(r"SecretID:.*?;", s1).group()
        client_token = s2.split(" ")[-1].replace(";", "")
        logger.info("agent token: {}".format(client_token))
        conn.run("echo \"Bootstrap token: {}\nkv-read token: {}\" >> /etc/consul.d/token.txt".format(Bootstrap_token, client_token), hide=True, warn=True)

    # 将服务信息写入文件
    logger.info("consul msg write to ServerMsg.txt")
    with open(msgFile, 'a+', encoding='utf-8') as f:
        dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(">>>>>>>>>>>>>>>>>>>>>>>>> consul server <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
        f.write("time: {}\n".format(dtime))
        f.write("Bootstrap token: {}\n".format(Bootstrap_token))
        f.write("kv-read token: {}\n".format(client_token))


def install_client(hosts, join_server, token, consulenv, logger):
    l = []
    for host in hosts:
        s = host['ip'].split('.')
        cname = "client-{}-{}".format(s[-2], s[-1])
        tag = host['tag']
        l.append("ip: {}, tag: {}".format(host['ip'], tag))

        # 连接远程机器
        logger.info("=" * 40)
        logger.info("[{}] consul install start......".format(host['ip']))
        logger.info("=" * 40)
        with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                               connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
            rcode = consul_install(conn, logger)
            if rcode is not None:
                logger.error("consul install faild!")
                return 1
            logger.info("consul install success.")

            # 拷贝配置文件并启动服务
            logger.info("copy consul-template file...")
            conn.run("[ -d /etc/consul-template ] && mv /etc/consul-template /etc/consul-template_{}".format(time.strftime("%Y%m%d%H%M%S")), hide=True, warn=True)
            conn.run("mkdir /etc/consul-template", hide=True, warn=True)

            with conn.cd(remotepath):
                conn.run("cp -r consul-template /etc/", hide=True)
                conn.run("cp -f consul-template.service /lib/systemd/system/", hide=True)

            if consulenv == "dev":
                ConsulGroup = "dev/{}".format(tag)
            elif consulenv == "uat":
                ConsulGroup = "uat/{}".format(tag)
            else:
                logger.error("consulEnv is not set or set incorrectly!")
                return 1
            conn.run("sed -i 's#ConsulGroup#{}#g' /etc/consul-template/iptables.ctmpl".format(ConsulGroup), hide=True)
            conn.run("sed -i 's#token = \"\"#token = \"{}\"#' /etc/consul-template/config.hcl".format(token), hide=True, warn=True)
            conn.run("sed -i 's#address = \"\"#address = \"{}\"#' /etc/consul-template/config.hcl".format(join_server), hide=True, warn=True)

            # 服务添加与启动
            logger.info("starting consul-template server...")
            conn.run("systemctl daemon-reload", hide=True)
            try:
                conn.run("systemctl start consul-template", hide=True)
                conn.run("systemctl enable consul-template", hide=True)
            except:
                logger.error("consul-template server start error.")
                return 1
            logger.info("consul-template server start success.")

    # 将服务信息写入文件
    logger.info("consul msg write to ServerMsg.txt")
    with open(msgFile, 'a+', encoding='utf-8') as f:
        dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(">>>>>>>>>>>>>>>>>>>>>>>>> consul agent <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
        f.write("time: {}\n".format(dtime))
        for i in l:
            f.write("{}\n".format(i))


def consul_install(conn, logger):
    # 判断是否已经安装consul
    logger.info("Check whether consul is installed...")
    r = conn.run("which consul &>/dev/null && which consul-template &>/dev/null", warn=True, hide=True)
    if r.exited == 0:
        logger.info("consul is isntalled")
        return 0

    # 遍历目录文件并上传到服务器
    logger.info("upload {} files to remote host...".format(pkgpath))
    for root, dirs, files in os.walk(pkgpath):
        rpath = root.replace(pkgpath, remotepath).replace('\\', '/')
        conn.run("mkdir -p {}".format(rpath))
        for file in files:
            localfile = os.path.join(root, file)
            conn.put(localfile, rpath)

    logger.info("install consul and consul_template")
    try:
        conn.run("unzip -o {}/bin/consul_{}_linux_amd64.zip -d /usr/bin".format(remotepath, consul_v), hide=True)
        conn.run("unzip -o {}/bin/consul-template_{}_linux_amd64.zip -d /usr/bin".format(remotepath, consul_template_v), hide=True)
    except:
        logger.error("install consul faild!")
        return 1