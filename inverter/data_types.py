from __future__ import annotations

import dataclasses
from datetime import datetime, time
from enum import Enum
from pathlib import Path
from typing import Callable

import msgspec
from rich import print

from inverter.constants import BASE_PATH, TYPE_MAP


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


@dataclasses.dataclass
class Config:
    inverter_name: str | None

    host: str | None = None
    port: int = 48899

    pause: float = 0.1
    timeout: int = 5

    init_cmd: bytes = b'WIFIKIT-214028-READ'
    verbose: bool = True
    debug: bool = False

    daily_production_name: str = 'Daily Production'  # Must be the same as in yaml config!
    reset_needed_start: time = time(hour=1)
    reset_needed_end: time = time(hour=3)

    # Will be set by post init:
    definition_file_path: Path = None
    validation_file_path: Path = None

    def __post_init__(self):
        if self.inverter_name:
            self.definition_file_path = BASE_PATH / 'definitions' / f'{self.inverter_name}.yaml'
            if not self.definition_file_path.is_file():
                raise FileNotFoundError(
                    f'Wrong inverter name: {self.inverter_name!r}: File not found: {self.definition_file_path}'
                )

            self.validation_file_path = BASE_PATH / 'definitions' / f'{self.inverter_name}_validations.yaml'
            if not self.validation_file_path.is_file():
                raise FileNotFoundError(
                    f'Wrong inverter name: {self.inverter_name!r}: File not found: {self.validation_file_path}'
                )

        if self.verbose or self.debug:
            print(self)


@dataclasses.dataclass
class ResetState:
    started: datetime
    set_time_count: int = 0
    successful_count: int = 0
    last_success_dt: datetime = None
    reset_needed: bool = False


@dataclasses.dataclass
class Parameter:
    start_register: int
    length: int
    group: str
    name: str  # e.g.: "PV1 Voltage" / "PV1 Current" / "Daily Production" etc.
    device_class: str  # e.g.: "voltage" / "current" / "energy" etc.
    state_class: str | None  # e.g.: "measurement" / "total" / "total_increasing" etc.
    unit: str  # e.g.: "V" / "A" / "kWh" etc.
    scale: float  # e.g.: 1 / 0.1
    parser: Callable
    offset: int | None = None
    lookup: dict | None = None


@dataclasses.dataclass
class ValueSpecs:
    name: str
    type: str
    min_value: float
    max_value: float
    type_func: Callable = None

    def __post_init__(self):
        try:
            self.type_func = TYPE_MAP[self.type]
        except KeyError:
            raise KeyError(f'Unsupported type: {self.type!r}')

        if self.min_value is not None:
            self.min_value = self.type_func(self.min_value)

        if self.max_value is not None:
            self.max_value = self.type_func(self.max_value)


class Validators(msgspec.Struct):
    validators: list[ValueSpecs]
