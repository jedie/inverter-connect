import logging
import os
import unittest.util


# Hacky way to expand the failed test output:
unittest.util._MAX_LENGTH = os.environ.get('UNITTEST_MAX_LENGTH', 300)


# Display DEBUG logs in tests:
logging.basicConfig(level=logging.DEBUG)
