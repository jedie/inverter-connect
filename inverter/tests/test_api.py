from unittest import TestCase

from inverter.api import InverterValue, ValueType, compute_values


class ApiTestCase(TestCase):
    def test_compute_values(self):
        results = list(compute_values(values={}))
        self.assertEqual(results, [])

        values = {
            'PV1 Voltage': InverterValue(type=ValueType.READ_OUT, name='PV1 Voltage', value=30, unit='V', result=None),
            'PV1 Current': InverterValue(type=ValueType.READ_OUT, name='PV1 Current', value=1, unit='A', result=None),
        }
        results = list(compute_values(values))
        self.assertEqual(
            results,
            [
                InverterValue(type=ValueType.COMPUTED, name='PV1 Power', value=30, unit='W', result=None),
                InverterValue(type=ValueType.COMPUTED, name='Total Power', value=30, unit='W', result=None),
            ],
        )

        values['PV2 Voltage'] = InverterValue(
            type=ValueType.READ_OUT, name='PV2 Voltage', value=25, unit='V', result=None
        )
        values['PV2 Current'] = InverterValue(
            type=ValueType.READ_OUT, name='PV2 Current', value=2, unit='A', result=None
        )

        results = list(compute_values(values))
        self.assertEqual(
            results,
            [
                InverterValue(type=ValueType.COMPUTED, name='PV1 Power', value=30, unit='W', result=None),
                InverterValue(type=ValueType.COMPUTED, name='PV2 Power', value=50, unit='W', result=None),
                InverterValue(type=ValueType.COMPUTED, name='Total Power', value=80, unit='W', result=None),
            ],
        )
