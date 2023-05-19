from __future__ import annotations


from bx_py_utils.iteration import chunk_iterable
from rich import get_console, print  # noqa
from rich.table import Table

from inverter.constants import ERROR_STR_NO_DATA
from inverter.data_types import InverterRegisterVersionResult, InverterValue, ModbusResponse, Parameter, ValueType
from inverter.exceptions import ModbusNoData, ModbusNoHexData


def convert_address_option(raw_address: str, debug: bool = True) -> int:
    """
    >>> convert_address_option(raw_address='0x123', debug=True)
    Address: 0x123
    291
    >>> convert_address_option(raw_address='456', debug=True)
    Address: 0x1c8
    456
    """
    if 'x' in raw_address:
        base = 16
    else:
        base = 10
    address = int(raw_address, base=base)
    if debug:
        print('Address:', hex(address))

    return address


def print_hex_table(address, data_hex, title):
    table = Table(title=title)
    table.add_column('Counter\n', justify='right')
    table.add_column('Address\n(hex)', justify='center', style='cyan')
    table.add_column('Address\n(dec)', justify='right', style='cyan')
    table.add_column('[green]Value\n(hex)', justify='center', style='green')
    table.add_column('Value\n(dec)', justify='right', style='magenta')

    for offset, values in enumerate(chunk_iterable(iterable=data_hex, chunk_size=2)):
        hex_value = ''.join(values)
        table.add_row(
            str(offset + 1),  # Counter
            hex(address + offset),  # Address (hex)
            str(address + offset),  # Address (dec)
            hex_value,  # Hex value
            f'{int(hex_value, 16):>2}',  # Decimal
        )

    console = get_console()
    console.print(table)


def print_register(inv_sock, start_register, length):
    try:
        response: ModbusResponse = inv_sock.read(start_register=start_register, length=length)
    except ModbusNoHexData as err:
        print(f'[yellow]Non hex response: [magenta]{err.data!r}')
    except ModbusNoData:
        print('[yellow]no data')
    else:
        print(response)
        print(f'\nResult (in hex): [cyan]{response.data_hex}\n')

        print_hex_table(
            address=start_register,
            data_hex=response.data_hex,
            title=f'[green][bold]{length} value(s) from {hex(start_register)}',
        )


def print_inverter_versions(results: list[InverterRegisterVersionResult], title='Inventer Version Information'):
    table = Table(title=title)
    table.add_column('Counter\n', justify='right')
    table.add_column('Name\n', justify='right')
    table.add_column('Address\n(hex)', justify='center', style='cyan')
    table.add_column('Address\n(dec)', justify='right', style='cyan')
    table.add_column('Value\n(hex)', justify='center', style='')
    table.add_column('[green]Version', justify='right', style='green')

    for offset, result in enumerate(results):
        table.add_row(
            str(offset + 1),  # Counter
            result.info.name,  # Name
            hex(result.info.register + offset),  # Address (hex)
            str(result.info.register + offset),  # Address (dec)
            result.data_hex,  # Hex value
            f'v{result.version}',  # Human readable version
        )

    console = get_console()
    console.print('\n')
    console.rule()
    console.print(table)


def print_inverter_values(values: list[InverterValue], title='Inverter Values'):
    table = Table(title=title)

    table.add_column('Counter', justify='right')
    table.add_column('Name', justify='right')
    table.add_column('Value', justify='left')
    table.add_column('Register', justify='center')
    table.add_column('Length', justify='center')
    table.add_column('Raw data', justify='right')

    for offset, value in enumerate(values):
        if value.value == ERROR_STR_NO_DATA:
            value_str = f'[red]{ERROR_STR_NO_DATA}'
        else:
            value_str = f'[green]{value.value:>12} [blue]{value.unit}'

        if value.type == ValueType.READ_OUT:
            parameter: Parameter = value.result.parameter
            register_str = f'[cyan]{parameter.start_register:04X}'
            length_str = f'{parameter.length}'
            raw_data_str = value.result.response.data_hex
        else:
            register_str = '-'
            length_str = '-'
            raw_data_str = '(Computed)'

        table.add_row(
            str(offset + 1),  # Counter
            f'[blue]{value.name}',
            value_str,
            register_str,
            length_str,
            raw_data_str,
        )

    console = get_console()
    console.print('\n')
    console.rule()
    console.print(table)
