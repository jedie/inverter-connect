from ha_services.mqtt4homeassistant.data_classes import MqttSettings

from inverter.data_types import Config


def set_defaults(dictionary: dict, defaults: dict):
    for key, value in defaults.items():
        dictionary.setdefault(key, value)


def get_config(**kwargs) -> Config:
    set_defaults(
        kwargs,
        defaults=dict(
            verbosity=0,
            host='123.123.0.1',
            port=48899,
            mqtt_settings=MqttSettings(),
            inverter_name='deye_2mppt',
        ),
    )
    return Config(**kwargs)
