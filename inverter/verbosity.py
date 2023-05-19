import logging

import click
from rich.logging import RichHandler


OPTION_KWARGS_VERBOSE = dict(
    count=True,
    type=click.IntRange(0, 3),
    default=1,
    help='Verbosity level; Accepts integer value e.g.: "--verbose 2" or can be count e.g.: "-vv" ',
    show_default=True,
)


def setup_logging(*, verbosity: int):
    log_format = '%(message)s'
    if verbosity == 0:
        level = logging.ERROR
    elif verbosity == 1:
        level = logging.WARNING
    elif verbosity == 2:
        level = logging.INFO
        log_format = '%(asctime)s %(message)s'
    else:
        level = logging.DEBUG
        log_format = '%(asctime)s (%(name)s) %(message)s'

    if verbosity:
        print(f'Set log level to: {logging.getLevelName(level)}')
    logging.basicConfig(level=level, format=log_format, datefmt='[%X]', handlers=[RichHandler()], force=True)
