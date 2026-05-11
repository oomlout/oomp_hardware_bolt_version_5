from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_PORT_CONFIG = {
    "host": "127.0.0.1",
    "port": 5000,
}


def load_port_config(config_path: Path | str) -> dict[str, Any]:
    path = Path(config_path)
    config = dict(DEFAULT_PORT_CONFIG)
    if not path.exists():
        return config

    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        return config

    raw_host = str(loaded.get("host", config["host"])).strip()
    if raw_host:
        config["host"] = raw_host

    raw_port = loaded.get("port", config["port"])
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        return config

    if 1 <= port <= 65535:
        config["port"] = port

    return config
