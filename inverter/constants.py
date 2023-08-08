from __future__ import annotations

from pathlib import Path

from bx_py_utils.path import assert_is_file

import inverter


CLI_EPILOG = 'Project Homepage: https://github.com/jedie/inverter-connect'


PACKAGE_ROOT = Path(inverter.__file__).parent.parent
assert_is_file(PACKAGE_ROOT / 'pyproject.toml')

DEFINITIONS_PATH = PACKAGE_ROOT / 'inverter' / 'definitions'


ERROR_STR_NO_DATA = 'no data'
AT_READ_FUNC_NUMBER = 0x03
AT_WRITE_FUNC_NUMBER = 0x10
TYPE_MAP = {
    'float': float,
    'int': int,
}

SETTINGS_DIR_NAME = 'inverter-connect'
SETTINGS_FILE_NAME = 'inverter-connect'
