import dataclasses
import json
import logging
import socket
from pathlib import Path

import tomlkit
from ha_services.mqtt4homeassistant.data_classes import MqttSettings as OriginMqttSettings
from ha_services.toml_settings.serialize import dataclass2toml
from rich import print  # noqa
from tomlkit import TOMLDocument

from inverter.constants import USER_SETTINGS_PATH
from inverter.data_types import Config
from inverter.utilities.cli import exit_with_human_error


@dataclasses.dataclass
class MqttSettings(OriginMqttSettings):
    """
    MQTT server settings.
    """

    host: str = 'mqtt.your-server.tld'


@dataclasses.dataclass
class Inverter:
    """
    The "name" is the prefix of "inverter/definitions/*.yaml" files!

    Set "ip" of the inverter if it's always the same. (Hint: Pin it in FritzBox settings ;)
    You can leave it empty, but then you must always pass "--ip" to CLI commands.
    Even if it is specified here, you can always override it in the CLI with "--ip".
    """

    name: str = 'deye_2mppt'
    ip: str = ''
    port: int = 48899


@dataclasses.dataclass
class UserSettings:
    """
    User settings for inverter-connect
    """

    mqtt: dataclasses = dataclasses.field(default_factory=MqttSettings)
    inverter: dataclasses = dataclasses.field(default_factory=Inverter)


def migrate_old_settings():  # TODO: Remove in the Future
    new_settings_path = Path(USER_SETTINGS_PATH).expanduser()
    if new_settings_path.is_file():
        return

    old_settings_path = Path('~/.inverter-connect').expanduser()
    if not old_settings_path.is_file():
        return

    logging.info('Migrate old settings from: %s', old_settings_path)
    settings_str = old_settings_path.read_text(encoding='UTF-8')
    data = json.loads(settings_str)
    mqtt = MqttSettings(**data)
    user_settings = UserSettings()
    user_settings.mqtt = mqtt

    document: TOMLDocument = dataclass2toml(instance=user_settings)
    doc_str = tomlkit.dumps(document, sort_keys=False)

    new_settings_path.write_text(doc_str, encoding='UTF-8')

    logging.info('Migrate settings to: %s', new_settings_path)

    old_settings_path.unlink()


def make_config(*, user_settings: UserSettings, ip, port, verbosity, inverter=None) -> Config:
    # "Validate" ip address:
    try:
        result = socket.gethostbyname(ip)
    except socket.gaierror as err:
        exit_with_human_error(hint=f'Is the given {ip=!r} is wrong?!?', print_traceback=err)
    else:
        logging.debug('%r -> %r', ip, result)

    return Config(
        verbosity=verbosity,
        host=ip,
        port=port,
        mqtt_settings=user_settings.mqtt,
        inverter_name=inverter,
    )
