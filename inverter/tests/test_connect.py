from unittest import TestCase

from inverter.connection import ModbusResponse, Parameter, parse_modbus_response


def get_parameter(**kwargs) -> Parameter:
    used_kwargs = dict(
        start_register=0,
        length=0,
        name='',
        unit='',
        scale=None,
        parser=lambda x: x,
    )
    used_kwargs.update(kwargs)
    return Parameter(**used_kwargs)


class ConnectTestCase(TestCase):
    def test_parse_modbus_response(self):
        self.assertEqual(
            parse_modbus_response('010302012D79C9'),
            ModbusResponse(slave_id=1, modbus_function=3, data_hex='012d'),
        )

        self.assertEqual(
            parse_modbus_response('010304002B00008A3B'),
            ModbusResponse(slave_id=1, modbus_function=3, data_hex='002b0000'),
        )
