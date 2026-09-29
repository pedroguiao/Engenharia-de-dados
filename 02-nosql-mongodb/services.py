from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from bson.decimal128 import Decimal128
from pymongo.errors import DuplicateKeyError

from repositories import RepositoryBundle


FORMACOES = ("Graduação", "Especialização", "Mestrado", "Doutorado")
GRAUS = ("Bacharelado", "Licenciatura Plena")
TURNOS = ("Matutino", "Vespertino", "Noturno", "Turno Indefinido")
NIVEIS = ("Graduação", "Mestrado", "Doutorado", "Lato")
STATUS_VINCULO = ("Ativo", "Cancelada", "Formando", "Graduado")


class DomainError(Exception):
    category = "error"


class ValidationError(DomainError):
    pass


class DuplicateError(DomainError):
    category = "warning"


class NotFoundError(DomainError):
    pass


class ReferenceError(DomainError):
    pass


class DeleteBlockedError(DomainError):
    category = "warning"


def _value(data: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return default


def _text(
    value: Any,
    field_name: str,
    *,
    required: bool = False,
    max_length: int | None = None,
) -> str | None:
    if value is None:
        value = ""
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    if not normalized:
        if required:
            raise ValidationError(f"{field_name} é obrigatório.")
        return None
    if max_length is not None and len(normalized) > max_length:
        raise ValidationError(
            f"{field_name} deve ter no máximo {max_length} caracteres."
        )
    return normalized


def _integer(
    value: Any,
    field_name: str,
    *,
    required: bool = False,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{field_name} é obrigatório.")
        return None
    try:
        converted = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} deve ser um número inteiro.") from exc
    if minimum is not None and converted < minimum:
        raise ValidationError(f"{field_name} deve ser no mínimo {minimum}.")
    if maximum is not None and converted > maximum:
        raise ValidationError(f"{field_name} deve ser no máximo {maximum}.")
    return converted


def _decimal(
    value: Any,
    field_name: str,
    *,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
) -> Decimal128 | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, Decimal128):
        converted = value.to_decimal()
    elif isinstance(value, Decimal):
        converted = value
    else:
        try:
            converted = Decimal(str(value).strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{field_name} deve ser numérico.") from exc
    if minimum is not None and converted < minimum:
        raise ValidationError(f"{field_name} deve ser no mínimo {minimum}.")
    if maximum is not None and converted > maximum:
        raise ValidationError(f"{field_name} deve ser no máximo {maximum}.")
    return Decimal128(converted)


def _date(value: Any, field_name: str) -> datetime | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationError(f"{field_name} deve ser uma data válida.") from exc
    raise ValidationError(f"{field_name} deve ser uma data válida.")


def _array(value: Any) -> list[str] | None:
    if value is None:
        return None
    source = value if isinstance(value, (list, tuple)) else str(value).split(",")
    normalized = [str(item).strip() for item in source if str(item).strip()]
    return normalized or None


def _enum(value: Any, field_name: str, allowed: tuple[str, ...], *, required: bool) -> str | None:
    normalized = _text(value, field_name, required=required)
    if normalized is not None and normalized not in allowed:
        raise ValidationError(
            f"{field_name} inválido. Valores aceitos: {', '.join(allowed)}."
        )
    return normalized


def _cpf(value: Any) -> str:
    normalized = _text(value, "CPF", required=True, max_length=13)
    assert normalized is not None
    if not re.fullmatch(r"[0-9]{1,13}", normalized):
        raise ValidationError("CPF deve conter somente números e no máximo 13 dígitos.")
    return normalized


def _matricula(value: Any) -> str:
    normalized = _text(value, "Matrícula", required=True, max_length=7)
    assert normalized is not None
    return normalized


def _without_password(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    public = deepcopy(document)
    public.pop("senha", None)
    return public


def _matches(document: dict[str, Any], query: str, *fields: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True
    for field in fields:
        value = document.get(field)
        if value is not None and needle in str(value).lower():
            return True
    return False


class UniversityService:
    def __init__(self, repositories: RepositoryBundle):
        self.repositories = repositories

    # Usuário
    def _build_user(self, data: dict[str, Any], *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
        cpf = _cpf(_value(data, "cpf", default=previous and previous.get("cpf")))
        if previous and cpf != previous["cpf"]:
            raise ValidationError("CPF é uma chave imutável.")
        password_value = _value(data, "senha", default=None)
        if previous and (password_value is None or not str(password_value).strip()):
            password = previous.get("senha")
        else:
            password = _text(password_value, "Senha", max_length=32)
        return {
            "cpf": cpf,
            "nome": _text(
                _value(data, "nome", default=previous and previous.get("nome")),
                "Nome",
                required=True,
                max_length=100,
            ),
            "data_nascimento": _date(
                _value(data, "data_nascimento", default=previous and previous.get("data_nascimento")),
                "Data de nascimento",
            ),
            "email": _array(_value(data, "email", default=previous and previous.get("email"))),
            "telefone": _array(
                _value(data, "telefone", default=previous and previous.get("telefone"))
            ),
            "login": _text(
                _value(data, "login", default=previous and previous.get("login")),
                "Login",
                max_length=45,
            ),
            "senha": password,
        }

    def _assert_user_unique(self, document: dict[str, Any], *, current_cpf: str | None = None) -> None:
        by_cpf = self.repositories.usuarios.get(document["cpf"])
        if by_cpf and document["cpf"] != current_cpf:
            raise DuplicateError("Já existe um usuário com este CPF.")
        if document.get("login"):
            by_login = self.repositories.usuarios.find_one({"login": document["login"]})
            if by_login and by_login["cpf"] != current_cpf:
                raise DuplicateError("Já existe um usuário com este login.")

    def create_user(self, data: dict[str, Any]) -> dict[str, Any]:
        document = self._build_user(data)
        self._assert_user_unique(document)
        try:
            created = self.repositories.usuarios.insert(document)
        except DuplicateKeyError as exc:
            raise DuplicateError("CPF ou login já cadastrado.") from exc
        return _without_password(created) or {}

    def list_users(self, query: str | None = None) -> list[dict[str, Any]]:
        users = [
            _without_password(document) or {}
            for document in self.repositories.usuarios.list_all(sort=[("nome", 1)])
        ]
        if query:
            users = [u for u in users if _matches(u, query, "nome", "cpf", "login")]
        return users

    def get_user(self, cpf: Any) -> dict[str, Any]:
        document = self.repositories.usuarios.get(_cpf(cpf))
        if not document:
            raise NotFoundError("Usuário não encontrado.")
        return _without_password(document) or {}

    def update_user(self, cpf: Any, data: dict[str, Any]) -> dict[str, Any]:
        normalized_cpf = _cpf(cpf)
        previous = self.repositories.usuarios.get(normalized_cpf)
        if not previous:
            raise NotFoundError("Usuário não encontrado.")
        document = self._build_user({**data, "cpf": normalized_cpf}, previous=previous)
        self._assert_user_unique(document, current_cpf=normalized_cpf)
        try:
            updated = self.repositories.usuarios.update((normalized_cpf,), document)
        except DuplicateKeyError as exc:
            raise DuplicateError("O login informado já está em uso.") from exc
        return _without_password(updated) or {}

    def delete_user(self, cpf: Any) -> None:
        normalized_cpf = _cpf(cpf)
        if not self.repositories.usuarios.get(normalized_cpf):
            raise NotFoundError("Usuário não encontrado.")
        if self.repositories.estudantes.exists({"cpf": normalized_cpf}):
            raise DeleteBlockedError(
                "Exclusão bloqueada: existe estudante referenciando este usuário."
            )
        self.repositories.usuarios.delete(normalized_cpf)

    # Estudante
    def _build_student(
        self, data: dict[str, Any], *, previous: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        matricula = _matricula(
            _value(data, "mat_estudante", "matricula", default=previous and previous.get("mat_estudante"))
        )
        if previous and matricula != previous["mat_estudante"]:
            raise ValidationError("Matrícula é uma chave imutável.")
        return {
            "mat_estudante": matricula,
            "cpf": _cpf(_value(data, "cpf", default=previous and previous.get("cpf"))),
            "MC": _decimal(
                _value(data, "MC", "mc", default=previous and previous.get("MC")),
                "MC",
                minimum=Decimal("0"),
                maximum=Decimal("10"),
            ),
            "ano_ingresso": _integer(
                _value(data, "ano_ingresso", default=previous and previous.get("ano_ingresso")),
                "Ano de ingresso",
                minimum=1900,
                maximum=2100,
            ),
        }

    def _assert_student_valid(
        self, document: dict[str, Any], *, current_mat: str | None = None
    ) -> None:
        if not self.repositories.usuarios.get(document["cpf"]):
            raise ReferenceError("O CPF informado não pertence a um usuário existente.")
        by_mat = self.repositories.estudantes.get(document["mat_estudante"])
        if by_mat and document["mat_estudante"] != current_mat:
            raise DuplicateError("Já existe um estudante com esta matrícula.")
        by_cpf = self.repositories.estudantes.find_one({"cpf": document["cpf"]})
        if by_cpf and by_cpf["mat_estudante"] != current_mat:
            raise DuplicateError("Este usuário já possui um cadastro de estudante.")

    def create_student(self, data: dict[str, Any]) -> dict[str, Any]:
        document = self._build_student(data)
        self._assert_student_valid(document)
        try:
            return self.repositories.estudantes.insert(document)
        except DuplicateKeyError as exc:
            raise DuplicateError("Matrícula ou CPF já associado a outro estudante.") from exc

    def list_students(self, query: str | None = None) -> list[dict[str, Any]]:
        students = self.repositories.estudantes.list_all(sort=[("mat_estudante", 1)])
        for student in students:
            user = self.repositories.usuarios.get(student["cpf"])
            student["usuario_nome"] = user["nome"] if user else "Usuário ausente"
        if query:
            students = [
                s for s in students
                if _matches(s, query, "mat_estudante", "cpf", "usuario_nome")
            ]
        return students

    def get_student(self, matricula: Any) -> dict[str, Any]:
        document = self.repositories.estudantes.get(_matricula(matricula))
        if not document:
            raise NotFoundError("Estudante não encontrado.")
        document["usuario"] = _without_password(
            self.repositories.usuarios.get(document["cpf"])
        )
        document["vinculos"] = self.repositories.vinculos.list_all(
            sort=[("idVinculo", 1)]
        )
        document["vinculos"] = [
            item for item in document["vinculos"] if item["mat_estudante"] == document["mat_estudante"]
        ]
        return document

    def update_student(self, matricula: Any, data: dict[str, Any]) -> dict[str, Any]:
        normalized_mat = _matricula(matricula)
        previous = self.repositories.estudantes.get(normalized_mat)
        if not previous:
            raise NotFoundError("Estudante não encontrado.")
        document = self._build_student(
            {**data, "mat_estudante": normalized_mat}, previous=previous
        )
        self._assert_student_valid(document, current_mat=normalized_mat)
        try:
            return self.repositories.estudantes.update((normalized_mat,), document) or {}
        except DuplicateKeyError as exc:
            raise DuplicateError("O CPF já está associado a outro estudante.") from exc

    def delete_student(self, matricula: Any) -> None:
        normalized_mat = _matricula(matricula)
        if not self.repositories.estudantes.get(normalized_mat):
            raise NotFoundError("Estudante não encontrado.")
        if self.repositories.vinculos.exists({"mat_estudante": normalized_mat}):
            raise DeleteBlockedError(
                "Exclusão bloqueada: remova primeiro os vínculos deste estudante."
            )
        self.repositories.estudantes.delete(normalized_mat)

    # Curso
    def _build_course(
        self, data: dict[str, Any], *, previous: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        course_id = _integer(
            _value(data, "idCurso", default=previous and previous.get("idCurso")),
            "ID do curso",
            required=True,
            minimum=1,
        )
        assert course_id is not None
        if previous and course_id != previous["idCurso"]:
            raise ValidationError("ID do curso é uma chave imutável.")
        return {
            "idCurso": course_id,
            "nome": _text(_value(data, "nome", default=previous and previous.get("nome")), "Nome", required=True, max_length=100),
            "grau": _enum(_value(data, "grau", default=previous and previous.get("grau")), "Grau", GRAUS, required=False),
            "turno": _enum(_value(data, "turno", default=previous and previous.get("turno")), "Turno", TURNOS, required=True),
            "campus": _text(_value(data, "campus", default=previous and previous.get("campus")), "Campus", max_length=100),
            "nivel": _enum(_value(data, "nivel", default=previous and previous.get("nivel")), "Nível", NIVEIS, required=False),
        }

    def _assert_course_unique(self, document: dict[str, Any], *, current_id: int | None = None) -> None:
        by_id = self.repositories.cursos.get(document["idCurso"])
        if by_id and document["idCurso"] != current_id:
            raise DuplicateError("Já existe um curso com este identificador.")
        composite = ("nome", "turno", "campus", "nivel")
        if all(document.get(field) is not None for field in composite):
            existing = self.repositories.cursos.find_one(
                {field: document[field] for field in composite}
            )
            if existing and existing["idCurso"] != current_id:
                raise DuplicateError(
                    "Já existe curso com o mesmo nome, turno, campus e nível."
                )

    def create_course(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        if not _value(payload, "idCurso"):
            payload["idCurso"] = self.repositories.cursos.next_integer("idCurso")
        document = self._build_course(payload)
        self._assert_course_unique(document)
        try:
            return self.repositories.cursos.insert(document)
        except DuplicateKeyError as exc:
            raise DuplicateError("Curso duplicado.") from exc

    def list_courses(self, query: str | None = None) -> list[dict[str, Any]]:
        courses = self.repositories.cursos.list_all(sort=[("nome", 1), ("turno", 1)])
        if query:
            courses = [
                c for c in courses
                if _matches(c, query, "nome", "campus", "turno", "nivel", "grau")
            ]
        return courses

    def get_course(self, course_id: Any) -> dict[str, Any]:
        normalized_id = _integer(course_id, "ID do curso", required=True, minimum=1)
        document = self.repositories.cursos.get(normalized_id)
        if not document:
            raise NotFoundError("Curso não encontrado.")
        document["total_vinculos"] = self.repositories.vinculos.count({"idCurso": normalized_id})
        return document

    def update_course(self, course_id: Any, data: dict[str, Any]) -> dict[str, Any]:
        normalized_id = _integer(course_id, "ID do curso", required=True, minimum=1)
        previous = self.repositories.cursos.get(normalized_id)
        if not previous:
            raise NotFoundError("Curso não encontrado.")
        document = self._build_course({**data, "idCurso": normalized_id}, previous=previous)
        self._assert_course_unique(document, current_id=normalized_id)
        try:
            return self.repositories.cursos.update((normalized_id,), document) or {}
        except DuplicateKeyError as exc:
            raise DuplicateError("Já existe curso com esta combinação de dados.") from exc

    def delete_course(self, course_id: Any) -> None:
        normalized_id = _integer(course_id, "ID do curso", required=True, minimum=1)
        if not self.repositories.cursos.get(normalized_id):
            raise NotFoundError("Curso não encontrado.")
        if self.repositories.vinculos.exists({"idCurso": normalized_id}):
            raise DeleteBlockedError(
                "Exclusão bloqueada: o curso possui vínculos estudantis."
            )
        self.repositories.cursos.delete(normalized_id)

    # Vínculo
    def _build_link(
        self, data: dict[str, Any], *, previous: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        link_id = _integer(
            _value(data, "idVinculo", default=previous and previous.get("idVinculo")),
            "ID do vínculo",
            required=True,
            minimum=1,
        )
        assert link_id is not None
        if previous and link_id != previous["idVinculo"]:
            raise ValidationError("ID do vínculo é uma chave imutável.")
        entry = _date(_value(data, "data_entrada", default=previous and previous.get("data_entrada")), "Data de entrada")
        exit_date = _date(_value(data, "data_saida", default=previous and previous.get("data_saida")), "Data de saída")
        if entry and exit_date and exit_date < entry:
            raise ValidationError("Data de saída não pode ser anterior à data de entrada.")
        course_id = _integer(
            _value(data, "idCurso", "curso", default=previous and previous.get("idCurso")),
            "Curso",
            required=True,
            minimum=1,
        )
        assert course_id is not None
        return {
            "idVinculo": link_id,
            "mat_estudante": _matricula(
                _value(data, "mat_estudante", "matricula", default=previous and previous.get("mat_estudante"))
            ),
            "idCurso": course_id,
            "data_entrada": entry,
            "status": _enum(
                _value(data, "status", default=previous and previous.get("status")),
                "Status",
                STATUS_VINCULO,
                required=True,
            ),
            "data_saida": exit_date,
        }

    def _assert_link_valid(self, document: dict[str, Any], *, current_id: int | None = None) -> None:
        if not self.repositories.estudantes.get(document["mat_estudante"]):
            raise ReferenceError("O estudante informado não existe.")
        if not self.repositories.cursos.get(document["idCurso"]):
            raise ReferenceError("O curso informado não existe.")
        by_id = self.repositories.vinculos.get(document["idVinculo"])
        if by_id and document["idVinculo"] != current_id:
            raise DuplicateError("Já existe um vínculo com este identificador.")
        duplicate = self.repositories.vinculos.find_one(
            {
                "mat_estudante": document["mat_estudante"],
                "idCurso": document["idCurso"],
            }
        )
        if duplicate and duplicate["idVinculo"] != current_id:
            raise DuplicateError("O estudante já possui vínculo com este curso.")

    def create_link(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        if not _value(payload, "idVinculo"):
            payload["idVinculo"] = self.repositories.vinculos.next_integer("idVinculo")
        document = self._build_link(payload)
        self._assert_link_valid(document)
        try:
            return self.repositories.vinculos.insert(document)
        except DuplicateKeyError as exc:
            raise DuplicateError("Vínculo duplicado.") from exc

    def list_links(self, query: str | None = None) -> list[dict[str, Any]]:
        links = self.repositories.vinculos.list_all(sort=[("idVinculo", 1)])
        for link in links:
            student = self.repositories.estudantes.get(link["mat_estudante"])
            course = self.repositories.cursos.get(link["idCurso"])
            user = self.repositories.usuarios.get(student["cpf"]) if student else None
            link["estudante_nome"] = user["nome"] if user else "Estudante ausente"
            link["curso_nome"] = course["nome"] if course else "Curso ausente"
        if query:
            links = [
                l for l in links
                if _matches(l, query, "mat_estudante", "estudante_nome", "curso_nome", "status")
            ]
        return links

    def get_link(self, link_id: Any) -> dict[str, Any]:
        normalized_id = _integer(link_id, "ID do vínculo", required=True, minimum=1)
        document = self.repositories.vinculos.get(normalized_id)
        if not document:
            raise NotFoundError("Vínculo não encontrado.")
        student = self.repositories.estudantes.get(document["mat_estudante"])
        course = self.repositories.cursos.get(document["idCurso"])
        document["estudante"] = student
        document["curso"] = course
        return document

    def update_link(self, link_id: Any, data: dict[str, Any]) -> dict[str, Any]:
        normalized_id = _integer(link_id, "ID do vínculo", required=True, minimum=1)
        previous = self.repositories.vinculos.get(normalized_id)
        if not previous:
            raise NotFoundError("Vínculo não encontrado.")
        document = self._build_link({**data, "idVinculo": normalized_id}, previous=previous)
        self._assert_link_valid(document, current_id=normalized_id)
        try:
            return self.repositories.vinculos.update((normalized_id,), document) or {}
        except DuplicateKeyError as exc:
            raise DuplicateError("O estudante já possui vínculo com este curso.") from exc

    def delete_link(self, link_id: Any) -> None:
        normalized_id = _integer(link_id, "ID do vínculo", required=True, minimum=1)
        if not self.repositories.vinculos.delete(normalized_id):
            raise NotFoundError("Vínculo não encontrado.")

    # Admissão atômica
    def admit(
        self,
        user_data: dict[str, Any],
        student_data: dict[str, Any],
        link_data: dict[str, Any],
    ) -> dict[str, Any]:
        user = self._build_user(user_data)
        student = self._build_student({**student_data, "cpf": user["cpf"]})
        payload_link = dict(link_data)
        payload_link["mat_estudante"] = student["mat_estudante"]
        if not _value(payload_link, "idVinculo"):
            payload_link["idVinculo"] = self.repositories.vinculos.next_integer("idVinculo")
        link = self._build_link(payload_link)

        # Tudo é validado antes da primeira escrita.
        self._assert_user_unique(user)
        if self.repositories.estudantes.get(student["mat_estudante"]):
            raise DuplicateError("Já existe um estudante com esta matrícula.")
        if self.repositories.estudantes.find_one({"cpf": student["cpf"]}):
            raise DuplicateError("Este usuário já possui estudante.")
        if not self.repositories.cursos.get(link["idCurso"]):
            raise ReferenceError("O curso informado não existe.")

        try:
            with self.repositories.atomic():
                created_user = self.repositories.usuarios.insert(user)
                created_student = self.repositories.estudantes.insert(student)
                created_link = self.repositories.vinculos.insert(link)
        except DuplicateKeyError as exc:
            raise DuplicateError("A admissão conflita com um registro existente.") from exc

        return {
            "usuario": _without_password(created_user),
            "estudante": created_student,
            "vinculo": created_link,
        }

    def seed_demo(self) -> None:
        """Insere uma amostra mínima apenas quando DEMO_SEED foi explícito."""
        if self.repositories.cursos.count() or self.repositories.usuarios.count():
            return
        course = self.create_course(
            {
                "nome": "Ciência da Computação",
                "grau": "Bacharelado",
                "turno": "Vespertino",
                "campus": "São Cristóvão",
                "nivel": "Graduação",
            }
        )
        self.admit(
            {
                "cpf": "10000000000",
                "nome": "Estudante Demonstração",
                "data_nascimento": "2000-01-01",
                "email": "demo@example.org",
                "telefone": "79999999999",
                "login": "demo",
                "senha": "temporaria",
            },
            {"mat_estudante": "DEMO001", "MC": "8.0", "ano_ingresso": 2026},
            {"idCurso": course["idCurso"], "status": "Ativo"},
        )