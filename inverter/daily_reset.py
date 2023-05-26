from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from inverter.api import Inverter, set_current_time
from inverter.data_types import Config, InverterValue


logger = logging.getLogger(__name__)


class DailyProductionResetState:
    """
    Persistent state for "Daily reset"
    """

    def __init__(self, config_path: Path):
        # config_path = toml_settings.file_path.parent  # FIXME: Get this information on a nicer way ;)
        self.state_file_path = config_path / 'daily_reset_state.txt'

        self.last_reset = self.read_last_reset()
        if not self.last_reset:
            logger.warning('Assume daily reset is done for today')
            self.reset_done()

    @property
    def reset_done_today(self) -> bool:
        return date.today() == self.last_reset

    def reset_done(self) -> None:
        # Reset was successfully done -> Store current date
        today = date.today()
        if self.last_reset is None or today > self.last_reset:
            logger.info('Store today date %s to state file', today)
            self.state_file_path.write_text(today.isoformat())
            self.last_reset = today
        else:
            logger.info('Reset already done today: Skip touch the disk')

    def read_last_reset(self) -> date | None:
        try:
            raw_date_str = self.state_file_path.read_text()
        except OSError as err:
            logger.info('Can not read last reset date from %s: %s', self.state_file_path, err)
            return None

        try:
            last_reset_date = date.fromisoformat(raw_date_str)
        except ValueError as err:
            logger.error('Can not parse last reset date: %s', err)
            return None

        logger.info('Read last reset date: %s', last_reset_date)
        return last_reset_date

    def __str__(self):
        return f'{self.last_reset=} {self.reset_done_today=}'

    def __repr__(self):
        return f'<DailyProductionResetState {self}>'


class DailyProductionReset:
    """
    Deye SUN600 will not automatically reset the "Daily Production" counter.
    To reset this counter it's needed to set the current time
    """

    def __init__(self, reset_state: DailyProductionResetState, inverter: Inverter, config: Config):
        self.reset_state = reset_state
        self.inverter = inverter
        self.config = config

    def __enter__(self):
        return self

    def __call__(self, value: InverterValue):
        assert self.inverter is not None

        if self.reset_state.reset_done_today:
            logger.debug('Not needed: %s', self.reset_state)
            return

        if value.name != self.config.daily_production_name:
            logger.debug('Ignore %r (It is not %r)', value.name, self.config.daily_production_name)
            return

        if value.value != 0:
            logger.info('set current time to reset counter %s', self.reset_state)
            set_current_time(inv_sock=self.inverter.inv_sock)
        else:
            self.reset_state.reset_done()
            logger.info('Successfully reset counter. %s', self.reset_state)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inverter = None
        if exc_type:
            return False
