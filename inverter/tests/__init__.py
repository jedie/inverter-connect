import os
import unittest.util

from inverter.utilities.log_setup import basic_log_setup


# Hacky way to expand the failed test output:
unittest.util._MAX_LENGTH = os.environ.get('UNITTEST_MAX_LENGTH', 300)


# Display DEBUG logs in tests:
basic_log_setup(debug=True)
