from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterable
from enum import Enum

from rich import print  # noqa

from inverter.config import Config
from inverter.connection import InverterSock, ModbusReadResult
from inverter.definitions import get_parameter


logger = logging.getLogger(__name__)


class ValueType(Enum):
    READ_OUT = 'read out'
    COMPUTED = 'computed'


@dataclasses.dataclass
class InverterValue:
    type: ValueType
    name: str
    value: float | str
    device_class: str  # e.g.: "voltage" / "current" / "energy" etc.
    state_class: str | None  # e.g.: "measurement" / "total" / "total_increasing" etc.
    unit: str  # e.g.: "V" / "A" / "kWh" etc.
    result: ModbusReadResult | None


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
        self.parameters = get_parameter(yaml_filename=config.yaml_filename, debug=config.debug)
        self.inv_sock = InverterSock(config)

    def __enter__(self):
        self.inv_sock.__enter__()
        return self

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
            assert name not in values, f'Double {name=}: {value=} - {values=}'
            values[name] = value
            yield value

        if values := compute_values(values):
            yield from values

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inv_sock.__exit__(exc_type, exc_val, exc_tb)
        if exc_type:
            return False
