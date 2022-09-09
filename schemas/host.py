from pydantic import BaseModel


class HostBase(BaseModel):
    host: str
    port: int = 22
    user: str = "root"

    class Config:
        orm_mode = True


class Host(HostBase):
    password: str
