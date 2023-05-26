import logging
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import TestCase

from freezegun import freeze_time

from inverter.daily_reset import DailyProductionReset, DailyProductionResetState
from inverter.data_types import InverterValue, ValueType
from inverter.tests import fixtures


class DailyProductionResetTestCase(TestCase):
    @freeze_time('2020-01-01T00:00:00+0000', as_kwarg='frozen_time')
    def test_happy_path(self, frozen_time):
        with tempfile.TemporaryDirectory(prefix='test-inverter-connect') as temp_dir:
            temp_path = Path(temp_dir)

            reset_state = DailyProductionResetState(config_path=temp_path)
            # On start, without a state file, the fallback is to don't reset on the same day:
            self.assertEqual(str(reset_state), 'self.last_reset=FakeDate(2020, 1, 1) self.reset_done_today=True')

            class InverterMock:
                writes = []

                def __init__(self):
                    self.inv_sock = self

                def write(self, *, address, values):
                    self.writes.append((address, values))

            inverter = InverterMock()
            config = fixtures.get_config()

            # On start, without a state file, the fallback is to do no reset on the same day:
            with DailyProductionReset(reset_state, inverter, config) as daily_production_reset:
                self.assertIs(daily_production_reset.reset_state.reset_done_today, True)

                with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                    daily_production_reset(
                        value='Fake InverterValue',  # noqa
                    )
                self.assertEqual(
                    logs.output,
                    [
                        'DEBUG:inverter.daily_reset:Not needed: self.last_reset=FakeDate(2020, 1, 1) '
                        'self.reset_done_today=True'
                    ],
                )

                # Next day a reset is needed:
                frozen_time.tick(delta=timedelta(days=1))
                self.assertIs(daily_production_reset.reset_state.reset_done_today, False)

                # Ignore all non 'Daily Production' values:
                with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                    daily_production_reset(
                        value=InverterValue(
                            type=ValueType.COMPUTED,
                            name='Total Power',  # <<< it's not the correct value -> ignore
                            value=80,
                            device_class='power',
                            state_class='measurement',
                            unit='W',
                            result=None,
                        )
                    )
                self.assertEqual(
                    logs.output, ["DEBUG:inverter.daily_reset:Ignore 'Total Power' (It is not 'Daily Production')"]
                )
                self.assertEqual(inverter.writes, [])

                # Trigger **two** times the reset:

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
                        # first call:
                        'INFO:inverter.daily_reset:set current time to reset counter '
                        'self.last_reset=FakeDate(2020, 1, 1) self.reset_done_today=False',
                        #
                        # Second call:
                        'INFO:inverter.daily_reset:set current time to reset counter '
                        'self.last_reset=FakeDate(2020, 1, 1) self.reset_done_today=False',
                    ],
                )
                self.assertIs(daily_production_reset.reset_state.reset_done_today, False)
                self.assertEqual(
                    inverter.writes,
                    [
                        (22, [5121, 512, 512]),  # <<< set time 1
                        (22, [5121, 512, 1024]),  # <<< set time 2
                    ],
                )
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
                        'INFO:inverter.daily_reset:Store today date 2020-01-02 to state file',
                        #
                        'INFO:inverter.daily_reset:Successfully reset counter. '
                        'self.last_reset=FakeDate(2020, 1, 2) self.reset_done_today=True',
                        #
                        'DEBUG:inverter.daily_reset:Not needed: self.last_reset=FakeDate(2020, 1, 2) '
                        'self.reset_done_today=True',
                    ],
                )
                self.assertIs(daily_production_reset.reset_state.reset_done_today, True)
                self.assertEqual(inverter.writes, [])  # no new set time writes

    @freeze_time('2020-01-01T00:00:00+0000', as_kwarg='frozen_time')
    def test_state(self, frozen_time):
        with tempfile.TemporaryDirectory(prefix='test-inverter-connect') as temp_dir:
            temp_path = Path(temp_dir)

            with self.assertLogs(logger=None, level=logging.WARNING) as logs:
                state = DailyProductionResetState(config_path=temp_path)
            self.assertEqual(state.last_reset.isoformat(), '2020-01-01')
            self.assertIs(state.reset_done_today, True)

            self.assertEqual(logs.output, ['WARNING:inverter.daily_reset:Assume daily reset is done for today'])

            # It's stored to disk:
            self.assertEqual(state.state_file_path.read_text(), '2020-01-01')

            # Simulate a "fresh" start -> date should be read from disk:
            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                state = DailyProductionResetState(config_path=temp_path)
            self.assertEqual(state.last_reset.isoformat(), '2020-01-01')
            self.assertIs(state.reset_done_today, True)
            self.assertEqual(logs.output, ['INFO:inverter.daily_reset:Read last reset date: 2020-01-01'])

            # Still the same day:
            frozen_time.move_to('2020-01-01T23:59:59+0000')
            self.assertIs(state.reset_done_today, True)

            # Sleep a day ;)
            frozen_time.move_to('2020-01-02T01:02:03+0000')
            self.assertIs(state.reset_done_today, False)  # Next day -> reset not done
            # File untouched:
            self.assertEqual(state.last_reset.isoformat(), '2020-01-01')

            # Simulate a "fresh" start -> date should be read from disk:
            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                state = DailyProductionResetState(config_path=temp_path)
            self.assertEqual(state.last_reset.isoformat(), '2020-01-01')
            self.assertEqual(logs.output, ['INFO:inverter.daily_reset:Read last reset date: 2020-01-01'])
            self.assertIs(state.reset_done_today, False)  # It's still the "next" day -> reset needed!

            # Let's say the reset was done:
            self.assertIs(state.reset_done_today, False)
            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                state.reset_done()
            self.assertIs(state.reset_done_today, True)
            self.assertEqual(state.last_reset.isoformat(), '2020-01-02')
            self.assertEqual(state.state_file_path.read_text(), '2020-01-02')
            self.assertEqual(logs.output, ['INFO:inverter.daily_reset:Store today date 2020-01-02 to state file'])

            # Simulate a "fresh" start:
            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                state = DailyProductionResetState(config_path=temp_path)
            self.assertEqual(state.last_reset.isoformat(), '2020-01-02')
            self.assertEqual(logs.output, ['INFO:inverter.daily_reset:Read last reset date: 2020-01-02'])
            self.assertIs(state.reset_done_today, True)

            # Skip reset on same day:
            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                state.reset_done()
            self.assertEqual(logs.output, ['INFO:inverter.daily_reset:Reset already done today: Skip touch the disk'])

            # What happen if file is corrupt:
            state.state_file_path.write_text('Bam!')
            with self.assertLogs(logger=None, level=logging.DEBUG) as logs:
                DailyProductionResetState(config_path=temp_path)
            self.assertEqual(
                logs.output,
                [
                    'ERROR:inverter.daily_reset:Can not parse last reset date: Invalid isoformat ' "string: 'Bam!'",
                    'WARNING:inverter.daily_reset:Assume daily reset is done for today',
                    'INFO:inverter.daily_reset:Store today date 2020-01-02 to state file',
                ],
            )
