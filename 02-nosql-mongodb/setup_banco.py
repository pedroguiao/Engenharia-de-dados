from __future__ import annotations

import argparse
from typing import Any, Iterable
from pymongo.errors import OperationFailure

from schemas_mongodb import COLLECTION_NAMES, COLLECTION_SPECS


def print_plan() -> None:
    print("Plano de schema MongoDB (sem dados, seeds ou exclusões)")
    for collection_name in COLLECTION_NAMES:
        spec = COLLECTION_SPECS[collection_name]
        index_names = ", ".join(index["name"] for index in spec["indexes"])
        print(
            f"- {collection_name}: aplicar validator; "
            f"índices [{index_names or 'nenhum'}]"
        )


def _create_index(collection: Any, definition: dict[str, Any]) -> str:
    options = {
        key: value
        for key, value in definition.items()
        if key not in {"keys"}
    }
    try:
        return collection.create_index(definition["keys"], **options)
    except OperationFailure as exc:
        if exc.code == 85:
            print(f"    [!] Corrigindo conflito de nome no índice {definition.get('name')}...")
            collection.drop_index(definition["keys"])
            return collection.create_index(definition["keys"], **options)
        raise

def apply_schema() -> None:
    """Aplica apenas collections, validators e índices; nunca altera documentos."""
    from db import create_mongo_client

    client = None
    try:
        client, database = create_mongo_client()
        existing = set(database.list_collection_names())
        for collection_name in COLLECTION_NAMES:
            spec = COLLECTION_SPECS[collection_name]
            if collection_name in existing:
                database.command(
                    "collMod",
                    collection_name,
                    validator=spec["validator"],
                    validationLevel="strict",
                    validationAction="error",
                )
                action = "validator atualizado"
            else:
                database.create_collection(
                    collection_name,
                    validator=spec["validator"],
                    validationLevel="strict",
                    validationAction="error",
                )
                action = "coleção criada"

            collection = database[collection_name]
            created_indexes = [
                _create_index(collection, definition)
                for definition in spec["indexes"]
            ]
            print(
                f"{collection_name}: {action}; "
                f"{len(created_indexes)} índice(s) confirmado(s)"
            )
    finally:
        if client is not None:
            client.close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Setup seguro dos validators e índices MongoDB"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="somente mostra o plano (padrão)")
    mode.add_argument("--apply", action="store_true", help="autoriza alterações de schema")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_argument_parser().parse_args(list(argv) if argv is not None else None)
    print_plan()
    if not args.apply:
        print("\nDry-run concluído: nenhuma conexão ou alteração foi realizada.")
        return 0

    try:
        apply_schema()
    except Exception as exc:
        print(f"Falha ao aplicar schema: {exc}")
        return 2
    print("\nSchemas e índices aplicados; nenhum documento foi modificado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
