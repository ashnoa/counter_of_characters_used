import csv
import tempfile
import unittest
from pathlib import Path

from encode_text_to_words import EOF_WORD, NEWLINE_WORD, encode_text, format_dw, load_mapping


class EncodeTextToWordsTest(unittest.TestCase):
    def test_encode_text_uses_bank_upper_4_bits_and_index_lower_12_bits(self):
        mapping = {"あ": 0x000A, "い": 0x100B}

        self.assertEqual(encode_text("あい", mapping), [0x000A, 0x100B, EOF_WORD])

    def test_encode_text_uses_special_words_for_newline_and_eof(self):
        mapping = {"あ": 0x000A}

        self.assertEqual(encode_text("あ\n", mapping), [0x000A, NEWLINE_WORD, EOF_WORD])

    def test_encode_text_rejects_unmapped_character(self):
        with self.assertRaisesRegex(ValueError, "no mapping"):
            encode_text("未", {})

    def test_format_dw_outputs_hex_words(self):
        output = format_dw([0x0000, 0x100A, NEWLINE_WORD, EOF_WORD], values_per_line=2)

        self.assertEqual(output, "dw $0000, $100A\ndw $FFFE, $FFFF")

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
