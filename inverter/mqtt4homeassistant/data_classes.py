from __future__ import annotations

import dataclasses
import json

from bx_py_utils.anonymize import anonymize


@dataclasses.dataclass
class HaValue:
    name: str
    value: int | float | str
    device_class: str  # e.g.: "voltage" / "current" / "energy" etc.
    state_class: str  # e.g.: "measurement" / "total" / "total_increasing" etc.
    unit: str | None  # e.g.: "V" / "A" / "kWh" etc.


@dataclasses.dataclass
class HaValues:
    device_name: str
    values: list[HaValue, ...]
    prefix: str = 'homeassistant'
    component: str = 'sensor'


@dataclasses.dataclass
class HaMqttPayload:
    configs: list[dict, ...]
    state: dict


@dataclasses.dataclass
class MqttSettings:
    host: str
    port: int
    user_name: str
    password: str

    def as_json(self):
        data = dataclasses.asdict(self)
        data_str = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        return data_str

    @classmethod
    def from_json(cls, data_str):
        data = json.loads(data_str)
        return cls(**data)

    def anonymized(self):
        data = dataclasses.asdict(self)
        if self.password:
            data['password'] = anonymize(self.password)
        return data
