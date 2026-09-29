from __future__ import annotations

from pathlib import Path
import unittest

import ETL
from schemas_mongodb import COLLECTION_NAMES, COLLECTION_SPECS


EXPECTED_COLLECTIONS = {
    "usuario",
    "professor",
    "departamento",
    "curso",
    "estudante",
    "vinculo",
    "projeto",
    "plano",
    "disciplina",
    "semestre",
    "sala",
    "horario",
    "turma",
    "leciona",
    "alocacao",
    "cursa",
}


class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.result = ETL.load_sql_dump(root / "universidade-dump-engdados.sql")

    def test_all_16_collections_have_schema_and_report(self) -> None:
        self.assertEqual(set(COLLECTION_NAMES), EXPECTED_COLLECTIONS)
        self.assertEqual(set(ETL.COLUMN_SPECS), EXPECTED_COLLECTIONS)
        self.assertEqual(set(self.result.reports), EXPECTED_COLLECTIONS)
        for name, spec in COLLECTION_SPECS.items():
            self.assertIn("validator", spec, name)
            self.assertIn("indexes", spec, name)
            required = set(spec["validator"]["$jsonSchema"]["required"])
            self.assertTrue(set(spec["primary_key"]).issubset(required), name)

    def test_dump_reads_every_table_that_has_insert_data(self) -> None:
        expected_non_empty = EXPECTED_COLLECTIONS - {"sala", "horario", "alocacao"}
        read_non_empty = {
            name for name, report in self.result.reports.items() if report.lidos > 0
        }
        self.assertEqual(read_non_empty, expected_non_empty)

    def test_department_chief_updates_are_processed(self) -> None:
        self.assertEqual(self.result.chief_updates, 4)
        departments = {
            document["cod_depto"]: document
            for document in self.result.documents["departamento"]
        }
        self.assertEqual(departments["DCOMP"]["chefe"], "P100")
        self.assertEqual(departments["DMA"]["chefe"], "P600")
        self.assertEqual(departments["DECAT"]["chefe"], "P1100")
        self.assertEqual(departments["DFI"]["chefe"], "P1400")

    def test_duplicate_detection(self) -> None:
        result = ETL.process_sql(
            """
            INSERT INTO universidade.projeto VALUES (1, 'primeiro');
            INSERT INTO universidade.projeto VALUES (1, 'segundo');
            """
        )
        self.assertEqual(result.reports["projeto"].duplicados, 1)
        self.assertEqual(result.reports["projeto"].validos, 1)
        self.assertTrue(result.has_blocking_issues)

    def test_missing_reference_detection(self) -> None:
        result = ETL.process_sql(
            """
            INSERT INTO universidade.professor
            VALUES ('P1', '123', NULL, NULL, NULL, NULL, NULL);
            """
        )
        self.assertEqual(result.reports["professor"].referencias_ausentes, 1)
        self.assertEqual(result.reports["professor"].invalidos, 1)
        self.assertEqual(result.reports["professor"].validos, 0)

    def test_current_dump_has_no_blocking_data_issue(self) -> None:
        self.assertFalse(self.result.has_blocking_issues, self.result.errors)


if __name__ == "__main__":
    unittest.main()
