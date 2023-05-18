from click.testing import Result
from ha_services.cli_tools.test_utils.assertion import assert_in
from manageprojects.test_utils.click_cli_utils import ClickInvokeCliException, invoke_click
from manageprojects.tests.base import BaseTestCase

from inverter.cli.cli_app import cli


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
