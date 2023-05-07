from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime

from rich import print  # noqa
from rich.pretty import pprint

from inverter.connection import InverterSock
from inverter.data_types import Config, InverterValue, ModbusReadResult, ValueType
from inverter.definitions import get_parameter
from inverter.exceptions import ValidationError
from inverter.validators import InverterValueValidator


logger = logging.getLogger(__name__)


def compute_values(values: dict) -> Iterable[InverterValue]:
    total_power = None
    for no in range(1, 10):
        section = f'PV{no}'

        voltage_name = f'{section} Voltage'
        current_name = f'{section} Current'
        if voltage_name in values and current_name in values:
            name = f'{section} Power'
            voltage: InverterValue = values[voltage_name]
            current: InverterValue = values[current_name]
            try:
                power = voltage.value * current.value
            except TypeError as err:
                print(f'[red]Error calculate: {voltage.value=!r} * {current.value=!r}: {err}')
            else:
                if total_power is None:
                    total_power = power
                else:
                    total_power += power
                logging.debug(
                    'Compute %r from %s %r and %s %r = %s',
                    name,
                    voltage_name,
                    voltage.value,
                    current_name,
                    current.value,
                    total_power,
                )
                power = round(power, 2)
                yield InverterValue(
                    type=ValueType.COMPUTED,
                    name=name,
                    value=power,
                    device_class='power',
                    state_class='measurement',
                    unit='W',
                    result=None,
                )

    if total_power is not None:
        yield InverterValue(
            type=ValueType.COMPUTED,
            name='Total Power',
            value=round(total_power, 2),
            device_class='power',
            state_class='measurement',
            unit='W',
            result=None,
        )


class Inverter:
    def __init__(self, config: Config):
        self.config = config
        self.parameters = get_parameter(config=config)
        self.value_validator = InverterValueValidator(config=config)
        self.inv_sock = InverterSock(config)

    def __enter__(self):
        self.inv_sock.__enter__()
        return self

    def connect(self) -> None:
        self.inv_sock.connect()

    def __iter__(self) -> Iterable[InverterValue]:
        values = {}
        for parameter in self.parameters:
            name = parameter.name

            result = None  # noqa
            for try_count in range(3):
                try:
                    result: ModbusReadResult = self.inv_sock.read_paremeter(parameter=parameter)
                except Exception as err:
                    logger.warning('%s - retry...', err)
                else:
                    break
            if result is None:
                raise Exception from err  # noqa

            value = InverterValue(
                type=ValueType.READ_OUT,
                name=name,
                value=result.parsed_value,
                device_class=parameter.device_class,
                state_class=parameter.state_class,
                unit=parameter.unit,
                result=result,
            )
            if self.config.debug:
                pprint(value, indent_guides=False)

            try:
                self.value_validator(inverter_value=value)
            except ValidationError as err:
                logger.info(f'Validation error: {err}')
                raise

            assert name not in values, f'Double {name=}: {value=} - {values=}'
            values[name] = value
            yield value

        if values := compute_values(values):
            yield from values

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inv_sock.__exit__(exc_type, exc_val, exc_tb)
        if exc_type:
            return False


def set_current_time(inv_sock: InverterSock, address=0x16, verbose=True):
    """
    Set current date time in the inverter device.

    Default start address is 0x16, so that this will be filled:
        0x16 - year + month
        0x17 - day + hour
        0x18 - minute + second
    """
    now = datetime.now()
    if verbose:
        print(f'Send current time: {now}')

    values = [
        256 * (now.year % 100) + now.month,
        256 * now.day + now.hour,
        256 * now.minute + now.second,
    ]
    data = inv_sock.write(address=address, values=values)

    if verbose:
        print(f'Response: {data!r}')
