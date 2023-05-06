import logging
from datetime import datetime, timedelta
from unittest import TestCase

from freezegun import freeze_time

from inverter.daily_reset import DailyProductionReset
from inverter.data_types import Config, InverterValue, ResetState, ValueType


class DailyProductionResetTestCase(TestCase):
    @freeze_time('2020-01-01T00:00:00+0000', as_kwarg='frozen_time')
    def test_happy_path(self, frozen_time):
        start_dt = datetime.now()

        reset_state = ResetState(started=start_dt)
        self.assertEqual(reset_state.started.isoformat(), '2020-01-01T00:00:00')

        class InverterMock:
            writes = []

            def __init__(self):
                self.inv_sock = self

            def write(self, *, address, values):
                self.writes.append((address, values))

        inverter = InverterMock()
        config = Config(inverter_name=None, verbose=False)

        with DailyProductionReset(reset_state, inverter, config) as daily_production_reset:
            self.assertEqual(
                daily_production_reset.reset_state,
                ResetState(started=start_dt, set_time_count=0, successful_count=0, reset_needed=False),
            )

        other_value = InverterValue(
            type=ValueType.COMPUTED,
            name='Total Power',
            value=80,
            device_class='power',
            state_class='measurement',
            unit='W',
            result=None,
        )

        frozen_time.move_to('2020-01-01T00:59:59')
        with DailyProductionReset(reset_state, inverter, config) as daily_production_reset:
            # Not config.reset_needed_start -> False
            self.assertIs(daily_production_reset.reset_state.reset_needed, False)

            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                daily_production_reset(value=other_value)
            self.assertEqual(
                logs.output,
                [
                    'DEBUG:inverter.daily_reset:Not needed: ResetState(started=FakeDatetime(2020, '
                    '1, 1, 0, 0), set_time_count=0, successful_count=0, last_success_dt=None, '
                    'reset_needed=False)'
                ],
            )
            self.assertEqual(inverter.writes, [])

        frozen_time.move_to('2020-01-01T01:00:00')
        with DailyProductionReset(reset_state, inverter, config) as daily_production_reset:
            # We are now in config.reset_needed_start -> True
            self.assertIs(daily_production_reset.reset_state.reset_needed, True)

            # Ignore all non 'Daily Production' values:

            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                daily_production_reset(value=other_value)
            self.assertEqual(
                logs.output, ["DEBUG:inverter.daily_reset:Ignore 'Total Power' (It is not 'Daily Production')"]
            )
            self.assertEqual(inverter.writes, [])

            # set current time, two times:

            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                for _ in range(2):
                    frozen_time.tick(delta=timedelta(minutes=2))
                    daily_production_reset(
                        value=InverterValue(
                            type=ValueType.READ_OUT,
                            name='Daily Production',
                            value=1,  # <<< last reset not successfully
                            device_class='power',
                            state_class='measurement',
                            unit='kWh',
                            result=None,
                        )
                    )
            self.assertEqual(
                logs.output,
                [
                    'INFO:inverter.daily_reset:set current time to reset counter '
                    'ResetState(started=FakeDatetime(2020, 1, 1, 0, 0), set_time_count=1, '
                    'successful_count=0, last_success_dt=None, reset_needed=True)',
                    'INFO:inverter.daily_reset:set current time to reset counter '
                    'ResetState(started=FakeDatetime(2020, 1, 1, 0, 0), set_time_count=2, '
                    'successful_count=0, last_success_dt=None, reset_needed=True)',
                ],
            )
            self.assertEqual(inverter.writes, [(22, [5121, 257, 512]), (22, [5121, 257, 1024])])
            inverter.writes.clear()

            # success, two times

            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                for _ in range(2):
                    frozen_time.tick(delta=timedelta(minutes=2))
                    daily_production_reset(
                        value=InverterValue(
                            type=ValueType.READ_OUT,
                            name='Daily Production',
                            value=0,  # <<< success
                            device_class='power',
                            state_class='measurement',
                            unit='kWh',
                            result=None,
                        )
                    )
            self.assertEqual(
                logs.output,
                [
                    'INFO:inverter.daily_reset:Successfully reset counter. '
                    'ResetState(started=FakeDatetime(2020, 1, 1, 0, 0), set_time_count=2, '
                    'successful_count=1, last_success_dt=FakeDatetime(2020, 1, 1, 1, 6), '
                    'reset_needed=False)',
                    'DEBUG:inverter.daily_reset:Not needed: ResetState(started=FakeDatetime(2020, '
                    '1, 1, 0, 0), set_time_count=2, successful_count=1, '
                    'last_success_dt=FakeDatetime(2020, 1, 1, 1, 6), reset_needed=False)',
                ],
            )
            self.assertEqual(inverter.writes, [])  # no new set time writes
