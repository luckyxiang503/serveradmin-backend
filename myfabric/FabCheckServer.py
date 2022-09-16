'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/16 16:45
'''
import time
import fabric
import SimpleFunc


class bcolors:
    # Reset
    Coloroff = '\033[0m'  # Text Reset

    # Regular Colors
    Black = '\033[0;30m'  # Black
    Red = '\033[0;31m'  # Red
    Green = '\033[0;32m'  # Green
    Yellow = '\033[0;33m'  # Yellow
    Blue = '\033[0;34m'  # Blue
    Purple = '\033[0;35m'  # Purple
    Cyan = '\033[0;36m'  # Cyan
    White = '\033[0;37m'  # White

def title(s):
    print(bcolors.Blue + ">"*20 + "  {}  ".format(s) + "<"*20 + bcolors.Coloroff)

class CheckServer():
    def __init__(self, l):
        self.checkmain(l)

    def checkmain(self, lst):
        for s in lst:
            hosts = s['host']
            if s['srvname'] == "redis":
                self.checkredis(hosts)
            elif s['srvname'] == "mysql":
                self.checkmysql(hosts)
            elif s['srvname'] == 'rocketmq':
                self.checkrocketmq(hosts)
            elif s['srvname'] == 'zookeeper':
                self.checkzookeeper(hosts)
            elif s['srvname'] == 'jdk':
                self.checkjdk(hosts)
            elif s['srvname'] == 'nginx':
                self.checknginx(hosts)
            elif s['srvname'] == 'mongodb':
                mode = s['mode']
                self.checkmongodb(mode, hosts)
            elif s['srvname'] == 'nacos':
                self.checknacos(hosts)
            elif s['srvname'] == 'base':
                tools = s['tool']
                self.checkbase(hosts, tools)
            else:
                continue

    def checkbase(self, hosts, tools):
        for host in hosts:
            title("{}: base check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                print("{b}tools:{c}".format(b=bcolors.Cyan, c=bcolors.Coloroff))
                for tool in tools:
                    r = conn.run("which {}".format(tool), warn=True, hide=True)
                    if r.exited == 0:
                        print("{b}  - {s}{c}".format(b=bcolors.Yellow, c=bcolors.Coloroff, s=r.stdout.replace("\n", "")))
                print("\n")

    def checkjdk(self, hosts):
        for host in hosts:
            title("{}: jdk check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                with conn.prefix("source /etc/profile"):
                    r1 = conn.run("echo $JAVA_HOME", hide=True, warn=True)
                    jvhome = r1.stdout.replace("\n", "")
                    if jvhome == "":
                        print("JAVA_HOME: {b}None{c}".format(b=bcolors.Red, c=bcolors.Coloroff))
                    else:
                        print("JAVA_HOME: {b}{s}{c}".format(b=bcolors.Cyan, c=bcolors.Coloroff, s=jvhome))

                    r2 = conn.run("java -version 2>&1 | grep version", warn=True, hide=True)
                    if r2.exited == 0:
                        javav = r2.stdout.split("\"")[-2].replace("\n", "")
                        print("java version: {b}{s}{c}".format(b=bcolors.Cyan, c=bcolors.Coloroff, s=javav))
                    else:
                        print("{b}java not exist!{c}".format(b=bcolors.Red, c=bcolors.Coloroff))
                    print("\n")

    def checknacos(self, hosts):
        for host in hosts:
            title("{}: nacos server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck("java", conn)

    def checkredis(self, hosts):
        for host in hosts:
            title("{}: redis server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck('redis-server', conn)

    def checkmysql(self, hosts):
        for host in hosts:
            title("{}: mysqld server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck("mysqld", conn)

    def checkrocketmq(self, hosts):
        for host in hosts:
            title("{}: rocketmq server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck("java", conn)

    def checkzookeeper(self, hosts):
        for host in hosts:
            title("{}: zookeeper server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck("java", conn)

    def checknginx(self, hosts):
        for host in hosts:
            title("{}: nginx server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck("nginx", conn)

    def checkmongodb(self, mode, hosts):
        for host in hosts:
            title("{}: mongodb server check".format(host['ip']))
            with fabric.Connection(host=host['ip'], port=host['port'], user=host['user'],
                                   connect_kwargs={"password": host['password']}, connect_timeout=10) as conn:
                self.servercheck("mongo", conn)

    def servercheck(self, srvname, conn):
        # r = conn.run("ps -ef | grep {} | grep -v grep".format(srvname), warn=True, hide=True)
        # if r.exited != 0:
        #     print("{b}{srvname} process not exist!{c}".format(b=bcolors.Red, c=bcolors.Coloroff, srvname=srvname))
        # else:
        #     print("{b}{s}{c}\n".format(b=bcolors.Cyan, c=bcolors.Coloroff, s=r.stdout))
        r = conn.run("ss -tunlp | grep {} | column -t".format(srvname), warn=True, hide=True)
        if r.exited != 0:
            print("{b}{srvname} listen port not exist!{c}".format(b=bcolors.Red, c=bcolors.Coloroff, srvname=srvname))
        else:
            print("{b}{s}{c}\n".format(b=bcolors.Yellow, c=bcolors.Coloroff, s=r.stdout))
