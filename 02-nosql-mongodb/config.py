from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Indica configuração ausente ou inválida."""


def _load_env_file(path: Path = Path(".env")) -> None:
    """Carrega pares simples de um .env local sem sobrescrever o ambiente."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    mongodb_mode: str
    mongodb_uri: str | None
    mongodb_database: str | None
    demo_seed: bool
    flask_secret_key: str | None


def get_settings(*, require_mongodb: bool = False) -> Settings:
    """Retorna configurações; exige as duas variáveis somente para escrita."""
    _load_env_file()
    mode = (os.getenv("MONGODB_MODE") or "disabled").strip().lower()
    if mode not in {"disabled", "mock", "atlas"}:
        raise ConfigurationError(
            "MONGODB_MODE deve ser 'mock', 'atlas' ou permanecer desabilitado."
        )
    settings = Settings(
        mongodb_mode=mode,
        mongodb_uri=os.getenv("MONGODB_URI") or None,
        mongodb_database=os.getenv("MONGODB_DATABASE") or None,
        demo_seed=(os.getenv("DEMO_SEED") or "0").strip().lower()
        in {"1", "true", "yes", "sim"},
        flask_secret_key=os.getenv("FLASK_SECRET_KEY") or None,
    )
    if require_mongodb:
        missing = []
        if settings.mongodb_mode != "atlas":
            missing.append("MONGODB_MODE=atlas")
        if not settings.mongodb_uri:
            missing.append("MONGODB_URI")
        if not settings.mongodb_database:
            missing.append("MONGODB_DATABASE")
        if missing:
            raise ConfigurationError(
                "Configuração obrigatória ausente: " + ", ".join(missing)
            )
    return settings
