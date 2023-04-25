from pathlib import Path

from rich import print

from inverter.mqtt4homeassistant.data_classes import MqttSettings


CREDENTIAL_FILE_PATH = Path('~/.inverter-connect').expanduser()


def store_mqtt_settings(settings: MqttSettings):
    print(f'Store MQTT server settings into: {CREDENTIAL_FILE_PATH}')

    data_str = settings.as_json()

    CREDENTIAL_FILE_PATH.touch(exist_ok=True)
    CREDENTIAL_FILE_PATH.chmod(0o600)
    CREDENTIAL_FILE_PATH.write_text(data_str, encoding='UTF-8')
    return CREDENTIAL_FILE_PATH


def get_mqtt_settings() -> MqttSettings:
    try:
        data_str = CREDENTIAL_FILE_PATH.read_text(encoding='UTF-8')
    except FileNotFoundError as err:
        print(f'\n[red]ERROR: Error reading config: {err}')
        print('[bold](Hint save settings first with: "./cli.py store-settings")\n')
        raise FileNotFoundError(err)
    settings = MqttSettings.from_json(data_str)
    return settings
