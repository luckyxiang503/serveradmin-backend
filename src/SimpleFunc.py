'''
    @Project   : fabric
    @Author    : xiang
    @CreateTime: 2022/8/10 16:59

    一些常用函数
'''
import logging
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


def FileLog(name, host=None, loglevel=logging.DEBUG, logfile=settings.logfile):
    # 创建logger对象
    logger = logging.getLogger(name)
    logger.setLevel(loglevel)
    # 创建 handler，写入文件
    fh = logging.FileHandler(logfile, mode='a')
    fh.setLevel(loglevel)
    # 定义输出格式
    if host == None:
        formatter = logging.Formatter('[%(asctime)s] [%(funcName)s] [%(levelname)s]: %(message)s')
    else:
        formatter = logging.Formatter('[%(asctime)s] [{}] [%(funcName)s] [%(levelname)s]: %(message)s'.format(host))
    fh.setFormatter(formatter)
    # 将对应的handler添加到logger对象中
    logger.addHandler(fh)
    return logger

def StreamLog(name, host=None, loglevel=logging.DEBUG):
    # 创建logger对象
    logger = logging.getLogger(name)
    logger.setLevel(loglevel)
    # 创建 streamhandler
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)
    # 定义输出格式
    if host == None:
        formatter = logging.Formatter('[%(asctime)s] [%(funcName)s] [%(levelname)s]: %(message)s')
    else:
        formatter = logging.Formatter('[%(asctime)s] [{}] [%(funcName)s] [%(levelname)s]: %(message)s'.format(host))
    ch.setFormatter(formatter)
    # 将对应的handler添加到logger对象中
    logger.addHandler(ch)
    return logger