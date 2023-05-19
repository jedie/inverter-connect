import logging

import click
from rich import get_console
from rich.logging import RichHandler


MAX_LOG_LEVEL = 3

OPTION_KWARGS_VERBOSE = dict(
    count=True,
    type=click.IntRange(0, MAX_LOG_LEVEL),
    default=0,
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
    else:
        level = logging.DEBUG
        log_format = '(%(name)s) %(message)s'

    console = get_console()
    console.print(f'(Set log level {verbosity}: {logging.getLevelName(level)})', justify='right')
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt='[%x %X.%f]',
        handlers=[RichHandler(console=console, omit_repeated_times=False)],
        force=True,
    )
