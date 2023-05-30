"""
    @Time        : 2023/3/22 15:42
    @Author      : Xiang
"""
import fabric

from schemas.host import Host


def conn_test(host: Host):
    with fabric.Connection(host=host.host, port=host.port, user=host.user,
                           connect_kwargs={"password": host.password}, connect_timeout=5) as conn:
        try:
            conn.run("uname", hide=True)
            return True
        except:
            return False