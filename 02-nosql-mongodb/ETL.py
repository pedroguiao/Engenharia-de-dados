from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from schemas_mongodb import COLLECTION_NAMES, COLLECTION_SPECS


# (nome SQL, nome MongoDB, conversor)
COLUMN_SPECS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "usuario": (
        ("cpf", "cpf", "cpf"),
        ("nome", "nome", "str"),
        ("data_nascimento", "data_nascimento", "date"),
        ("email", "email", "array"),
        ("telefone", "telefone", "array"),
        ("login", "login", "str"),
        ("senha", "senha", "str"),
    ),
    "professor": (
        ("mat_professor", "mat_professor", "str"),
        ("cpf", "cpf", "cpf"),
        ("departamento", "departamento", "str"),
        ("formacao", "formacao", "str"),
        ("data_admissao", "data_admissao", "date"),
        ("tipo_jornada_trabalho", "tipo_jornada_trabalho", "str"),
        ("salario", "salario", "decimal"),
    ),
    "departamento": (
        ("cod_depto", "cod_depto", "str"),
        ("nome", "nome", "str"),
        ("chefe", "chefe", "str"),
        ("orcamento", "orcamento", "decimal"),
        ("comissal", "comissal", "decimal"),
    ),
    "curso": (
        ("idcurso", "idCurso", "int"),
        ("nome", "nome", "str"),
        ("grau", "grau", "str"),
        ("turno", "turno", "str"),
        ("campus", "campus", "str"),
        ("nivel", "nivel", "str"),
    ),
    "estudante": (
        ("mat_estudante", "mat_estudante", "str"),
        ("cpf", "cpf", "cpf"),
        ("mc", "MC", "decimal"),
        ("ano_ingresso", "ano_ingresso", "int"),
    ),
    "vinculo": (
        ("idvinculo", "idVinculo", "int"),
        ("mat_estudante", "mat_estudante", "str"),
        ("curso", "idCurso", "int"),
        ("data_entrada", "data_entrada", "date"),
        ("status", "status", "str"),
        ("data_saida", "data_saida", "date"),
    ),
    "projeto": (
        ("id_projeto", "id_projeto", "int"),
        ("descricao", "descricao", "str"),
    ),
    "plano": (
        ("id_projeto", "id_projeto", "int"),
        ("mat_professor", "mat_professor", "str"),
        ("mat_estudante", "mat_estudante", "str"),
        ("ano", "ano", "int"),
    ),
    "disciplina": (
        ("cod_disc", "cod_disc", "str"),
        ("nome", "nome", "str"),
        ("pre_req", "pre_req", "str"),
        ("creditos", "creditos", "int"),
        ("depto_responsavel", "depto_responsavel", "str"),
    ),
    "semestre": (
        ("ano", "ano", "int"),
        ("semestre", "semestre", "int"),
        ("data_inicio", "data_inicio", "date"),
        ("data_fom", "data_fom", "date"),
    ),
    "sala": (
        ("id_sala", "id_sala", "int"),
        ("descricao", "descricao", "str"),
    ),
    "horario": (
        ("id_horario", "id_horario", "int"),
        ("dia", "dia", "str"),
        ("slot", "slot", "int"),
    ),
    "turma": (
        ("id_turma", "id_turma", "int"),
        ("cod_disc", "cod_disc", "str"),
        ("numero", "numero", "int"),
        ("ano", "ano", "int"),
        ("semestre", "semestre", "int"),
    ),
    "leciona": (
        ("id_turma", "id_turma", "int"),
        ("mat_professor", "mat_professor", "str"),
    ),
    "alocacao": (
        ("id_turma", "id_turma", "int"),
        ("id_horario", "id_horario", "int"),
        ("id_sala", "id_sala", "int"),
    ),
    "cursa": (
        ("mat_estudante", "mat_estudante", "str"),
        ("id_turma", "id_turma", "int"),
        ("nota", "nota", "decimal"),
    ),
}


INSERT_RE = re.compile(
    r"^\s*INSERT\s+INTO\s+(?:universidade\.)?"
    r"(?P<table>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?:\((?P<columns>[^)]*)\))?\s*"
    r"VALUES\s*\((?P<values>.*)\)\s*$",
    re.IGNORECASE | re.DOTALL,
)

CHIEF_UPDATE_RE = re.compile(
    r"^\s*UPDATE\s+(?:universidade\.)?departamento\s+"
    r"SET\s+chefe\s*=\s*(?P<chefe>NULL|'(?:''|[^'])*')\s+"
    r"WHERE\s+cod_depto\s*=\s*(?P<codigo>'(?:''|[^'])*')\s*$",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class TableReport:
    lidos: int = 0
    validos: int = 0
    invalidos: int = 0
    duplicados: int = 0
    referencias_ausentes: int = 0


@dataclass
class ETLResult:
    documents: dict[str, list[dict[str, Any]]]
    valid_documents: dict[str, list[dict[str, Any]]]
    reports: dict[str, TableReport]
    errors: list[str] = field(default_factory=list)
    chief_updates: int = 0

    @property
    def has_blocking_issues(self) -> bool:
        return any(
            report.invalidos or report.duplicados or report.referencias_ausentes
            for report in self.reports.values()
        )


def split_sql_statements(content: str) -> list[str]:
    """Divide SQL apenas em ponto e vírgula fora de strings e comentários."""
    statements: list[str] = []
    buffer: list[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: str | None = None
    index = 0

    while index < len(content):
        char = content[index]
        nxt = content[index + 1] if index + 1 < len(content) else ""

        if in_line_comment:
            buffer.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            buffer.append(char)
            if char == "*" and nxt == "/":
                buffer.append(nxt)
                index += 2
                in_block_comment = False
            else:
                index += 1
            continue

        if dollar_tag:
            if content.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
            else:
                buffer.append(char)
                index += 1
            continue

        if not in_single and not in_double:
            if char == "-" and nxt == "-":
                buffer.extend((char, nxt))
                index += 2
                in_line_comment = True
                continue
            if char == "/" and nxt == "*":
                buffer.extend((char, nxt))
                index += 2
                in_block_comment = True
                continue
            if char == "$":
                match = re.match(r"\$[A-Za-z_0-9]*\$", content[index:])
                if match:
                    dollar_tag = match.group(0)
                    buffer.append(dollar_tag)
                    index += len(dollar_tag)
                    continue

        if char == "'" and not in_double:
            buffer.append(char)
            if in_single and nxt == "'":
                buffer.append(nxt)
                index += 2
                continue
            in_single = not in_single
            index += 1
            continue

        if char == '"' and not in_single:
            buffer.append(char)
            if in_double and nxt == '"':
                buffer.append(nxt)
                index += 2
                continue
            in_double = not in_double
            index += 1
            continue

        if char == ";" and not in_single and not in_double:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            index += 1
            continue

        buffer.append(char)
        index += 1

    final = "".join(buffer).strip()
    if final:
        statements.append(final)
    if in_single or in_double or dollar_tag or in_block_comment:
        raise ValueError("SQL termina com literal, identificador ou comentário não fechado")
    return statements


def split_sql_values(raw_values: str) -> list[str]:
    """Divide uma lista VALUES respeitando strings e parênteses internos."""
    values: list[str] = []
    buffer: list[str] = []
    in_single = False
    in_double = False
    depth = 0
    index = 0
    while index < len(raw_values):
        char = raw_values[index]
        nxt = raw_values[index + 1] if index + 1 < len(raw_values) else ""
        if char == "'" and not in_double:
            buffer.append(char)
            if in_single and nxt == "'":
                buffer.append(nxt)
                index += 2
                continue
            in_single = not in_single
        elif char == '"' and not in_single:
            buffer.append(char)
            if in_double and nxt == '"':
                buffer.append(nxt)
                index += 2
                continue
            in_double = not in_double
        elif not in_single and not in_double and char == "(":
            depth += 1
            buffer.append(char)
        elif not in_single and not in_double and char == ")":
            depth -= 1
            buffer.append(char)
        elif not in_single and not in_double and char == "," and depth == 0:
            values.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
        index += 1
    if in_single or in_double or depth != 0:
        raise ValueError("lista VALUES malformada")
    values.append("".join(buffer).strip())
    return values


def parse_sql_literal(token: str) -> Any:
    """Converte NULL, strings SQL e números sem recorrer a float."""
    token = token.strip()
    if token.upper() == "NULL":
        return None
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1].replace("''", "'")
    if len(token) >= 3 and token[0] in "eE" and token[1] == "'" and token[-1] == "'":
        text = token[2:-1].replace("''", "'")
        return text.replace("\\'", "'").replace("\\\\", "\\")
    if re.fullmatch(r"[+-]?\d+", token):
        return int(token)
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?", token):
        try:
            return Decimal(token)
        except InvalidOperation as exc:
            raise ValueError(f"número inválido: {token}") from exc
    raise ValueError(f"literal SQL não suportado: {token}")


def parse_postgres_array(value: str) -> list[str | None]:
    """Interpreta array textual PostgreSQL, inclusive aspas, escapes e vírgulas."""
    if not (value.startswith("{") and value.endswith("}")):
        raise ValueError(f"array PostgreSQL inválido: {value}")
    content = value[1:-1]
    if not content:
        return []

    result: list[str | None] = []
    buffer: list[str] = []
    in_quotes = False
    quoted_element = False
    index = 0

    def append_element() -> None:
        text = "".join(buffer)
        if not quoted_element:
            text = text.strip()
        result.append(None if not quoted_element and text.upper() == "NULL" else text)

    while index < len(content):
        char = content[index]
        if char == "\\":
            index += 1
            if index >= len(content):
                raise ValueError("escape incompleto em array PostgreSQL")
            buffer.append(content[index])
        elif char == '"':
            if not in_quotes and not quoted_element and not "".join(buffer).strip():
                buffer = []
            in_quotes = not in_quotes
            quoted_element = True
        elif char == "," and not in_quotes:
            append_element()
            buffer = []
            quoted_element = False
        elif not in_quotes and quoted_element and char.isspace():
            pass
        else:
            buffer.append(char)
        index += 1
    if in_quotes:
        raise ValueError("aspas não fechadas em array PostgreSQL")
    append_element()
    return result


def convert_value(value: Any, kind: str) -> Any:
    if value is None:
        return None
    if kind == "str":
        if not isinstance(value, str):
            raise ValueError(f"texto esperado, recebido {value!r}")
        return value
    if kind == "cpf":
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            return str(value)
        raise ValueError(f"CPF inválido: {value!r}")
    if kind == "int":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, Decimal) and value == value.to_integral_value():
            return int(value)
        raise ValueError(f"inteiro esperado, recebido {value!r}")
    if kind == "decimal":
        if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
            return value
        raise ValueError(f"número esperado, recebido {value!r}")
    if kind == "date":
        if not isinstance(value, str):
            raise ValueError(f"data textual esperada, recebida {value!r}")
        for date_format in ("%Y/%m/%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                pass
        raise ValueError(f"data inválida: {value!r}")
    if kind == "array":
        if not isinstance(value, str):
            raise ValueError(f"array textual esperado, recebido {value!r}")
        return parse_postgres_array(value)
    raise ValueError(f"conversor desconhecido: {kind}")


def parse_insert_statement(statement: str) -> tuple[str, dict[str, Any]] | None:
    match = INSERT_RE.match(statement)
    if not match:
        return None
    table = match.group("table").lower()
    if table not in COLUMN_SPECS:
        return None

    raw_values = split_sql_values(match.group("values"))
    default_columns = COLUMN_SPECS[table]
    columns_text = match.group("columns")
    if columns_text:
        requested = [column.strip().strip('"').lower() for column in columns_text.split(",")]
        by_sql_name = {sql_name: (mongo_name, kind) for sql_name, mongo_name, kind in default_columns}
        try:
            columns = [(name, *by_sql_name[name]) for name in requested]
        except KeyError as exc:
            raise ValueError(f"coluna desconhecida em {table}: {exc.args[0]}") from exc
    else:
        columns = list(default_columns)

    if len(raw_values) != len(columns):
        raise ValueError(
            f"{table}: esperados {len(columns)} valores, recebidos {len(raw_values)}"
        )
    document: dict[str, Any] = {}
    for raw, (_, mongo_name, kind) in zip(raw_values, columns):
        document[mongo_name] = convert_value(parse_sql_literal(raw), kind)
    return table, document


def _matches_bson_type(value: Any, bson_types: str | list[str]) -> bool:
    allowed = [bson_types] if isinstance(bson_types, str) else bson_types
    checks = {
        "null": lambda item: item is None,
        "string": lambda item: isinstance(item, str),
        "array": lambda item: isinstance(item, list),
        "object": lambda item: isinstance(item, dict),
        "date": lambda item: isinstance(item, datetime),
        "decimal": lambda item: isinstance(item, Decimal),
        "double": lambda item: isinstance(item, float),
        "int": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "long": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "bool": lambda item: isinstance(item, bool),
    }
    return any(checks.get(name, lambda _item: False)(value) for name in allowed)


def validate_document(table: str, document: dict[str, Any]) -> list[str]:
    schema = COLLECTION_SPECS[table]["validator"]["$jsonSchema"]
    errors: list[str] = []
    for required in schema.get("required", []):
        if required not in document or document[required] is None:
            errors.append(f"campo obrigatório ausente: {required}")

    allowed_properties = set(schema.get("properties", {}))
    extras = set(document) - allowed_properties
    if extras and schema.get("additionalProperties") is False:
        errors.append("campos desconhecidos: " + ", ".join(sorted(extras)))

    for field_name, value in document.items():
        rule = schema.get("properties", {}).get(field_name)
        if not rule:
            continue
        if "bsonType" in rule and not _matches_bson_type(value, rule["bsonType"]):
            errors.append(f"{field_name}: tipo incompatível")
            continue
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"{field_name}: valor fora do domínio")
        if isinstance(value, str):
            if "maxLength" in rule and len(value) > rule["maxLength"]:
                errors.append(f"{field_name}: excede {rule['maxLength']} caracteres")
            if "pattern" in rule and not re.fullmatch(rule["pattern"], value):
                errors.append(f"{field_name}: formato inválido")
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            if "minimum" in rule:
                if rule.get("exclusiveMinimum") and value <= rule["minimum"]:
                    errors.append(f"{field_name}: deve ser maior que {rule['minimum']}")
                elif not rule.get("exclusiveMinimum") and value < rule["minimum"]:
                    errors.append(f"{field_name}: abaixo do mínimo {rule['minimum']}")
            if "maximum" in rule and value > rule["maximum"]:
                errors.append(f"{field_name}: acima do máximo {rule['maximum']}")
        if isinstance(value, list) and "items" in rule:
            for item in value:
                item_type = rule["items"].get("bsonType")
                if item_type and not _matches_bson_type(item, item_type):
                    errors.append(f"{field_name}: item com tipo incompatível")
                    break
    return errors


def _parse_chief_update(statement: str) -> tuple[str, str | None] | None:
    match = CHIEF_UPDATE_RE.match(statement)
    if not match:
        return None
    codigo = parse_sql_literal(match.group("codigo"))
    chefe = parse_sql_literal(match.group("chefe"))
    return codigo, chefe


def process_sql(content: str) -> ETLResult:
    documents = {name: [] for name in COLLECTION_NAMES}
    reports = {name: TableReport() for name in COLLECTION_NAMES}
    errors: list[str] = []
    chief_updates: list[tuple[str, str | None]] = []

    for statement_number, statement in enumerate(split_sql_statements(content), start=1):
        insert_match = re.match(
            r"^\s*INSERT\s+INTO\s+(?:universidade\.)?([A-Za-z_][A-Za-z0-9_]*)",
            statement,
            re.IGNORECASE,
        )
        if insert_match:
            table = insert_match.group(1).lower()
            if table not in documents:
                continue
            reports[table].lidos += 1
            try:
                parsed = parse_insert_statement(statement)
                if parsed is None:
                    raise ValueError("formato INSERT não reconhecido")
                _, document = parsed
                documents[table].append(document)
            except ValueError as exc:
                reports[table].invalidos += 1
                errors.append(f"comando {statement_number}, {table}: {exc}")
            continue

        try:
            update = _parse_chief_update(statement)
        except ValueError as exc:
            errors.append(f"comando {statement_number}, UPDATE de chefia: {exc}")
            continue
        if update:
            chief_updates.append(update)

    applied_updates = 0
    departments_by_code: dict[str, list[dict[str, Any]]] = {}
    for department in documents["departamento"]:
        departments_by_code.setdefault(department.get("cod_depto"), []).append(department)
    for codigo, chefe in chief_updates:
        targets = departments_by_code.get(codigo, [])
        if not targets:
            errors.append(f"UPDATE de chefia aponta para departamento inexistente: {codigo}")
            continue
        for target in targets:
            target["chefe"] = chefe
        applied_updates += 1

    duplicate_indices: dict[str, set[int]] = {name: set() for name in COLLECTION_NAMES}
    for table, table_documents in documents.items():
        for unique_fields in COLLECTION_SPECS[table]["unique_keys"]:
            seen: dict[tuple[Any, ...], int] = {}
            for index, document in enumerate(table_documents):
                key = tuple(document.get(field) for field in unique_fields)
                if any(value is None for value in key):
                    continue
                if key in seen:
                    duplicate_indices[table].add(index)
                    errors.append(
                        f"{table}: duplicidade em {unique_fields}: {key}"
                    )
                else:
                    seen[key] = index
        reports[table].duplicados = len(duplicate_indices[table])

    invalid_indices: dict[str, set[int]] = {name: set() for name in COLLECTION_NAMES}
    for table, table_documents in documents.items():
        for index, document in enumerate(table_documents):
            if index in duplicate_indices[table]:
                continue
            validation_errors = validate_document(table, document)
            if validation_errors:
                invalid_indices[table].add(index)
                errors.extend(f"{table}: {message}" for message in validation_errors)

    broken_references: set[tuple[str, int, int]] = set()
    changed = True
    while changed:
        changed = False
        target_keys: dict[tuple[str, tuple[str, ...]], set[tuple[Any, ...]]] = {}
        for target_table, target_documents in documents.items():
            for reference_owner in COLLECTION_SPECS.values():
                for reference in reference_owner["references"]:
                    if reference["target"] != target_table:
                        continue
                    target_fields = tuple(reference["target_fields"])
                    cache_key = (target_table, target_fields)
                    if cache_key in target_keys:
                        continue
                    target_keys[cache_key] = {
                        tuple(document.get(field) for field in target_fields)
                        for index, document in enumerate(target_documents)
                        if index not in duplicate_indices[target_table]
                        and index not in invalid_indices[target_table]
                    }

        for table, table_documents in documents.items():
            for index, document in enumerate(table_documents):
                if index in duplicate_indices[table] or index in invalid_indices[table]:
                    continue
                for reference_number, reference in enumerate(
                    COLLECTION_SPECS[table]["references"]
                ):
                    source_key = tuple(document.get(field) for field in reference["fields"])
                    if any(value is None for value in source_key):
                        continue
                    cache_key = (reference["target"], tuple(reference["target_fields"]))
                    if source_key not in target_keys.get(cache_key, set()):
                        broken = (table, index, reference_number)
                        if broken not in broken_references:
                            broken_references.add(broken)
                            reports[table].referencias_ausentes += 1
                            errors.append(
                                f"{table}: referência ausente {reference['fields']}={source_key} "
                                f"em {reference['target']}{reference['target_fields']}"
                            )
                        invalid_indices[table].add(index)
                        changed = True
                        break

    valid_documents: dict[str, list[dict[str, Any]]] = {}
    for table, table_documents in documents.items():
        valid_documents[table] = [
            document
            for index, document in enumerate(table_documents)
            if index not in duplicate_indices[table] and index not in invalid_indices[table]
        ]
        reports[table].invalidos += len(invalid_indices[table])
        reports[table].validos = len(valid_documents[table])

    return ETLResult(
        documents=documents,
        valid_documents=valid_documents,
        reports=reports,
        errors=errors,
        chief_updates=applied_updates,
    )


def load_sql_dump(path: str | Path) -> ETLResult:
    return process_sql(Path(path).read_text(encoding="utf-8"))


def print_report(result: ETLResult) -> None:
    print("\nRelatório do ETL")
    print(
        f"{'tabela':<15} {'lidos':>7} {'válidos':>8} {'inválidos':>10} "
        f"{'duplicados':>11} {'refs ausentes':>14}"
    )
    print("-" * 70)
    for table in COLLECTION_NAMES:
        report = result.reports[table]
        print(
            f"{table:<15} {report.lidos:>7} {report.validos:>8} "
            f"{report.invalidos:>10} {report.duplicados:>11} "
            f"{report.referencias_ausentes:>14}"
        )
    print(f"\nUPDATEs de chefia processados: {result.chief_updates}")
    if result.errors:
        print("\nInconsistências:")
        for error in result.errors:
            print(f"- {error}")
    else:
        print("\nNenhuma inconsistência de dados detectada.")


def _prepare_for_bson(value: Any) -> Any:
    if isinstance(value, Decimal):
        from bson.decimal128 import Decimal128

        return Decimal128(value)
    if isinstance(value, dict):
        return {key: _prepare_for_bson(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_prepare_for_bson(item) for item in value]
    return value


def apply_to_mongodb(result: ETLResult) -> None:
    """Faz somente upsert por chave primária; nunca remove documentos."""
    if result.has_blocking_issues:
        raise RuntimeError(
            "Aplicação cancelada: o dry-run contém inválidos, duplicados ou referências ausentes."
        )

    from pymongo import UpdateOne

    from db import create_mongo_client

    client = None
    try:
        client, database = create_mongo_client()
        for table in COLLECTION_NAMES:
            documents = result.valid_documents[table]
            if not documents:
                continue
            primary_key = COLLECTION_SPECS[table]["primary_key"]
            operations = []
            for document in documents:
                prepared = _prepare_for_bson(document)
                selector = {field: prepared[field] for field in primary_key}
                operations.append(UpdateOne(selector, {"$set": prepared}, upsert=True))
            database[table].bulk_write(operations, ordered=False)
            print(f"{table}: {len(operations)} upsert(s) enviados")
    finally:
        if client is not None:
            client.close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ETL seguro do dump SQL para MongoDB")
    parser.add_argument(
        "--input",
        default="universidade-dump-engdados.sql",
        help="caminho do dump SQL",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="somente analisa (padrão)")
    mode.add_argument("--apply", action="store_true", help="autoriza upserts no MongoDB")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_argument_parser().parse_args(list(argv) if argv is not None else None)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Modo: {mode}")
    print(f"Entrada: {args.input}")
    try:
        result = load_sql_dump(args.input)
    except (OSError, ValueError) as exc:
        print(f"Erro ao ler/processar o dump: {exc}", file=sys.stderr)
        return 2

    print_report(result)
    if not args.apply:
        print("\nDry-run concluído: nenhuma conexão ou escrita foi realizada.")
        return 1 if result.has_blocking_issues else 0

    try:
        apply_to_mongodb(result)
    except Exception as exc:
        print(f"Falha ao aplicar ETL: {exc}", file=sys.stderr)
        return 3
    print("Aplicação concluída sem exclusões.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
