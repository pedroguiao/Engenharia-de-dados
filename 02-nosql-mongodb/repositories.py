from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import Any, Callable, Iterator

from schemas_mongodb import COLLECTION_SPECS


_CURRENT_SESSION: ContextVar[Any | None] = ContextVar("mongo_session", default=None)


def _clean_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    cleaned = deepcopy(document)
    cleaned.pop("_id", None)
    return cleaned


def _ensure_safe_mapping(values: dict[str, Any]) -> None:
    """Impede que operadores MongoDB cheguem por filtros ou atualizações."""
    for key, value in values.items():
        if not isinstance(key, str) or key.startswith("$") or "." in key:
            raise ValueError("campo MongoDB não permitido")
        if isinstance(value, dict):
            raise ValueError("operadores MongoDB não são aceitos como valores")


class MongoRepository:
    def __init__(self, database: Any, collection_name: str):
        self.collection_name = collection_name
        self.collection = database[collection_name]
        self.primary_key = tuple(COLLECTION_SPECS[collection_name]["primary_key"])

    def _session_options(self) -> dict[str, Any]:
        session = _CURRENT_SESSION.get()
        return {"session": session} if session is not None else {}

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        _ensure_safe_mapping(document)
        payload = deepcopy(document)
        self.collection.insert_one(payload, **self._session_options())
        return _clean_document(payload) or {}

    def list_all(self, *, sort: list[tuple[str, int]] | None = None) -> list[dict[str, Any]]:
        cursor = self.collection.find({}, **self._session_options())
        if sort:
            cursor = cursor.sort(sort)
        return [_clean_document(document) or {} for document in cursor]

    def find_one(self, filters: dict[str, Any]) -> dict[str, Any] | None:
        _ensure_safe_mapping(filters)
        return _clean_document(
            self.collection.find_one(deepcopy(filters), **self._session_options())
        )

    def get(self, *key_values: Any) -> dict[str, Any] | None:
        if len(key_values) != len(self.primary_key):
            raise ValueError("quantidade incorreta de componentes da chave")
        return self.find_one(dict(zip(self.primary_key, key_values)))

    def exists(self, filters: dict[str, Any]) -> bool:
        return self.find_one(filters) is not None

    def update(self, key_values: tuple[Any, ...], changes: dict[str, Any]) -> dict[str, Any] | None:
        _ensure_safe_mapping(changes)
        selector = dict(zip(self.primary_key, key_values))
        _ensure_safe_mapping(selector)
        self.collection.update_one(
            selector,
            {"$set": deepcopy(changes)},
            **self._session_options(),
        )
        return self.find_one(selector)

    def delete(self, *key_values: Any) -> bool:
        selector = dict(zip(self.primary_key, key_values))
        _ensure_safe_mapping(selector)
        result = self.collection.delete_one(selector, **self._session_options())
        return result.deleted_count == 1

    def count(self, filters: dict[str, Any] | None = None) -> int:
        filters = filters or {}
        _ensure_safe_mapping(filters)
        return self.collection.count_documents(filters, **self._session_options())

    def next_integer(self, field: str) -> int:
        if field.startswith("$") or "." in field:
            raise ValueError("campo inválido")
        last = self.collection.find_one(
            {},
            sort=[(field, -1)],
            **self._session_options(),
        )
        return int(last[field]) + 1 if last and field in last else 1


class RepositoryBundle:
    """Agrupa repositórios e oferece fronteira transacional injetável."""

    COLLECTIONS = ("usuario", "estudante", "vinculo", "curso")

    def __init__(
        self,
        database: Any,
        *,
        mode: str = "mock",
        transaction_factory: Callable[[], Any] | None = None,
    ):
        self.database = database
        self.mode = mode
        self.transaction_factory = transaction_factory
        self.usuarios = MongoRepository(database, "usuario")
        self.estudantes = MongoRepository(database, "estudante")
        self.vinculos = MongoRepository(database, "vinculo")
        self.cursos = MongoRepository(database, "curso")
        self.by_name = {
            "usuario": self.usuarios,
            "estudante": self.estudantes,
            "vinculo": self.vinculos,
            "curso": self.cursos,
        }

    @contextmanager
    def atomic(self) -> Iterator[None]:
        """Rollback por snapshot no mock; aceita transação real futuramente."""
        if self.transaction_factory is not None:
            with self.transaction_factory() as session:
                token = _CURRENT_SESSION.set(session)
                try:
                    yield
                finally:
                    _CURRENT_SESSION.reset(token)
            return

        if self.mode != "mock":
            raise RuntimeError("transação real ainda não configurada para este modo")

        snapshots = {
            name: [deepcopy(document) for document in self.database[name].find({})]
            for name in self.COLLECTIONS
        }
        try:
            yield
        except Exception:
            for name, documents in snapshots.items():
                collection = self.database[name]
                collection.delete_many({})
                if documents:
                    collection.insert_many(documents)
            raise


def _create_indexes(bundle: RepositoryBundle) -> None:
    for collection_name, repository in bundle.by_name.items():
        for definition in COLLECTION_SPECS[collection_name]["indexes"]:
            options = {key: value for key, value in definition.items() if key != "keys"}
            repository.collection.create_index(definition["keys"], **options)


def create_repository_bundle(
    database: Any,
    *,
    mode: str = "mock",
    transaction_factory: Callable[[], Any] | None = None,
) -> RepositoryBundle:
    bundle = RepositoryBundle(
        database,
        mode=mode,
        transaction_factory=transaction_factory,
    )
    _create_indexes(bundle)
    return bundle
