from __future__ import annotations

import dataclasses
from datetime import time


@dataclasses.dataclass
class Config:
    yaml_filename: str | None

    host: str
    port: int = 48899

    pause: float = 0.1
    timeout: int = 5

    init_cmd: bytes = b'WIFIKIT-214028-READ'
    debug: bool = False

    daily_production_name: str = 'Daily Production'  # Must be the same as in yaml config!
    reset_needed_start: time = time(hour=1)
    reset_needed_end: time = time(hour=3)
