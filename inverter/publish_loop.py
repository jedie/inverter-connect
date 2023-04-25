import time

from rich import print  # noqa

from inverter.api import Inverter, InverterValue
from inverter.config import Config
from inverter.connection import InverterInfo
from inverter.constants import ERROR_STR_NO_DATA
from inverter.exceptions import ReadInverterError, ReadTimeout
from inverter.mqtt4homeassistant.converter import values2mqtt_payload
from inverter.mqtt4homeassistant.data_classes import HaValue, HaValues, MqttSettings
from inverter.mqtt4homeassistant.mqtt import HaMqttPublisher


def publish_forever(*, mqtt_settings: MqttSettings, config: Config, verbose):
    publisher = HaMqttPublisher(settings=mqtt_settings, verbose=verbose, config_count=1)

    while True:
        try:
            with Inverter(config=config) as inverter:
                inverter_info: InverterInfo = inverter.inv_sock.inverter_info
                print(inverter_info)
                print()

                try:
                    values = []
                    for value in inverter:
                        assert isinstance(value, InverterValue), f'{value!r}'
                        if value.value == ERROR_STR_NO_DATA:
                            # Don't send a MQTT message if one of the values are missing:
                            raise ReadInverterError(f'Missing data for {value.name}')

                        values.append(
                            HaValue(
                                name=value.name,
                                value=value.value,
                                device_class=value.device_class,
                                state_class=value.state_class,
                                unit=value.unit,
                            )
                        )
                except ReadInverterError as err:
                    print(f'[red]{err}')
                else:
                    values = HaValues(
                        device_name=str(inverter_info.serial),
                        values=values,
                        prefix='homeassistant',
                        component='sensor',
                    )
                    ha_mqtt_payload = values2mqtt_payload(values=values, name_prefix='inverter')
                    publisher.publish2homeassistant(ha_mqtt_payload=ha_mqtt_payload)
        except ReadTimeout as err:
            print(f'[red]{err}')

        print('Wait', end='...')
        for i in range(10, 1, -1):
            time.sleep(1)
            print(i, end='...')
