from uvicorn import run

if __name__ == '__main__':
    # uvicorn日志格式
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s - %(levelprefix)s: %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "./logs/default.log"
            },
            "access": {
                "formatter": "access",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "./logs/access.log"

            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }

    # 启动服务
    run("api:app", host='0.0.0.0', port=8090, reload=True, log_config=LOGGING_CONFIG)
