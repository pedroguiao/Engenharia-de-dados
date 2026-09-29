from __future__ import annotations

import atexit
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from functools import partial
import secrets
from typing import Any

from bson.decimal128 import Decimal128
from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from config import ConfigurationError, get_settings
from db import create_mock_database, create_mongo_client
from repositories import RepositoryBundle, create_repository_bundle
from services import (
    DomainError,
    GRAUS,
    NIVEIS,
    STATUS_VINCULO,
    TURNOS,
    UniversityService,
    ValidationError,
)


@contextmanager
def _atlas_transaction(client: Any):
    """Transação real via sessão do MongoDB (exige Atlas, que roda como replica set).

    session.start_transaction() já faz commit automático ao sair normalmente
    e aborta (rollback) automaticamente se uma exceção for propagada — mesmo
    comportamento que o snapshot manual do modo mock, só que de verdade.
    """
    with client.start_session() as session:
        with session.start_transaction():
            yield session


def _service() -> UniversityService:
    return current_app.extensions["university_service"]


def _user_form() -> dict[str, Any]:
    password = request.form.get("senha", "")
    confirmation = request.form.get("confirmar_senha", "")
    if password or confirmation:
        if password != confirmation:
            raise ValidationError("A confirmação da senha não corresponde.")
    return {
        "cpf": request.form.get("cpf"),
        "nome": request.form.get("nome"),
        "data_nascimento": request.form.get("data_nascimento"),
        "email": request.form.get("email"),
        "telefone": request.form.get("telefone"),
        "login": request.form.get("login"),
        "senha": password,
    }


def _student_form() -> dict[str, Any]:
    return {
        "mat_estudante": request.form.get("mat_estudante"),
        "cpf": request.form.get("cpf"),
        "MC": request.form.get("MC"),
        "ano_ingresso": request.form.get("ano_ingresso"),
    }


def _course_form() -> dict[str, Any]:
    return {
        "nome": request.form.get("nome"),
        "grau": request.form.get("grau"),
        "turno": request.form.get("turno"),
        "campus": request.form.get("campus"),
        "nivel": request.form.get("nivel"),
    }


def _link_form() -> dict[str, Any]:
    return {
        "mat_estudante": request.form.get("mat_estudante"),
        "idCurso": request.form.get("idCurso"),
        "data_entrada": request.form.get("data_entrada"),
        "status": request.form.get("status"),
        "data_saida": request.form.get("data_saida"),
    }


def _flash_domain_error(error: DomainError) -> None:
    flash(str(error), getattr(error, "category", "error"))


def create_app(
    test_config: dict[str, Any] | None = None,
    *,
    database: Any | None = None,
    repositories: RepositoryBundle | None = None,
) -> Flask:
    settings = get_settings()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.flask_secret_key or secrets.token_hex(32),
        MONGODB_MODE=settings.mongodb_mode,
        MONGODB_DATABASE=settings.mongodb_database or "universidade_mock",
        DEMO_SEED=settings.demo_seed,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    mode = str(app.config.get("MONGODB_MODE", "disabled")).lower()
    mock_client = None
    mongo_client = None
    if repositories is None:
        if mode == "mock":
            if database is None:
                mock_client, database = create_mock_database(app.config["MONGODB_DATABASE"])
            repositories = create_repository_bundle(database, mode="mock")
        elif mode == "atlas":
            if database is None:
                mongo_client, database = create_mongo_client()
            repositories = create_repository_bundle(
                database,
                mode="atlas",
                transaction_factory=partial(_atlas_transaction, mongo_client),
            )
        else:
            raise ConfigurationError(
                "MONGODB_MODE deve ser 'mock' ou 'atlas' para iniciar a aplicação."
            )

    service = UniversityService(repositories)
    app.extensions["repositories"] = repositories
    app.extensions["university_service"] = service
    app.extensions["mock_client"] = mock_client
    app.extensions["mongo_client"] = mongo_client
    app.config["MONGODB_MODE"] = mode

    if mongo_client is not None:
        atexit.register(mongo_client.close)

    if mode == "mock":
        print("[MODO MOCK] Banco MongoDB em memória; nenhuma conexão de rede será aberta.")
    elif mode == "atlas":
        print(f"[MODO ATLAS] Conectado ao banco '{app.config['MONGODB_DATABASE']}' no MongoDB Atlas.")
    if app.config.get("DEMO_SEED") and mode == "mock":
        service.seed_demo()
        print("[MODO DEMONSTRAÇÃO] Dados temporários inseridos explicitamente no mock.")
    elif app.config.get("DEMO_SEED"):
        print("[AVISO] DEMO_SEED ignorado: só é aplicado em MONGODB_MODE=mock, nunca no Atlas real.")

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {
            "mongodb_mode": app.config["MONGODB_MODE"],
            "graus": GRAUS,
            "turnos": TURNOS,
            "niveis": NIVEIS,
            "status_vinculo": STATUS_VINCULO,
        }

    @app.template_filter("date_input")
    def date_input(value: Any) -> str:
        return value.strftime("%Y-%m-%d") if isinstance(value, datetime) else ""

    @app.template_filter("date_br")
    def date_br(value: Any) -> str:
        return value.strftime("%d/%m/%Y") if isinstance(value, datetime) else "—"

    @app.template_filter("decimal_value")
    def decimal_value(value: Any) -> str:
        if isinstance(value, Decimal128):
            return format(value.to_decimal(), "f")
        if isinstance(value, Decimal):
            return format(value, "f")
        return "" if value is None else str(value)

    @app.get("/")
    def index():
        repos = current_app.extensions["repositories"]
        return render_template(
            "index.html",
            counts={name: repository.count() for name, repository in repos.by_name.items()},
        )

    # Usuários
    @app.get("/usuarios")
    def users_list():
        query = request.args.get("q", "").strip()
        return render_template(
            "usuarios/list.html",
            usuarios=_service().list_users(query or None),
            q=query,
        )

    @app.route("/usuarios/novo", methods=["GET", "POST"])
    def users_create():
        if request.method == "POST":
            try:
                user = _service().create_user(_user_form())
                flash("Usuário cadastrado com sucesso.", "success")
                return redirect(url_for("users_detail", cpf=user["cpf"]))
            except DomainError as error:
                _flash_domain_error(error)
                return redirect(url_for("users_create"))
        return render_template("usuarios/form.html", usuario=None, editing=False)

    @app.get("/usuarios/<cpf>")
    def users_detail(cpf: str):
        try:
            user = _service().get_user(cpf)
        except DomainError:
            abort(404)
        student = current_app.extensions["repositories"].estudantes.find_one({"cpf": cpf})
        return render_template("usuarios/detail.html", usuario=user, estudante=student)

    @app.route("/usuarios/<cpf>/editar", methods=["GET", "POST"])
    def users_edit(cpf: str):
        try:
            user = _service().get_user(cpf)
            if request.method == "POST":
                _service().update_user(cpf, _user_form())
                flash("Usuário atualizado com sucesso.", "success")
                return redirect(url_for("users_detail", cpf=cpf))
            return render_template("usuarios/form.html", usuario=user, editing=True)
        except DomainError as error:
            _flash_domain_error(error)
            return redirect(url_for("users_list"))

    @app.post("/usuarios/<cpf>/excluir")
    def users_delete(cpf: str):
        try:
            _service().delete_user(cpf)
            flash("Usuário excluído.", "success")
        except DomainError as error:
            _flash_domain_error(error)
        return redirect(url_for("users_list"))

    # Estudantes
    @app.get("/estudantes")
    def students_list():
        query = request.args.get("q", "").strip()
        return render_template(
            "estudantes/list.html",
            estudantes=_service().list_students(query or None),
            q=query,
        )

    @app.route("/estudantes/novo", methods=["GET", "POST"])
    def students_create():
        if request.method == "POST":
            try:
                student = _service().create_student(_student_form())
                flash("Estudante cadastrado com sucesso.", "success")
                return redirect(url_for("students_detail", matricula=student["mat_estudante"]))
            except DomainError as error:
                _flash_domain_error(error)
                return redirect(url_for("students_create"))
        return render_template(
            "estudantes/form.html",
            estudante=None,
            editing=False,
            usuarios=_service().list_users(),
        )

    @app.get("/estudantes/<matricula>")
    def students_detail(matricula: str):
        try:
            student = _service().get_student(matricula)
        except DomainError:
            abort(404)
        return render_template("estudantes/detail.html", estudante=student)

    @app.route("/estudantes/<matricula>/editar", methods=["GET", "POST"])
    def students_edit(matricula: str):
        try:
            student = _service().get_student(matricula)
            if request.method == "POST":
                _service().update_student(matricula, _student_form())
                flash("Estudante atualizado com sucesso.", "success")
                return redirect(url_for("students_detail", matricula=matricula))
            return render_template(
                "estudantes/form.html",
                estudante=student,
                editing=True,
                usuarios=_service().list_users(),
            )
        except DomainError as error:
            _flash_domain_error(error)
            return redirect(url_for("students_list"))

    @app.post("/estudantes/<matricula>/excluir")
    def students_delete(matricula: str):
        try:
            _service().delete_student(matricula)
            flash("Estudante excluído.", "success")
        except DomainError as error:
            _flash_domain_error(error)
        return redirect(url_for("students_list"))

    # Cursos
    @app.get("/cursos")
    def courses_list():
        query = request.args.get("q", "").strip()
        return render_template(
            "cursos/list.html",
            cursos=_service().list_courses(query or None),
            q=query,
        )

    @app.route("/cursos/novo", methods=["GET", "POST"])
    def courses_create():
        if request.method == "POST":
            try:
                course = _service().create_course(_course_form())
                flash("Curso cadastrado com sucesso.", "success")
                return redirect(url_for("courses_detail", course_id=course["idCurso"]))
            except DomainError as error:
                _flash_domain_error(error)
                return redirect(url_for("courses_create"))
        return render_template("cursos/form.html", curso=None, editing=False)

    @app.get("/cursos/<int:course_id>")
    def courses_detail(course_id: int):
        try:
            course = _service().get_course(course_id)
        except DomainError:
            abort(404)
        return render_template("cursos/detail.html", curso=course)

    @app.route("/cursos/<int:course_id>/editar", methods=["GET", "POST"])
    def courses_edit(course_id: int):
        try:
            course = _service().get_course(course_id)
            if request.method == "POST":
                _service().update_course(course_id, _course_form())
                flash("Curso atualizado com sucesso.", "success")
                return redirect(url_for("courses_detail", course_id=course_id))
            return render_template("cursos/form.html", curso=course, editing=True)
        except DomainError as error:
            _flash_domain_error(error)
            return redirect(url_for("courses_list"))

    @app.post("/cursos/<int:course_id>/excluir")
    def courses_delete(course_id: int):
        try:
            _service().delete_course(course_id)
            flash("Curso excluído.", "success")
        except DomainError as error:
            _flash_domain_error(error)
        return redirect(url_for("courses_list"))

    # Vínculos
    @app.get("/vinculos")
    def links_list():
        query = request.args.get("q", "").strip()
        return render_template(
            "vinculos/list.html",
            vinculos=_service().list_links(query or None),
            q=query,
        )

    @app.route("/vinculos/novo", methods=["GET", "POST"])
    def links_create():
        if request.method == "POST":
            try:
                link = _service().create_link(_link_form())
                flash("Vínculo cadastrado com sucesso.", "success")
                return redirect(url_for("links_detail", link_id=link["idVinculo"]))
            except DomainError as error:
                _flash_domain_error(error)
                return redirect(url_for("links_create"))
        return render_template(
            "vinculos/form.html",
            vinculo=None,
            editing=False,
            estudantes=_service().list_students(),
            cursos=_service().list_courses(),
        )

    @app.get("/vinculos/<int:link_id>")
    def links_detail(link_id: int):
        try:
            link = _service().get_link(link_id)
        except DomainError:
            abort(404)
        return render_template("vinculos/detail.html", vinculo=link)

    @app.route("/vinculos/<int:link_id>/editar", methods=["GET", "POST"])
    def links_edit(link_id: int):
        try:
            link = _service().get_link(link_id)
            if request.method == "POST":
                _service().update_link(link_id, _link_form())
                flash("Vínculo atualizado com sucesso.", "success")
                return redirect(url_for("links_detail", link_id=link_id))
            return render_template(
                "vinculos/form.html",
                vinculo=link,
                editing=True,
                estudantes=_service().list_students(),
                cursos=_service().list_courses(),
            )
        except DomainError as error:
            _flash_domain_error(error)
            return redirect(url_for("links_list"))

    @app.post("/vinculos/<int:link_id>/excluir")
    def links_delete(link_id: int):
        try:
            _service().delete_link(link_id)
            flash("Vínculo excluído sem alterar estudante ou curso.", "success")
        except DomainError as error:
            _flash_domain_error(error)
        return redirect(url_for("links_list"))

    # Admissão conjunta
    @app.route("/admissoes/nova", methods=["GET", "POST"])
    def admission_create():
        if request.method == "POST":
            try:
                user_data = _user_form()
                student_data = _student_form()
                link_data = _link_form()
                result = _service().admit(user_data, student_data, link_data)
                flash("Admissão concluída atomicamente.", "success")
                return redirect(
                    url_for(
                        "students_detail",
                        matricula=result["estudante"]["mat_estudante"],
                    )
                )
            except DomainError as error:
                _flash_domain_error(error)
                return redirect(url_for("admission_create"))
        return render_template(
            "admission.html",
            cursos=_service().list_courses(),
        )

    @app.errorhandler(404)
    def not_found(_error: Any):
        return render_template("error.html", title="Não encontrado", message="O registro ou página solicitado não existe."), 404

    @app.errorhandler(500)
    def internal_error(error: Any):
        current_app.logger.error("Falha interna tratada: %s", type(error).__name__)
        return render_template("error.html", title="Erro interno", message="Não foi possível concluir a operação. Nenhum dado sensível foi exibido."), 500

    return app