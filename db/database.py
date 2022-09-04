'''
    @Project   : ServerAdmin
    @Author    : xiang
    @CreateTime: 2022/8/25 10:06
'''
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib import parse


dbhost = '192.168.10.253'
dbuser = 'serveradmin'
dbpasswd = 'Admin@123'
dbname = 'ServerAdmin'

pwd = parse.quote_plus(dbpasswd)

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://{}:{}@{}/{}".format(dbuser, pwd, dbhost, dbname)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 数据库连接
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

