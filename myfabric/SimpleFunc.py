'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/10 16:59

    一些常用函数
'''
import logging
import os.path
import random

from config import settings


def createpasswd(length=10):
    str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#%^&*()_+"
    passwd = random.choice(str[0:26]) + random.choice(str[26:52]) + random.choice(str[52:62]) + \
             random.choice(str[62:])
    for i in range(length - 4):
        passwd += random.choice(str)

    random.shuffle(list(passwd))
    new_passwd = "".join(passwd)
    return new_passwd


def FileLog(logfile, loglevel=logging.INFO):
    # 创建logger对象
    logger = logging.getLogger('FabricServer')
    # 清空 handler,避免重复输出
    logger.handlers = []
    # 设置日志等级
    logger.setLevel(loglevel)
    # 创建 handler，写入文件
    logfile1 = settings.logfile
    fh1 = logging.FileHandler(logfile1)
    fh1.setLevel(loglevel)

    logfile2 = os.path.join(settings.logpath, logfile)
    fh2 = logging.FileHandler(logfile2)
    fh2.setLevel(loglevel)
    # 定义输出格式
    formatter = logging.Formatter('[%(asctime)s] [%(funcName)s] [%(levelname)s]: %(message)s')

    fh1.setFormatter(formatter)
    fh2.setFormatter(formatter)

    # 将对应的handler添加到logger对象中
    logger.addHandler(fh1)
    logger.addHandler(fh2)

    return logger


def StreamLog(loglevel=logging.DEBUG):
    # 创建logger对象
    logger = logging.getLogger('FabricServer')
    # 清空 handler,避免重复输出
    logger.handlers = []
    # 设置日志等级
    logger.setLevel(loglevel)
    # 创建 streamhandler
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    # 定义输出格式
    formatter = logging.Formatter('[%(asctime)s] [%(funcName)s] [%(levelname)s]: %(message)s')

    ch.setFormatter(formatter)
    # 将对应的handler添加到logger对象中
    logger.addHandler(ch)
    return logger