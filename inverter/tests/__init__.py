import os
import unittest.util

from inverter.verbosity import MAX_LOG_LEVEL, setup_logging


# Hacky way to expand the failed test output:
unittest.util._MAX_LENGTH = os.environ.get('UNITTEST_MAX_LENGTH', 300)


# Display DEBUG logs in tests:
setup_logging(verbosity=MAX_LOG_LEVEL)
