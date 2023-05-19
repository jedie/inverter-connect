from unittest import TestCase

from inverter.connection import parse_modbus_response, parse_response
from inverter.data_types import ModbusResponse, Parameter, RawModBusResponse


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


class ConnectionTestCase(TestCase):
    def test_parse_modbus_response(self):
        self.assertEqual(
            parse_modbus_response('010302012D79C9'),
            ModbusResponse(slave_id=1, modbus_function=3, data_hex='012d'),
        )

        self.assertEqual(
            parse_modbus_response('010304002B00008A3B'),
            ModbusResponse(slave_id=1, modbus_function=3, data_hex='002b0000'),
        )

    def test_parse_response(self):
        self.assertEqual(
            parse_response(b'+ok=\n\rCh,SSID,BSSID,Security,Indicator\n\r+ok\r\n\r\n'),
            RawModBusResponse(prefix='+ok=', data='Ch,SSID,BSSID,Security,Indicator'),
        )
        self.assertEqual(
            parse_response(b'-1\n\n+ok=214028'),
            RawModBusResponse(prefix='-1\n\n+ok=', data='214028'),
        )
        self.assertEqual(
            parse_response(b'+ERR=-3\r\n\r\n'),
            RawModBusResponse(prefix='', data='+ERR=-3'),
        )
