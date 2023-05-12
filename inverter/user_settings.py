import dataclasses
import json
import logging
import socket
import sys
from pathlib import Path

import tomlkit
from ha_services.cli_tools.rich_utils import human_error
from ha_services.mqtt4homeassistant.data_classes import MqttSettings as OriginMqttSettings
from ha_services.systemd.data_classes import BaseSystemdServiceInfo, BaseSystemdServiceTemplateContext
from ha_services.toml_settings.api import TomlSettings
from ha_services.toml_settings.serialize import dataclass2toml
from rich import print  # noqa
from tomlkit import TOMLDocument

from inverter.data_types import Config


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
class SystemdServiceTemplateContext(BaseSystemdServiceTemplateContext):
    """
    Context values for the systemd service file content
    """

    verbose_service_name: str = 'Inverter Connect'
    exec_start: str = f'{sys.executable} -m inverter publish-loop'


@dataclasses.dataclass
class SystemdServiceInfo(BaseSystemdServiceInfo):
    """
    Information for systemd helper functions
    """

    template_context: SystemdServiceTemplateContext = dataclasses.field(default_factory=SystemdServiceTemplateContext)


@dataclasses.dataclass
class UserSettings:
    """
    User settings for inverter-connect
    """

    systemd: dataclasses = dataclasses.field(default_factory=SystemdServiceInfo)
    mqtt: dataclasses = dataclasses.field(default_factory=MqttSettings)
    inverter: dataclasses = dataclasses.field(default_factory=Inverter)


def migrate_old_settings(toml_settings: TomlSettings):  # TODO: Remove in the Future
    file_path = toml_settings.file_path  # '~/config/inverter-connect/inverter-connect.toml'
    if file_path.is_file():
        logging.debug('v2 settings file exists: %s -> no migration needed', file_path)
        return
    else:
        logging.debug('v2 settings not exists: %s -> try migration', file_path)

    # '~/.inverter-connect' -> '~/config/inverter-connect/inverter-connect.toml'
    v1_settings_path = Path('~/.inverter-connect').expanduser()
    if v1_settings_path.is_file():
        logging.info('Migrate v1 settings from: %s', v1_settings_path)
        settings_str = v1_settings_path.read_text(encoding='UTF-8')
        assert settings_str, f'Empty file: {v1_settings_path} (Please remove it!)'
        data = json.loads(settings_str)
        mqtt = MqttSettings(**data)
        user_settings = UserSettings()
        user_settings.mqtt = mqtt

        document: TOMLDocument = dataclass2toml(instance=user_settings)
        doc_str = tomlkit.dumps(document, sort_keys=False)

        file_path.write_text(doc_str, encoding='UTF-8')

        logging.info('Migrate settings to: %s', file_path)

        v1_settings_path.unlink()
    else:
        logging.debug('No v1 settings file: %s', v1_settings_path)

        v2_settings_path = Path('~/.inverter-connect.toml').expanduser()
        if v2_settings_path.is_file():
            logging.info('Move settings file %s to %s', v2_settings_path, file_path)
            file_path.parent.mkdir(exist_ok=True)
            v2_settings_path.rename(file_path)
        else:
            logging.debug('No old settings file found here: %s', v2_settings_path)


def make_config(*, user_settings: UserSettings, ip, port, verbosity, inverter=None) -> Config:
    # "Validate" ip address:
    try:
        result = socket.gethostbyname(ip)
    except socket.gaierror as err:
        human_error(message=f'Is the given {ip=!r} is wrong?!?', title='[red]IP address error', exception=err)
    else:
        logging.debug('%r -> %r', ip, result)

    return Config(
        verbosity=verbosity,
        host=ip,
        port=port,
        mqtt_settings=user_settings.mqtt,
        inverter_name=inverter,
    )
