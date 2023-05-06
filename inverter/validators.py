from __future__ import annotations

import logging

import msgspec
from bx_py_utils.path import assert_is_file
from rich import print  # noqa

from inverter.data_types import Config, InverterValue, Validators, ValueSpecs
from inverter.exceptions import ValidationError


logger = logging.getLogger(__name__)


def get_validator_specs(*, config: Config) -> list[ValueSpecs]:
    validation_file_path = config.validation_file_path
    assert_is_file(validation_file_path)
    data = validation_file_path.read_text(encoding='UTF-8')

    validators = msgspec.yaml.decode(data, type=Validators)
    return validators.validators


class InverterValueValidator:
    def __init__(self, *, config: Config):
        self.config = config
        specs = get_validator_specs(config=config)
        self.spec_map = {spec.name: spec for spec in specs}

    def __call__(self, *, inverter_value: InverterValue):
        try:
            spec: ValueSpecs = self.spec_map[inverter_value.name]
        except KeyError as err:
            logger.debug(f'No validation specs for: {err}, ok.')
            return

        value = inverter_value.value

        value = spec.type_func(value)

        if spec.min_value and value < spec.min_value:
            raise ValidationError(f'{inverter_value.name} {value=!r} is less than {spec.min_value!r}')

        if spec.max_value and value > spec.max_value:
            raise ValidationError(f'{inverter_value.name} {value=!r} is greater than {spec.min_value!r}')

        logger.debug(f'{inverter_value.name} {value=!r} is valid, ok.')
