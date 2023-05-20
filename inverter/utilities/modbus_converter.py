from __future__ import annotations

import logging

from packaging.version import Version


logger = logging.getLogger(__name__)


def hex2int(*, data_hex: str, scale, offset) -> int:
    """
    >>> hex2int(data_hex='0938', scale=0.1, offset=None)
    236.0
    >>> hex2int(data_hex='1388', scale=0.01, offset=None)
    50.0
    >>> hex2int(data_hex='00000168', scale=0.1, offset=None)
    36.0
    """
    logger.debug(f'{data_hex=} {scale=} {offset=}')
    data = bytes.fromhex(data_hex)
    number = int.from_bytes(data, byteorder='big')

    if offset:
        logger.debug(f'{number=} {offset=}')
        number = number - offset
        logger.debug(f'{number=}')

    logger.debug(f'{number=} {scale=}')
    number = number * scale
    logger.debug(f'{number=}')

    result = round(number, 2)
    logger.debug(f'{result=}')
    return result


def parse_number(*, data_hex: str, scale: int | float, offset: int = None, lookup: dict = None):
    """
    >>> parse_number(data_hex='0938', scale=0.1)
    236.0
    >>> parse_number(data_hex='0002', scale=1, lookup={2: 'Normal', 3: 'Warning'})
    'Normal'
    """
    assert len(data_hex) == 4, f'Wrong len {len(data_hex)}: {data_hex=}'
    logger.debug(f'{data_hex=}')
    number = hex2int(data_hex=data_hex, scale=scale, offset=offset)

    if lookup:
        logger.debug(f'Use {lookup=}')
        return lookup.get(number, f'<unknown lookup: {number!r}>')
    else:
        return number


def parse_swapped_number(*, data_hex: str, scale: int | float, offset: int = None, lookup: dict = None):
    """
    >>> parse_swapped_number(data_hex='002b0000', scale=0.1)
    4.3
    >>> parse_swapped_number(data_hex='01900000', scale=0.1)
    40.0
    >>> parse_swapped_number(data_hex='002b', scale=0.1)
    4.3
    """
    assert not lookup
    logger.debug(f'{data_hex=}')

    length = len(data_hex)
    if length == 8:
        # '1234abcd' -> 'abcd1234'
        data_hex = data_hex[-4:] + data_hex[:4]
        logger.debug(f'Swap to: {data_hex=}')
    elif length != 4:
        AssertionError(f'Wrong len {length}: {data_hex=}')
    return hex2int(data_hex=data_hex, scale=scale, offset=offset)


def parse_string(*, data_hex: str, scale, offset, lookup):
    return data_hex


def parse_version_string(*, data_hex: str, scale=None, offset=None, lookup=None) -> Version:
    """
    >>> parse_version_string(data_hex='0114')
    <Version('0.1.1.4')>
    """
    version = Version('.'.join(number for number in data_hex))
    return version


def debug_converter(*, data_hex: str, scale, offset, lookup):
    print(f'Debug converter: {data_hex=} {scale=} {offset=} {lookup=}')
    return f'<raw hex: {data_hex}>'
