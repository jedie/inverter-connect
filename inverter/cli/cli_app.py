"""
    CLI for usage
"""
import atexit
import datetime
import locale
import logging
import sys
import time
from pathlib import Path

import rich_click
import rich_click as click
from bx_py_utils.path import assert_is_file
from ha_services.mqtt4homeassistant.mqtt import get_connected_client
from ha_services.systemd.api import ServiceControl
from ha_services.toml_settings.api import TomlSettings
from ha_services.toml_settings.exceptions import UserSettingsNotFound
from rich import get_console, print  # noqa
from rich.pretty import pprint
from rich.table import Table
from rich.traceback import install as rich_traceback_install
from rich_click import RichGroup

import inverter
from inverter import constants
from inverter.api import Inverter, fetch_inverter_versions, set_current_time
from inverter.connection import InverterSock
from inverter.constants import SETTINGS_DIR_NAME, SETTINGS_FILE_NAME
from inverter.data_types import InverterRegisterVersionInfo
from inverter.exceptions import ReadInverterError
from inverter.publish_loop import publish_forever
from inverter.user_settings import SystemdServiceInfo, UserSettings, make_config, migrate_old_settings
from inverter.utilities.cli import (
    convert_address_option,
    print_inverter_values,
    print_inverter_versions,
    print_register,
)
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


toml_settings = TomlSettings(
    dir_name=SETTINGS_DIR_NAME,
    file_name=SETTINGS_FILE_NAME,
    settings_dataclass=UserSettings(),
)
migrate_old_settings(toml_settings)  # TODO: Remove in the Future

try:
    user_settings: UserSettings = toml_settings.get_user_settings(debug=True)
except UserSettingsNotFound:
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
    toml_settings.open_in_editor()


cli.add_command(edit_settings)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def debug_settings(verbosity: int):
    """
    Display (anonymized) MQTT server username and password
    """
    setup_logging(verbosity=verbosity)
    toml_settings.print_settings()


cli.add_command(debug_settings)


######################################################################################################
# Manage systemd service commands:


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def systemd_debug(verbosity: int):
    """
    Print Systemd service template + context + rendered file content.
    """
    setup_logging(verbosity=verbosity)
    systemd_settings: SystemdServiceInfo = user_settings.systemd

    ServiceControl(info=systemd_settings).debug_systemd_config()


cli.add_command(systemd_debug)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def systemd_setup(verbosity: int):
    """
    Write Systemd service file, enable it and (re-)start the service. (May need sudo)
    """
    setup_logging(verbosity=verbosity)
    systemd_settings: SystemdServiceInfo = user_settings.systemd

    ServiceControl(info=systemd_settings).setup_and_restart_systemd_service()


cli.add_command(systemd_setup)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def systemd_remove(verbosity: int):
    """
    Write Systemd service file, enable it and (re-)start the service. (May need sudo)
    """
    setup_logging(verbosity=verbosity)
    systemd_settings: SystemdServiceInfo = user_settings.systemd

    ServiceControl(info=systemd_settings).remove_systemd_service()


cli.add_command(systemd_remove)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def systemd_status(verbosity: int):
    """
    Display status of systemd service. (May need sudo)
    """
    setup_logging(verbosity=verbosity)
    systemd_settings: SystemdServiceInfo = user_settings.systemd

    ServiceControl(info=systemd_settings).status()


cli.add_command(systemd_status)


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def systemd_stop(verbosity: int):
    """
    Stops the systemd service. (May need sudo)
    """
    setup_logging(verbosity=verbosity)
    systemd_settings: SystemdServiceInfo = user_settings.systemd

    ServiceControl(info=systemd_settings).stop()


cli.add_command(systemd_stop)


######################################################################################################


@click.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--inverter', **option_kwargs_inverter_name)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def print_values(ip, port, inverter, verbosity: int):
    """
    Print all known register values from Inverter, e.g.:

    .../inverter-connect$ ./cli.py print-values
    """
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

        print('Fetch', end='...')
        values = []
        for value in inverter:
            print(f'[yellow]{value.name}[/yellow],', end='')
            values.append(value)

    if verbosity > 1:
        pprint(values)
    print_inverter_values(values)


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

    .../inverter-connect$ ./cli.py print-at-commands

    Or specify one or more AT-commands, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands WEBVER
    .../inverter-connect$ ./cli.py print-at-commands WEBVER WEBU

    e.g.: Set NTP server, enable NTP and check the values:

    .../inverter-connect$ ./cli.py print-at-commands NTPSER=192.168.1.1 NTPEN=on NTPSER NTPEN

    wait a while and request the current date time:

    .../inverter-connect$ ./cli.py print-at-commands NTPTM

    (Note: The prefix "AT+" will be added to every command)
    """
    setup_logging(verbosity=verbosity)

    if not commands:
        commands = (
            'KEY',  # Set/Get Device Password
            'VER',
            'BVER',  # bootloader version
            'HWVER',  # hardware version
            'WEBVER',  # web version
            'YZVER',  # Firmware version
            'PING',
            'YZWAKEYCTL',
            'YZLOG',
            'YZAPP',
            # 'YZAPSTAT', # (doesn't work!)
            'YZEXPFUN',
            'MID',
            # 'CFGRD',  # current system config (doesn't work!)
            # 'SMEM',  # system memory stat (doesn't work!)
            'TIME',
            'ADDRESS',  # Set/Get Device Address
            'KEY',
            'NDBGS',  # Set/Get Debug Status
            'WIFI',  # Set/Get WIFI status: Power up: "WIFI=UP" Power down: "WIFI=DOWN"
            'WMODE',  # Set/Get the WIFI Operation Mode (AP or STA)
            'WEBU',  # Set/Get the Login Parameters of WEB page
            'WAP',  # Set/Get the AP parameters
            'WSSSID',  # Set/Get the AP's SSID of WIFI STA Mode
            'WSKEY',  # Set/Get the Security Parameters of WIFI STA Mode
            'WAKEY',  # Set/Get the Security Parameters of WIFI AP Mode
            'TXPWR',  # Set/Get wifi rf tx power'
            'WANN',  # Set/Get The WAN setting if in STA mode.
            'LANN',  # Set/Get The LAN setting if in ADHOC mode.
            'UPURL',  # Set/Get the path of remote upgrade
            'WAPMXSTA',  # Set/Get the Max Number Of Sta Connected to Ap
            'WSCAN',  # Get The AP site Survey (only for STA Mode).
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

        print('Fetch', end='...')
        results = []
        for command in commands:
            print(f'[yellow]{command}', end='')
            result: str = inv_sock.cleaned_at_command(command)
            results.append(dict(command=command, result=result))
            print(',', end='')

    if verbosity > 1:
        pprint(results)

    console = get_console()
    console.print('\n')
    console.rule()

    table = Table(title='AT-command results')
    table.add_column('Counter', justify='right')
    table.add_column('Command', justify='right')
    table.add_column('[green]Result', justify='left', style='green')

    for offset, result in enumerate(results):
        table.add_row(
            str(offset + 1),  # Counter
            f'[grey]AT+[/grey][bold][yellow]{result["command"]}',
            result['result'],
        )

    console.print(table)


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

        .../inverter-connect$ ./cli.py read-register 0x16 3

    e.g.: read the first 32 registers:

    .../inverter-connect$ ./cli.py read-register 0 32

    The start address can be pass as decimal number or as hex string, e.g.: 0x123
    """

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


@click.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def inverter_version(ip, port, verbosity: int):
    """
    Print all version information of the inverter
    """
    setup_logging(verbosity=verbosity)

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

        infos = [
            InverterRegisterVersionInfo(name='Control Board Firmware', register=0x000D),
            InverterRegisterVersionInfo(name='Communication Board Firmware', register=0x000E),
            InverterRegisterVersionInfo(name='Communication Protocol', register=0x0012),
        ]
        results = fetch_inverter_versions(inv_sock=inv_sock, infos=infos)

    print_inverter_versions(results)


cli.add_command(inverter_version)


######################################################################################################
# MQTT


@click.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def test_mqtt_connection(verbosity: int):
    """
    Test connection to MQTT Server
    """

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


def exit_func():
    console = get_console()
    console.rule(datetime.datetime.now().strftime('%c'))


def main():
    print(f'[bold][green]{inverter.__name__}[/green] v[cyan]{inverter.__version__}')
    locale.setlocale(locale.LC_ALL, '')

    console = get_console()
    rich_traceback_install(
        width=console.size.width,  # full terminal width
        show_locals=True,
        suppress=[click, rich_click],
        max_frames=2,
    )

    atexit.register(exit_func)

    # Execute Click CLI:
    cli.name = './cli.py'
    cli()
