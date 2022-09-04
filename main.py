'''
    @Project   : ServerAdmin
    @Author    : xiang
    @CreateTime: 2022/8/24 16:52
'''
from uvicorn import run

if __name__ == '__main__':
    # 启动服务
    run("api:app", host='127.0.0.1', port=5000, reload=True)
