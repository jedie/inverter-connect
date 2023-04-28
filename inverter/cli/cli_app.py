import datetime
import getpass
import logging
import sys
import time
from pathlib import Path

import rich_click as click
from bx_py_utils.path import assert_is_file
from manageprojects.utilities import code_style
from manageprojects.utilities.publish import publish_package
from manageprojects.utilities.subprocess_utils import verbose_check_call
from manageprojects.utilities.version_info import print_version
from rich import print  # noqa
from rich.pretty import pprint
from rich_click import RichGroup

import inverter
from inverter import constants
from inverter.api import Inverter, ValueType
from inverter.config import Config
from inverter.connection import InverterInfo, InverterSock, ModbusResponse
from inverter.constants import ERROR_STR_NO_DATA
from inverter.definitions import Parameter
from inverter.exceptions import ModbusNoData, ModbusNoHexData
from inverter.mqtt4homeassistant.data_classes import MqttSettings
from inverter.mqtt4homeassistant.mqtt import get_connected_client
from inverter.publish_loop import publish_forever
from inverter.utilities.cli import convert_address_option, print_hex_table
from inverter.utilities.credentials import get_mqtt_settings, store_mqtt_settings
from inverter.utilities.log_setup import basic_log_setup


logger = logging.getLogger(__name__)


PACKAGE_ROOT = Path(inverter.__file__).parent.parent
assert_is_file(PACKAGE_ROOT / 'pyproject.toml')

OPTION_ARGS_DEFAULT_TRUE = dict(is_flag=True, show_default=True, default=True)
OPTION_ARGS_DEFAULT_FALSE = dict(is_flag=True, show_default=True, default=False)
ARGUMENT_EXISTING_DIR = dict(
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path)
)
ARGUMENT_NOT_EXISTING_DIR = dict(
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        readable=False,
        writable=True,
        path_type=Path,
    )
)
ARGUMENT_EXISTING_FILE = dict(
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path)
)


class ClickGroup(RichGroup):  # FIXME: How to set the "info_name" easier?
    def make_context(self, info_name, *args, **kwargs):
        info_name = './cli.py'
        return super().make_context(info_name, *args, **kwargs)


@click.group(
    cls=ClickGroup,
    epilog=constants.CLI_EPILOG,
)
def cli():
    pass


@click.command()
@click.option('--verbose/--no-verbose', **OPTION_ARGS_DEFAULT_FALSE)
def mypy(verbose: bool = True):
    """Run Mypy (configured in pyproject.toml)"""
    verbose_check_call('mypy', '.', cwd=PACKAGE_ROOT, verbose=verbose, exit_on_error=True)


cli.add_command(mypy)


@click.command()
@click.option('--verbose/--no-verbose', **OPTION_ARGS_DEFAULT_FALSE)
def coverage(verbose: bool = True):
    """
    Run and show coverage.
    """
    verbose_check_call('coverage', 'run', verbose=verbose, exit_on_error=True)
    verbose_check_call('coverage', 'combine', '--append', verbose=verbose, exit_on_error=True)
    verbose_check_call('coverage', 'report', '--fail-under=30', verbose=verbose, exit_on_error=True)
    verbose_check_call('coverage', 'xml', verbose=verbose, exit_on_error=True)
    verbose_check_call('coverage', 'json', verbose=verbose, exit_on_error=True)


cli.add_command(coverage)


@click.command()
def install():
    """
    Run pip-sync and install 'inverter' via pip as editable.
    """
    verbose_check_call('pip-sync', PACKAGE_ROOT / 'requirements.dev.txt')
    verbose_check_call('pip', 'install', '--no-deps', '-e', '.')


cli.add_command(install)


@click.command()
def safety():
    """
    Run safety check against current requirements files
    """
    verbose_check_call('safety', 'check', '-r', 'requirements.dev.txt')


cli.add_command(safety)


@click.command()
def update():
    """
    Update "requirements*.txt" dependencies files
    """
    bin_path = Path(sys.executable).parent

    verbose_check_call(bin_path / 'pip', 'install', '-U', 'pip')
    verbose_check_call(bin_path / 'pip', 'install', '-U', 'pip-tools')

    extra_env = dict(
        CUSTOM_COMPILE_COMMAND='./cli.py update',
    )

    pip_compile_base = [
        bin_path / 'pip-compile',
        '--verbose',
        '--allow-unsafe',  # https://pip-tools.readthedocs.io/en/latest/#deprecations
        '--resolver=backtracking',  # https://pip-tools.readthedocs.io/en/latest/#deprecations
        '--upgrade',
        '--generate-hashes',
    ]

    # Only "prod" dependencies:
    verbose_check_call(
        *pip_compile_base,
        'pyproject.toml',
        '--output-file',
        'requirements.txt',
        extra_env=extra_env,
    )

    # dependencies + "dev"-optional-dependencies:
    verbose_check_call(
        *pip_compile_base,
        'pyproject.toml',
        '--extra=dev',
        '--output-file',
        'requirements.dev.txt',
        extra_env=extra_env,
    )

    verbose_check_call(bin_path / 'safety', 'check', '-r', 'requirements.dev.txt')

    # Install new dependencies in current .venv:
    verbose_check_call(bin_path / 'pip-sync', 'requirements.dev.txt')


cli.add_command(update)


@click.command()
def publish():
    """
    Build and upload this project to PyPi
    """
    _run_unittest_cli(verbose=False, exit_after_run=False)  # Don't publish a broken state

    publish_package(
        module=inverter,
        package_path=PACKAGE_ROOT,
        distribution_name='inverter-connect',
    )


cli.add_command(publish)


@click.command()
@click.option('--color/--no-color', **OPTION_ARGS_DEFAULT_TRUE)
@click.option('--verbose/--no-verbose', **OPTION_ARGS_DEFAULT_FALSE)
def fix_code_style(color: bool = True, verbose: bool = False):
    """
    Fix code style of all inverter source code files via darker
    """
    code_style.fix(package_root=PACKAGE_ROOT, color=color, verbose=verbose)


cli.add_command(fix_code_style)


@click.command()
@click.option('--color/--no-color', **OPTION_ARGS_DEFAULT_TRUE)
@click.option('--verbose/--no-verbose', **OPTION_ARGS_DEFAULT_FALSE)
def check_code_style(color: bool = True, verbose: bool = False):
    """
    Check code style by calling darker + flake8
    """
    code_style.check(package_root=PACKAGE_ROOT, color=color, verbose=verbose)


cli.add_command(check_code_style)


@click.command()
def update_test_snapshot_files():
    """
    Update all test snapshot files (by remove and recreate all snapshot files)
    """

    def iter_snapshot_files():
        yield from PACKAGE_ROOT.rglob('*.snapshot.*')

    removed_file_count = 0
    for item in iter_snapshot_files():
        item.unlink()
        removed_file_count += 1
    print(f'{removed_file_count} test snapshot files removed... run tests...')

    # Just recreate them by running tests:
    _run_unittest_cli(
        extra_env=dict(
            RAISE_SNAPSHOT_ERRORS='0',  # Recreate snapshot files without error
        ),
        verbose=False,
        exit_after_run=False,
    )

    new_files = len(list(iter_snapshot_files()))
    print(f'{new_files} test snapshot files created, ok.\n')


cli.add_command(update_test_snapshot_files)


def _run_unittest_cli(extra_env=None, verbose=True, exit_after_run=True):
    """
    Call the origin unittest CLI and pass all args to it.
    """
    if extra_env is None:
        extra_env = dict()

    extra_env.update(
        dict(
            PYTHONUNBUFFERED='1',
            PYTHONWARNINGS='always',
        )
    )

    args = sys.argv[2:]
    if not args:
        if verbose:
            args = ('--verbose', '--locals', '--buffer')
        else:
            args = ('--locals', '--buffer')

    verbose_check_call(
        sys.executable,
        '-m',
        'unittest',
        *args,
        timeout=15 * 60,
        extra_env=extra_env,
    )
    if exit_after_run:
        sys.exit(0)


@click.command()  # Dummy command
def test():
    """
    Run unittests
    """
    _run_unittest_cli()


cli.add_command(test)


def _run_tox():
    verbose_check_call(sys.executable, '-m', 'tox', *sys.argv[2:])
    sys.exit(0)


@click.command()  # Dummy "tox" command
def tox():
    """
    Run tox
    """
    _run_tox()


cli.add_command(tox)


@click.command()
def version():
    """Print version and exit"""
    # Pseudo command, because the version always printed on every CLI call ;)
    sys.exit(0)


cli.add_command(version)
######################################################################################################
# Project specific commands


@click.command()
@click.argument('ip')
@click.option(
    '--port', type=click.IntRange(1000, 65535), default=48899, help='Port of the inverter', show_default=True
)
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_FALSE)
def print_values(ip, port, debug):
    """
    Print all known register values from Inverter, e.g.:

    .../inverter-connect$ ./cli.py print-values 192.168.123.456
    """
    basic_log_setup(debug=debug)

    config = Config(yaml_filename='deye_2mppt.yaml', host=ip, port=port, debug=debug)
    with Inverter(config=config) as inverter:
        inverter_info: InverterInfo = inverter.inv_sock.inverter_info
        print(inverter_info)
        print()

        for value in inverter:
            print(f'\t* [yellow]{value.name:<31}[/yellow]:', end=' ')
            if value.value == ERROR_STR_NO_DATA:
                color = 'red'
                msg = ERROR_STR_NO_DATA
            else:
                color = 'green'
                msg = f'{value.value} {value.unit}'
            print(f'[{color}]{msg:<11}[/{color}]', end=' ')

            if value.type == ValueType.READ_OUT:
                parameter: Parameter = value.result.parameter
                print(
                    f'(Register: [cyan]{parameter.start_register:04X}[/cyan], length:'
                    f' [blue]{parameter.length}[/blue])'
                )
            elif value.type == ValueType.COMPUTED:
                print('(Computed)')

            if debug:
                print()


cli.add_command(print_values)


@click.command()
@click.argument('ip')
@click.argument('commands', nargs=-1)
@click.option(
    '--port', type=click.IntRange(1000, 65535), default=48899, help='Port of the inverter', show_default=True
)
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_FALSE)
def print_at_commands(ip, port, commands, debug):
    """
    Print one or more AT command values from Inverter.

    Use all known AT commands, if no one is given, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456

    Or speficy one or more AT-commands, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 WEBVER
    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 WEBVER WEBU

    (Note: The prefix "AT+" will be added to every command)
    """
    basic_log_setup(debug=debug)

    if not commands:
        commands = (
            'WANN',
            'WEBVER',
            'WEBU',
            'WAP',
            'WSSSID',
            'WSKEY',
            'YZAPP',
            'UPURL',
            'WAPMXSTA',  # max. number of wifi clients
            'NTPTM',  # NTP date time? e.g.: "1970-1-1  0:3:9  Thur"
            'NTPRF',  # NTP request interval in min (?)
        )

    config = Config(yaml_filename=None, host=ip, port=port, debug=debug)
    if debug:
        print(config)

    with InverterSock(config) as inv_sock:
        inverter_info: InverterInfo = inv_sock.inverter_info
        print(inverter_info)
        print()

        for command in commands:
            print(f'\t* [grey]AT+[/grey][bold][yellow]{command:<10}[/yellow]:', end=' ')
            result: str = inv_sock.cleaned_at_command(command)
            print(f'[green]{result}')


cli.add_command(print_at_commands)


@click.command()
@click.argument('ip')
@click.option(
    '--port', type=click.IntRange(1000, 65535), default=48899, help='Port of the inverter', show_default=True
)
@click.option('--register', default="0x16", help='Start address', show_default=True)
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_TRUE)
def set_time(ip, port, register, debug):
    """
    Set current date time in the inverter device.

    Default start address is 0x16, so that this will be filled:
        0x16 - year + month
        0x17 - day + hour
        0x18 - minute + second
    """
    address = convert_address_option(raw_address=register, debug=debug)

    config = Config(yaml_filename=None, host=ip, port=port, debug=debug)
    if debug:
        print(config)

    with InverterSock(config) as inv_sock:
        inverter_info: InverterInfo = inv_sock.inverter_info
        print(inverter_info)
        print()

        now = datetime.datetime.now()
        print(f'Send current time: {now}')
        values = [
            256 * (now.year % 100) + now.month,
            256 * now.day + now.hour,
            256 * now.minute + now.second,
        ]
        data = inv_sock.write(address=address, values=values)
        print(f'Response: {data!r}')

        print('\nCheck time by request "AT+NTPTM"', end='...')
        time.sleep(1)
        result: str = inv_sock.cleaned_at_command(command='NTPTM')
        print(f'[green]{result}')


cli.add_command(set_time)


@click.command()
@click.argument('ip')
@click.option(
    '--port', type=click.IntRange(1000, 65535), default=48899, help='Port of the inverter', show_default=True
)
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_TRUE)
@click.argument('register')
@click.argument('length', type=click.IntRange(1, 100))
def read_register(ip, port, register, length, debug):
    """
    Read register(s) from the inverter

    e.g.: read 3 registers starting from 0x16:

        .../inverter-connect$ ./cli.py read-register 192.168.123.456 0x16 3

    e.g.: read the first 32 registers:

    .../inverter-connect$ ./cli.py read-register 192.168.123.456 0 32

    The start address can be pass as decimal number or as hex string, e.g.: 0x123
    """
    print(f'Read {length} register(s) from {register=!r} ({ip}:{port})')
    address = convert_address_option(raw_address=register, debug=debug)

    config = Config(yaml_filename=None, host=ip, port=port, debug=debug)
    if debug:
        print(config)

    with InverterSock(config) as inv_sock:
        inverter_info: InverterInfo = inv_sock.inverter_info
        print(inverter_info)
        print()

        try:
            response: ModbusResponse = inv_sock.read(start_register=address, length=length)
        except ModbusNoHexData as err:
            print(f'[yellow]Non hex response: [magenta]{err.data!r}')
        except ModbusNoData:
            print('[yellow]no data')
        else:
            print(response)
            print(f'\nResult (in hex): [cyan]{response.data_hex}\n')

            print_hex_table(
                address=address,
                data_hex=response.data_hex,
                title=f'[green][bold]{length} value(s) from {hex(address)}',
            )


cli.add_command(read_register)


######################################################################################################
# MQTT


@click.command()
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_FALSE)
def store_settings(debug):
    """
    Store MQTT server settings.
    """
    basic_log_setup(debug=debug)

    try:
        settings: MqttSettings = get_mqtt_settings()
    except FileNotFoundError:
        print('No settings stored, yet. ok.')
        print()
        print('Input settings:')
    else:
        print('Current settings:')
        pprint(settings.anonymized())
        print()
        print('Input new settings:')

    host = input('host (e.g.: "test.mosquitto.org"): ')
    if not host:
        print('Host is needed! Abort.')
        sys.exit(1)

    port = input('port (default: 1883): ')
    if port:
        port = int(port)
    else:
        port = 1883
    user_name = input('user name: ')
    password = getpass.getpass('password: ')

    settings = MqttSettings(host=host, port=port, user_name=user_name, password=password)
    file_path = store_mqtt_settings(settings)
    print(f'MQTT server settings stored into: {file_path}')


cli.add_command(store_settings)


@click.command()
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_FALSE)
def debug_settings(debug):
    """
    Display (anonymized) MQTT server username and password
    """
    basic_log_setup(debug=debug)
    settings: MqttSettings = get_mqtt_settings()
    pprint(settings.anonymized())


cli.add_command(debug_settings)


@click.command()
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_FALSE)
def test_mqtt_connection(debug):
    """
    Test connection to MQTT Server
    """
    basic_log_setup(debug=debug)
    settings: MqttSettings = get_mqtt_settings()
    mqttc = get_connected_client(settings=settings, verbose=True)
    mqttc.loop_start()
    mqttc.loop_stop()
    mqttc.disconnect()
    print('\n[green]Test succeed[/green], bye ;)')


cli.add_command(test_mqtt_connection)


@click.command()
@click.argument('ip')
@click.option(
    '--port', type=click.IntRange(1000, 65535), default=48899, help='Port of the inverter', show_default=True
)
@click.option('--log/--no-log', **OPTION_ARGS_DEFAULT_TRUE)
@click.option('--verbose/--no-verbose', **OPTION_ARGS_DEFAULT_TRUE)
@click.option('--debug/--no-debug', **OPTION_ARGS_DEFAULT_FALSE)
def publish_loop(ip, port, log, verbose, debug):
    """
    Publish current data via MQTT (endless loop)
    """
    if log:
        basic_log_setup(debug=debug)

    config = Config(yaml_filename='deye_2mppt.yaml', host=ip, port=port, debug=debug)

    mqtt_settings: MqttSettings = get_mqtt_settings()
    pprint(mqtt_settings.anonymized())
    try:
        publish_forever(mqtt_settings=mqtt_settings, config=config, verbose=verbose)
    except KeyboardInterrupt:
        print('Bye, bye')


cli.add_command(publish_loop)

######################################################################################################


def main():
    print_version(inverter)

    if len(sys.argv) >= 2:
        # Check if we just pass a command call
        command = sys.argv[1]
        if command == 'test':
            _run_unittest_cli()
        elif command == 'tox':
            _run_tox()

    # Execute Click CLI:
    cli.name = './cli.py'
    cli()
