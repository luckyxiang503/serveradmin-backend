'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/10 10:03
'''
import os
import datetime
import fabric

import CommonFunc
from config import settings, nginxConf


class fabTengine():
    def __init__(self, d, logger):
        self.remotepath = "{}/{}".format(settings.remotedir, d['srvname'])
        self.pkgsdir = settings.pkgsdir
        self.pkgpath = os.path.join(settings.pkgsdir, d['srvname'], "pkgs")
        self.tmplatepath = os.path.join(settings.pkgsdir, d['srvname'], "template")
        self.nginxVersion = nginxConf.nginx_version
        self.luajitVersion = nginxConf.luajit_version
        self.nginxPath = nginxConf.nginx_install_path
        self.msgFile = settings.serverMsgText
        self.logger = logger
        self.d = d

    def tengineMain(self):
        l = []
        hosts = self.d['host']

        for host in hosts:
            l.append(host['ip'])

            self.logger.info("=" * 40)
            self.logger.info("[{}] nginx install start......".format(host['ip']))
            self.logger.info("=" * 40)
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                #安装nginx
                rcode = self.tengineInstall(conn)
                if rcode == 0:
                    self.logger.info("nginx install stop.")
                    return 1
                elif rcode == 1:
                    self.logger.error("nginx install faild !")
                    return 1
                self.logger.info("nginx install success")

                # ngnix配置
                self.logger.info("copy nginx.conf...")
                conn.run("[ -f /etc/nginx/nginx.conf ] && mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf_bak_`date +%F_%H%M%S`", warn=True)
                conn.run("cp -f {}/nginx.conf /etc/nginx/nginx.conf".format(self.remotepath), hide=True)
                self.logger.info("create user nginx...")
                conn.run("id -u nginx >/dev/null 2>&1 || useradd nginx -s /sbin/nologin", warn=True, hide=True)
                conn.run("mkdir -p /var/log/nginx && chown -R nginx:nginx /var/log/nginx", hide=True)
                conn.run("chown -R nginx:nginx /usr/local/nginx", hide=True)
                self.logger.info("create nginx.service...")
                txt = CommonFunc.FillTemplate(self.tmplatepath, 'nginx.service', nginxpath=self.nginxPath)
                conn.run("echo '{}' > /lib/systemd/system/nginx.service".format(txt), hide=True, warn=True)

                # 启动nginx
                self.logger.info(">>>>>>>>>>>>> starting nginx <<<<<<<<<<<<<<<<")
                conn.run("systemctl daemon-reload", hide=True)
                try:
                    conn.run("systemctl start nginx.service")
                    conn.run("systemctl enable nginx.service", hide=True)
                except:
                    self.logger.error("start nginx faild!")
                    return 1
                self.logger.info("nginx start success.")

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Nginx server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Host: {}\n".format(",".join(l)))

    def tengineInstall(self, conn):
        # 判断nginx是否已经安装
        self.logger.info("Check whether nginx is installed...")
        r = conn.run("[ -d {0} ] && [ -f {0}/sbin/nginx ]".format(self.nginxPath), warn=True, hide=True)
        if r.exited == 0:
            self.logger.info("nginx server is installed, please check it.")
            return 1
        else:
            self.logger.info("nginx server not install.")

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
                # self.logger.info("put file: {} to {}".format(localfile, rpath))
                conn.put(localfile, rpath)

        # 安装本地yum源
        rcode = self.createyumrepos(conn)
        if rcode != None:
            self.logger.error("create local yumrepos faild!")
            return 1

        # 安装依赖包
        self.logger.info("yum install zlib-devel pcre-devel openssl-devel...")
        try:
            conn.run("yum -y install zlib-devel pcre-devel openssl-devel", hide=True)
        except:
            self.logger.error("install faild!")
            return 1

        # 编译LuaJIT,使得nginx能支持lua
        self.logger.info(">>>>>>>>>>>>>>> install luajit <<<<<<<<<<<<<<<<<<<<")
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}.tar.gz".format(self.luajitVersion), hide=True)
        self.logger.info("install luajit...")
        try:
            with conn.cd("{}/{}".format(self.remotepath, self.luajitVersion)):
                self.logger.info("make install runing, , Please wait 3-5 minutes...")
                conn.run("make install PREFIX=/usr/local/luajit", hide=True)
        except:
            self.logger.error("install luajit faild!")
            return 1
        self.logger.info("luajit install success.")
        r = conn.run("grep -E \"LUAJIT_(LIB|INC)=/usr/local/luajit.*\" /etc/profile", hide=True, warn=True)
        if r.exited != 0:
            conn.run("echo \"export LUAJIT_LIB=/usr/local/luajit/lib\" >> /etc/profile", hide=True)
            conn.run("echo \"export LUAJIT_INC=/usr/local/luajit/include/luajit-2.0\" >> /etc/profile", hide=True)

        # 编译nginx
        self.logger.info(">>>>>>>>>>>>>>> install nginx <<<<<<<<<<<<<<<<<<<")
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}.tar.gz".format(self.nginxVersion), hide=True)
        self.logger.info("install nginx...")
        try:
            with conn.cd("{}/{}".format(self.remotepath, self.nginxVersion)):
                with conn.prefix("source /etc/profile"):
                    self.logger.info("configure runing, Please wait 5-10 minutes...")
                    conn.run("./configure --prefix=/usr/local/nginx/ --conf-path=/etc/nginx/nginx.conf --with-pcre --with-debug --with-http_stub_status_module --with-http_ssl_module --with-ld-opt=-Wl,-rpath,/usr/local/luajit/lib --add-module=modules/ngx_http_lua_module --add-module=modules/ngx_http_upstream_check_module --add-module=modules/ngx_http_reqstat_module", hide=True)
                self.logger.info("make runing, Please wait 3-5 minutes...")
                conn.run("make -j 4 && make install", hide=True)
        except:
            self.logger.error("install nginx faild!")
            return 1
        self.logger.info("nginx install success.")

    def createyumrepos(self, conn):
        # 安装本地yum源
        self.logger.info("check local repos, Please wait 5-10 minutes...")
        r = conn.run("yum repolist | grep -E \"^local\ +\"", warn=True, hide=True)
        if r.exited == 0:
            self.logger.info("yum local repos is installed.")
            return
        localrepo = "{}/yumrepos".format(self.pkgsdir)
        self.logger.info("create yum local repos, Please wait 3-5 minutes...")
        remoterepo = "/opt/yumrepos"
        # 拷贝文件到远程主机
        self.logger.info("copy repopkgs to remothost.")
        if not os.path.exists(localrepo):
            self.logger.error("local path {} not exist.".format(localrepo))
            return 1
        conn.run("[ -d {0} ] && rm -rf {0}/*".format(remoterepo), warn=True, hide=True)
        # 遍历目录文件并上传到服务器
        for root, dirs, files in os.walk(localrepo):
            repopath = root.replace(localrepo, remoterepo).replace('\\', '/')
            conn.run("mkdir -p {}".format(repopath))
            for file in files:
                localfile = os.path.join(root, file)
                # self.logger.info("put file: {} to {}".format(localfile, repopath))
                conn.put(localfile, repopath)
        self.logger.info("create local.repo...")
        repofile = '[local]\nname=local repository\nbaseurl=file://{}\ngpgcheck=0\nenabled=1'.format(remoterepo)
        conn.run("echo '{}' > /etc/yum.repos.d/local.repo".format(repofile))
        self.logger.info("yum makecache...")
        conn.run("yum makecache", hide=True, warn=True)
        self.logger.info("yum local repos create success.")


def check_nginx(conn):
    r = conn.run("[ -d {0} ] && [ -f {0}/sbin/nginx ]".format(nginxConf.nginx_install_path), warn=True, hide=True)
    if r.exited != 0:
        return "未安装"
    r = conn.run("ps -ef | grep nginx | grep -v grep", warn=True, hide=True)
    if r.exited != 0:
        return "已安装，未启动服务"
    else:
        return "服务已启动"
