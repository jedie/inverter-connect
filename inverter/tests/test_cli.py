import os
import tempfile
from pathlib import Path

from bx_py_utils.environ import OverrideEnviron
from click.testing import Result
from ha_services.cli_tools.test_utils.assertion import assert_in
from ha_services.cli_tools.test_utils.rich_test_utils import NoColorRichClickCli
from manageprojects.test_utils.click_cli_utils import ClickInvokeCliException, invoke_click
from manageprojects.tests.base import BaseTestCase

from inverter.cli.cli_app import cli
from inverter.constants import PACKAGE_ROOT


class CliTestCase(BaseTestCase):
    def test_print_at_commands_invalid_ip(self):
        with self.assertRaises(ClickInvokeCliException) as cm:
            invoke_click(
                cli,
                'print-at-commands',
                '--ip',
                '123.456.789.666',  # <<< not a valid IPv4 -> socket.gaierror will be raised
            )

        result: Result = cm.exception.result
        assert_in(
            content=result.stdout,
            parts=('[Errno -2]', 'Hint: Check 123.456.789.666:48899'),
        )
        assert_in(
            content=result.stderr,
            parts=(
                'gaierror: [Errno -2]',
                "Is the given ip='123.456.789.666' is wrong?!?",
            ),
        )

    def test_print_values_invalid_ip(self):
        with self.assertRaises(ClickInvokeCliException) as cm:
            invoke_click(
                cli,
                'print-values',
                '--ip',
                '123.456.789.666',  # <<< not a valid IPv4 -> socket.gaierror will be raised
            )

        result: Result = cm.exception.result
        assert_in(
            content=result.stdout,
            parts=('[Errno -2]', 'Hint: Check 123.456.789.666:48899'),
        )
        assert_in(
            content=result.stderr,
            parts=(
                'gaierror: [Errno -2]',
                "Is the given ip='123.456.789.666' is wrong?!?",
            ),
        )

    def test_settings_not_exists(self):
        env = os.environ.copy()
        with tempfile.TemporaryDirectory(prefix='test-inverter-connect') as temp_dir:
            temp_path = Path(temp_dir)
            with OverrideEnviron(
                HOME=temp_dir,
                PATH='',  # Avoid finding any editor to start!
            ):
                assert Path('~').expanduser() == temp_path
                Path(temp_path / '.config').mkdir()

                with NoColorRichClickCli() as cli:
                    stdout = cli.invoke(cli_bin=PACKAGE_ROOT / '.venv-app/bin/inverter_app', args=('edit-settings',))
                    assert_in(
                        stdout,
                        parts=(
                            'No settings created yet',
                            'call "edit-settings" first',
                            #
                            # FIXME: Error message to open a editor in ha-services:
                            f'open {temp_path}/.config/inverter-connect/inverter-connect.toml!',
                        ),
                    )
        self.assertEqual(os.environ, env)
