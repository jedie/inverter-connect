from __future__ import annotations

from collections.abc import Iterable

import yaml
from bx_py_utils.dict_utils import pluck
from bx_py_utils.path import assert_is_file

from inverter.data_types import Config, Parameter
from inverter.utilities.modbus_converter import debug_converter, parse_number, parse_string, parse_swapped_number


rule2converter = {
    1: parse_number,
    3: parse_swapped_number,
    5: parse_string,
}


def get_definition(*, config: Config):
    definition_file_path = config.definition_file_path
    assert_is_file(definition_file_path)
    content = definition_file_path.read_text(encoding='UTF-8')
    data = yaml.safe_load(content)
    return data['parameters']


def convert_lookup(raw_lookup: list):
    """
    >>> convert_lookup([{'key': 2, 'value': 'Normal'},{'key': 3, 'value': 'Warning'}])
    {2: 'Normal', 3: 'Warning'}
    """
    return {entry['key']: entry['value'] for entry in raw_lookup}


def get_parameter(*, config: Config) -> Iterable[Parameter]:
    data = get_definition(config=config)
    parameters = []
    for group_data in data:
        group_name = group_data['group']
        for item in group_data['items']:
            # example = {
            #     'name': 'PV1 Voltage',
            #     'class': 'voltage',
            #     'state_class': 'measurement',
            #     'uom': 'V',
            #     'scale': 0.1,
            #     'rule': 1,
            #     'registers': [109],
            #     'icon': 'mdi:solar-power',
            # }
            rule = item['rule']
            registers = item['registers']

            parameter_kwargs = pluck(item, keys=['name', 'state_class', 'scale', 'offset'])
            if lookup := item.get('lookup'):
                lookup = convert_lookup(lookup)

            converter_func = rule2converter.get(rule, debug_converter)

            parameter = Parameter(
                start_register=registers[0],
                length=len(registers),
                group=group_name,
                lookup=lookup,
                unit=item['uom'],
                parser=converter_func,
                device_class=item['class'],
                **parameter_kwargs,
            )
            parameters.append(parameter)
    return parameters
