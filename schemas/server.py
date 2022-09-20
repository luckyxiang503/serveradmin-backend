from pydantic import BaseModel
from typing import List


class HostBase(BaseModel):
    ip: str
    role: str


class Host(HostBase):
    port: int
    user: str
    password: str


class ServerBase(BaseModel):
    srvname: str
    mode: str


class Server(ServerBase):
    host: List[HostBase]


class ServerRecord(ServerBase):
    id: int
    host: List[HostBase]
    createtime: str
    updatetime: str
    status: int
    logfile: str


class ServerInstall(ServerBase):
    id: int
    host: List[Host]
    logfile: str