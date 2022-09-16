from db.database import SessionLocal, Base, engine
from db.models import Server, ServerHost

from datetime import datetime

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    # dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # s_obj = Server(srvname='redis', mode='', createtime=dt, updatetime=None)
    # s_obj.serverhost = [ServerHost(host="127.0.0.1"), ServerHost(host="127.0.0.2")]
    # db.add(s_obj)
    # db.commit()
    servers = db.query(Server).all()
    for server in servers:
        for host in server.serverhost:
            print(server.srvname, host.host)