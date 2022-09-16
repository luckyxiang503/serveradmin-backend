'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/10 10:03
'''
import os
import datetime
import fabric
import SimpleFunc

class fabTengine():
    def __init__(self, pkgsdir, d):
        self.pkgsdir = pkgsdir
        self.pkgpath = os.path.join(pkgsdir, d['srvname'])
        hosts = d['host']
        self.remotepath = "/opt/pkgs/nginx"
        self.nginxVersion = "tengine-2.3.3"
        self.luajitVersion = "LuaJIT-2.0.4"
        self.nginxPath = "/usr/local/nginx"
        dirpath = os.path.dirname(__file__)
        self.msgFile = os.path.join(os.path.dirname(dirpath), "ServerMsg.txt")

        self.tengineMain(hosts)

    def tengineMain(self, hosts):
        l = []
        for host in hosts:
            l.append(host['ip'])
            s = host['ip'].split('.')[-1]
            logger = SimpleFunc.FileLog("tengine_{}".format(s), host['ip'])

            logger.info(">>>>>>>>>>>>>>>>>>>> [{}] nginx start install <<<<<<<<<<<<<<<<<<<".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                #安装nginx
                rcode = self.tengineInstall(conn, logger)
                if rcode == 0:
                    logger.info("nginx install stop.")
                    return
                elif rcode == 1:
                    logger.error("nginx install faild !")
                    return 1
                logger.info("nginx install success")

                # ngnix配置
                logger.info("copy nginx.conf")
                conn.run("[ -f /etc/nginx/nginx.conf ] && mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf_bak_`date +%F_%H%M%S`", warn=True)
                conn.run("cp -f {}/nginx.conf /etc/nginx/nginx.conf".format(self.remotepath), hide=True)
                logger.info("create user nginx...")
                conn.run("id -u nginx >/dev/null 2>&1 || useradd nginx -s /sbin/nologin", warn=True, hide=True)
                conn.run("mkdir -p /var/log/nginx && chown -R nginx:nginx /var/log/nginx", hide=True)
                conn.run("chown -R nginx:nginx /usr/local/nginx", hide=True)
                logger.info("copy nginx.service...")
                conn.run("cp -f {}/nginx.service /usr/lib/systemd/system/".format(self.remotepath))

                # 启动nginx
                logger.info(">>>>>>>>>>>>> starting nginx <<<<<<<<<<<<<<<<")
                try:
                    conn.run("systemctl start nginx.service")
                    conn.run("systemctl enable nginx.service", hide=True)
                except:
                    logger.error("start nginx faild!")
                    return 1
                logger.info("nginx start success.")

                # nginx服务检查
                self.nginxCheck(conn, logger)

        # 将服务信息写入文件
        with open(self.msgFile, 'a+', encoding='utf-8') as f:
            dtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(">>>>>>>>>>>>>>>>>>>>>>>>>  Nginx server  <<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
            f.write("time: {}\n".format(dtime))
            f.write("Host: {}\n".format(",".join(l)))
            f.write("Config file: /etc/nginx/nginx.conf\n")
            f.write("Logfile: /var/log/nginx\n\n")

    def tengineInstall(self, conn, logger):
        # 判断nginx是否已经安装
        logger.info(">>>>>>>>>>>>>> check nginx server isn't installed <<<<<<<<<<<<<")
        r = conn.run("[ -d {0} ] && [ -f {0}/sbin/nginx ]".format(self.nginxPath), warn=True, hide=True)
        if r.exited == 0:
            logger.info("nginx server is installed, please check it.")
            return 1
        else:
            logger.info("nginx server not install.")

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

        # 安装本地yum源
        rcode = self.createyumrepos(conn, logger)
        if rcode != None:
            logger.error("install local yumrepos faild!")
            return 1

        # 安装依赖包
        logger.info("yum install zlib-devel pcre-devel openssl-devel...")
        try:
            conn.run("yum -y install zlib-devel pcre-devel openssl-devel", hide=True)
        except:
            logger.error("install faild!")
            return 1

        # 编译LuaJIT,使得nginx能支持lua
        logger.info(">>>>>>>>>>>>>>> install luajit <<<<<<<<<<<<<<<<<<<<")
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}.tar.gz".format(self.luajitVersion), hide=True)
        logger.info("install luajit...")
        try:
            with conn.cd("{}/{}".format(self.remotepath, self.luajitVersion)):
                logger.info("make install runing...")
                conn.run("make install PREFIX=/usr/local/luajit", hide=True)
        except:
            logger.error("install luajit faild!")
            return 1
        logger.info("luajit install success.")
        r = conn.run("grep -E \"LUAJIT_(LIB|INC)=/usr/local/luajit.*\" /etc/profile", hide=True, warn=True)
        if r.exited != 0:
            conn.run("echo \"export LUAJIT_LIB=/usr/local/luajit/lib\" >> /etc/profile", hide=True)
            conn.run("echo \"export LUAJIT_INC=/usr/local/luajit/include/luajit-2.0\" >> /etc/profile", hide=True)

        # 编译nginx
        logger.info(">>>>>>>>>>>>>>> install nginx <<<<<<<<<<<<<<<<<<<")
        with conn.cd(self.remotepath):
            conn.run("tar -xf {}.tar.gz".format(self.nginxVersion), hide=True)
        logger.info("install nginx...")
        try:
            with conn.cd("{}/{}".format(self.remotepath, self.nginxVersion)):
                with conn.prefix("source /etc/profile"):
                    logger.info("configure runing...")
                    conn.run("./configure --prefix=/usr/local/nginx/ --conf-path=/etc/nginx/nginx.conf --with-pcre --with-debug --with-http_stub_status_module --with-http_ssl_module --with-ld-opt=-Wl,-rpath,/usr/local/luajit/lib --add-module=modules/ngx_http_lua_module --add-module=modules/ngx_http_upstream_check_module --add-module=modules/ngx_http_reqstat_module", hide=True)
                logger.info("make runing...")
                conn.run("make -j 4 && make install", hide=True)
        except:
            logger.error("install nginx faild!")
            return 1
        logger.info("nginx install success.")

    def createyumrepos(self, conn, logger):
        # 安装本地yum源
        logger.info(">>>>>>>>>>>>>  check local repos  <<<<<<<<<<<<<<")
        r = conn.run("yum repolist | grep -E \"^local\ +\"", warn=True, hide=True)
        if r.exited == 0:
            logger.info("yum local repos is installed.")
            return
        localrepo = "{}/yumrepos".format(self.pkgsdir)
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

    def nginxCheck(self, conn, logger):
        logger.info(">>>>>>>>>>>>>>> check nginx server <<<<<<<<<<<<<<")
        try:
            logger.info("check nginx server process.")
            conn.run("ps -ef | grep nginx | grep -v grep", hide=True)
            logger.info("nginx server listen port.")
            conn.run("ss -tunlp | grep nginx")
        except:
            logger.error("nginx server check error!")
