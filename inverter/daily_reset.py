import logging
from datetime import datetime

from inverter.api import Inverter, set_current_time
from inverter.data_types import Config, InverterValue, ResetState

logger = logging.getLogger(__name__)


class DailyProductionReset:
    """
    Deye SUN600 will not automatically reset the "Daily Production" counter.
    Ro reset this counter it's needed to set the current time
    """

    def __init__(self, reset_state: ResetState, inverter: Inverter, config: Config):
        self.reset_state = reset_state
        self.inverter = inverter
        self.config = config

    def __enter__(self):
        now = datetime.now()
        now_time = now.time()
        if self.config.reset_needed_start <= now_time <= self.config.reset_needed_end:
            self.reset_state.reset_needed = True

        return self

    def __call__(self, value: InverterValue):
        assert self.inverter is not None

        if not self.reset_state.reset_needed:
            logger.debug('Not needed: %s', self.reset_state)
            return

        if value.name != self.config.daily_production_name:
            logger.debug('Ignore %r (It is not %r)', value.name, self.config.daily_production_name)
            return

        if value.value != 0:
            self.reset_state.set_time_count += 1
            logger.info('set current time to reset counter %s', self.reset_state)
            set_current_time(inv_sock=self.inverter.inv_sock)
        else:
            self.reset_state.reset_needed = False
            self.reset_state.last_success_dt = datetime.now()
            self.reset_state.successful_count += 1
            logger.info('Successfully reset counter. %s', self.reset_state)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inverter = None
