import tempfile
from pathlib import Path

import tomlkit
from bx_py_utils.auto_doc import assert_readme_block
from bx_py_utils.environ import OverrideEnviron
from bx_py_utils.path import assert_is_file
from click._compat import strip_ansi
from ha_services.toml_settings.serialize import dataclass2toml
from manageprojects.test_utils.click_cli_utils import subprocess_cli
from manageprojects.tests.base import BaseTestCase
from tomlkit import TOMLDocument

from inverter import constants
from inverter.cli.cli_app import PACKAGE_ROOT
from inverter.constants import USER_SETTINGS_PATH
from inverter.user_settings import UserSettings


def assert_cli_help_in_readme(text_block: str, marker: str):
    README_PATH = PACKAGE_ROOT / 'README.md'
    assert_is_file(README_PATH)

    text_block = text_block.replace(constants.CLI_EPILOG, '')
    text_block = f'```\n{text_block.strip()}\n```'
    assert_readme_block(
        readme_path=README_PATH,
        text_block=text_block,
        start_marker_line=f'[comment]: <> (✂✂✂ auto generated {marker} start ✂✂✂)',
        end_marker_line=f'[comment]: <> (✂✂✂ auto generated {marker} end ✂✂✂)',
    )


class ReadmeTestCase(BaseTestCase):
    def invoke(self, *, cli_bin, args):
        """
        IMPORTANT: We must ensure that no local user settings added to the help text
        So we can't directly invoke_click() here, because user settings are read and
        used on module level!
        So we must use subprocess and use a default settings file!
        """
        with tempfile.TemporaryDirectory(prefix='test-inverter-connect') as temp_dir:
            temp_path = Path(temp_dir)

            with OverrideEnviron(HOME=temp_dir, TERM='dump', PYTHONUNBUFFERED='1'):
                assert Path('~').expanduser() == temp_path

                document: TOMLDocument = dataclass2toml(instance=UserSettings())
                doc_str = tomlkit.dumps(document, sort_keys=False)
                Path(USER_SETTINGS_PATH).expanduser().write_text(doc_str, encoding='UTF-8')

                stdout = subprocess_cli(cli_bin=cli_bin, args=args)

                stdout = strip_ansi(stdout)  # FIXME

                # Skip header stuff:
                lines = stdout.splitlines()
                for pos, line in enumerate(lines):
                    if line.lstrip().startswith('Usage: ./'):
                        stdout = '\n'.join(lines[pos:])
                        break

                return '\n'.join(line.rstrip() for line in stdout.splitlines())

    def invoke_cli(self, *args):
        return self.invoke(cli_bin=PACKAGE_ROOT / 'cli.py', args=args)

    def invoke_dev_cli(self, *args):
        return self.invoke(cli_bin=PACKAGE_ROOT / 'dev-cli.py', args=args)

    def test_main_help(self):
        stdout = self.invoke_cli('--help')
        self.assert_in_content(
            got=stdout,
            parts=(
                'Usage: ./cli.py [OPTIONS] COMMAND [ARGS]...',
                'print-at-commands',
                'print-values',
                constants.CLI_EPILOG,
            ),
        )
        assert_cli_help_in_readme(text_block=stdout, marker='main help')

    def test_dev_help(self):
        stdout = self.invoke_dev_cli('--help')
        self.assert_in_content(
            got=stdout,
            parts=(
                'Usage: ./dev-cli.py [OPTIONS] COMMAND [ARGS]...',
                'fix-code-style',
                'tox',
                constants.CLI_EPILOG,
            ),
        )
        assert_cli_help_in_readme(text_block=stdout, marker='dev help')

    def test_publish_loop_help(self):
        stdout = self.invoke_cli('publish-loop', '--help')
        self.assert_in_content(
            got=stdout,
            parts=(
                'Usage: ./cli.py publish-loop [OPTIONS]',
                'IP address of your inverter [required]',
                '--port',
                '--verbosity',
            ),
        )
        assert_cli_help_in_readme(text_block=stdout, marker='publish-loop help')

    def test_print_values_help(self):
        stdout = self.invoke_cli('print-values', '--help')
        self.assert_in_content(
            got=stdout,
            parts=(
                'Usage: ./cli.py print-values [OPTIONS]',
                'IP address of your inverter [required]',
                '--port',
                '--verbosity',
            ),
        )
        assert_cli_help_in_readme(text_block=stdout, marker='print-values help')

    def test_print_at_commands(self):
        stdout = self.invoke_cli('print-at-commands', '--help')
        self.assert_in_content(
            got=stdout,
            parts=(
                'Usage: ./cli.py print-at-commands [OPTIONS] [COMMANDS]...',
                'IP address of your inverter [required]',
                '--port',
                '--verbosity',
            ),
        )
        assert_cli_help_in_readme(text_block=stdout, marker='print-at-commands help')

    def test_read_register(self):
        stdout = self.invoke_cli('read-register', '--help')
        self.assert_in_content(
            got=stdout,
            parts=(
                'Usage: ./cli.py read-register [OPTIONS] REGISTER LENGTH',
                'IP address of your inverter [required]',
                '--port',
                '--verbosity',
            ),
        )
        assert_cli_help_in_readme(text_block=stdout, marker='read-register help')
