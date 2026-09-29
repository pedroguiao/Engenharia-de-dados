from __future__ import annotations

from unittest import mock
import unittest

import mongomock

from repositories import create_repository_bundle
from services import (
    DeleteBlockedError,
    DuplicateError,
    NotFoundError,
    ReferenceError,
    UniversityService,
)


class CrudServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = mongomock.MongoClient()
        self.database = self.client["test_universidade"]
        self.repositories = create_repository_bundle(self.database, mode="mock")
        self.service = UniversityService(self.repositories)

    def user_data(self, cpf: str = "12345678901", login: str = "alice") -> dict:
        return {
            "cpf": cpf,
            "nome": "Alice Exemplo",
            "data_nascimento": "2000-01-02",
            "email": "alice@example.org, alice@universidade.br",
            "telefone": "79999999999",
            "login": login,
            "senha": "segredo-local",
        }

    def course_data(self, name: str = "Computação", shift: str = "Noturno") -> dict:
        return {
            "nome": name,
            "grau": "Bacharelado",
            "turno": shift,
            "campus": "São Cristóvão",
            "nivel": "Graduação",
        }

    def create_user_student_course(self) -> tuple[dict, dict, dict]:
        user = self.service.create_user(self.user_data())
        student = self.service.create_student(
            {
                "mat_estudante": "E100",
                "cpf": user["cpf"],
                "MC": "7.5",
                "ano_ingresso": "2026",
            }
        )
        course = self.service.create_course(self.course_data())
        return user, student, course

    def test_complete_user_crud_and_password_rules(self) -> None:
        created = self.service.create_user(self.user_data())
        self.assertEqual(created["nome"], "Alice Exemplo")
        self.assertNotIn("senha", created)
        self.assertNotIn("senha", self.service.get_user(created["cpf"]))
        self.assertNotIn("senha", self.service.list_users()[0])

        stored_password = self.repositories.usuarios.get(created["cpf"])["senha"]
        updated = self.service.update_user(
            created["cpf"],
            {"nome": "Alice Atualizada", "login": "alice.nova", "senha": ""},
        )
        self.assertEqual(updated["nome"], "Alice Atualizada")
        self.assertEqual(
            self.repositories.usuarios.get(created["cpf"])["senha"], stored_password
        )
        self.service.delete_user(created["cpf"])
        with self.assertRaises(NotFoundError):
            self.service.get_user(created["cpf"])

    def test_duplicate_cpf_and_login(self) -> None:
        self.service.create_user(self.user_data())
        with self.assertRaises(DuplicateError):
            self.service.create_user(self.user_data(login="outro"))
        with self.assertRaises(DuplicateError):
            self.service.create_user(self.user_data(cpf="99999999999"))

    def test_complete_student_crud_and_duplicate_rules(self) -> None:
        first = self.service.create_user(self.user_data())
        second = self.service.create_user(self.user_data("99999999999", "bob"))
        student = self.service.create_student(
            {"mat_estudante": "E100", "cpf": first["cpf"], "MC": "6.5"}
        )
        self.assertEqual(self.service.get_student("E100")["cpf"], first["cpf"])
        updated = self.service.update_student(
            "E100", {"cpf": second["cpf"], "MC": "8.0", "ano_ingresso": 2025}
        )
        self.assertEqual(updated["cpf"], second["cpf"])
        with self.assertRaises(DuplicateError):
            self.service.create_student(
                {"mat_estudante": "E100", "cpf": first["cpf"]}
            )
        with self.assertRaises(DuplicateError):
            self.service.create_student(
                {"mat_estudante": "E200", "cpf": second["cpf"]}
            )
        self.service.delete_student("E100")
        with self.assertRaises(NotFoundError):
            self.service.get_student("E100")

    def test_student_requires_existing_user(self) -> None:
        with self.assertRaises(ReferenceError):
            self.service.create_student(
                {"mat_estudante": "E404", "cpf": "40440440404"}
            )

    def test_complete_course_crud_and_duplicate_rule(self) -> None:
        course = self.service.create_course(self.course_data())
        self.assertEqual(len(self.service.list_courses()), 1)
        self.assertEqual(self.service.get_course(course["idCurso"])["nome"], "Computação")
        updated = self.service.update_course(
            course["idCurso"], {**self.course_data(name="Engenharia"), "turno": "Matutino"}
        )
        self.assertEqual(updated["nome"], "Engenharia")
        with self.assertRaises(DuplicateError):
            self.service.create_course({**self.course_data(name="Engenharia"), "turno": "Matutino"})
        self.service.delete_course(course["idCurso"])
        with self.assertRaises(NotFoundError):
            self.service.get_course(course["idCurso"])

    def test_complete_link_crud_duplicate_and_individual_delete(self) -> None:
        _, student, first_course = self.create_user_student_course()
        second_course = self.service.create_course(self.course_data("Sistemas", "Vespertino"))
        first = self.service.create_link(
            {
                "mat_estudante": student["mat_estudante"],
                "idCurso": first_course["idCurso"],
                "status": "Ativo",
            }
        )
        second = self.service.create_link(
            {
                "mat_estudante": student["mat_estudante"],
                "idCurso": second_course["idCurso"],
                "status": "Ativo",
            }
        )
        with self.assertRaises(DuplicateError):
            self.service.create_link(
                {
                    "mat_estudante": student["mat_estudante"],
                    "idCurso": first_course["idCurso"],
                    "status": "Ativo",
                }
            )
        updated = self.service.update_link(
            first["idVinculo"],
            {
                "mat_estudante": student["mat_estudante"],
                "idCurso": first_course["idCurso"],
                "status": "Graduado",
                "data_saida": "2026-12-20",
            },
        )
        self.assertEqual(updated["status"], "Graduado")
        self.service.delete_link(first["idVinculo"])
        self.assertIsNotNone(self.repositories.vinculos.get(second["idVinculo"]))
        self.assertIsNotNone(self.repositories.estudantes.get(student["mat_estudante"]))
        self.assertIsNotNone(self.repositories.cursos.get(first_course["idCurso"]))

    def test_link_requires_existing_student_and_course(self) -> None:
        course = self.service.create_course(self.course_data())
        with self.assertRaises(ReferenceError):
            self.service.create_link(
                {"mat_estudante": "E404", "idCurso": course["idCurso"], "status": "Ativo"}
            )
        user = self.service.create_user(self.user_data())
        student = self.service.create_student(
            {"mat_estudante": "E100", "cpf": user["cpf"]}
        )
        with self.assertRaises(ReferenceError):
            self.service.create_link(
                {"mat_estudante": student["mat_estudante"], "idCurso": 999, "status": "Ativo"}
            )

    def test_referenced_course_student_and_user_deletes_are_blocked(self) -> None:
        user, student, course = self.create_user_student_course()
        self.service.create_link(
            {"mat_estudante": student["mat_estudante"], "idCurso": course["idCurso"], "status": "Ativo"}
        )
        with self.assertRaises(DeleteBlockedError):
            self.service.delete_course(course["idCurso"])
        with self.assertRaises(DeleteBlockedError):
            self.service.delete_student(student["mat_estudante"])
        with self.assertRaises(DeleteBlockedError):
            self.service.delete_user(user["cpf"])

    def test_optional_fields_are_accepted(self) -> None:
        user = self.service.create_user({"cpf": "1", "nome": "Sem opcionais"})
        self.assertIsNone(user["email"])
        student = self.service.create_student(
            {"mat_estudante": "E1", "cpf": user["cpf"]}
        )
        self.assertIsNone(student["MC"])
        course = self.service.create_course(
            {"nome": "Curso mínimo", "turno": "Turno Indefinido"}
        )
        self.assertIsNone(course["campus"])

    def test_admission_rolls_back_when_last_insert_fails(self) -> None:
        course = self.service.create_course(self.course_data())
        with mock.patch.object(
            self.repositories.vinculos,
            "insert",
            side_effect=RuntimeError("falha simulada"),
        ):
            with self.assertRaises(RuntimeError):
                self.service.admit(
                    self.user_data(),
                    {"mat_estudante": "E100", "ano_ingresso": 2026},
                    {"idCurso": course["idCurso"], "status": "Ativo"},
                )
        self.assertEqual(self.repositories.usuarios.count(), 0)
        self.assertEqual(self.repositories.estudantes.count(), 0)
        self.assertEqual(self.repositories.vinculos.count(), 0)
        self.assertEqual(self.repositories.cursos.count(), 1)


if __name__ == "__main__":
    unittest.main()
