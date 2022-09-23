'''
    @Project   : ServerAdmin
    @Author    : xiang
    @CreateTime: 2022/8/24 16:52
'''
from uvicorn import run, config

if __name__ == '__main__':
    log_config = config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s: %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s: %(message)s"

    # 启动服务
    run("api:app", host='127.0.0.1', port=8000, reload=True, log_config=log_config)
