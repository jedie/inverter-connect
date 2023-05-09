"""
    CLI for usage
"""

import logging
import sys
import time
from pathlib import Path

import rich_click as click
from bx_py_utils.path import assert_is_file
from ha_services.mqtt4homeassistant.mqtt import get_connected_client
from ha_services.toml_settings.api import debug_print_user_settings, edit_user_settings, get_user_settings
from ha_services.toml_settings.exceptions import UserSettingsNotFound
from rich import print  # noqa
from rich_click import RichGroup

import inverter
from inverter import constants
from inverter.api import Inverter, set_current_time
from inverter.connection import InverterSock
from inverter.constants import ERROR_STR_NO_DATA, USER_SETTINGS_PATH
from inverter.data_types import Parameter, ValueType
from inverter.exceptions import ReadInverterError
from inverter.publish_loop import publish_forever
from inverter.user_settings import UserSettings, make_config, migrate_old_settings
from inverter.utilities.cli import convert_address_option, print_register
from inverter.verbosity import OPTION_KWARGS_VERBOSE, setup_logging


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


######################################################################################################


@click.command()
def version():
    """Print version and exit"""
    # Pseudo command, because the version always printed on every CLI call ;)
    sys.exit(0)


cli.add_command(version)


######################################################################################################
# User settings


migrate_old_settings()  # TODO: Remove in the Future

try:
    user_settings: UserSettings = get_user_settings(user_settings=UserSettings(), settings_path=USER_SETTINGS_PATH)
except UserSettingsNotFound:
    print(f'[red]No settings file found: [yellow]{USER_SETTINGS_PATH}')
    input('Press any key, to create it')
    edit_user_settings(user_settings=UserSettings(), settings_path=USER_SETTINGS_PATH)
    sys.exit(1)


option_kwargs_ip = dict(
    required=True,
    type=str,
    help='IP address of your inverter',
    default=user_settings.inverter.ip or None,  # Don't accept empty string as IP: We need a address ;)
    show_default=True,
)
option_kwargs_port = dict(
    required=True,
    type=int,
    default=user_settings.inverter.port,
    help='Port of inverter services',
    show_default=True,
)
option_kwargs_inverter_name = dict(
    required=True,
    type=str,
    default=user_settings.inverter.name,
    help='Prefix of yaml config files in inverter/definitions/',
    show_default=True,
)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def edit_settings(verbosity: int):
    """
    Edit the settings file. On first call: Create the default one.
    """
    setup_logging(verbosity=verbosity)
    edit_user_settings(user_settings=UserSettings(), settings_path=USER_SETTINGS_PATH)


cli.add_command(edit_settings)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def debug_settings(verbosity: int):
    """
    Display (anonymized) MQTT server username and password
    """
    setup_logging(verbosity=verbosity)
    try:
        debug_print_user_settings(user_settings=UserSettings(), settings_path=USER_SETTINGS_PATH)
    except UserSettingsNotFound as err:
        print(f'[yellow]No settings created yet[/yellow]: {err} [green](Hint: call "edit-settings" first!)')


cli.add_command(debug_settings)


######################################################################################################


@click.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--inverter', **option_kwargs_inverter_name)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def print_values(ip, port, inverter, verbosity: int):
    """
    Print all known register values from Inverter, e.g.:

    .../inverter-connect$ ./cli.py print-values 192.168.123.456
    """
    if user_settings is None:
        print('[yellow]No settings created yet! [green]Call "edit-settings" first!')
        return

    setup_logging(verbosity=verbosity)

    print()

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=inverter,
    )

    with Inverter(config=config) as inverter:
        try:
            inverter.connect()
        except ReadInverterError as err:
            print(f'[red]{err}')
            sys.exit(1)

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

            if verbosity:
                print()


cli.add_command(print_values)


@click.command()
@click.argument('commands', nargs=-1)
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def print_at_commands(ip, port, commands, verbosity: int):
    """
    Print one or more AT command values from Inverter.

    Use all known AT commands, if no one is given, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456

    Or specify one or more AT-commands, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 WEBVER
    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 WEBVER WEBU

    e.g.: Set NTP server, enable NTP and check the values:

    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 NTPSER=192.168.1.1 NTPEN=on NTPSER NTPEN

    wait a while and request the current date time:

    .../inverter-connect$ ./cli.py print-at-commands 192.168.123.456 NTPTM

    (Note: The prefix "AT+" will be added to every command)
    """
    if user_settings is None:
        print('[yellow]No settings created yet! [green]Call "edit-settings" first!')
        return

    setup_logging(verbosity=verbosity)

    if not commands:
        commands = (
            # 'KEY',  # Set/Get Device Password
            'VER',
            'BVER',  # bootloader version
            'HWVER',  # hardware version
            'WEBVER',  # web version
            'YZVER',  # Firmware version
            'PING',
            # 'YZWAKEYCTL',
            # 'YZLOG',
            # 'YZAPP',
            # 'YZAPSTAT',
            # 'YZEXPFUN',
            # 'MID',
            #
            # 'CFGRD',  # current system config
            # 'SMEM',  # system memory stat
            'TIME',
            # 'ADDRESS', # Set/Get Device Address
            # 'KEY',
            'NDBGS',  # Set/Get Debug Status
            'WIFI',  # Set/Get WIFI status: Power up: "WIFI=UP" Power down: "WIFI=DOWN"
            'WMODE',  # Set/Get the WIFI Operation Mode (AP or STA)
            'WEBU',  # Set/Get the Login Parameters of WEB page
            'WAP',  # Set/Get the AP parameters
            'WSSSID',  # Set/Get the AP's SSID of WIFI STA Mode
            'WSKEY',  # Set/Get the Security Parameters of WIFI STA Mode
            'WAKEY',  # Set/Get the Security Parameters of WIFI AP Mode
            # 'TXPWR',  # Set/Get wifi rf tx power'
            'WANN',  # Set/Get The WAN setting if in STA mode.
            'LANN',  # Set/Get The LAN setting if in ADHOC mode.
            'UPURL',  # Set/Get the path of remote upgrade
            'YZAPP',
            'WAPMXSTA',  # Set/Get the Max Number Of Sta Connected to Ap
            # 'WSCAN',  # Get The AP site Survey (only for STA Mode).
            'NTPTM',  # NTP date time? e.g.: "1970-1-1  0:3:9  Thur"
            'NTPSER',  # set/query NTP server, e.g.: "NTPSER=192.168.1.1"
            'NTPRF',  # NTP request interval in min (?)
            'NTPEN',  # Enable/Disable NTP Server
            'WSDNS',  # Set/Get the DNS Server address
            'DEVICENUM',  # Set/Get Device Link Num
            'DEVSELCTL',  # Set/Get Web Device List Info
        )

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=None,
    )

    with InverterSock(config) as inv_sock:
        try:
            inv_sock.connect()
        except ReadInverterError as err:
            print(f'[red]{err}')
            sys.exit(1)

        for command in commands:
            print(f'\t* [grey]AT+[/grey][bold][yellow]{command:<10}[/yellow]:', end=' ')
            result: str = inv_sock.cleaned_at_command(command)
            print(f'[green]{result}')


cli.add_command(print_at_commands)


@click.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--register', default="0x16", help='Start address', show_default=True)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def set_time(ip, port, register, verbosity: int):
    """
    Set current date time in the inverter device.

    Default start address is 0x16, so that this will be filled:
        0x16 - year + month
        0x17 - day + hour
        0x18 - minute + second
    """
    if user_settings is None:
        print('[yellow]No settings created yet! [green]Call "edit-settings" first!')
        return

    setup_logging(verbosity=verbosity)

    address = convert_address_option(raw_address=register, debug=bool(verbosity))

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=None,
    )

    with InverterSock(config) as inv_sock:
        try:
            inv_sock.connect()
        except ReadInverterError as err:
            print(f'[red]{err}')
            sys.exit(1)

        set_current_time(inv_sock=inv_sock, address=address, verbose=True)

        print('\nRead register...')
        time.sleep(1)
        print_register(inv_sock, start_register=address, length=3)

        print('\nCheck time by request "AT+NTPTM"', end='...')
        time.sleep(1)
        result: str = inv_sock.cleaned_at_command(command='NTPTM')
        print(f'[green]{result}')


cli.add_command(set_time)


@click.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.argument('register')
@click.argument('length', type=click.IntRange(1, 100))
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def read_register(ip, port, register, length, verbosity: int):
    """
    Read register(s) from the inverter

    e.g.: read 3 registers starting from 0x16:

        .../inverter-connect$ ./cli.py read-register 192.168.123.456 0x16 3

    e.g.: read the first 32 registers:

    .../inverter-connect$ ./cli.py read-register 192.168.123.456 0 32

    The start address can be pass as decimal number or as hex string, e.g.: 0x123
    """
    if user_settings is None:
        print('[yellow]No settings created yet! [green]Call "edit-settings" first!')
        return

    setup_logging(verbosity=verbosity)

    print(f'Read {length} register(s) from {register=!r} ({ip}:{port})')
    address = convert_address_option(raw_address=register, debug=bool(verbosity))

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=None,
    )

    with InverterSock(config) as inv_sock:
        try:
            inv_sock.connect()
        except ReadInverterError as err:
            print(f'[red]{err}')
            sys.exit(1)

        print_register(inv_sock, start_register=address, length=length)


cli.add_command(read_register)


######################################################################################################
# MQTT


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def test_mqtt_connection(verbosity: int):
    """
    Test connection to MQTT Server
    """
    if user_settings is None:
        print('[yellow]No settings created yet! [green]Call "edit-settings" first!')
        return

    setup_logging(verbosity=verbosity)

    mqttc = get_connected_client(settings=user_settings.mqtt, verbose=True)
    mqttc.loop_start()
    mqttc.loop_stop()
    mqttc.disconnect()
    print('\n[green]Test succeed[/green], bye ;)')


cli.add_command(test_mqtt_connection)


@click.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--inverter', **option_kwargs_inverter_name)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def publish_loop(ip, port, inverter, verbosity: int):
    """
    Publish current data via MQTT for Home Assistant (endless loop)

    The "Daily Production" count will be cleared in the night,
    by set the current date time via AT-command.
    """
    if user_settings is None:
        print('[yellow]No settings created yet! [green]Call "edit-settings" first!')
        return

    setup_logging(verbosity=verbosity)

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=inverter,
    )
    try:
        publish_forever(config=config, verbosity=verbosity)
    except KeyboardInterrupt:
        print('Bye, bye')


cli.add_command(publish_loop)


def main():
    print(f'[bold][green]{inverter.__name__}[/green] v[cyan]{inverter.__version__}')

    # Execute Click CLI:
    cli.name = './cli.py'
    cli()
