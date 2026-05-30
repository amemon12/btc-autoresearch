from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btc_autoresearch.simple_yaml import load_yaml


@dataclass(frozen=True)
class AppConfig:
    root: Path
    values: dict[str, Any]

    @property
    def database_path(self) -> Path:
        return self.root / self.values["database_path"]

    @property
    def data_dir(self) -> Path:
        return self.root / self.values["data_dir"]

    @property
    def vault_dir(self) -> Path:
        return self.root / self.values["vault_dir"]


def load_config(path: str | Path = "config/config.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    values = load_yaml(config_path)
    return AppConfig(root=config_path.parent.parent, values=values)
