from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import os
import unittest
from unittest import mock

from app import create_app


class FlaskAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = StringIO()
        with redirect_stdout(self.output):
            self.app = create_app(
                {
                    "TESTING": True,
                    "SECRET_KEY": "test-only",
                    "MONGODB_MODE": "mock",
                    "DEMO_SEED": False,
                    "MONGODB_DATABASE": "flask_test",
                }
            )
        self.client = self.app.test_client()
        self.service = self.app.extensions["university_service"]

    def test_mock_mode_is_visible_and_does_not_open_network(self) -> None:
        self.assertIn("MODO MOCK", self.output.getvalue())
        with mock.patch("pymongo.MongoClient", side_effect=AssertionError("rede")):
            with redirect_stdout(StringIO()):
                app = create_app(
                    {
                        "TESTING": True,
                        "SECRET_KEY": "test-only",
                        "MONGODB_MODE": "mock",
                        "MONGODB_DATABASE": "no_network",
                    }
                )
            self.assertEqual(app.config["MONGODB_MODE"], "mock")

    def test_missing_mode_never_falls_back_to_atlas(self) -> None:
        with mock.patch.dict(os.environ, {"MONGODB_MODE": ""}, clear=False):
            with self.assertRaises(Exception):
                create_app({"MONGODB_MODE": "disabled"})

    def test_principal_get_routes(self) -> None:
        routes = (
            "/",
            "/usuarios",
            "/usuarios/novo",
            "/estudantes",
            "/estudantes/novo",
            "/cursos",
            "/cursos/novo",
            "/vinculos",
            "/vinculos/novo",
            "/admissoes/nova",
        )
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_routes_create_four_canonical_documents(self) -> None:
        response = self.client.post(
            "/cursos/novo",
            data={
                "nome": "Computação",
                "grau": "Bacharelado",
                "turno": "Noturno",
                "campus": "São Cristóvão",
                "nivel": "Graduação",
            },
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/usuarios/novo",
            data={
                "cpf": "12345678901",
                "nome": "Alice",
                "login": "alice",
                "senha": "segredo",
                "confirmar_senha": "segredo",
            },
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/estudantes/novo",
            data={"mat_estudante": "E100", "cpf": "12345678901"},
        )
        self.assertEqual(response.status_code, 302)
        course = self.service.list_courses()[0]
        response = self.client.post(
            "/vinculos/novo",
            data={
                "mat_estudante": "E100",
                "idCurso": str(course["idCurso"]),
                "status": "Ativo",
            },
        )
        self.assertEqual(response.status_code, 302)
        repos = self.app.extensions["repositories"]
        self.assertEqual(repos.usuarios.count(), 1)
        self.assertEqual(repos.estudantes.count(), 1)
        self.assertEqual(repos.cursos.count(), 1)
        self.assertEqual(repos.vinculos.count(), 1)
        link = self.service.list_links()[0]
        for route in (
            "/usuarios/12345678901",
            "/usuarios/12345678901/editar",
            "/estudantes/E100",
            "/estudantes/E100/editar",
            f"/cursos/{course['idCurso']}",
            f"/cursos/{course['idCurso']}/editar",
            f"/vinculos/{link['idVinculo']}",
            f"/vinculos/{link['idVinculo']}/editar",
        ):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_route_updates_and_controlled_deletes(self) -> None:
        user = self.service.create_user(
            {"cpf": "12345678901", "nome": "Alice", "login": "alice", "senha": "original"}
        )
        student = self.service.create_student(
            {"mat_estudante": "E100", "cpf": user["cpf"], "ano_ingresso": 2025}
        )
        course = self.service.create_course(
            {"nome": "Computação", "turno": "Noturno"}
        )
        link = self.service.create_link(
            {"mat_estudante": student["mat_estudante"], "idCurso": course["idCurso"], "status": "Ativo"}
        )

        self.client.post(
            f"/usuarios/{user['cpf']}/editar",
            data={"nome": "Alice Nova", "login": "alice", "senha": "", "confirmar_senha": ""},
        )
        self.assertEqual(self.service.get_user(user["cpf"])["nome"], "Alice Nova")
        self.assertEqual(
            self.app.extensions["repositories"].usuarios.get(user["cpf"])["senha"],
            "original",
        )
        self.client.post(
            f"/estudantes/{student['mat_estudante']}/editar",
            data={"cpf": user["cpf"], "MC": "9.0", "ano_ingresso": "2026"},
        )
        self.client.post(
            f"/cursos/{course['idCurso']}/editar",
            data={"nome": "Computação Aplicada", "turno": "Noturno"},
        )
        self.client.post(
            f"/vinculos/{link['idVinculo']}/editar",
            data={
                "mat_estudante": student["mat_estudante"],
                "idCurso": course["idCurso"],
                "status": "Formando",
            },
        )
        self.assertEqual(self.service.get_link(link["idVinculo"])["status"], "Formando")

        blocked = self.client.post(
            f"/cursos/{course['idCurso']}/excluir", follow_redirects=True
        )
        self.assertIn("bloqueada".encode(), blocked.data.lower())
        self.client.post(f"/vinculos/{link['idVinculo']}/excluir")
        self.client.post(f"/estudantes/{student['mat_estudante']}/excluir")
        self.client.post(f"/usuarios/{user['cpf']}/excluir")
        self.client.post(f"/cursos/{course['idCurso']}/excluir")
        repos = self.app.extensions["repositories"]
        self.assertEqual(sum(repository.count() for repository in repos.by_name.values()), 0)

    def test_password_never_appears_in_html(self) -> None:
        self.service.create_user(
            {"cpf": "12345678901", "nome": "Alice", "login": "alice", "senha": "nao-exibir-123"}
        )
        for route in ("/usuarios", "/usuarios/12345678901", "/usuarios/12345678901/editar"):
            response = self.client.get(route)
            self.assertNotIn(b"nao-exibir-123", response.data)

    def test_duplicate_route_is_handled_with_flash(self) -> None:
        data = {"cpf": "12345678901", "nome": "Alice", "login": "alice"}
        self.client.post("/usuarios/novo", data=data)
        response = self.client.post("/usuarios/novo", data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("já existe".encode(), response.data.lower())

    def test_unknown_detail_returns_friendly_404(self) -> None:
        response = self.client.get("/usuarios/999")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"solicitado n\xc3\xa3o existe", response.data)


if __name__ == "__main__":
    unittest.main()
