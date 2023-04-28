from __future__ import annotations

import dataclasses
import logging
import socket
import time

from rich import print  # noqa

from inverter.config import Config
from inverter.constants import AT_READ_FUNC_NUMBER, AT_WRITE_FUNC_NUMBER, ERROR_STR_NO_DATA
from inverter.definitions import Parameter
from inverter.exceptions import CrcError, ModbusNoData, ModbusNoHexData, ParseModbusValueError, ReadTimeout


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class InverterInfo:
    ip: str
    mac: str
    serial: int


@dataclasses.dataclass
class RawModBusResponse:
    prefix: str
    data: str


@dataclasses.dataclass
class ModbusResponse:
    slave_id: int
    modbus_function: int
    data_hex: str


@dataclasses.dataclass
class ModbusReadResult:
    parameter: Parameter
    parsed_value: float | str
    response: ModbusResponse = None


def make_modbus_result(*, response: ModbusResponse, parameter: Parameter) -> ModbusReadResult:
    parser_func = parameter.parser
    data_hex = response.data_hex
    logger.debug('Call %s with %r', parser_func.__class__.__name__, data_hex)
    try:
        parsed_value = parser_func(
            data_hex=data_hex,
            scale=parameter.scale,
            offset=parameter.offset,
            lookup=parameter.lookup,
        )
    except (ValueError, AssertionError) as err:
        raise ParseModbusValueError(f'Parser error with {response=} {parameter=}: {err}')
    logger.debug(f'{parsed_value=}')
    result = ModbusReadResult(parameter=parameter, response=response, parsed_value=parsed_value)
    logger.debug('%s', result)
    return result


def modbus_crc(data):
    """
    >>> hex(modbus_crc(b'foobar'))
    '0xabc8'
    """
    POLY = 0xA001
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ POLY
            else:
                crc = crc >> 1
    return crc


def get_business_field(
    start_register: int,
    length: int,
    slave_id: int,
    modbus_function: int,
    values: None | list[int, ...] = None,
):
    """
    >>> get_business_field(0x0056, length=1, slave_id=1, modbus_function=3).hex()
    '010300560001641a'
    >>> get_business_field(0x0056, length=1, slave_id=1, modbus_function=10, values=[0xcd]).hex()
    '010a00560001000200cd34f2'
    """
    request_data = bytearray([slave_id, modbus_function])
    request_data.extend(start_register.to_bytes(2, 'big'))
    request_data.extend(length.to_bytes(2, 'big'))

    if values:
        assert length == len(values), f'{length=} {values=}'
        request_data.extend((length * 2).to_bytes(2, 'big'))
        for value in values:
            request_data.extend(value.to_bytes(2, 'big'))

    crc = modbus_crc(request_data)
    request_data.extend(crc.to_bytes(2, 'little'))
    return request_data


def parameter2modbus_at_command(
    start_register: int,
    length: int,
    modbus_function: int,
    values: None | list[int, ...] = None,
) -> str:
    """
    >>> parameter2modbus_at_command(start_register=0x0056, length=1, modbus_function=3)
    'INVDATA=8,010300560001641a'
    >>> parameter2modbus_at_command(start_register=0x0056, length=1, modbus_function=10, values=[0xcd])
    'INVDATA=12,010a00560001000200cd34f2'
    """
    request_data = get_business_field(
        start_register=start_register,
        length=length,
        slave_id=1,
        modbus_function=modbus_function,
        values=values,
    )
    cmd_length = len(request_data)
    at_command = f'INVDATA={cmd_length},{request_data.hex()}'
    return at_command


def parse_response(data: bytes) -> RawModBusResponse:
    """
    >>> parse_response(b'+ok=01\x1003\x1004\x1001\x105E\x1000\x1000\x109A\x101D\x10\\r\\n\\r\\n')
    RawModBusResponse(prefix='+ok', data='010304015E00009A1D')
    """
    logger.debug(f'parse_response({data=})')
    data = data.decode('ASCII')
    data = data.rstrip('\r\n')
    data = data.replace('\x10', '')  # FIXME
    logger.debug(f'{data=}')

    if data == '+ok':
        result = RawModBusResponse(prefix=data, data='')
    else:
        try:
            prefix, data = data.split('=', 1)
        except ValueError as err:
            raise ValueError(f'{data=}: {err}')

        result = RawModBusResponse(prefix=prefix, data=data)
    logger.debug('%s', result)
    return result


def parse_modbus_response(data: str) -> ModbusResponse:
    logger.debug(f'parse_modbus_response({data=})')
    if data == ERROR_STR_NO_DATA:
        raise ModbusNoData

    try:
        data_bytes = bytes.fromhex(data)
    except ValueError as err:
        logger.warning(f'Value error with {data=}: {err}')
        raise ModbusNoHexData(data=data)

    logger.debug(f'{data_bytes=}')

    calculated_crc = modbus_crc(data_bytes[:-2])
    calculated_crc = calculated_crc.to_bytes(2, 'little')
    got_crc = data_bytes[-2:]
    if got_crc != calculated_crc:
        raise CrcError(f'{got_crc.hex()=} {calculated_crc.hex()=} from {data=}')

    length = data_bytes[2]
    data = data_bytes[3:-2]
    assert len(data) == length, f'Data is not {length=}: {data=}'

    result = ModbusResponse(
        slave_id=data_bytes[0],
        modbus_function=data_bytes[1],
        data_hex=data.hex(),
    )
    logger.debug('%s', result)
    return result


class InverterSock:
    def __init__(self, config: Config):
        self.config = config

        self.dock = None
        self.inverter_info = None

    def __enter__(self):
        logger.info(f'Connect to {self.config.host}:{self.config.port}...')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(self.config.timeout)

        self.inverter_info = self.init_inventer()

        return self

    def send(self, *, command: bytes):
        if self.config.debug:
            print(f'send: {command}', end='...', flush=True)
        self.sock.sendto(command, (self.config.host, self.config.port))

        if self.config.debug:
            print('OK', flush=True)

        time.sleep(self.config.pause)

    def recv_command(self, *, command: bytes, buffer_size=1024):
        self.send(command=command)

        if self.config.debug:
            print('recv', end='...', flush=True)

        try:
            data = self.sock.recv(buffer_size)
        except TimeoutError as err:
            raise ReadTimeout(f'Get no response from {self.config.host}: {err}')
        else:
            if self.config.debug:
                print(f'{data}', flush=True)

            return data

    def at_command(self, command: str, buffer_size=1024):
        assert not command.startswith('AT+'), f'Remove "AT+" prefix from: {command=}'
        assert not command.endswith('\n'), f'Line ending found in: {command=}'
        command = f'AT+{command}\n'.encode()

        for try_count in range(3):
            try:
                return self.recv_command(command=command, buffer_size=buffer_size)
            except ReadTimeout as err:
                logger.warning('%s - retry...', err)
                self.recv_command(command=self.config.init_cmd)
                self.send(command=b'+ok')
                print('retry...', end='')
        raise ReadTimeout from err  # noqa

    def cleaned_at_command(self, command: str, buffer_size=1024) -> str:
        logger.debug(f'cleaned_at_command({command=})')

        data = self.at_command(command, buffer_size=buffer_size)
        logger.debug(f'{data=}')

        raw_modbus_response: RawModBusResponse = parse_response(data=data)
        logger.debug(f'{raw_modbus_response=}')
        if data == 'no data':
            raise ModbusNoData

        return raw_modbus_response.data

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('\nSigning off with "AT+Q"', end='...')
        self.send(command=b'AT+Q\n')
        print('Goodbye ;)\n')
        if exc_type:
            return False

    def init_inventer(self):
        data = self.recv_command(command=self.config.init_cmd)
        self.send(command=b'+ok')
        data = data.decode()
        data = data.split(',')
        return InverterInfo(ip=data[0], mac=data[1], serial=int(data[2]))

    def read(self, *, start_register: int, length: int) -> ModbusResponse:
        if self.config.debug:
            print(f'Read {length} value(s) from start register: {hex(start_register)}')

        command = parameter2modbus_at_command(
            start_register=start_register,
            length=length,
            modbus_function=AT_READ_FUNC_NUMBER,
        )
        if self.config.debug:
            print(f'AT command: {command}')

        data: str = self.cleaned_at_command(command=command)
        try:
            response: ModbusResponse = parse_modbus_response(data=data)
        except ParseModbusValueError as err:
            raise ParseModbusValueError(f'parse error: {data=}: {err}')
        return response

    def read_paremeter(self, *, parameter: Parameter) -> ModbusReadResult:
        if self.config.debug:
            print(parameter)

        try:
            response: ModbusResponse = self.read(
                start_register=parameter.start_register,
                length=parameter.length,
            )
        except ModbusNoData:
            # Modbus register value is: b'no data'
            result = ModbusReadResult(parameter=parameter, parsed_value='no data')
        else:
            result: ModbusReadResult = make_modbus_result(response=response, parameter=parameter)
        return result

    def write(self, *, address: int, values: list[int, ...]):
        if self.config.debug:
            print(f'Write {" ".join(hex(value) for value in values)} to {hex(address)}')

        command = parameter2modbus_at_command(
            start_register=address,
            length=len(values),
            modbus_function=AT_WRITE_FUNC_NUMBER,
            values=values,
        )
        if self.config.debug:
            print(f'AT command: {command}')

        data: str = self.cleaned_at_command(command=command)
        return data
