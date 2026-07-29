import csv
import tempfile
import unittest
from pathlib import Path

from encode_text_to_words import (
    EOF_WORD,
    NEWLINE_WORD,
    encode_text,
    format_dw,
    load_mapping,
    output_path_for_page,
    split_pages,
)


class EncodeTextToWordsTest(unittest.TestCase):
    def test_encode_text_uses_bank_upper_4_bits_and_index_lower_12_bits(self):
        mapping = {"あ": 0x000A, "い": 0x100B}

        self.assertEqual(encode_text("あい", mapping), [0x000A, 0x100B, EOF_WORD])

    def test_encode_text_uses_special_words_for_newline_and_eof(self):
        mapping = {"あ": 0x000A}

        self.assertEqual(encode_text("あ\n", mapping), [0x000A, NEWLINE_WORD, EOF_WORD])

    def test_encode_text_supports_misaki_extension_characters_from_mapping(self):
        mapping = {"Ⅰ": 0x1000, "Ⅱ": 0x1001, "Ⅲ": 0x1002}

        self.assertEqual(
            encode_text("ⅠⅡⅢ", mapping),
            [0x1000, 0x1001, 0x1002, EOF_WORD],
        )

    def test_encode_text_rejects_unmapped_character(self):
        with self.assertRaisesRegex(ValueError, "no mapping"):
            encode_text("未", {})

    def test_format_dw_outputs_hex_words(self):
        output = format_dw([0x0000, 0x100A, NEWLINE_WORD, EOF_WORD], values_per_line=2)

        self.assertEqual(output, "dw $0000, $100A\ndw $FFFE, $FFFF")

    def test_split_pages_on_page_break_marker_line(self):
        self.assertEqual(split_pages("あ\n[改ページ]\nい\n"), ["あ\n", "い\n"])

    def test_split_pages_keeps_page_break_text_inside_a_line(self):
        self.assertEqual(split_pages("あ[改ページ]\n"), ["あ[改ページ]\n"])

    def test_output_path_for_page_adds_page_index(self):
        self.assertEqual(output_path_for_page(Path("text.asm"), 0), Path("text_0.asm"))
        self.assertEqual(output_path_for_page(Path("text.asm"), 1), Path("text_1.asm"))

    def test_load_mapping_from_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mapping.csv"
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["character", "bank", "index"])
                writer.writeheader()
                writer.writerow({"character": "あ", "bank": "0", "index": "10"})
                writer.writerow({"character": "い", "bank": "1", "index": "11"})

            self.assertEqual(load_mapping(path), {"あ": 0x000A, "い": 0x100B})


if __name__ == "__main__":
    unittest.main()
