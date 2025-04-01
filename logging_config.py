import logging
import logging.config

# Configuração básica de logging
def configure_logging():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(module)s - %(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": "sistema.log",  # Nome do arquivo de log
                "level": "DEBUG",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "INFO",
            },
        },
        "root": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
        },
        "loggers": {
            "utils": {
                "handlers": ["file", "console"],
                "level": "DEBUG",
                "propagate": False,
            },
            "database": {
                "handlers": ["file", "console"],
                "level": "DEBUG",
                "propagate": False,
            },
            "api": {
                "handlers": ["file", "console"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)
