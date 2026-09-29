from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import ETL
import setup_banco


class SQLParserTests(unittest.TestCase):
    def test_null_and_quoted_null_are_distinct(self) -> None:
        self.assertIsNone(ETL.parse_sql_literal("NULL"))
        self.assertIsNone(ETL.parse_sql_literal(" null "))
        self.assertEqual(ETL.parse_sql_literal("'NULL'"), "NULL")

    def test_string_with_comma_and_apostrophe(self) -> None:
        parsed = ETL.parse_insert_statement(
            "INSERT INTO universidade.projeto VALUES (1, 'D''Ávila, etapa 1')"
        )
        self.assertIsNotNone(parsed)
        _, document = parsed
        self.assertEqual(document["descricao"], "D'Ávila, etapa 1")

    def test_postgres_array_with_quotes_commas_and_null(self) -> None:
        value = ETL.parse_postgres_array('{"primeiro,valor", "segundo", NULL}')
        self.assertEqual(value, ["primeiro,valor", "segundo", None])

    def test_dates_are_normalized_to_datetime(self) -> None:
        self.assertEqual(
            ETL.convert_value("1972/08/3", "date"),
            datetime(1972, 8, 3),
        )
        self.assertEqual(
            ETL.convert_value("2026-07-14", "date"),
            datetime(2026, 7, 14),
        )

    def test_decimals_do_not_become_float(self) -> None:
        value = ETL.parse_sql_literal("10.125")
        self.assertEqual(value, Decimal("10.125"))
        self.assertNotIsInstance(value, float)

    def test_lowercase_multiline_insert(self) -> None:
        result = ETL.process_sql(
            """
            insert into universidade.projeto
                values (1, 'Projeto em várias linhas');
            """
        )
        self.assertEqual(result.reports["projeto"].lidos, 1)
        self.assertEqual(result.reports["projeto"].validos, 1)

    def test_semicolon_inside_string_does_not_split_statement(self) -> None:
        sql = "INSERT INTO universidade.projeto VALUES (1, 'etapa 1; etapa 2');"
        statements = ETL.split_sql_statements(sql)
        self.assertEqual(len(statements), 1)
        result = ETL.process_sql(sql)
        self.assertEqual(result.valid_documents["projeto"][0]["descricao"], "etapa 1; etapa 2")

    def test_dry_runs_do_not_create_mongo_client(self) -> None:
        sql = "INSERT INTO universidade.projeto VALUES (1, 'offline');"
        with tempfile.TemporaryDirectory() as directory:
            dump_path = Path(directory) / "dump.sql"
            dump_path.write_text(sql, encoding="utf-8")
            with mock.patch(
                "db.create_mongo_client",
                side_effect=AssertionError("dry-run tentou conectar"),
            ):
                with redirect_stdout(StringIO()):
                    self.assertEqual(ETL.main(["--input", str(dump_path)]), 0)
                    self.assertEqual(setup_banco.main([]), 0)


if __name__ == "__main__":
    unittest.main()
