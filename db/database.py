import time

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib import parse

from config import settings


pwd = parse.quote_plus(settings.dbpasswd)

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://{}:{}@{}/{}".format(settings.dbuser, pwd, settings.dbhost, settings.dbname)

engine = create_engine(SQLALCHEMY_DATABASE_URL,
                       pool_size=10,
                       pool_recycle=7200,
                       pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
