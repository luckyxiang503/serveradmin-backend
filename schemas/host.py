from pydantic import BaseModel


class HostBase(BaseModel):
    host: str
    port: int = 22
    user: str = "root"
    sys_version: str

    class Config:
        orm_mode = True


class Host(HostBase):
    password: str
