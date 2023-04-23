from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class Config:
    yaml_filename: str | None

    host: str
    port: int = 48899

    pause: float = 0.1
    timeout: int = 5

    init_cmd: bytes = b'WIFIKIT-214028-READ'
    debug: bool = False
