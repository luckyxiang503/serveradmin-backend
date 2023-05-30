'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/7/12 10:55
'''
import argparse
import os
import sys
import yaml
import time

import config

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from fabricsrc import *


def ParseYaml(file):
    '''
    解析 yaml 文件，返回字典
    '''
    if not os.path.exists(file):
        raise "{} not exist!".format(file)

    try:
        with open(file, 'r', encoding='utf-8') as f:
            d = yaml.load(f.read(), Loader=yaml.Loader)
    except Exception as e:
        raise "parse {} faild: {}".format(file, e)

    for i in range(len(d['server'])):
        hl = []
        for host in d['server'][i]['host']:
            dl = {}
            l = host.split(' ')
            for m in l:
                n = m.split("=", 1)
                dl[n[0]] = n[1]
            hl.append(dl)
        d['server'][i]['host'] = hl
    return d


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-install", help="安装", action="store_true")
    parser.add_argument("-check", help="检查", action="store_true")
    parser.add_argument("-config", help="配置文件")
    args = parser.parse_args()

    # 解析 Yaml 文件,得到安装信息
    file = args.config
    d = ParseYaml(file)

    if args.check:
        FabCheckServer.CheckServer(d['server'])

    # 创建日志目录
    logpath = config.settings.logpath
    if not os.path.exists(logpath):
        os.mkdir(logpath)

    if args.install:
        for s in d['server']:
            logger = CommonFunc.StreamLog(name="{}".format(s['srvname']))

            if s['srvname'] == 'base':
                rcode = BaseTools.base(s, logger)
            elif s['srvname'] == "redis":
                redis = FabRedis.fabRedis(s, logger)
                rcode = redis.redisMain()
            elif s['srvname'] == "mysql":
                mysql = FabMysql.fabMysql(s, logger)
                rcode = mysql.mysqlMain()
            elif s['srvname'] == 'rocketmq':
                rocketmq = FabRocketMq.fabRocketmq()
                rcode = rocketmq.rocketmqMain(s, logger)
            elif s['srvname'] == 'jdk':
                rcode = FabApp.jdkMain(s, logger)
            elif s['srvname'] == 'app':
                rcode = FabApp.appinit(s, logger)
            elif s['srvname'] == 'consul':
                rcode = FabConsul.consulMain(s, logger)
            elif s['srvname'] == 'nginx':
                nginx = FabTengine.fabTengine(s, logger)
                rcode = nginx.tengineMain()
            elif s['srvname'] == 'mongodb':
                mongod = FabMongodb.fabMongodb()
                rcode = mongod.mongodbMain(s, logger)
            elif s['srvname'] == 'zookeeper':
                zookeeper = FabZookeeper.fabZookeeper()
                rcode = zookeeper.zookeeperMain(s, logger)
            else:
                raise "srvname not ture,please check it!"
        time.sleep(5)
        print("\n\ninstall finished, server msg is write to \"ServerMsg.txt\".\n\n")
