from __future__ import annotations

from typing import Any

from config import get_settings


def create_mock_database(database_name: str = "universidade_mock") -> tuple[Any, Any]:
    """Cria MongoDB estritamente em memória, sem qualquer socket de rede."""
    try:
        import mongomock
    except ImportError as exc:
        raise RuntimeError(
            "A dependência mongomock não está instalada. Instale requirements.txt."
        ) from exc
    client = mongomock.MongoClient()
    return client, client[database_name]


def create_mongo_client() -> tuple[Any, Any]:
    """Cria cliente Atlas somente quando MONGODB_MODE=atlas foi explícito."""
    settings = get_settings(require_mongodb=True)
    try:
        from pymongo import MongoClient
    except ImportError as exc:  # pragma: no cover - depende do ambiente remoto
        raise RuntimeError(
            "A dependência pymongo não está instalada. Instale requirements.txt."
        ) from exc

    client = MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
    except Exception:
        client.close()
        raise
    return client, client[settings.mongodb_database]
