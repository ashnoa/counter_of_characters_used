import csv
import io
import tempfile
import unittest
from pathlib import Path

from add_bank_index_columns import (
    add_bank_index_columns,
    bank_index_for_row,
    is_newline_row,
    read_csv,
    write_csv,
)


class AddBankIndexColumnsTest(unittest.TestCase):
    def test_bank_index_for_row_uses_383_rows_per_bank(self):
        self.assertEqual(bank_index_for_row(0), (1, 0))
        self.assertEqual(bank_index_for_row(254), (1, 254))
        self.assertEqual(bank_index_for_row(255), (1, 256))
        self.assertEqual(bank_index_for_row(381), (1, 382))
        self.assertEqual(bank_index_for_row(382), (2, 0))
        self.assertEqual(bank_index_for_row(383), (2, 1))

    def test_adds_columns_after_existing_columns(self):
        fieldnames = ["character", "count"]
        rows = [{"character": "あ", "count": "2"}, {"character": "い", "count": "1"}]

        output_fieldnames, output_rows = add_bank_index_columns(rows, fieldnames)

        self.assertEqual(
            output_fieldnames,
            ["character", "count", "mode", "bank", "index", "check"],
        )
        self.assertEqual(
            output_rows,
            [
                {
                    "character": "あ",
                    "count": "2",
                    "mode": "8000",
                    "bank": "1",
                    "index": "0",
                    "check": "1",
                },
                {
                    "character": "い",
                    "count": "1",
                    "mode": "8000",
                    "bank": "1",
                    "index": "1",
                    "check": "1",
                },
            ],
        )

    def test_skips_newline_rows_before_assigning_indexes(self):
        fieldnames = ["character", "display", "count"]
        rows = [
            {"character": "あ", "display": "あ", "count": "1"},
            {"character": "\n", "display": "<LF>", "count": "1"},
            {"character": "い", "display": "い", "count": "1"},
        ]

        _, output_rows = add_bank_index_columns(rows, fieldnames)

        self.assertEqual([row["character"] for row in output_rows], ["あ", "い"])
        self.assertEqual([row["index"] for row in output_rows], ["0", "1"])

    def test_detects_newline_rows(self):
        self.assertTrue(is_newline_row({"character": "\n", "display": "<LF>"}))
        self.assertTrue(is_newline_row({"character": "", "display": "<LF>"}))
        self.assertFalse(is_newline_row({"character": "あ", "display": "あ"}))

    def test_replaces_existing_generated_columns(self):
        fieldnames = ["character", "mode", "bank", "index", "check"]
        rows = [
            {
                "character": "あ",
                "mode": "old",
                "bank": "9",
                "index": "9",
                "check": "0",
            }
        ]

        output_fieldnames, output_rows = add_bank_index_columns(rows, fieldnames)

        self.assertEqual(output_fieldnames, ["character", "mode", "bank", "index", "check"])
        self.assertEqual(output_rows[0]["mode"], "8000")
        self.assertEqual(output_rows[0]["bank"], "1")
        self.assertEqual(output_rows[0]["index"], "0")
        self.assertEqual(output_rows[0]["check"], "1")

    def test_read_and_write_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text("character,count\nあ,2\n", encoding="utf-8")

            fieldnames, rows = read_csv(path)

        self.assertEqual(fieldnames, ["character", "count"])
        self.assertEqual(rows, [{"character": "あ", "count": "2"}])

        output = io.StringIO()
        original_stdout = None
        try:
            import sys

            original_stdout = sys.stdout
            sys.stdout = output
            write_csv(None, ["character", "count"], rows)
        finally:
            if original_stdout is not None:
                sys.stdout = original_stdout

        self.assertEqual(output.getvalue(), "character,count\r\nあ,2\r\n")


if __name__ == "__main__":
    unittest.main()
