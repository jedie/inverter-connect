import subprocess
from unittest import TestCase

from bx_py_utils.path import assert_is_file
from manageprojects.test_utils.click_cli_utils import subprocess_cli
from manageprojects.test_utils.project_setup import check_editor_config, get_py_max_line_length
from manageprojects.utilities import code_style
from packaging.version import Version

from inverter import __version__
from inverter.cli.cli_app import PACKAGE_ROOT


class ProjectSetupTestCase(TestCase):
    app_cli_bin = PACKAGE_ROOT / 'cli.py'
    dev_cli_bin = PACKAGE_ROOT / 'dev-cli.py'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        assert_is_file(cls.app_cli_bin)
        assert_is_file(cls.dev_cli_bin)

    def test_version(self):
        self.assertIsNotNone(__version__)

        version = Version(__version__)  # Will raise InvalidVersion() if wrong formatted
        self.assertEqual(str(version), __version__)

        # The "app" cli:
        output = subprocess.check_output([self.app_cli_bin, 'version'], text=True)
        self.assertIn(f'inverter v{__version__}', output)

        # The "development" cli:
        output = subprocess.check_output([self.dev_cli_bin, 'version'], text=True)
        self.assertIn(f'inverter v{__version__}', output)

    def test_code_style(self):
        try:
            output = subprocess_cli(
                cli_bin=self.dev_cli_bin,
                args=('check-code-style',),
                exit_on_error=False,
            )
        except subprocess.CalledProcessError as err:
            self.assertIn('.venv/bin/darker', err.stdout)  # darker was called?
        else:
            if 'Code style: OK' in output:
                self.assertIn('.venv/bin/darker', output)  # darker was called?
                return  # Nothing to fix -> OK

        # Try to "auto" fix code style:

        try:
            output = subprocess_cli(
                cli_bin=self.dev_cli_bin,
                args=('fix-code-style',),
                exit_on_error=False,
            )
        except subprocess.CalledProcessError as err:
            output = err.stdout

        self.assertIn('.venv/bin/darker', output)  # darker was called?

        # Check again and display the output:

        try:
            code_style.check(package_root=PACKAGE_ROOT)
        except SystemExit as err:
            self.assertEqual(err.code, 0, 'Code style error, see output above!')

    def test_check_editor_config(self):
        check_editor_config(package_root=PACKAGE_ROOT)

        max_line_length = get_py_max_line_length(package_root=PACKAGE_ROOT)
        self.assertEqual(max_line_length, 119)
