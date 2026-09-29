from __future__ import annotations

from typing import Any


DATE_OR_NULL = {"bsonType": ["date", "null"]}
INT = {"bsonType": ["int", "long"]}
INT_OR_NULL = {"bsonType": ["int", "long", "null"]}
NUMBER_OR_NULL = {"bsonType": ["decimal", "double", "int", "long", "null"]}
MATRICULA = {"bsonType": "string", "maxLength": 7}
MATRICULA_OR_NULL = {"bsonType": ["string", "null"], "maxLength": 7}
CPF = {"bsonType": "string", "pattern": "^[0-9]{1,13}$", "maxLength": 13}
CPF_OR_NULL = {
    "bsonType": ["string", "null"],
    "pattern": "^[0-9]{1,13}$",
    "maxLength": 13,
}


def _validator(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "additionalProperties": False,
            "required": required,
            "properties": {
                "_id": {"bsonType": "objectId"},
                **properties,
            },
        }
    }


def _index(
    name: str,
    *fields: str,
    unique: bool = True,
    partial: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition: dict[str, Any] = {
        "name": name,
        "keys": [(field, 1) for field in fields],
        "unique": unique,
    }
    if partial:
        definition["partialFilterExpression"] = partial
    return definition


COLLECTION_SPECS: dict[str, dict[str, Any]] = {
    "usuario": {
        "primary_key": ("cpf",),
        "unique_keys": (("cpf",), ("login",)),
        "references": (),
        "validator": _validator(
            ["cpf", "nome"],
            {
                "cpf": CPF,
                "nome": {"bsonType": "string", "maxLength": 100},
                "data_nascimento": DATE_OR_NULL,
                "email": {
                    "bsonType": ["array", "null"],
                    "items": {"bsonType": ["string", "null"]},
                },
                "telefone": {
                    "bsonType": ["array", "null"],
                    "items": {"bsonType": ["string", "null"]},
                },
                "login": {"bsonType": ["string", "null"], "maxLength": 45},
                "senha": {"bsonType": ["string", "null"], "maxLength": 32},
            },
        ),
        "indexes": [
            _index("uq_usuario_cpf", "cpf"),
            _index(
                "uq_usuario_login",
                "login",
                partial={"login": {"$type": "string"}},
            ),
        ],
    },
    "professor": {
        "primary_key": ("mat_professor",),
        "unique_keys": (("mat_professor",), ("cpf",)),
        "references": (
            {"fields": ("cpf",), "target": "usuario", "target_fields": ("cpf",)},
            {
                "fields": ("departamento",),
                "target": "departamento",
                "target_fields": ("cod_depto",),
            },
        ),
        "validator": _validator(
            ["mat_professor"],
            {
                "mat_professor": MATRICULA,
                "cpf": CPF_OR_NULL,
                "departamento": {"bsonType": ["string", "null"], "maxLength": 5},
                "formacao": {
                    "enum": [None, "Graduação", "Especialização", "Mestrado", "Doutorado"]
                },
                "data_admissao": DATE_OR_NULL,
                "tipo_jornada_trabalho": {"enum": [None, "20h", "40h", "DE"]},
                "salario": NUMBER_OR_NULL,
            },
        ),
        "indexes": [
            _index("pk_professor", "mat_professor"),
            _index("uq_professor_cpf", "cpf", partial={"cpf": {"$type": "string"}}),
        ],
    },
    "departamento": {
        "primary_key": ("cod_depto",),
        "unique_keys": (("cod_depto",),),
        "references": (
            {
                "fields": ("chefe",),
                "target": "professor",
                "target_fields": ("mat_professor",),
            },
        ),
        "validator": _validator(
            ["cod_depto", "nome"],
            {
                "cod_depto": {"bsonType": "string", "maxLength": 5},
                "nome": {"bsonType": "string", "maxLength": 50},
                "chefe": MATRICULA_OR_NULL,
                "orcamento": {
                    "bsonType": ["decimal", "double", "int", "long", "null"],
                    "minimum": 0,
                    "exclusiveMinimum": True,
                },
                "comissal": NUMBER_OR_NULL,
            },
        ),
        "indexes": [_index("pk_departamento", "cod_depto")],
    },
    "curso": {
        "primary_key": ("idCurso",),
        "unique_keys": (("idCurso",), ("nome", "turno", "campus", "nivel")),
        "references": (),
        "validator": _validator(
            ["idCurso", "nome", "turno"],
            {
                "idCurso": INT,
                "nome": {"bsonType": "string", "maxLength": 100},
                "grau": {"enum": [None, "Bacharelado", "Licenciatura Plena"]},
                "turno": {"enum": ["Matutino", "Vespertino", "Noturno", "Turno Indefinido"]},
                "campus": {"bsonType": ["string", "null"], "maxLength": 100},
                "nivel": {"enum": [None, "Graduação", "Mestrado", "Doutorado", "Lato"]},
            },
        ),
        "indexes": [
            _index("pk_curso", "idCurso"),
            _index(
                "uq_curso_nome_turno_campus_nivel",
                "nome",
                "turno",
                "campus",
                "nivel",
                partial={
                    "nome": {"$type": "string"},
                    "turno": {"$type": "string"},
                    "campus": {"$type": "string"},
                    "nivel": {"$type": "string"},
                },
            ),
        ],
    },
    "estudante": {
        "primary_key": ("mat_estudante",),
        "unique_keys": (("mat_estudante",), ("cpf",)),
        "references": (
            {"fields": ("cpf",), "target": "usuario", "target_fields": ("cpf",)},
        ),
        "validator": _validator(
            ["mat_estudante"],
            {
                "mat_estudante": MATRICULA,
                "cpf": CPF_OR_NULL,
                "MC": NUMBER_OR_NULL,
                "ano_ingresso": INT_OR_NULL,
            },
        ),
        "indexes": [
            _index("pk_estudante", "mat_estudante"),
            _index("uq_estudante_cpf", "cpf", partial={"cpf": {"$type": "string"}}),
        ],
    },
    "vinculo": {
        "primary_key": ("idVinculo",),
        "unique_keys": (("idVinculo",), ("mat_estudante", "idCurso")),
        "references": (
            {
                "fields": ("mat_estudante",),
                "target": "estudante",
                "target_fields": ("mat_estudante",),
            },
            {"fields": ("idCurso",), "target": "curso", "target_fields": ("idCurso",)},
        ),
        "validator": _validator(
            ["idVinculo"],
            {
                "idVinculo": INT,
                "mat_estudante": MATRICULA_OR_NULL,
                "idCurso": INT_OR_NULL,
                "data_entrada": DATE_OR_NULL,
                "status": {"enum": [None, "Ativo", "Cancelada", "Formando", "Graduado"]},
                "data_saida": DATE_OR_NULL,
            },
        ),
        "indexes": [
            _index("pk_vinculo", "idVinculo"),
            _index(
                "uq_vinculo_estudante_curso",
                "mat_estudante",
                "idCurso",
                partial={
                    "mat_estudante": {"$type": "string"},
                    "idCurso": {"$type": "int"},
                },
            ),
            _index("ix_vinculo_estudante", "mat_estudante", unique=False),
            _index("ix_vinculo_curso", "idCurso", unique=False),
        ],
    },
    "projeto": {
        "primary_key": ("id_projeto",),
        "unique_keys": (("id_projeto",),),
        "references": (),
        "validator": _validator(
            ["id_projeto"],
            {"id_projeto": INT, "descricao": {"bsonType": ["string", "null"]}},
        ),
        "indexes": [_index("pk_projeto", "id_projeto")],
    },
    "plano": {
        "primary_key": ("mat_estudante", "ano"),
        "unique_keys": (("mat_estudante", "ano"),),
        "references": (
            {"fields": ("id_projeto",), "target": "projeto", "target_fields": ("id_projeto",)},
            {
                "fields": ("mat_professor",),
                "target": "professor",
                "target_fields": ("mat_professor",),
            },
            {
                "fields": ("mat_estudante",),
                "target": "estudante",
                "target_fields": ("mat_estudante",),
            },
        ),
        "validator": _validator(
            ["mat_estudante", "ano"],
            {
                "id_projeto": INT_OR_NULL,
                "mat_professor": MATRICULA_OR_NULL,
                "mat_estudante": MATRICULA,
                "ano": INT,
            },
        ),
        "indexes": [_index("pk_plano", "mat_estudante", "ano")],
    },
    "disciplina": {
        "primary_key": ("cod_disc",),
        "unique_keys": (("cod_disc",),),
        "references": (
            {"fields": ("pre_req",), "target": "disciplina", "target_fields": ("cod_disc",)},
            {
                "fields": ("depto_responsavel",),
                "target": "departamento",
                "target_fields": ("cod_depto",),
            },
        ),
        "validator": _validator(
            ["cod_disc", "nome"],
            {
                "cod_disc": {"bsonType": "string", "maxLength": 8},
                "nome": {"bsonType": "string", "maxLength": 40},
                "pre_req": {"bsonType": ["string", "null"], "maxLength": 8},
                "creditos": {"bsonType": ["int", "long", "null"], "minimum": 1, "maximum": 11},
                "depto_responsavel": {"bsonType": ["string", "null"], "maxLength": 5},
            },
        ),
        "indexes": [_index("pk_disciplina", "cod_disc")],
    },
    "semestre": {
        "primary_key": ("ano", "semestre"),
        "unique_keys": (("ano", "semestre"),),
        "references": (),
        "validator": _validator(
            ["ano", "semestre"],
            {
                "ano": INT,
                "semestre": INT,
                "data_inicio": DATE_OR_NULL,
                "data_fom": DATE_OR_NULL,
            },
        ),
        "indexes": [_index("pk_semestre", "ano", "semestre")],
    },
    "sala": {
        "primary_key": ("id_sala",),
        "unique_keys": (("id_sala",),),
        "references": (),
        "validator": _validator(
            ["id_sala"],
            {"id_sala": INT, "descricao": {"bsonType": ["string", "null"]}},
        ),
        "indexes": [_index("pk_sala", "id_sala")],
    },
    "horario": {
        "primary_key": ("id_horario",),
        "unique_keys": (("id_horario",),),
        "references": (),
        "validator": _validator(
            ["id_horario", "dia", "slot"],
            {
                "id_horario": INT,
                "dia": {"bsonType": "string", "maxLength": 15},
                "slot": INT,
            },
        ),
        "indexes": [_index("pk_horario", "id_horario")],
    },
    "turma": {
        "primary_key": ("id_turma",),
        "unique_keys": (("id_turma",), ("cod_disc", "numero", "semestre", "ano")),
        "references": (
            {"fields": ("cod_disc",), "target": "disciplina", "target_fields": ("cod_disc",)},
            {"fields": ("ano", "semestre"), "target": "semestre", "target_fields": ("ano", "semestre")},
        ),
        "validator": _validator(
            ["id_turma", "cod_disc"],
            {
                "id_turma": INT,
                "cod_disc": {"bsonType": "string", "maxLength": 8},
                "numero": INT_OR_NULL,
                "ano": INT_OR_NULL,
                "semestre": INT_OR_NULL,
            },
        ),
        "indexes": [
            _index("pk_turma", "id_turma"),
            _index(
                "uq_turma_disc_num_sem_ano",
                "cod_disc",
                "numero",
                "semestre",
                "ano",
                partial={
                    "cod_disc": {"$type": "string"},
                    "numero": {"$type": ["int", "long"]},
                    "semestre": {"$type": ["int", "long"]},
                    "ano": {"$type": ["int", "long"]},
                },
            ),
        ],
    },
    "leciona": {
        "primary_key": ("id_turma", "mat_professor"),
        "unique_keys": (("id_turma", "mat_professor"),),
        "references": (
            {"fields": ("id_turma",), "target": "turma", "target_fields": ("id_turma",)},
            {
                "fields": ("mat_professor",),
                "target": "professor",
                "target_fields": ("mat_professor",),
            },
        ),
        "validator": _validator(
            ["id_turma", "mat_professor"],
            {"id_turma": INT, "mat_professor": MATRICULA},
        ),
        "indexes": [_index("pk_leciona", "id_turma", "mat_professor")],
    },
    "alocacao": {
        "primary_key": ("id_turma", "id_horario"),
        "unique_keys": (("id_turma", "id_horario"), ("id_horario", "id_sala")),
        "references": (
            {"fields": ("id_turma",), "target": "turma", "target_fields": ("id_turma",)},
            {"fields": ("id_horario",), "target": "horario", "target_fields": ("id_horario",)},
            {"fields": ("id_sala",), "target": "sala", "target_fields": ("id_sala",)},
        ),
        "validator": _validator(
            ["id_turma", "id_horario"],
            {"id_turma": INT, "id_horario": INT, "id_sala": INT_OR_NULL},
        ),
        "indexes": [
            _index("pk_alocacao", "id_turma", "id_horario"),
            _index(
                "uq_alocacao_horario_sala",
                "id_horario",
                "id_sala",
                partial={
                    "id_horario": {"$type": ["int", "long"]},
                    "id_sala": {"$type": ["int", "long"]},
                },
            ),
        ],
    },
    "cursa": {
        "primary_key": ("mat_estudante", "id_turma"),
        "unique_keys": (("mat_estudante", "id_turma"),),
        "references": (
            {
                "fields": ("mat_estudante",),
                "target": "estudante",
                "target_fields": ("mat_estudante",),
            },
            {"fields": ("id_turma",), "target": "turma", "target_fields": ("id_turma",)},
        ),
        "validator": _validator(
            ["mat_estudante", "id_turma"],
            {
                "mat_estudante": MATRICULA,
                "id_turma": INT,
                "nota": NUMBER_OR_NULL,
            },
        ),
        "indexes": [_index("pk_cursa", "mat_estudante", "id_turma")],
    },
}

COLLECTION_NAMES = tuple(COLLECTION_SPECS)


def get_schema_plan() -> dict[str, dict[str, Any]]:
    """Retorna o catálogo usado por setup, ETL, testes e documentação."""
    return COLLECTION_SPECS
