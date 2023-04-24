import logging


def basic_log_setup(*, debug: bool):
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level)
