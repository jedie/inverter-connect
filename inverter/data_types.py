from __future__ import annotations

import dataclasses
import logging
from enum import Enum
from pathlib import Path
from typing import Callable

import msgspec
from ha_services.mqtt4homeassistant.data_classes import MqttSettings
from packaging.version import Version
from rich import print

from inverter.constants import DEFINITIONS_PATH, TYPE_MAP


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
    compact: bool
    verbosity: int
    host: str
    port: int
    mqtt_settings: MqttSettings

    inverter_name: str | None

    socket_timeout: int = 5

    init_cmd: bytes = b'WIFIKIT-214028-READ'

    daily_production_name: str = 'Daily Production'  # Must be the same as in yaml config!
    config_path: Path = None  # e.g.: ~/.config/inverter-connect/

    # Will be set by post init:
    definition_file_path: Path = None
    validation_file_path: Path = None

    def __post_init__(self):
        if self.inverter_name:
            self.definition_file_path = DEFINITIONS_PATH / f'{self.inverter_name}.yaml'
            if not self.definition_file_path.is_file():
                raise FileNotFoundError(
                    f'Wrong inverter name: {self.inverter_name!r}: File not found: {self.definition_file_path}'
                )

            self.validation_file_path = DEFINITIONS_PATH / f'{self.inverter_name}_validations.yaml'
            if not self.validation_file_path.is_file():
                raise FileNotFoundError(
                    f'Wrong inverter name: {self.inverter_name!r}: File not found: {self.validation_file_path}'
                )

        if self.verbosity > 1:
            print(self)


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


@dataclasses.dataclass
class InverterRegisterVersionInfo:
    name: str
    register: int
    inverter: str | None = None


@dataclasses.dataclass
class InverterRegisterVersionResult:
    info: InverterRegisterVersionInfo
    data_hex: str
    version: Version
