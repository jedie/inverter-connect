from inverter.mqtt4homeassistant.data_classes import HaMqttPayload, HaValue, HaValues
from inverter.mqtt4homeassistant.utilities.string_utils import slugify


def values2mqtt_payload(
    values: HaValues,
    name_prefix: str,
    default_device_class: str = 'energy',
    default_state_class: str = 'measurement',
) -> HaMqttPayload:
    assert not name_prefix[0].isdigit(), f'Invalid: {name_prefix=}'
    device_id = f'{slugify(name_prefix).lower()}_{slugify(values.device_name).lower()}'
    state = {
        'data': {},
        'topic': f'{values.prefix}/{values.component}/{device_id}/state',
    }
    config_data = {}
    for value in values.values:
        assert isinstance(value, HaValue), f'Wrong type: {value=!r}'

        key = slugify(value.name).lower()
        unique_id = f'{device_id}_{key}'

        assert key not in config_data, f'Double {unique_id=!r} from {value=!r} - {config_data=!r}'
        config_data[unique_id] = dict(
            name=value.name,
            device_class=value.device_class or default_device_class,
            state_class=value.state_class or default_state_class,
            state_topic=state['topic'],
            unit_of_measurement=value.unit,
            unique_id=unique_id,
            value_template='{{ value_json.%(value_key)s }}' % dict(value_key=unique_id),
        )
        state['data'][unique_id] = value.value

    configs = []
    for unique_id, data in config_data.items():
        configs.append(
            {
                'data': {
                    'device': {
                        'identifiers': sorted(config_data.keys()),
                        'name': values.device_name,
                    },
                    **data,
                },
                'topic': f'{values.prefix}/{values.component}/{unique_id}/config',
            }
        )

    return HaMqttPayload(configs=configs, state=state)
