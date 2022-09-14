from pydantic import BaseModel
from typing import List


class Host(BaseModel):
    ip: str
    port: int
    user: str
    password: str
    role: str

class Server(BaseModel):
    srvname: str
    mode: str
    tool: list
    host: List[Host]