import logging
from unittest import TestCase

from inverter.data_types import Config, InverterValue, ValueType
from inverter.exceptions import ValidationError
from inverter.validators import InverterValueValidator


class ValidatorsTestCase(TestCase):
    def test_happy_path(self):
        config = Config(inverter_name='deye_2mppt', verbose=False)
        validator = InverterValueValidator(config=config)

        with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
            validator(
                inverter_value=InverterValue(
                    type=ValueType.COMPUTED,
                    name='Total Power',
                    value=30,
                    device_class='power',
                    state_class='measurement',
                    unit='W',
                    result=None,
                )
            )
        self.assertEqual(
            logs.output,
            ["DEBUG:inverter.validators:No validation specs for: 'Total Power', ok."],
        )

        with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
            validator(
                inverter_value=InverterValue(
                    type=ValueType.READ_OUT,
                    name='Radiator Temperature',
                    value=30.5,
                    device_class='temperature',
                    state_class='measurement',
                    unit='°C',
                    result=None,
                )
            )
        self.assertEqual(logs.output, ['DEBUG:inverter.validators:Radiator Temperature value=30.5 is valid, ok.'])

        with self.assertRaises(ValidationError) as err:
            validator(
                inverter_value=InverterValue(
                    type=ValueType.READ_OUT,
                    name='Radiator Temperature',
                    value=-10,
                    device_class='temperature',
                    state_class='measurement',
                    unit='°C',
                    result=None,
                )
            )
        self.assertEqual(str(err.exception), 'Radiator Temperature value=-10.0 is less than -9.9')
