# Fabric离线安装常用服务使用手册

### 1、支持组件列表

**已验证操作系统**

- CentOS 7.9

**已验证组件**

- redis

- mysql5

- rocketMQ

- tengine

- jdk

- mongodb

- netdata

- nacos

| 组件                   | 安装方式  | 版本      | 启动用户  | 监听端口           | 配置文件路经                                                 | 日志文件路径                                                 | 数据文件路径                                                 | 服务启停                                                     |
| ---------------------- | --------- | --------- | --------- | ------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| redis单机              | 编译安装  | 6.2.7     | redis     | 6379               | /etc/redis/redis.conf                                        | /var/log/redis/redis.log                                     | /opt/redis/data                                              | systemctl (start \| stop) redis-6379                         |
| redis伪集群            | 编译安装  | 6.2.7     | redis     | 7000-7005          | /etc/redis-cluster/[7000-7005\]/redis.conf                   | /var/log/redis-cluster/[7000-7005\]/redis.log                | /opt/redis-cluster/[7000-7005]                               | systemctl (start \| stop) redis-\[7000-7005\]                |
| redis三节点集群        | 编译安装  | 6.2.7     | redis     | 7000-7001          | /etc/redis-cluster/[7000-7001\]/redis.conf                   | /var/log/redis-cluster/[7000-7001\]/redis.log                | /opt/redis-cluster/[7000-7001]                               | systemctl (start \| stop) redis-\[7000-7001\]                |
| redis六节点集群        | 编译安装  | 6.2.7     | redis     | 7000               | /etc/redis-cluster/7000/redis.conf                           | /var/log/redis-cluster/7000/redis.log                        | /opt/redis-cluster/7000                                      | systemctl (start \| stop) redis-7000                         |
| mysql单机及2节点主从   | rpm包安装 | 5.7.39    | mysql     | 3306               | /etc/my.cnf                                                  | /data/mysql/log                                              | /var/lib/mysql                                               | systemctl (start \| stop) mysqld                             |
| rocketMQ单机与多主集群 | unzip     | 4.9.4     | rocketmq  | 9876,30911,8080    | /opt/rocketMQ/conf/broker.conf                               | /opt/rocketMQ/logs                                           | /opt/rocketMQ/data                                           | systemctl (start \| stop) (rocketmq-namesrv \| rocketmq-broker) |
| tengine                | 编译安装  | 2.3.3     | nginx     | 80                 | /etc/nginx/nginx.conf                                        | /var/log/nginx                                               |                                                              | systemctl (start \| stop) nginx                              |
| jdk                    | tar       | 1.8.0_341 |           |                    |                                                              |                                                              |                                                              |                                                              |
| mongodb单机            | tar       | 5.0.10    | mongod    | 27017              | /etc/mongodb/mongod.conf                                     | /var/log/mongodb/mongod.log                                  | /opt/mongodb/data                                            | systemct (start \| stop) mongod                              |
| mongodb三节点分片集群  | tar       | 5.0.10    | mongod    | 27000-27003, 27017 | /etc/mongodb-cluster/<br/>{shard1,shard2,shard3,configsrv,mongos}/ | /var/log/mongod-cluster/<br/>{shard1,shard2,shard3,configsrv,mongos}/ | /opt/mongodb-cluster/<br/>{shard1,shard2,shard3,configsrv,mongos}/ | systemctl (start \| stop ) (mongod-shard[1-3] \| mongod-config \|mongod-mongos) |
| netdata                | yum       | 1.34.1    | netdata   | 8125,19999         | /etc/netdata/netdata.conf                                    |                                                              |                                                              | systemctl (start \| stop) netdata                            |
| nacos单机及集群        | tar       | 2.1.1     | nacos     | 8848               | /opt/nacos/conf/application.properties<br/>/opt/nacos/conf/cluster.conf | /opt/nacos/logs                                              |                                                              | systemctl (start \| stop) nacos                              |
| zookeeper单机及集群    | tar       | 3.4.14    | zookeeper | 2181               | /opt/zookeeper/conf/zoo.cfg                                  |                                                              | /opt/zookeeper/data                                          | systemctl (start \| stop) zookeeper                          |

**base**

| 软件名称      | 版本       | 部署方式    | 是否支持离线 |
| --------- | -------- | ------- | ------ |
| tsar      | 2.1.1    | yum源安装  | 是      |
| iftop     | 1.0-0.21 | yum源安装  | 是      |
| iotop     | 0.6-4    | yum源安装  | 是      |
| dstat     | 0.7.2-12 | yum源安装  | 是      |
| sysstat   | 10.1.5   | yum源安装  | 是      |
| clamav    | 0.103.7  | yum源安装  | 是      |
| netdata   | 1.34.1   | yum源安装  | 是      |
| glances   | 3.2.7    | pip3源安装 | 是      |
| asciinema | 2.2.0    | pip3源安装 | 是      |

### 2、安装说明

**安装环境**

将fabric离线安装包上传到服务器，进入目录，执行

```bash
sh install_python.sh
```

脚本会安装好python 环境和fabric、PyYaml 模块。

**主函数FabMain.py**

安装时执行:

```bash
python3 FabMain.py [-i | install] fabric.yml
```

检查服务执行:

```bash
python3 FabMain.py [-c | check] fabric.yml
```

**信息记录：ServerMsg.txt**

安装完成后，服务信息会记录在FabMain.py文件目录下的ServerMsg.txt文件中，如下

```ServerMsg.txt
>>>>>>>>>>>>>>>>>>>>>>>>>  mysql 1M1S  <<<<<<<<<<<<<<<<<<<<<<<<<<<
time: 2022-08-08_15:29:02
master: 192.168.195.132:3306
slave: 192.168.195.133:3306
mysql root password: zP5!%qM3Zj
mysql rep passwd: iI2!HkHgtR
mysql data path: /data/mysql
```

**fabric.yml文件**

该文件中记录要安装服务的名称、模式、主机信息，示例如下：

```yaml
pkgsdir: '/opt/pkgs' # 本地包路径
server:
-
    srvname: redis
    mode: 'redis-single' # 单机：redis-single 单机伪集群：redis-cluster-one 三节点集群：redis-cluster-three 六节点集群：redis-cluster-three
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: mysql
    mode: 'mysql-1M1S' # 单机 ：mysql-single 1主1从：mysql-1M1S
    host:
    -
        role: 'master'
        ip: '192.168.195.132'
        port: 22
        user: 'root'
        password: '123456'
    -
        role: 'slave'
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
```

- pkgpath: 本地包路径

- server：固定格式

- srvname: 服务名称（redis, mysql, jdk,rocketmq,tengine...）

- mode: 安装模式，如无可不写

- host: 要安装主机节点的相关信息

- role: 安装节点的属性

**可参考如下配置文件 fabric.yml_demo**

```yaml
pkgsdir: '/opt/pkgs' # 本地包路径
server:
-
    srvname: base
    tool:   # 安装基本工具: tsar、netdata、sysstat、iotop、iftop、dstat、net-tools、glances、asciinema、clamav
        - tsar
        - netdata
        - sysstat
        - iotop
        - iftop
        - dstat
        - net-tools
        - glances
        - asciinema
        - clamav
    host:
    -
        ip: '192.168.195.132'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: redis
    mode: 'redis-single' # 单机：redis-single 单机伪集群：redis-cluster-one 三节点集群：redis-cluster-three 六节点集群：redis-cluster-six
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: mysql
    mode: 'mysql-1M1S' # 单机 ：mysql-single 1主1从：mysql-1M1S
    host:
    -
        role: 'master'  # mysql主从机器标识，master：主  slave: 从
        ip: '192.168.195.132'
        port: 22
        user: 'root'
        password: '123456'
    -
        role: 'slave'
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: rocketmq
    mode: 'rocketmq-single' # 单机：rocketmq-single 多主集群：rocketmq-nM
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'

-
    srvname: jdk
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: app  # 初始化spring环境和安装tomcat
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: nginx
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: mongodb
    mode: 'mongodb-single' # 单机：mongodb-single  分片集群：mongodb-sharding
    host:
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: mongodb
    mode: 'mongodb-sharding'
    host:
    -
        # 表示要部署的组件，shard：数据分片; configsrv：配置服务; mongos: mongos路由; 按空格分割
        role: shard configsrv mongos
        ip: '192.168.195.132'
        port: 22
        user: 'root'
        password: '123456'
    -
        role: shard configsrv
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
    -
        role: shard configsrv
        ip: '192.168.195.134'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: nacos
    mode: "nacos-cluster" # 单机：nacos-single 集群：nacos-cluster
    host:
    -
        ip: '192.168.195.132'
        port: 22
        user: 'root'
        password: '123456'
    -
        ip: '192.168.195.133'
        port: 22
        user: 'root'
        password: '123456'
    -
        ip: '192.168.195.134'
        port: 22
        user: 'root'
        password: '123456'
-
    srvname: zookeeper
    mode: "zookeeper-single" # 单机：zookeeper-single 集群：zookeeper-cluster
    host:
    -
        ip: '192.168.195.132'
        port: 22
        user: 'root'
        password: '123456'
```

##### 附录（更新记录）：

| 版本   | 更新时间       | 更新内容 |
| ---- | ---------- | ---- |
| v1.0 | 2022/08/24 |      |
|      |            |      |