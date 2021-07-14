# stdlib
from datetime import datetime
import logging

# external
import coloredlogs  # colored logs


def get_logger(log_level, name=__name__):
    """
    Colored logging

    :param log_level:  'warning', 'info', 'debug'
    :param name: logger name (use __name__ variable)
    :return: Logger
    """

    fmt = '%(asctime)s %(threadName)-10s %(levelname)-8s %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    fs = {
        'asctime': {'color': 'green'},
        'hostname': {'color': 'magenta'},
        'levelname': {'color': 'red', 'bold': True},
        'name': {'color': 'magenta'},
        'programname': {'color': 'cyan'},
        'username': {'color': 'yellow'},
    }

    ls = {
        'critical': {'color': 'red', 'bold': True},
        'debug': {'color': 'green'},
        'error': {'color': 'red'},
        'info': {},
        'notice': {'color': 'magenta'},
        'spam': {'color': 'green', 'faint': True},
        'success': {'color': 'green', 'bold': True},
        'verbose': {'color': 'blue'},
        'warning': {'color': 'yellow'},
    }

    logger = logging.getLogger(name)

    # log to file
    now_str = datetime.now().strftime('%F_%T')
    handler = logging.FileHandler(f'{now_str}.log')
    formatter = logging.Formatter(fmt, datefmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # logger.propagate = False  # no logging of libs
    coloredlogs.install(level=log_level, logger=logger, fmt=fmt, datefmt=datefmt, level_styles=ls, field_styles=fs)
    return logger
